import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.widgets import DateEntry
import threading
import queue
import pandas as pd
from datetime import datetime

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
        self.root.geometry("800x600")

        # --- State and Control Variables ---
        self.results_data = []
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        # --- Main Frame ---
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Frame ---
        input_frame = ttk.Labelframe(main_frame, text="Parâmetros da Análise", padding=10)
        input_frame.pack(fill=tk.X, pady=5)
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Símbolo:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.symbol_entry = ttk.Entry(input_frame, width=15)
        self.symbol_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.symbol_entry.insert(0, "BTCUSDT")

        ttk.Label(input_frame, text="Data de Início:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.start_date_entry = DateEntry(input_frame, dateformat="%Y-%m-%d", firstweekday=6, bootstyle=DEFAULT)
        self.start_date_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(input_frame, text="Data de Fim:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.end_date_entry = DateEntry(input_frame, dateformat="%Y-%m-%d", firstweekday=6, bootstyle=DEFAULT)
        self.end_date_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # --- Action Frame ---
        action_frame = ttk.Frame(main_frame, padding=(0, 10))
        action_frame.pack(fill=tk.X, pady=10)

        self.run_button = ttk.Button(action_frame, text="Iniciar Análise", command=self.start_backtest_thread, bootstyle=SUCCESS)
        self.run_button.pack(side=tk.LEFT, padx=(0, 5))

        self.pause_button = ttk.Button(action_frame, text="Pausar", command=self.toggle_pause, state="disabled", bootstyle=WARNING)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(action_frame, text="Parar", command=self.stop_backtest, state="disabled", bootstyle=DANGER)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(action_frame, text="")
        self.status_label.pack(side=tk.LEFT, padx=10)

        spacer = ttk.Frame(action_frame)
        spacer.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.export_button = ttk.Button(action_frame, text="Exportar para Excel", command=self.export_to_excel, state="disabled", bootstyle=INFO)
        self.export_button.pack(side=tk.RIGHT, padx=5)

        # --- Output Frame ---
        output_frame = ttk.Labelframe(main_frame, text="Resultados", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = ScrolledText(output_frame, state="disabled", height=10, wrap=tk.WORD, autohide=True)
        self.results_text.pack(fill=tk.BOTH, expand=True)

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
        self.results_text.text.configure(state="normal")
        if "---" in message: # Style separators differently
             self.results_text.insert(tk.END, message + "\n", "separator")
        else:
             self.results_text.insert(tk.END, message + "\n")
             # Store structured data for export
             try:
                 parts = message.split(' - ')
                 timestamp_str = parts[0].split(' ')[0]
                 signal = parts[1]
                 self.results_data.append({"Timestamp": timestamp_str, "Symbol": self.symbol_entry.get(), "Signal": signal})
             except IndexError:
                 pass # Not a result line
        self.results_text.text.configure(state="disabled")
        self.results_text.see(tk.END)
        self.results_text.tag_config("separator", foreground="cyan", font=("Arial", 10, "italic"))

    def start_backtest_thread(self):
        symbol = self.symbol_entry.get().strip().upper()
        start_date = self.start_date_entry.entry.get()
        end_date = self.end_date_entry.entry.get()

        if not all([symbol, start_date, end_date]):
            messagebox.showerror("Erro de Entrada", "Todos os campos devem ser preenchidos.")
            return

        self.stop_event.clear()
        self.pause_event.clear()
        self.is_paused = False
        self.results_data.clear()

        self.run_button.config(state="disabled")
        self.pause_button.config(state="normal", text="Pausar")
        self.stop_button.config(state="normal")
        self.export_button.config(state="disabled")
        self.status_label.config(text="Buscando dados...")

        self.results_text.text.config(state="normal")
        self.results_text.delete(1.0, tk.END)
        self.results_text.text.config(state="disabled")

        thread = threading.Thread(
            target=self.run_backtest_logic,
            args=(symbol, start_date, end_date),
            daemon=True
        )
        thread.start()

    def run_backtest_logic(self, symbol, start_date, end_date):
        # --- IMPORTANT: This block is for using real data. ---
        historical_df = fetch_historical_data(symbol, start_date, end_date)

        
        self.queue.put("--- AVISO: Usando dados de teste! A busca real na API está desativada. ---")
        date_range = pd.to_datetime(pd.date_range(start=start_date, end=end_date, freq='1h'))
        if date_range.tz is None:
            date_range = date_range.tz_localize('UTC')
        mock_data = {
            'timestamp': date_range,
            'open': 40000 + pd.Series(range(len(date_range))) * 10,
            'high': 40500 + pd.Series(range(len(date_range))) * 10,
            'low': 39800 + pd.Series(range(len(date_range))) * 10,
            'close': 40200 + pd.Series(range(len(date_range))) * 5,
            'volume': 100 + pd.Series(range(len(date_range)))
        }
        historical_df = pd.DataFrame(mock_data)
        
        if historical_df.empty:
            self.queue.put(f"ERRO: Não foi possível buscar dados para {symbol}.")
            self.gui_task_done()
            return

        self.status_label.config(text="Analisando...")
        run_backtest(historical_df, symbol, self.stop_event, self.pause_event, self.queue.put)
        self.gui_task_done()

    def toggle_pause(self):
        if self.is_paused:
            self.pause_event.clear()
            self.pause_button.config(text="Pausar")
            self.status_label.config(text="Analisando...")
            self.is_paused = False
        else:
            self.pause_event.set()
            self.pause_button.config(text="Continuar")
            self.status_label.config(text="Pausado")
            self.is_paused = True

    def stop_backtest(self):
        self.stop_event.set()

    def gui_task_done(self):
        self.status_label.config(text="Concluído")
        self.run_button.config(state="normal")
        self.pause_button.config(state="disabled", text="Pausar")
        self.stop_button.config(state="disabled")
        if self.results_data:
            self.export_button.config(state="normal")

    def export_to_excel(self):
        if not self.results_data:
            messagebox.showinfo("Exportar", "Não há dados para exportar.")
            return

        df = pd.DataFrame(self.results_data)

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            title="Salvar resultados como..."
        )

        if not filepath:
            return

        try:
            df.to_excel(filepath, index=False, engine='openpyxl')
            messagebox.showinfo("Sucesso", f"Resultados salvos com sucesso em:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar o arquivo:\n{e}")

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = BacktesterGUI(root)
    root.mainloop()
