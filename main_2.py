import os
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='templates', static_folder='static')

current_data = {"players": {}, "round": {}}
resultados = {}

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
    return jsonify({"resultados": resultados})

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    mesa_id = str(data.get("mesa_id"))
    resultado = data.get("resultado", "")

    # Se já existe um resultado final para esta mesa e não é "Nenhum resultado reportado" nem "Jogando"
    if mesa_id in resultados and resultados[mesa_id] != "Jogando" and resultados[mesa_id] != "Nenhum resultado reportado":
        return jsonify({"message": "Essa mesa já possui um resultado final. Use 'Reporte Incorreto' para alterar."}), 400

    resultado_final = convert_outcome_with_names(resultado, mesa_id)
    resultados[mesa_id] = resultado_final
    print(f"Resultado da Mesa {mesa_id}: {resultado_final}")

    update_current_data_outcome(mesa_id, resultado_final)

    return jsonify({
        "message": f"Resultado da Mesa {mesa_id} foi reportado como '{resultado_final}'",
        "final_outcome": resultado_final
    })


@app.route("/clear-report", methods=["POST"])
def clear_report():
    data = request.get_json()
    mesa_id = str(data.get("mesa_id"))
    if mesa_id in resultados:
        del resultados[mesa_id]
    print(f"Reporte da Mesa {mesa_id} foi removido.")
    return jsonify({"message": f"Reporte da Mesa {mesa_id} foi removido."})

@app.route("/limpar-resultados", methods=["POST"])
def limpar_resultados():
    resultados.clear()
    print("Todos os resultados foram removidos.")
    return jsonify({"message": "Todos os resultados foram removidos."})

@app.route("/end-round", methods=["POST"])
def end_round():
    # Aqui você pode adicionar lógica para encerrar a rodada se necessário.
    # Por exemplo, limpar resultados, marcar estado da rodada, etc.
    # Caso não haja lógica, apenas retorna sucesso.
    print("Rodada finalizada pelo operador.")
    return jsonify({"message": "Rodada finalizada!"}), 200


def convert_outcome_with_names(resultado, mesa_id):
    if resultado.startswith("Vitória Jogador 1"):
        player_name = get_player_name_for_position(mesa_id, 1)
        if player_name:
            return f"Vitória de {player_name}"
    elif resultado.startswith("Vitória Jogador 2"):
        player_name = get_player_name_for_position(mesa_id, 2)
        if player_name:
            return f"Vitória de {player_name}"
    return resultado

def get_player_name_for_position(mesa_id, position):
    tables_data = extract_latest_tables(current_data)
    if mesa_id in tables_data:
        info = tables_data[mesa_id]
        return info.get('player1' if position == 1 else 'player2', None)
    return None

def update_current_data_outcome(mesa_id, final_outcome):
    rounds = current_data.get("round", {})
    if not rounds:
        return
    round_nums = [int(r) for r in rounds.keys()]
    if not round_nums:
        return
    latest_round = max(round_nums)
    divisions = rounds[str(latest_round)]
    division_keys = list(divisions.keys())
    if not division_keys:
        return
    current_division = division_keys[0]
    tablesData = divisions[current_division]['table']

    if mesa_id in tablesData:
        tablesData[mesa_id]['outcome'] = final_outcome

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
    tablesData = divisions[current_division]['table']
    return tablesData
