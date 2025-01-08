import os
import platform
import paramiko
from scp import SCPClient
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess


class RaspberryPiConnection:
    def __init__(self):
        # Constantes privadas (encapsulamento)
        self.__hostname = "100.80.36.66"  # Substitua pelo IP do Tailscale
        self.__username = "duprado"  # Nome de usuário do Raspberry Pi
        self.__password = "110300"  # Substitua pela senha do Raspberry Pi
        self.__remote_directory = "/home/duprado/main/files/"  # Diretório remoto no Raspberry Pi
        self.__start_script_path = "/home/duprado/main/codigo/web_server/CODIGO_WEB_server/start_main.sh"  # Caminho do script de inicialização no Raspberry Pi

    def __print_details(self):
        """Exibe detalhes da conexão."""
        print("Configuração atual:")
        print(f"  Hostname: {self.__hostname}")
        print(f"  Usuário: {self.__username}")
        print("  Senha: [protegida]\n")

    def test_ping(self):
        """Testa a conexão via ping."""
        print(f"Testando conexão com {self.__hostname}...")

        # Detectar sistema operacional
        if platform.system().lower() == "windows":
            # No Windows, use "ping -n 1"
            response = os.system(f"ping -n 1 {self.__hostname}")
        else:
            # No Linux/Unix, use "ping -c 1"
            response = os.system(f"ping -c 1 {self.__hostname}")

        # Verificar resposta do comando
        if response == 0:
            print(f"{self.__hostname} está acessível!\n")
            return True
        else:
            print(f"Falha no ping. {self.__hostname} não está acessível. Verifique a rede!\n")
            return False

    def test_ssh_connection(self):
        """Testa a conexão via SSH."""
        print(f"Tentando conexão SSH com {self.__hostname}...\n")
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.__hostname, username=self.__username, password=self.__password)
            print(f"Conexão SSH bem-sucedida com {self.__hostname}!\n")
            ssh.close()
            return True
        except paramiko.AuthenticationException:
            print("Falha na autenticação. Verifique usuário e senha.\n")
            return False
        except paramiko.SSHException as sshException:
            print(f"Erro de conexão SSH: {sshException}\n")
            return False
        except Exception as e:
            print(f"Erro inesperado: {e}\n")
            return False

    def start_remote_script(self):
        """Executa o script start_main.sh no Raspberry Pi em segundo plano."""
        try:
            print("Iniciando o script start_main.sh no Raspberry Pi...")

            # Conexão SSH para executar o script
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.__hostname, username=self.__username, password=self.__password)

            # Executando o script remoto em segundo plano com nohup
            execute_command = f"nohup bash {self.__start_script_path} > /dev/null 2>&1 &"
            stdin, stdout, stderr = ssh.exec_command(execute_command)

            # Verificando saída e possíveis erros
            stderr_output = stderr.read().decode().strip()
            if stderr_output:
                print(f"Erro ao executar o comando: {stderr_output}")
                ssh.close()
                return False

            print("Script start_main.sh executado com sucesso em segundo plano.\n")
            ssh.close()
            return True
        except Exception as e:
            print(f"Erro ao executar o script remoto no Raspberry Pi: {e}")
            return False

    def stop_remote_script(self):
        """Encerra o processo main.py no Raspberry Pi."""
        try:
            print("Tentando encerrar o processo main.py no Raspberry Pi...")
            
            # Conexão SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.__hostname, username=self.__username, password=self.__password)

            # Comando para encontrar e matar o processo main.py
            find_and_kill_command = "pkill -f '/home/duprado/main/codigo/web_server/CODIGO_WEB_server/main.py'"
            stdin, stdout, stderr = ssh.exec_command(find_and_kill_command)

            # Verificando saída e possíveis erros
            stderr_output = stderr.read().decode().strip()
            if stderr_output:
                print(f"Erro ao encerrar o processo: {stderr_output}")
            else:
                print("Processo main.py encerrado com sucesso.")

            ssh.close()
        except Exception as e:
            print(f"Erro ao encerrar o script remoto no Raspberry Pi: {e}")

    def send_file(self, local_path, remote_filename):
        """Envia um arquivo para o Raspberry Pi e o substitui se já existir."""
        try:
            print(f"Conectando ao Raspberry Pi ({self.__hostname}) via SSH...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.__hostname, username=self.__username, password=self.__password)

            with SCPClient(ssh.get_transport()) as scp:
                print(f"Enviando {local_path} para {self.__remote_directory}{remote_filename}...")
                scp.put(local_path, f"{self.__remote_directory}{remote_filename}")
                print(f"Arquivo {remote_filename} enviado com sucesso para o Raspberry Pi.")

            ssh.close()
        except Exception as e:
            print(f"Erro ao enviar arquivo para o Raspberry Pi: {e}")


class TDFHandler(FileSystemEventHandler):
    def __init__(self, connection):
        self.connection = connection

    def on_modified(self, event):
        """Ação executada quando um arquivo é modificado."""
        if event.src_path.endswith(".tdf"):  # Monitora apenas arquivos .tdf
            print(f"Arquivo modificado: {event.src_path}")
            filename = os.path.basename(event.src_path)
            self.connection.send_file(event.src_path, filename)


def monitorar_pasta(diretorio, connection):
    """Inicia o monitoramento de uma pasta para alterações."""
    print(f"Iniciando monitoramento da pasta: {diretorio}")
    event_handler = TDFHandler(connection)
    observer = Observer()
    observer.schedule(event_handler, path=diretorio, recursive=False)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def realizar_ping(connection):
    """Realiza o teste de ping no Raspberry Pi."""
    if connection.test_ping():
        print("Ping concluído com sucesso.\n")
        return True
    else:
        print("Falha no ping. O Raspberry Pi não está acessível.\n")
        return False


def realizar_conexao_ssh(connection):
    """Realiza a conexão SSH com o Raspberry Pi."""
    if connection.test_ssh_connection():
        print("Conexão com o Raspberry Pi estabelecida com sucesso via SSH!\n")
        return True
    else:
        print("Falha na conexão SSH.\n")
        return False


def iniciar_script_remoto(connection):
    """Inicia o script remoto no Raspberry Pi."""
    if connection.start_remote_script():
        print("Script remoto iniciado com sucesso.\n")
        return True
    else:
        print("Falha ao iniciar o script remoto.\n")
        return False


def iniciar_monitoramento(connection):
    """Inicia o monitoramento do diretório local."""
    local_directory = r"C:\Users\Marco Prado\OneDrive\ONE DRIVE\OneDrive\SISTEMAS\2024\LIGAS\TOM_APP\DATA\TOM_DATA\TOM_DATA"
    if os.path.exists(local_directory):
        try:
            monitorar_pasta(local_directory, connection)
        except KeyboardInterrupt:
            print("\nMonitoramento encerrado. Parando main.py no Raspberry Pi...")
            connection.stop_remote_script()
    else:
        print(f"Erro: O diretório {local_directory} não existe!")


def main():
    print("Iniciando teste de conexão com o Raspberry Pi...\n")
    connection = RaspberryPiConnection()

    # Mostrar detalhes da conexão
    connection._RaspberryPiConnection__print_details()

    if not realizar_ping(connection):
        return

    if not realizar_conexao_ssh(connection):
        return

    if not iniciar_script_remoto(connection):
        return

    iniciar_monitoramento(connection)


if __name__ == "__main__":
    main()
