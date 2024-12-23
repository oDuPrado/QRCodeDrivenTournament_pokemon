import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='templates', static_folder='static')

current_data = {"players": {}, "round": {}, "pins": {}}
resultados = {}
votes = {}  

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/mesa/<int:mesa_id>")
def mesa(mesa_id):
    return render_template("mesa.html", mesa_id=mesa_id)

@app.route("/report.html")
def report_page():
    return render_template("report.html")

@app.route("/get-data", methods=["GET"])
def get_data():
    """Retorna todo o current_data para que o index.html e mesa.html possam enxergar
       os outcomes atualizados (ex: 'Vitória de Fulano')."""
    return jsonify(current_data)

@app.route("/update-data", methods=["POST"])
def update_data():
    global current_data
    data = request.get_json()
    if data:
        current_data = data
        print("Dados atualizados com sucesso no servidor online!")
        return jsonify({"message": "Dados atualizados no servidor online."}), 200
    return jsonify({"message": "Nenhum dado recebido."}), 400

@app.route("/get-resultados", methods=["GET"])
def get_resultados():
    """Retorna as mesas finalizadas e parciais para report.html."""
    final_info = {}
    partial_info = {}
    build_result_info(final_info, partial_info)
    return jsonify({"final": final_info, "partial": partial_info})

def build_result_info(final_info, partial_info):
    tables_data = extract_latest_tables(current_data)
    for mesa_id, data in tables_data.items():
        str_mesa_id = str(mesa_id)
        if str_mesa_id in resultados:
            final_info[str_mesa_id] = resultados[str_mesa_id]
        else:
            handle_partial_result(str_mesa_id, data, partial_info)

def handle_partial_result(str_mesa_id, data, partial_info):
    """Verifica se já temos votos parciais para a mesa; em caso afirmativo,
       checa se ambos votaram, se há divergência, ou se falta alguém votar."""
    if str_mesa_id not in votes:
        partial_info[str_mesa_id] = "Nenhum voto ainda"
        return

    v = votes[str_mesa_id]
    player1_id = data.get('player1_id')
    player2_id = data.get('player2_id')

    p1_vote = v.get(player1_id)
    p2_vote = v.get(player2_id)

    pins_data = current_data.get('pins', {})

    def get_player_name(pid):
        info = pins_data.get(pid)
        return info['name'] if info else "Jogador Desconhecido"

    # Se ambos votaram
    if p1_vote and p2_vote:
        if p1_vote == p2_vote:
            resultados[str_mesa_id] = p1_vote
        else:
            partial_info[str_mesa_id] = "Votos divergentes"
        return

    # Se somente player1 votou
    if p1_vote and not p2_vote:
        partial_info[str_mesa_id] = f"Aguardando voto de {get_player_name(player2_id)}"
        return

    # Se somente player2 votou
    if p2_vote and not p1_vote:
        partial_info[str_mesa_id] = f"Aguardando voto de {get_player_name(player1_id)}"
        return

    # Caso nenhum tenha votado
    partial_info[str_mesa_id] = "Nenhum voto ainda"

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    mesa_id = str(data.get("mesa_id"))
    resultado = data.get("resultado", "")
    pin = data.get("pin")

    if not pin:
        return jsonify({"message": "PIN não fornecido."}), 400

    player_id, _ = find_player_id_by_pin(pin)
    if player_id is None:
        return jsonify({"message": "PIN inválido."}), 403

    # Verificar se esse player_id pertence à mesa
    tables_data = extract_latest_tables(current_data)
    if mesa_id not in tables_data:
        return jsonify({"message": "Mesa não encontrada."}), 400

    info = tables_data[mesa_id]
    player1_id = info.get('player1_id')
    player2_id = info.get('player2_id')

    if player_id not in [player1_id, player2_id]:
        return jsonify({"message": "Este jogador não pertence a esta mesa."}), 403

    # Converte "Vitória Jogador 1" -> "Vitória de Fulano"
    #           "Vitória Jogador 2" -> "Vitória de Cicrano"
    resultado_final = convert_outcome_with_names(resultado, mesa_id)

    if mesa_id not in votes:
        votes[mesa_id] = {}

    votes[mesa_id][player_id] = resultado_final

    p1_vote = votes[mesa_id].get(player1_id)
    p2_vote = votes[mesa_id].get(player2_id)
    if p1_vote and p2_vote:
        if p1_vote == p2_vote:
            resultados[mesa_id] = p1_vote
            print(f"Resultado final da Mesa {mesa_id}: {p1_vote}")
            # Atualiza current_data para que index.html também veja a mudança
            update_current_data_outcome(mesa_id, p1_vote)
            return jsonify({
                "message": f"Voto registrado. Resultado final: {p1_vote}",
                "final_outcome": p1_vote
            })
        else:
            return jsonify({
                "message": "Voto registrado, mas há divergência entre os jogadores.",
                "final_outcome": None
            })
    else:
        return jsonify({
            "message": "Voto registrado, aguardando outro jogador.",
            "final_outcome": None
        })

@app.route("/clear-report", methods=["POST"])
def clear_report():
    data = request.get_json()
    mesa_id = str(data.get("mesa_id"))
    if mesa_id in resultados:
        del resultados[mesa_id]
    if mesa_id in votes:
        del votes[mesa_id]
    # Se quiser resetar o outcome no current_data, basta setar para "Jogando" novamente
    reset_current_data_outcome(mesa_id)
    print(f"Reporte da Mesa {mesa_id} foi removido.")
    return jsonify({"message": f"Reporte da Mesa {mesa_id} foi removido."})

@app.route("/limpar-resultados", methods=["POST"])
def limpar_resultados():
    resultados.clear()
    votes.clear()
    # Opcional: resetar todos os outcomes
    reset_all_outcomes_in_current_data()
    print("Todos os resultados e votos foram removidos.")
    return jsonify({"message": "Todos os resultados foram removidos."})

def extract_latest_tables(data):
    rounds = data.get("round", {})
    if not rounds:
        return {}
    round_nums = [int(r) for r in rounds.keys()]
    if not round_nums:
        return {}
    latest_round = max(round_nums)
    divisions = rounds[str(latest_round)]
    division_keys = list(divisions.keys())
    current_division = division_keys[0]
    return divisions[current_division]['table']

def convert_outcome_with_names(resultado, mesa_id):
    """Transforma 'Vitória Jogador 1' em 'Vitória de <nomeP1>' e
       'Vitória Jogador 2' em 'Vitória de <nomeP2>', caso contrário retorna como está."""
    # Precisamos achar player1_id, player2_id, e nomes:
    tables_data = extract_latest_tables(current_data)
    table_info = tables_data.get(mesa_id)
    if not table_info:
        return resultado  # Se não achar mesa, retorna inalterado

    player1_id = table_info.get('player1_id')
    player2_id = table_info.get('player2_id')

    p1_name = current_data['pins'].get(player1_id, {}).get('name', 'Jogador 1')
    p2_name = current_data['pins'].get(player2_id, {}).get('name', 'Jogador 2')

    if resultado.startswith("Vitória Jogador 1"):
        return f"Vitória de {p1_name}"
    elif resultado.startswith("Vitória Jogador 2"):
        return f"Vitória de {p2_name}"
    return resultado

def find_player_id_by_pin(pin):
    """Retorna (player_id, nome_do_jogador) ou (None, None) se não encontrado."""
    pins = current_data.get('pins', {})
    for pid, info in pins.items():
        if info['pin'] == pin:
            return pid, info['name']
    return None, None

def update_current_data_outcome(mesa_id, final_outcome):
    """Atualiza o campo 'outcome' em current_data para refletir a vitória de Fulano
       e permitir que a index.html exiba corretamente."""
    tables_data = extract_latest_tables(current_data)
    if mesa_id in tables_data:
        tables_data[mesa_id]['outcome'] = final_outcome

def reset_current_data_outcome(mesa_id):
    """Opcional: se o operador quiser 'limpar' a mesa, retorna para 'Jogando'."""
    tables_data = extract_latest_tables(current_data)
    if mesa_id in tables_data:
        tables_data[mesa_id]['outcome'] = "Jogando"

def reset_all_outcomes_in_current_data():
    """Define 'Jogando' para todas as mesas, caso limpem todos resultados."""
    tables_data = extract_latest_tables(current_data)
    for key in tables_data:
        tables_data[key]['outcome'] = "Jogando"
