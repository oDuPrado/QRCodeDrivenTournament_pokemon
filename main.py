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

# =========== IMPORTS FIREBASE =============
import firebase_admin
from firebase_admin import credentials, firestore

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

ONLINE_SERVER_URL = "https://yourserver.pythonanywhere.com"

# ========== Inicializa Firebase Admin =========
cred = credentials.Certificate("serviceAccountKey.json")  # Ajuste o caminho se necessário
firebase_admin.initialize_app(cred)
db = firestore.client()

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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Lista de PINs dos jogadores", ln=1, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Player_ID | Nome do Jogador | PIN", ln=1)
    pdf.ln(2)
    for pid, info in pins_dict.items():
        line = f"{pid} | {info['name']} | {info['pin']}"
        pdf.cell(0, 10, line, ln=1)
    pdf.output("players_pins.pdf")
    print("PDF com lista de PINs gerado: players_pins.pdf")

# =========== Funções para Firebase ============
def sanitize_filename_as_id(filename: str) -> str:
    base = os.path.basename(filename)
    name_no_ext, _ = os.path.splitext(base)
    sanitized = (name_no_ext.replace(" ", "_")
                             .replace("#", "-")
                             .replace(":", "-")
                             .replace("/", "-"))
    return sanitized

def upload_players_to_firebase(my_json):
    players_dict = my_json.get("players", {})
    pins_dict = my_json.get("pins", {})

    for player_id, fullname in players_dict.items():
        pin_entry = pins_dict.get(player_id, {})
        doc_ref = db.collection("players").document(player_id)
        doc_ref.set({
            "userid": player_id,
            "fullname": fullname,
            "pin": pin_entry.get("pin", "0000"),
            "name": pin_entry.get("name", fullname)
        }, merge=True)
        print(f"Player {player_id} salvo no Firebase.")

def upload_tournament_to_firebase(tournament_id, my_json):
    if "round" not in my_json:
        return

    pins_dict = my_json.get("pins", {})
    tournaments_ref = db.collection("tournaments").document(tournament_id)
    round_dict = my_json["round"]

    for round_number, divisions in round_dict.items():
        for division_key, data_division in divisions.items():
            table_data = data_division.get("table", {})
            round_doc_ref = tournaments_ref.collection("rounds").document(str(round_number))

            for table_id, match_info in table_data.items():
                # Usa o número do outcome já existente, se disponível
                outcome_num = match_info.get("outcomeNumber", 0)

                # IDs e PINs dos jogadores
                p1_id = match_info.get("player1_id") or "N/A"
                p2_id = match_info.get("player2_id") or "N/A"
                p1_pin = pins_dict.get(p1_id, {}).get('pin', '0000')
                p2_pin = pins_dict.get(p2_id, {}).get('pin', '0000')

                # Atualiza os dados
                new_data = dict(match_info)
                new_data["outcomeNumber"] = outcome_num  # Usa o valor existente
                new_data["player1_pin"] = p1_pin
                new_data["player2_pin"] = p2_pin

                # Salva no Firestore
                round_doc_ref.collection("matches").document(table_id).set(new_data, merge=True)
                print(f"Torneio {tournament_id} -> Round {round_number} -> Table {table_id} salvo no Firebase.")


# =========== Handler =============
class TDFHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = directory
        self.last_sent_data = None  
        self.player_data = {}  

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
        print(f"Iniciando o processamento do arquivo: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.read()

            soup = BeautifulSoup(data, 'lxml')

            # Extrai players e guarda em self.player_data
            self.player_data = self.extract_players(soup)
            my_json = {'players': self.player_data}

            # Extrai rounds, com base em self.player_data
            my_json['round'] = self.extract_rounds(soup)

            # Gera pins
            pin_file = "player_pins.json"
            player_pins_map = load_pins_file(pin_file)
            pins_dict = {}

            for pid, p_name in my_json['players'].items():
                if pid not in player_pins_map:
                    player_pins_map[pid] = generate_random_pin(4)
                pins_dict[pid] = {"pin": player_pins_map[pid], "name": p_name}

            save_pins_file(pin_file, player_pins_map)
            my_json['pins'] = pins_dict

            # Gera PDF
            print_pins_pdf(pins_dict)

            data_str = json.dumps(my_json, indent=4, ensure_ascii=False)
            print(f"JSON gerado:\n{data_str}")

            # Evita duplicar se não houve mudança
            if data_str == self.last_sent_data:
                print("Nenhuma mudança detectada. Ignorando repetição.")
                return
            self.last_sent_data = data_str

            # Envia p/ main_2 via HTTP
            try:
                resp = requests.post(f"{ONLINE_SERVER_URL}/update-data", json=my_json)
                if resp.status_code == 200:
                    print("Dados enviados para o servidor online com sucesso!")
                else:
                    print(f"Falha ao enviar dados. Status: {resp.status_code}, {resp.text}")
            except Exception as e:
                print(f"Erro ao enviar dados ao servidor online: {e}")

            # Salva no Firebase
            upload_players_to_firebase(my_json)
            tournament_id = sanitize_filename_as_id(file_path)
            upload_tournament_to_firebase(tournament_id, my_json)

        except Exception as e:
            print(f"Erro ao processar o arquivo: {e}")

    def extract_players(self, soup):
        players_xml = soup.find("players").find_all('player')
        print(f"Jogadores encontrados: {len(players_xml)}")
        p_data = {}
        for p in players_xml:
            userid = p.get('userid', '0000')
            firstname = p.find('firstname').string if p.find('firstname') else "Desconhecido"
            lastname = p.find('lastname').string if p.find('lastname') else "Desconhecido"
            p_data[userid] = f"{firstname} {lastname}"
        return p_data

    def extract_rounds(self, soup):
        pods = soup.find("pods").find_all('pod')
        print(f"Divisões encontradas: {len(pods)}")

        round_data = {}
        for pod in pods:
            div_key = category.get(pod['category'], 'None')
            rounds_list = pod.find('rounds').find_all('round')

            for r in rounds_list:
                round_number = r['number']
                if round_number not in round_data:
                    round_data[round_number] = {}
                round_data[round_number][div_key] = self.extract_matches(r)
        return round_data

    def extract_matches(self, round_tag):
        placeholder = {'table': {}}
        matches = round_tag.find('matches').find_all('match')

        for m in matches:
            table_number = m.find("tablenumber").string if m.find("tablenumber") else "Desconhecido"
            player1_tag = m.find("player1")
            player2_tag = m.find("player2")

            player1_id = player1_tag['userid'] if player1_tag else "N/A"
            player2_id = player2_tag['userid'] if player2_tag else "N/A"

            # Nomes
            p1_name = self.player_data.get(player1_id, "N/A")
            p2_name = self.player_data.get(player2_id, "N/A")

            result_code = m.get('outcome', "0")  # Default para "0" se não houver outcome

            # Lógica para outcome "Vitória de Fulano"
            if result_code == "5":
                single_tag = m.find("player")
                single_id = single_tag['userid'] if single_tag else "N/A"
                single_name = self.player_data.get(single_id, "N/A")
                placeholder['table'][table_number] = {
                    "player1_id": single_id,
                    "player2_id": None,
                    "player1": single_name,
                    "player2": "N/A",
                    "outcome": "Vitória Automática (BYE)",
                    "outcomeNumber": 5  # Adiciona o número diretamente
                }
            else:
                # Determina o número e a descrição do resultado
                outcome_num, outcome_str = self.determine_outcome(result_code, player1_id, player2_id)
                placeholder['table'][table_number] = {
                    "player1_id": player1_id,
                    "player2_id": player2_id,
                    "player1": p1_name,
                    "player2": p2_name,
                    "outcome": outcome_str,
                    "outcomeNumber": outcome_num  # Adiciona o número diretamente
                }

        return placeholder
    
    def determine_outcome(self, result_code, player1_id, player2_id):
        """Determina o número e a descrição do resultado."""
        outcome_num = 0
        
        if result_code == "1":
            outcome_num = 1
            outcome_str = f"Vitória de {self.player_data.get(player1_id, 'Jogador 1')}"
        elif result_code == "2":
            outcome_num = 2
            outcome_str = f"Vitória de {self.player_data.get(player2_id, 'Jogador 2')}"
        elif result_code == "3":
            outcome_num = 3
            outcome_str = "Empate"
        elif result_code == "0":
            outcome_num = 0
            outcome_str = "Jogando"
        elif result_code == "10":
            outcome_num = 10
            outcome_str = "Derrota dupla"
        elif result_code == "5":
            outcome_num = 5
            outcome_str = "Vitória Automática (BYE)"
        else:
            outcome_str = "Resultado desconhecido"

        return outcome_num, outcome_str



def iniciar_monitoramento(diretorio):
    handler = TDFHandler(diretorio)
    observer = Observer()
    observer.schedule(handler, diretorio, recursive=False)
    print(f"Iniciando monitoramento do diretório: {diretorio}")
    observer.start()
    try:
        while True:
            asyncio.run(asyncio.sleep(1))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    base_url = "https://yourserver.pythonanywhere.com"
    num_mesas = 25
    generate_qr_codes(base_url, num_mesas)

    tom_data_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if not os.path.exists(tom_data_directory):
        print("Diretório inválido. Encerrando.")
        exit()

    tdf_files = [f for f in os.listdir(tom_data_directory) if f.endswith('.tdf')]
    print(f"Arquivos .tdf encontrados no diretório: {tdf_files}")

    # Sobe Flask e inicia monitoramento
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    iniciar_monitoramento(tom_data_directory)
