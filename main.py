import asyncio
import os
import qrcode
import threading
import requests
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json

app = Flask(__name__, template_folder='templates', static_folder='static')

outcome = {
    0: "Jogando",
    1: "Vitória Jogador 1",
    2: "Vitória Jogador 2",
    3: "Empate",
    5: "BY",
    10: "Derrota Dupla",
}

category = {
    'Junior': 0,
    'Senior': 1,
    'Master': 2,
}

# Variáveis globais do main_1
resultados = {}
last_processed_data = None

# URL do servidor online (main_2 no PythonAnywhere)
ONLINE_SERVER_URL = "https://DuPrado.pythonanywhere.com"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/mesa/<int:mesa_id>")
def mesa(mesa_id):
    return render_template("mesa.html", mesa_id=mesa_id)

@app.route("/report.html")
def report_page():
    return render_template("report.html")

@app.route("/get-resultados", methods=["GET"])
def get_resultados():
    return jsonify({"resultados": resultados})

def get_mesa_players(mesa_id):
    if not last_processed_data:
        return None, None
    round_data = last_processed_data.get('round', {})
    if not round_data:
        return None, None
    
    round_nums = [int(r) for r in round_data.keys()]
    if not round_nums:
        return None, None
    latest_round = max(round_nums)
    division_data = round_data[str(latest_round)]
    division_keys = list(division_data.keys())
    current_division = division_keys[0]
    tables = division_data[current_division]['table']

    mesa_info = tables.get(str(mesa_id))
    if not mesa_info:
        return None, None
    player1 = mesa_info['player1']
    player2 = mesa_info['player2']
    return player1, player2

def convert_outcome(resultado, mesa_id):
    if resultado.startswith("Vitória Jogador 1"):
        p1, _ = get_mesa_players(mesa_id)
        if p1:
            return f"Vitória de {p1}"
    elif resultado.startswith("Vitória Jogador 2"):
        _, p2 = get_mesa_players(mesa_id)
        if p2:
            return f"Vitória de {p2}"
    return resultado

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    mesa_id = data.get("mesa_id")
    resultado = data.get("resultado")
    current = resultados.get(mesa_id, "Jogando")
    if current != "Jogando" and current != "Nenhum resultado reportado":
        return jsonify({"message": "Essa mesa já possui um resultado final. Use 'Reporte Incorreto' para alterar."}), 400

    resultado_final = convert_outcome(resultado, mesa_id)
    resultados[mesa_id] = resultado_final
    print(f"Resultado da Mesa {mesa_id}: {resultado_final}")
    return jsonify({"message": f"Resultado da Mesa {mesa_id} foi reportado como '{resultado_final}'"})

@app.route("/clear-report", methods=["POST"])
def clear_report():
    data = request.get_json()
    mesa_id = data.get("mesa_id")
    if mesa_id in resultados:
        del resultados[mesa_id]
    print(f"Reporte da Mesa {mesa_id} foi removido.")
    return jsonify({"message": f"Reporte da Mesa {mesa_id} foi removido."})

@app.route("/limpar-resultados", methods=["POST"])
def limpar_resultados():
    resultados.clear()
    print("Todos os resultados foram removidos.")
    return jsonify({"message": "Todos os resultados foram removidos."})

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

def generate_qr_codes(base_url, num_mesas):
    qr_code_dir = "qrcodes"
    os.makedirs(qr_code_dir, exist_ok=True)
    for mesa_id in range(1, num_mesas + 1):
        url = f"{base_url}/mesa/{mesa_id}"
        qr = qrcode.make(url)
        qr_path = os.path.join(qr_code_dir, f"mesa_{mesa_id}.png")
        qr.save(qr_path)
        print(f"QR Code gerado para Mesa {mesa_id}: {url}")

def get_latest_tdf(directory):
    tdf_files = [f for f in os.listdir(directory) if f.endswith('.tdf')]
    if not tdf_files:
        print("Nenhum arquivo .tdf encontrado no diretório.")
        return None
    latest_file = max(tdf_files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))
    print(f"Último arquivo .tdf encontrado: {latest_file}")
    return os.path.join(directory, latest_file)

class TDFHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = directory
        self.last_sent_data = None

    def handle_tdf_event(self, event, action):
        if event.src_path.endswith(".tdf"):
            print(f"Arquivo {action}: {event.src_path}")
            latest_file = get_latest_tdf(self.directory)
            if latest_file:
                self.process_file(latest_file)

    def on_created(self, event):
        self.handle_tdf_event(event, "criado")

    def on_modified(self, event):
        self.handle_tdf_event(event, "modificado")

    def process_file(self, file_path):
        global last_processed_data
        print(f"Iniciando o processamento do arquivo: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = file.read()

            soup = BeautifulSoup(data, 'lxml')

            my_json = {'players': self.extract_players(soup)}
            my_json['round'] = self.extract_rounds(soup, my_json['players'])
            last_processed_data = my_json

            data_str = json.dumps(my_json, indent=4, ensure_ascii=False)
            print(f"JSON gerado:\n{data_str}")

            # Após gerar o JSON, enviar para o servidor online no PythonAnywhere
            try:
                response = requests.post(f"{ONLINE_SERVER_URL}/update-data", json=my_json)
                if response.status_code == 200:
                    print("Dados enviados para o servidor online com sucesso!")
                else:
                    print(f"Falha ao enviar dados. Status: {response.status_code}, {response.text}")
            except Exception as e:
                print(f"Erro ao enviar dados para o servidor online: {e}")

        except Exception as e:
            print(f"Erro ao processar o arquivo: {e}")

    def extract_players(self, soup):
        players = soup.find("players").find_all('player')
        print(f"Jogadores encontrados: {len(players)}")
        player_data = {}
        for player in players:
            userid = player['userid']
            firstname = player.find("firstname").string if player.find("firstname") else "Desconhecido"
            lastname = player.find("lastname").string if player.find("lastname") else "Desconhecido"
            player_data[userid] = f"{firstname} {lastname}"
        return player_data

    def extract_rounds(self, soup, player_data):
        pods = soup.find("pods").find_all('pod')
        print(f"Divisões encontradas: {len(pods)}")
        round_data = {}
        for pod in pods:
            division = category.get(pod['category'], 'None')
            rounds = pod.find('rounds').find_all('round')
            for my_round in rounds:
                round_number = my_round['number']
                if round_number not in round_data:
                    round_data[round_number] = {}
                round_data[round_number][division] = self.extract_matches(my_round, player_data)
        return round_data

    def extract_matches(self, my_round, player_data):
        placeholder = {'table': {}}
        matches = my_round.find('matches').find_all('match')
        for match in matches:
            table_number = match.find("tablenumber").string if match.find("tablenumber") else "Desconhecido"
            player1_id = match.find("player1")['userid'] if match.find("player1") else "N/A"
            player2_id = match.find("player2")['userid'] if match.find("player2") else "N/A"
            result = match.get('outcome')
            if result == "5":
                player_id = match.find("player")['userid'] if match.find("player") else "N/A"
                placeholder['table'][table_number] = {
                    'player1': player_data.get(player_id, "N/A"),
                    'player2': "N/A",
                    'outcome': "Vitória Automática (BYE)"
                }
            else:
                outcome_value = self.determine_outcome(result, player1_id, player2_id, player_data)
                placeholder['table'][table_number] = {
                    'player1': player_data.get(player1_id, "N/A"),
                    'player2': player_data.get(player2_id, "N/A"),
                    'outcome': outcome_value
                }
        return placeholder

    def determine_outcome(self, result, player1_id, player2_id, player_data):
        if result == "1":
            return f"Vitória de {player_data.get(player1_id, 'Jogador 1')}"
        elif result == "2":
            return f"Vitória de {player_data.get(player2_id, 'Jogador 2')}"
        elif result == "3":
            return "Empate"
        elif result == "0":
            return "Jogando"
        elif result == "10":
            return "Derrota dupla"
        else:
            return "Resultado desconhecido"

def iniciar_monitoramento(diretorio):
    event_handler = TDFHandler(diretorio)
    observer = Observer()
    observer.schedule(event_handler, diretorio, recursive=False)
    print(f"Iniciando monitoramento do diretório: {diretorio}")
    observer.start()
    try:
        while True:
            asyncio.run(asyncio.sleep(1))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    # Ajuste base_url para o servidor online do PythonAnywhere para os QRs
    base_url = "https://DuPrado.pythonanywhere.com"
    num_mesas = 10
    generate_qr_codes(base_url, num_mesas)

    tom_data_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if not os.path.exists(tom_data_directory):
        print("Diretório inválido. Encerrando.")
        exit()

    files = [f for f in os.listdir(tom_data_directory) if f.endswith('.tdf')]
    print(f"Arquivos .tdf encontrados no diretório: {files}")

    # Executa o Flask local (opcional, caso queira acessar localmente)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Inicia monitoramento local
    iniciar_monitoramento(tom_data_directory)
