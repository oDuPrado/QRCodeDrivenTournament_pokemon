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
import random
from fpdf import FPDF

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

resultados = {}
last_processed_data = None

ONLINE_SERVER_URL = "https://youruser.pythonanywhere.com"

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

def load_pins_file(pin_file):
    if os.path.exists(pin_file):
        with open(pin_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_pins_file(pin_file, pins):
    with open(pin_file, 'w', encoding='utf-8') as f:
        json.dump(pins, f, ensure_ascii=False, indent=4)

def generate_random_pin(digits=4):
    return f"{random.randint(0,10**digits-1):0{digits}d}"

def print_pins_pdf(pins_dict):
    # Gera um PDF com a lista de jogadores e seus PINs
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0,10,"Lista de PINs dos jogadores",ln=1,align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(0,10,"Player_ID | Nome do Jogador | PIN", ln=1)
    pdf.ln(2)
    for pid,info in pins_dict.items():
        pdf.cell(0,10,f"{pid} | {info['name']} | {info['pin']}", ln=1)
    pdf.output("players_pins.pdf")
    print("PDF com lista de PINs gerado: players_pins.pdf")

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

            pin_file = "player_pins.json"
            player_pins_map = load_pins_file(pin_file)

            pins_dict = {}

            for player_id, player_name in my_json['players'].items():
                if player_id not in player_pins_map:
                    player_pins_map[player_id] = generate_random_pin(4)
                # Agora armazenamos nome junto do PIN
                pins_dict[player_id] = {"pin": player_pins_map[player_id], "name": player_name}

            save_pins_file(pin_file, player_pins_map)

            my_json['pins'] = pins_dict

            # Gera o PDF com a lista de PINs
            print_pins_pdf(pins_dict)

            last_processed_data = my_json

            data_str = json.dumps(my_json, indent=4, ensure_ascii=False)
            print(f"JSON gerado:\n{data_str}")

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
                    'outcome': "Vitória Automática (BYE)",
                    'player1_id': player_id,
                    'player2_id': None
                }
            else:
                placeholder['table'][table_number] = {
                    'player1': player_data.get(player1_id, "N/A"),
                    'player2': player_data.get(player2_id, "N/A"),
                    'outcome': self.determine_outcome(result, player1_id, player2_id, player_data),
                    'player1_id': player1_id,
                    'player2_id': player2_id
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
    base_url = "https://youruser.pythonanywhere.com"
    num_mesas = 25
    generate_qr_codes(base_url, num_mesas)

    tom_data_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if not os.path.exists(tom_data_directory):
        print("Diretório inválido. Encerrando.")
        exit()

    files = [f for f in os.listdir(tom_data_directory) if f.endswith('.tdf')]
    print(f"Arquivos .tdf encontrados no diretório: {files}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    iniciar_monitoramento(tom_data_directory)
