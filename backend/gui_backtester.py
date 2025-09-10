import tkinter as tk
from tkinter import scrolledtext, font, messagebox
import threading
import queue

# Import the backtesting logic
try:
    from backtester import fetch_historical_data, run_backtest
except ImportError:
    messagebox.showerror("Erro de Importação", "Não foi possível encontrar o script 'backtester.py'. Certifique-se de que ele está na mesma pasta.")
    exit()

class BacktesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferramenta de Backtesting")
        self.root.geometry("750x550")

        # --- Fonts and Styles ---
        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Arial", size=10)
        self.label_font = font.Font(family="Arial", size=10, weight="bold")
        self.root.option_add("*TButton*padding", "5 2")

        # --- Main Frame ---
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Frame ---
        input_frame = tk.Frame(main_frame, pady=5)
        input_frame.pack(fill=tk.X)

        tk.Label(input_frame, text="Símbolo:", font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
        self.symbol_entry = tk.Entry(input_frame, width=15)
        self.symbol_entry.pack(side=tk.LEFT, padx=(0, 20))
        self.symbol_entry.insert(0, "BTCUSDT")

        tk.Label(input_frame, text="Data de Início:", font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
        self.start_date_entry = tk.Entry(input_frame, width=12)
        self.start_date_entry.pack(side=tk.LEFT, padx=(0, 20))
        self.start_date_entry.insert(0, "2023-01-01")

        tk.Label(input_frame, text="Data de Fim:", font=self.label_font).pack(side=tk.LEFT, padx=(0, 5))
        self.end_date_entry = tk.Entry(input_frame, width=12)
        self.end_date_entry.pack(side=tk.LEFT)
        self.end_date_entry.insert(0, "2023-01-31")

        # --- Action Frame ---
        action_frame = tk.Frame(main_frame, pady=10)
        action_frame.pack(fill=tk.X)

        self.run_button = tk.Button(action_frame, text="Iniciar Análise", command=self.start_backtest_thread)
        self.run_button.pack(side=tk.LEFT)

        self.status_label = tk.Label(action_frame, text="", fg="blue")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # --- Output Frame ---
        output_frame = tk.LabelFrame(main_frame, text="Resultados", font=self.label_font, padx=10, pady=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = scrolledtext.ScrolledText(output_frame, state="disabled", height=10, wrap=tk.WORD, bg="#f0f0f0", relief=tk.SUNKEN, borderwidth=1)
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Queue for thread-safe communication
        self.queue = queue.Queue()
        self.root.after(100, self.process_queue)

    def process_queue(self):
        try:
            message = self.queue.get_nowait()
            self.update_results(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def update_results(self, message):
        self.results_text.configure(state="normal")
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.configure(state="disabled")
        self.results_text.see(tk.END) # Auto-scroll

    def start_backtest_thread(self):
        symbol = self.symbol_entry.get().strip().upper()
        start_date = self.start_date_entry.get().strip()
        end_date = self.end_date_entry.get().strip()

        if not all([symbol, start_date, end_date]):
            messagebox.showerror("Erro de Entrada", "Todos os campos devem ser preenchidos.")
            return

        self.run_button.config(state="disabled")
        self.status_label.config(text="Buscando dados...")
        self.results_text.config(state="normal")
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state="disabled")

        # Run the backtest in a separate thread
        thread = threading.Thread(
            target=self.run_backtest_logic,
            args=(symbol, start_date, end_date),
            daemon=True
        )
        thread.start()

    def run_backtest_logic(self, symbol, start_date, end_date):
        # This function runs in the background thread

        # --- IMPORTANT ---
        # This is where the real data fetching would happen.
        # Due to the sandbox environment, we use mock data.
        # To use with real data, uncomment the first line and remove the mock data block.

        historical_df = fetch_historical_data(symbol, start_date, end_date)

    

        if historical_df.empty:
            self.queue.put(f"ERRO: Não foi possível buscar dados para {symbol}.")
            self.gui_task_done()
            return

        self.queue.put(f"Dados carregados. {len(historical_df)} registros. Iniciando análise...")

        # The callback function will put messages into the queue
        run_backtest(historical_df, symbol, output_callback=self.queue.put)

        self.gui_task_done()

    def gui_task_done(self):
        # This function is called from the thread to safely update the GUI
        self.queue.put("--- Análise Concluída ---")
        self.status_label.config(text="")
        self.run_button.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = BacktesterGUI(root)
    root.mainloop()
