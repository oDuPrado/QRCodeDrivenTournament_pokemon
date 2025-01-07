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

ONLINE_SERVER_URL = "https://youruser.pythonanywhere.com"

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
    """Localiza o arquivo .tdf mais recente no diretório."""
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

def upload_players_to_firebase(my_json):
    """
    Envia lista de players ao Firestore, incluindo 'birthdate' se disponível,
    mas sem colocar essa info em 'tournaments'.
    """
    players_dict = my_json.get("players", {})  
    pins_dict = my_json.get("pins", {})

    for player_id, p_info in players_dict.items():
        fullname = p_info.get("fullname", "Jogador Desconhecido")
        birthdate = p_info.get("birthdate", "")  # data de nascimento
        doc_ref = db.collection("players").document(player_id)

        pin_entry = pins_dict.get(player_id, {})
        pin_code = pin_entry.get("pin", "0000")
        name_field = pin_entry.get("name", fullname)

        doc_ref.set({
            "userid": player_id,
            "fullname": fullname,
            "birthdate": birthdate,
            "pin": pin_code,
            "name": name_field,
        }, merge=True)
        print(f"Player {player_id} salvo no Firebase.")


def upload_tournament_to_firebase(tournament_id, my_json):
    """Cria/atualiza doc de torneio: tournaments/<tournament_id>, rounds e places."""
    if "round" not in my_json:
        return

    pins_dict = my_json.get("pins", {})
    tournaments_ref = db.collection("tournaments").document(tournament_id)
    round_dict = my_json["round"]

    # Salva as rodadas
    for round_number, divisions in round_dict.items():
        for division_key, data_division in divisions.items():
            table_data = data_division.get("table", {})
            round_doc_ref = tournaments_ref.collection("rounds").document(str(round_number))

            for table_id, match_info in table_data.items():
                outcome_num = match_info.get("outcomeNumber", 0)

                p1_id = match_info.get("player1_id") or "N/A"
                p2_id = match_info.get("player2_id") or "N/A"
                p1_pin = pins_dict.get(p1_id, {}).get('pin', '0000')
                p2_pin = pins_dict.get(p2_id, {}).get('pin', '0000')

                new_data = dict(match_info)
                new_data["outcomeNumber"] = outcome_num
                new_data["player1_pin"] = p1_pin
                new_data["player2_pin"] = p2_pin

                round_doc_ref.collection("matches").document(table_id).set(new_data, merge=True)
                print(f"Torneio {tournament_id} -> Round {round_number} -> Table {table_id} salvo no Firebase.")

    # Se extraímos "finished_places" no JSON, salvamos em subcoleção "places"
    if "finished_places" in my_json:
        places_arr = my_json["finished_places"]
        places_coll = tournaments_ref.collection("places")
        for place_info in places_arr:
            place_doc = places_coll.document(str(place_info["place"]))
            place_doc.set({
                "userid": place_info["userid"],
                "fullname": place_info["fullname"],
            }, merge=True)
            print(f"Torneio {tournament_id} -> place {place_info['place']} salvo no Firebase.")


# =========== Handler =============
class TDFHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = directory
        self.last_sent_data = None
        # {userid: {fullname, birthdate, ...}}
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

            # Extrai nome e id do torneio
            tournament_name = "Torneio_Desconhecido"
            tournament_id_tag = "000"
            data_tag = soup.find("data")
            if data_tag:
                name_tag = data_tag.find("name")
                id_tag = data_tag.find("id")
                if name_tag and name_tag.string:
                    tournament_name = name_tag.string
                if id_tag and id_tag.string:
                    tournament_id_tag = id_tag.string

            tournament_id = f"{tournament_name}_{tournament_id_tag}".replace(" ", "_")

            # Extrai players
            self.player_data = self.extract_players(soup)
            my_json = {
                "players": self.player_data,
                "tournamentName": tournament_name,
                "tournamentID": tournament_id_tag,
            }

            # Extrai rounds
            my_json["round"] = self.extract_rounds(soup)

            # Extrai places (pódio) se existir <standings> + <pod category="2" type="finished">
            finished_places = self.extract_finished_places(soup)
            if finished_places:
                my_json["finished_places"] = finished_places

            # Gera PINs
            pin_file = "player_pins.json"
            player_pins_map = load_pins_file(pin_file)
            pins_dict = {}
            for pid, p_info in my_json["players"].items():
                if pid not in player_pins_map:
                    player_pins_map[pid] = generate_random_pin(4)
                pins_dict[pid] = {
                    "pin": player_pins_map[pid],
                    "name": p_info.get("fullname", "Jogador X")
                }
            save_pins_file(pin_file, player_pins_map)
            my_json["pins"] = pins_dict

            # Gera PDF
            print_pins_pdf(pins_dict)

            data_str = json.dumps(my_json, indent=4, ensure_ascii=False)
            print(f"JSON gerado:\n{data_str}")

            # Evita duplicar se não houve mudança
            if data_str == self.last_sent_data:
                print("Nenhuma mudança detectada. Ignorando repetição.")
                return
            self.last_sent_data = data_str

            # Envia p/ main_2
            try:
                resp = requests.post(f"{ONLINE_SERVER_URL}/update-data", json=my_json)
                if resp.status_code == 200:
                    print("Dados enviados ao servidor online com sucesso!")
                else:
                    print(f"Falha ao enviar dados. Status: {resp.status_code}, {resp.text}")
            except Exception as e:
                print(f"Erro ao enviar dados ao servidor online: {e}")

            # Salva no Firebase
            upload_players_to_firebase(my_json)
            upload_tournament_to_firebase(tournament_id, my_json)

        except Exception as e:
            print(f"Erro ao processar o arquivo: {e}")

    def extract_players(self, soup):
        """
        <players>
          <player userid='4176539'>
            <firstname>Joao</firstname>
            <lastname>Silva</lastname>
            <birthdate>08/09/2000</birthdate>
          </player>
          ...
        </players>
        """
        players_xml = soup.find("players").find_all("player")
        print(f"Jogadores encontrados: {len(players_xml)}")
        p_data = {}

        for p in players_xml:
            userid = p.get("userid", "0000")
            firstname = p.find("firstname").string if p.find("firstname") else "Desconhecido"
            lastname = p.find("lastname").string if p.find("lastname") else "Desconhecido"
            birthdate = p.find("birthdate").string if p.find("birthdate") else ""

            p_data[userid] = {
                "fullname": f"{firstname} {lastname}".strip(),
                "birthdate": birthdate
            }

        return p_data

    def extract_rounds(self, soup):
        pods_tag = soup.find("pods")
        if not pods_tag:
            print("Nenhuma <pods> encontrada.")
            return {}

        pods = pods_tag.find_all("pod")
        print(f"Divisões encontradas: {len(pods)}")
        round_data = {}

        for pod in pods:
            div_cat = pod.get("category", "None")
            div_idx = category.get(div_cat, "None")

            rounds_block = pod.find("rounds")
            if not rounds_block:
                continue

            rounds_list = rounds_block.find_all("round")
            for r in rounds_list:
                round_number = r["number"]
                if round_number not in round_data:
                    round_data[round_number] = {}
                round_data[round_number][div_idx] = self.extract_matches(r)
        return round_data

    def extract_matches(self, round_tag):
        placeholder = {"table": {}}
        matches = round_tag.find("matches")
        if not matches:
            return placeholder

        all_matches = matches.find_all("match")
        for m in all_matches:
            table_number = m.find("tablenumber").string if m.find("tablenumber") else "Desconhecido"
            player1_tag = m.find("player1")
            player2_tag = m.find("player2")

            p1_id = player1_tag["userid"] if player1_tag else "N/A"
            p2_id = player2_tag["userid"] if player2_tag else "N/A"

            p1_data = self.player_data.get(p1_id, {})
            p2_data = self.player_data.get(p2_id, {})

            p1_name = p1_data.get("fullname", "N/A")
            p2_name = p2_data.get("fullname", "N/A")

            outcome_code = m.get("outcome", "0")
            if outcome_code == "5":
                single_tag = m.find("player")
                single_id = single_tag["userid"] if single_tag else "N/A"
                single_data = self.player_data.get(single_id, {})
                single_name = single_data.get("fullname", "N/A")

                placeholder["table"][table_number] = {
                    "player1_id": single_id,
                    "player2_id": None,
                    "player1": single_name,
                    "player2": "N/A",
                    "outcome": "Vitória Automática (BYE)",
                    "outcomeNumber": 5,
                }
            else:
                outcome_num, outcome_str = self.determine_outcome(outcome_code, p1_id, p2_id)
                placeholder["table"][table_number] = {
                    "player1_id": p1_id,
                    "player2_id": p2_id,
                    "player1": p1_name,
                    "player2": p2_name,
                    "outcome": outcome_str,
                    "outcomeNumber": outcome_num,
                }
        return placeholder

    def determine_outcome(self, result_code, p1_id, p2_id):
        outcome_num = 0
        p1_data = self.player_data.get(p1_id, {})
        p2_data = self.player_data.get(p2_id, {})

        p1_name = p1_data.get("fullname", "Jogador 1")
        p2_name = p2_data.get("fullname", "Jogador 2")

        if result_code == "1":
            outcome_num = 1
            outcome_str = f"Vitória de {p1_name}"
        elif result_code == "2":
            outcome_num = 2
            outcome_str = f"Vitória de {p2_name}"
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

    def extract_finished_places(self, soup):
        """
        Exemplo esperado no .tdf:
        <standings>
          <pod category="2" type="finished">
            <player id="4176539" place="1" />
            <player id="5054993" place="2" />
            ...
          </pod>
        </standings>
        """
        results = []
        standings_tag = soup.find("standings")
        if not standings_tag:
            print("Nenhum <standings> encontrado no XML.")
            return results

        # Filtra pods "type=finished" e "category=2"
        pods = standings_tag.find_all("pod", {"type": "finished", "category": "2"})
        if not pods:
            print("Nenhum pod com category=2 e type=finished dentro de <standings>.")
            return results

        for pod in pods:
            # Para cada <player id="X" place="Y" />
            players = pod.find_all("player")
            for pl in players:
                pid = pl.get("id", "N/A")
                place_str = pl.get("place", "0")
                try:
                    place_int = int(place_str)
                except:
                    place_int = 0

                p_data = self.player_data.get(pid, {})
                fullname = p_data.get("fullname", "Desconhecido")

                results.append({
                    "userid": pid,
                    "place": place_int,
                    "fullname": fullname,
                })

        print("Places extraídos:", results)
        return results


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
    base_url = "https://DuPrado.pythonanywhere.com"
    num_mesas = 25
    generate_qr_codes(base_url, num_mesas)

    tom_data_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if not os.path.exists(tom_data_directory):
        print("Diretório inválido. Encerrando.")
        exit()

    files = [f for f in os.listdir(tom_data_directory) if f.endswith('.tdf')]
    print(f"Arquivos .tdf encontrados no diretório: {files}")

    # Inicia Flask em thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Inicia watchdog
    iniciar_monitoramento(tom_data_directory)
