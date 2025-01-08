import tkinter as tk
from tkinter import messagebox
import threading
import subprocess


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitoramento Raspberry Pi")
        self.root.geometry("300x150")
        self.process = None  # Para controlar o processo do script principal

        self.start_button = tk.Button(root, text="Iniciar", command=self.start_code, width=15, height=2, bg="green", fg="white")
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Parar", command=self.stop_code, width=15, height=2, bg="red", fg="white")
        self.stop_button.pack(pady=10)

        self.status_label = tk.Label(root, text="Status: Parado", fg="blue")
        self.status_label.pack(pady=10)

    def start_code(self):
        if self.process is not None and self.process.poll() is None:
            messagebox.showinfo("Informação", "O código já está em execução.")
            return

        def run_script():
            self.status_label.config(text="Status: Em execução", fg="green")
            self.process = subprocess.Popen(["python", "main_3.py"], shell=False)

        thread = threading.Thread(target=run_script)
        thread.start()

    def stop_code(self):
        if self.process is None or self.process.poll() is not None:
            messagebox.showinfo("Informação", "Nenhum processo em execução para parar.")
            return

        self.process.terminate()
        self.process.wait()
        self.status_label.config(text="Status: Parado", fg="blue")
        messagebox.showinfo("Informação", "Processo encerrado com sucesso.")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
