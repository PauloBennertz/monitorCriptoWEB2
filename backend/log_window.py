# log_window.py
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
import logging
import queue

class CustomLogHandler(logging.Handler):
    """
    Um manipulador de log personalizado que envia mensagens de log para uma fila,
    que será lida por uma janela Tkinter/ttkbootstrap.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """
        Formata o registro de log e o coloca na fila.
        """
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

class LogWindow(ttk.Toplevel):
    """
    Uma janela Toplevel para exibir logs em tempo real.
    """
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Logs do Monitor de Criptomoedas")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.hide_window) # Esconde em vez de destruir

        self.log_queue = queue.Queue() # Fila para comunicação thread-safe

        # Configura o manipulador de log para esta janela
        self.log_handler = CustomLogHandler(self.log_queue)
        # Define o formato do log para incluir o nível, nome do logger e mensagem
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        self.log_handler.setFormatter(formatter)

        # Adiciona o manipulador ao logger raiz
        # É importante remover outros manipuladores de console se você quiser que o log apareça apenas aqui
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.INFO) # Define o nível mínimo de log a ser capturado

        self.create_widgets()
        self.process_log_queue() # Inicia o processamento da fila de logs

    def create_widgets(self):
        """
        Cria os widgets da interface da janela de log.
        """
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=ttk.BOTH, expand=True)

        self.log_text = ScrolledText(frame, wrap=ttk.WORD, state=ttk.DISABLED,
                                     bootstyle="info", font=("Courier New", 10))
        self.log_text.pack(fill=ttk.BOTH, expand=True, pady=(0, 10))

        clear_button = ttk.Button(frame, text="Limpar Logs", command=self.clear_logs,
                                  bootstyle="danger")
        clear_button.pack(pady=5)

    def process_log_queue(self):
        """
        Processa as mensagens na fila de logs e as insere na caixa de texto.
        """
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_text.configure(state=ttk.NORMAL)
            self.log_text.insert(ttk.END, message + "\n")
            self.log_text.configure(state=ttk.DISABLED)
            self.log_text.yview(ttk.END) # Rola automaticamente para o final

        # Agenda a próxima verificação da fila
        self.after(100, self.process_log_queue) # Verifica a cada 100ms

    def clear_logs(self):
        """
        Limpa todo o texto da caixa de logs.
        """
        self.log_text.configure(state=ttk.NORMAL)
        self.log_text.delete(1.0, ttk.END)
        self.log_text.configure(state=ttk.DISABLED)

    def hide_window(self):
        """
        Esconde a janela de log em vez de destruí-la.
        """
        self.withdraw()

    def show_window(self):
        """
        Mostra a janela de log.
        """
        self.deiconify()

    def on_closing(self):
        """
        Método chamado ao fechar a janela. Remove o manipulador de log.
        """
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)
        self.destroy()

if __name__ == '__main__':
    # Exemplo de uso para testar a janela de log
    root = ttk.Window(themename="darkly")
    root.withdraw() # Esconde a janela principal para focar na de log

    log_win = LogWindow(root)
    log_win.show_window()

    # Exemplo de logs
    logging.debug("Esta é uma mensagem de depuração.")
    logging.info("Esta é uma mensagem informativa.")
    logging.warning("Esta é uma mensagem de aviso.")
    logging.error("Esta é uma mensagem de erro.")
    logging.critical("Esta é uma mensagem crítica.")

    root.mainloop()
