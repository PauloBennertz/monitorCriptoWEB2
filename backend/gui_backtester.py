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

import json
from .historical_analyzer import analyze_historical_alerts

# Import the backtesting and charting logic
try:
    from .backtester import fetch_historical_data, run_backtest
    from .chart_generator import generate_chart_image as generate_chart
except ImportError as e:
    messagebox.showerror("Erro de Importação", f"Não foi possível importar componentes necessários: {e}")
    exit()

class BacktesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferramenta de Backtesting")
        self.root.geometry("800x600")

        # --- State and Control Variables ---
        self.results_data = []
        self.backtest_df = None # To store the dataframe with results
        self.backtest_signals = None # To store the signals for charting
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

        self.chart_button = ttk.Button(action_frame, text="Ver Gráfico", command=self.show_chart, state="disabled", bootstyle=PRIMARY)
        self.chart_button.pack(side=tk.RIGHT, padx=5)

        self.export_button = ttk.Button(action_frame, text="Exportar para CSV", command=self.export_to_csv, state="disabled", bootstyle=INFO)
        self.export_button.pack(side=tk.RIGHT, padx=5)

        # --- Output Frame ---
        output_frame = ttk.Labelframe(main_frame, text="Resultados", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        # --- Treeview for structured results ---
        timeframes = ['15m', '30m', '1h', '4h', '24h']
        base_columns = ["timestamp", "symbol", "condition", "price"]
        hit_rate_columns = [f"{prefix}_{tf}" for tf in timeframes for prefix in ("hit", "pct")]
        columns = base_columns + hit_rate_columns

        self.results_tree = ttk.Treeview(output_frame, columns=columns, show="headings", height=10)

        # Define headings
        self.results_tree.heading("timestamp", text="Timestamp")
        self.results_tree.heading("symbol", text="Símbolo")
        self.results_tree.heading("condition", text="Condição")
        self.results_tree.heading("price", text="Preço")
        for tf in timeframes:
            self.results_tree.heading(f"hit_{tf}", text=f"Acerto ({tf})")
            self.results_tree.heading(f"pct_{tf}", text=f"% ({tf})")

        # Configure column widths
        self.results_tree.column("timestamp", width=150)
        self.results_tree.column("symbol", width=80)
        self.results_tree.column("condition", width=180)
        self.results_tree.column("price", width=80, anchor=E)
        for tf in timeframes:
            self.results_tree.column(f"hit_{tf}", width=70, anchor=CENTER)
            self.results_tree.column(f"pct_{tf}", width=70, anchor=E)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(fill=tk.BOTH, expand=True)

        # --- Summary Frame ---
        summary_frame = ttk.Labelframe(main_frame, text="Resumo da Taxa de Acerto", padding=10)
        summary_frame.pack(fill=tk.X, pady=(10, 5))
        self.summary_labels = {}
        timeframes = ['15m', '30m', '1h', '4h', '24h']
        for i, tf in enumerate(timeframes):
            label = ttk.Label(summary_frame, text=f"Período {tf}: N/A")
            label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.summary_labels[tf] = label

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
        if not isinstance(message, dict):
            return

        msg_type = message.get("type")
        if msg_type == "alert":
            alert_data = message.get("data", {})

            # --- Base Info ---
            ts_str = alert_data.get('timestamp', '')
            try:
                ts = pd.to_datetime(ts_str).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                ts = ts_str

            price = f"${alert_data.get('snapshot', {}).get('price', 0):.2f}"

            base_values = [
                ts,
                alert_data.get('symbol', 'N/A'),
                alert_data.get('description', 'N/A'),
                price
            ]

            # --- Hit Rate Info ---
            timeframes = ['15m', '30m', '1h', '4h', '24h']
            hit_rate_values = []
            for tf in timeframes:
                hit = alert_data.get(f'hit_{tf}')
                pct = alert_data.get(f'pct_change_{tf}')

                # Format for display
                hit_display = "Sim" if hit is True else ("Não" if hit is False else "N/A")
                pct_display = f"{pct:.2f}%" if pct is not None else "N/A"

                hit_rate_values.extend([hit_display, pct_display])

            # --- Combine and Insert ---
            values = tuple(base_values + hit_rate_values)
            self.results_tree.insert("", tk.END, values=values)
            self.results_data.append(alert_data) # Store original data

        elif msg_type == "status":
            self.status_label.config(text=message.get("msg"))
        elif msg_type == "error":
            messagebox.showerror("Erro na Análise", message.get("msg"))

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
        self.backtest_df = None
        self.backtest_signals = None

        self.run_button.config(state="disabled")
        self.pause_button.config(state="normal", text="Pausar")
        self.stop_button.config(state="normal")
        self.export_button.config(state="disabled")
        self.chart_button.config(state="disabled")
        self.status_label.config(text="Analisando...")

        # Clear previous results from the treeview
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)

        # Reset summary labels
        for tf, label in self.summary_labels.items():
            label.config(text=f"{tf}: N/A")

        thread = threading.Thread(
            target=self.run_backtest_logic,
            args=(symbol, start_date, end_date),
            daemon=True
        )
        thread.start()

    def run_backtest_logic(self, symbol, start_date, end_date):
        try:
            with open('backend/config.json', 'r') as f:
                config = json.load(f)
            crypto_config = next((c for c in config.get("cryptos_to_monitor", []) if c['symbol'] == symbol), {})
            alert_config = crypto_config.get('alert_config', {})
            if not alert_config:
                self.queue.put({"type": "status", "msg": f"AVISO: Nenhuma configuração de alerta para {symbol}."})
        except Exception as e:
            self.queue.put({"type": "error", "msg": f"ERRO ao ler config.json: {e}"})
            self.gui_task_done()
            return

        alerts, df = analyze_historical_alerts(symbol, start_date, end_date, alert_config)
        self.backtest_df = df # Store historical data for the chart

        if not alerts:
            self.queue.put({"type": "status", "msg": f"Nenhum alerta encontrado para {symbol}."})
        else:
            formatted_signals = []
            for alert in alerts:
                if self.stop_event.is_set():
                    break
                self.queue.put({"type": "alert", "data": alert})
                # Re-format for the chart generator
                formatted_signals.append({
                    "timestamp": pd.to_datetime(alert["timestamp"]),
                    "price": alert["snapshot"]["price"],
                    "message": alert["description"]
                })
            self.backtest_signals = formatted_signals

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
            self.update_summary_display()

        if self.backtest_signals: # If there are any signals, enable the chart button
            self.chart_button.config(state="normal")

    def update_summary_display(self):
        if not self.results_data:
            return

        # Check if hit rate calculation was successful
        if 'hit_rate_calculated' in self.results_data[0] and not self.results_data[0]['hit_rate_calculated']:
            for tf, label in self.summary_labels.items():
                label.config(text=f"Período {tf}: Falha ao buscar dados detalhados.")
            return

        timeframes = ['15m', '30m', '1h', '4h', '24h']
        for tf in timeframes:
            hit_key = f'hit_{tf}'
            hits = 0
            misses = 0

            for result in self.results_data:
                if result.get(hit_key) is True:
                    hits += 1
                elif result.get(hit_key) is False:
                    misses += 1

            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                summary_text = f"Período {tf} - Acertos: {hits} / Erros: {misses} (Taxa de Acerto: {hit_rate:.1f}%)"
            else:
                summary_text = f"Período {tf}: Sem dados"

            self.summary_labels[tf].config(text=summary_text)

    def export_to_csv(self):
        if not self.results_data:
            messagebox.showinfo("Exportar", "Não há dados para exportar.")
            return

        df = pd.DataFrame(self.results_data)

        # Create a dynamic filename
        symbol = self.symbol_entry.get().strip().upper()
        start_date = self.start_date_entry.entry.get()
        end_date = self.end_date_entry.entry.get()
        filename = f"{symbol}_{start_date}_a_{end_date}.csv"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Salvar resultados como...",
            initialfile=filename
        )

        if not filepath:
            return

        try:
            # Drop the complex 'snapshot' column before saving
            if 'snapshot' in df.columns:
                df = df.drop(columns=['snapshot'])
            df.to_csv(filepath, index=False)
            messagebox.showinfo("Sucesso", f"Resultados salvos com sucesso em:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro ao salvar o arquivo:\n{e}")

    def show_chart(self):
        if self.backtest_df is not None and self.backtest_signals:
            # Run chart generation in a separate thread to avoid freezing the GUI
            chart_thread = threading.Thread(
                target=generate_chart,
                args=(self.backtest_df, self.backtest_signals),
                daemon=True
            )
            chart_thread.start()
        else:
            messagebox.showinfo("Gerar Gráfico", "Não há dados de backtest para exibir. Execute uma análise primeiro.")

if __name__ == "__main__":
    try:
        root = ttk.Window(themename="darkly")
        app = BacktesterGUI(root)
        root.mainloop()
    except tk.TclError as e:
        print(f"Could not start GUI, likely because no display is available. Error: {e}")
        # In a headless environment, we can't run the GUI.
        # We can at least confirm the code is syntactically correct.
        print("GUI Backtester script is syntactically correct and imports are resolved.")
