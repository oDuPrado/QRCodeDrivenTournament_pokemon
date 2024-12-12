import asyncio
import os
import qrcode
import threading
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from websocket_server import WebSocketServer
import json

app = Flask(__name__, template_folder='templates', static_folder='static')

outcome = {
    0: "Jogando",
    1: "Vitória Jogador 1",
    2: "Vitória Jogador 2",
    3: "Empate",
    10: "Derrota Dupla",
}

category = {
    'Junior': 0,
    'Senior': 1,
    'Master': 2,
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/mesa/<int:mesa_id>")
def mesa(mesa_id):
    return render_template("mesa.html", mesa_id=mesa_id)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    mesa_id = data.get("mesa_id")
    resultado = data.get("resultado")
    print(f"Resultado da Mesa {mesa_id}: {resultado}")
    return jsonify({"message": "Resultado recebido com sucesso!"})

def run_flask():
    # Roda o Flask no host e porta desejada
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
    def __init__(self, directory, websocket_server, loop):
        self.directory = directory
        self.websocket_server = websocket_server
        self.loop = loop
        self.last_sent_data = None

    def on_created(self, event):
        if event.src_path.endswith(".tdf"):
            print(f"Novo arquivo criado: {event.src_path}")
            latest_file = get_latest_tdf(self.directory)
            if latest_file:
                self.process_file(latest_file)

    def on_modified(self, event):
        if event.src_path.endswith(".tdf"):
            print(f"Arquivo modificado: {event.src_path}")
            latest_file = get_latest_tdf(self.directory)
            if latest_file:
                self.process_file(latest_file)

    def process_file(self, file_path):
        print(f"Iniciando o processamento do arquivo: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = file.read()

            soup = BeautifulSoup(data, 'lxml')

            my_json = {'players': self.extract_players(soup)}
            my_json['round'] = self.extract_rounds(soup, my_json['players'])

            data = json.dumps(my_json, indent=4, ensure_ascii=False)
            print(f"JSON gerado:\n{data}")
            
            if data != self.last_sent_data:
                self.last_sent_data = data
                asyncio.run_coroutine_threadsafe(self.websocket_server.broadcast(data), self.loop)

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

async def monitor_directory(directory, websocket_server):
    loop = asyncio.get_running_loop()
    event_handler = TDFHandler(directory, websocket_server, loop)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    print(f"Iniciando monitoramento do diretório: {directory}")
    observer.start()
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        observer.stop()
        observer.join()

async def main_async():
    base_url = "http://172.28.0.239:5000"
    num_mesas = 10
    generate_qr_codes(base_url, num_mesas)
    tom_data_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if not os.path.exists(tom_data_directory):
        print("Diretório inválido. Encerrando.")
        return
    
    files = [f for f in os.listdir(tom_data_directory) if f.endswith('.tdf')]
    print(f"Arquivos .tdf encontrados no diretório: {files}")

    from websocket_server import WebSocketServer
    websocket_server = WebSocketServer()
    websocket_task = asyncio.create_task(websocket_server.start())

    print("Iniciando sistema de monitoramento e WebSocket...")
    monitor_task = asyncio.create_task(monitor_directory(tom_data_directory, websocket_server))

    await asyncio.gather(websocket_task, monitor_task)

if __name__ == "__main__":
    # Inicia o Flask em uma thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Executa a lógica assíncrona (websocket, monitoramento)
    asyncio.run(main_async())
