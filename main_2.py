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
    if str_mesa_id in votes:
        v = votes[str_mesa_id]
        player1_id = data.get('player1_id')
        player2_id = data.get('player2_id')

        p1_vote = v.get(player1_id)
        p2_vote = v.get(player2_id)

        # Precisamos do nome do jogador. Está em current_data['pins'][player_id]['name']
        pins_data = current_data.get('pins', {})

        # Função auxiliar para obter o nome a partir do player_id
        def get_player_name(pid):
            info = pins_data.get(pid)
            return info['name'] if info else "Jogador Desconhecido"

        if p1_vote and p2_vote:
            if p1_vote == p2_vote:
                resultados[str_mesa_id] = p1_vote
            else:
                partial_info[str_mesa_id] = "Votos divergentes"
        elif p1_vote and not p2_vote:
            # Falta voto do segundo jogador
            player2_name = get_player_name(player2_id)
            partial_info[str_mesa_id] = f"Aguardando voto de {player2_name}"
        elif p2_vote and not p1_vote:
            # Falta voto do primeiro jogador
            player1_name = get_player_name(player1_id)
            partial_info[str_mesa_id] = f"Aguardando voto de {player1_name}"
        else:
            partial_info[str_mesa_id] = "Nenhum voto ainda"
    else:
        partial_info[str_mesa_id] = "Nenhum voto ainda"


@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    mesa_id = str(data.get("mesa_id"))
    resultado = data.get("resultado", "")
    pin = data.get("pin")

    if not pin:
        return jsonify({"message": "PIN não fornecido."}), 400

    player_id, player_name = find_player_id_by_pin(pin)
    if player_id is None:
        return jsonify({"message": "PIN inválido."}), 403

    # Verificar se esse player_id pertence à mesa
    tables_data = extract_latest_tables(current_data)
    if mesa_id not in tables_data:
        return jsonify({"message": "Mesa não encontrada."}), 400

    info = tables_data[mesa_id]
    player1_id = info.get('player1_id')
    player2_id = info.get('player2_id')

    # Se o player_id não é player1_id nem player2_id, não pode reportar
    if player_id not in [player1_id, player2_id]:
        return jsonify({"message": "Este jogador não pertence a esta mesa."}), 403

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
    print(f"Reporte da Mesa {mesa_id} foi removido.")
    return jsonify({"message": f"Reporte da Mesa {mesa_id} foi removido."})

@app.route("/limpar-resultados", methods=["POST"])
def limpar_resultados():
    resultados.clear()
    votes.clear()
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
    tables_data = divisions[current_division]['table']
    return tables_data

def convert_outcome_with_names(resultado, mesa_id):
    return resultado

def find_player_id_by_pin(pin):
    # Procura no current_data['pins'] quem tem esse PIN
    pins = current_data.get('pins', {})
    for pid, info in pins.items():
        if info['pin'] == pin:
            return pid, info['name']
    return None, None
