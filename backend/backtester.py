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
from .cache_manager import generate_cache_key, save_to_cache, load_from_cache

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
        self.root.geometry("1200x700")

        # --- State and Control Variables ---
        self.results_data = []
        self.backtest_df = None # To store the dataframe with results
        self.backtest_signals = None # To store the signals for charting
        self.is_paused = False
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        # --- Top Level Frame ---
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.BOTH, expand=True)

        # --- Left Frame (for controls and results) ---
        left_frame = ttk.Frame(top_frame, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # --- Right Frame (for alert configurations) ---
        right_frame = ttk.Labelframe(top_frame, text="Configuração dos Alertas", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.alert_info_text = ScrolledText(right_frame, wrap=tk.WORD, height=10)
        self.alert_info_text.pack(fill=tk.BOTH, expand=True)
        self.alert_info_text.configure(state="disabled")

        # --- Input Frame ---
        input_frame = ttk.Labelframe(left_frame, text="Parâmetros da Análise", padding=10)
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

        # --- Timeframes Frame ---
        timeframes_frame = ttk.Labelframe(left_frame, text="Períodos de Análise (Hit Rate)", padding=10)
        timeframes_frame.pack(fill=tk.X, pady=5)

        self.timeframe_vars = {}
        timeframes = {
            "5m": 5, "15m": 15, "30m": 30, "45m": 45,
            "1h": 60, "2h": 120, "6h": 360, "24h": 1440
        }

        col = 0
        for name, minutes in timeframes.items():
            var = tk.BooleanVar(value=(name in ['15m', '1h', '24h'])) # Default selection
            cb = ttk.Checkbutton(timeframes_frame, text=name, variable=var, bootstyle="primary")
            cb.grid(row=0, column=col, padx=5, pady=2, sticky="w")
            self.timeframe_vars[name] = {'var': var, 'minutes': minutes}
            col += 1

        # --- Action Frame ---
        action_frame = ttk.Frame(left_frame, padding=(0, 10))
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
        output_frame = ttk.Labelframe(left_frame, text="Resultados", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)

        # --- Treeview for structured results (placeholder) ---
        self.results_tree = ttk.Treeview(output_frame, show="headings", height=10)

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(fill=tk.BOTH, expand=True)

        # --- Summary Frame (placeholder) ---
        self.summary_frame = ttk.Labelframe(left_frame, text="Resumo da Taxa de Acerto", padding=10)
        self.summary_frame.pack(fill=tk.X, pady=(10, 5))
        self.summary_labels = {}

        self.queue = queue.Queue()
        self.root.after(100, self.process_queue)

        # --- Display Alert Configurations ---
        self._display_alert_configurations()

    def _display_alert_configurations(self):
        """
        Reads, formats, and displays the hardcoded alert logic in the right-side panel.
        This provides users with a clear view of the current alert rules.
        """
        config_text = """
Regras de Alerta Atuais:

--- COMPRA ---

1. RSI Sobrevenda:
   - Condição: RSI(14) <= 30
   - Descrição: Indica que o ativo pode estar sobrevendido e prestes a reverter a tendência de baixa.

2. Cruzamento de Alta do MACD:
   - Condição: Cruzamento de alta no MACD(12,26,9) E RSI(14) < 30.
   - Descrição: Sinal de compra forte, combinando momento (MACD) com condição de sobrevenda (RSI).

3. Cruz Dourada (Golden Cross):
   - Condição: MME(50) cruza para cima da MME(200).
   - Descrição: Sinal clássico de início de uma tendência de alta de longo prazo. Também desativa o "Modo Filtro".

4. HiLo Compra (Modo Filtro):
   - Condição: Preço cruza para cima do HiLo(34) E "Cruz da Morte" NÃO está ativa.
   - Descrição: Sinal de compra baseado no indicador HiLo, mas é ignorado se uma tendência de baixa de longo prazo ("Cruz da Morte") estiver em vigor.

5. Média Móvel para Cima (Modo Filtro):
   - Condição: Preço cruza para cima da MME(200) E MACD > 0 E "Cruz da Morte" NÃO está ativa.
   - Descrição: Confirmação de tendência de alta com o preço acima da média longa e momento positivo do MACD. Também é ignorado durante o "Modo Filtro".

--- VENDA ---

1. RSI Sobrecompra:
   - Condição: RSI(14) >= 75
   - Descrição: Indica que o ativo pode estar sobrecomprado e prestes a corrigir.

2. Cruzamento de Baixa do MACD:
   - Condição: Cruzamento de baixa no MACD(12,26,9).
   - Descrição: Sinal de possível reversão para uma tendência de baixa.

3. Cruz da Morte (Death Cross):
   - Condição: MME(50) cruza para baixo da MME(200) E o preço está abaixo da MME(200).
   - Descrição: Sinal forte de tendência de baixa. Ativa o "Modo Filtro", que desabilita os alertas 'HiLo Compra' e 'Média Móvel para Cima'.

4. HiLo Venda:
   - Condição: Preço cruza para baixo do HiLo(34).
   - Descrição: Sinal de venda baseado no indicador HiLo.

5. Média Móvel para Baixo:
   - Condição: Preço cruza para baixo da MME(17).
   - Descrição: Sinal de curto prazo que indica uma possível perda de força do preço.
"""
        # Enable the text widget to insert text, then disable it again
        self.alert_info_text.configure(state="normal")
        self.alert_info_text.delete("1.0", tk.END)
        self.alert_info_text.insert(tk.END, config_text)
        self.alert_info_text.configure(state="disabled")


    def setup_results_display(self, timeframes):
        """ Dynamically configures the Treeview and summary labels based on selected timeframes. """
        # --- Clear previous summary widgets ---
        for widget in self.summary_frame.winfo_children():
            widget.destroy()
        self.summary_labels.clear()

        # --- Configure Treeview ---
        base_columns = ["timestamp", "symbol", "condition", "price"]
        hit_rate_columns = [f"{prefix}_{tf}" for tf in timeframes for prefix in ("hit", "pct")]
        columns = base_columns + hit_rate_columns
        self.results_tree.config(columns=columns)

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

        # --- Configure Summary Labels ---
        for i, tf in enumerate(timeframes):
            label = ttk.Label(self.summary_frame, text=f"Período {tf}: N/A")
            label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.summary_labels[tf] = label

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
            timeframes = list(self.summary_labels.keys()) # Get dynamically set timeframes
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
        elif msg_type == "task_done":
            self.gui_task_done()

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

        # Get selected timeframes
        selected_timeframes = {name: data['minutes'] for name, data in self.timeframe_vars.items() if data['var'].get()}
        if not selected_timeframes:
            messagebox.showerror("Seleção Inválida", "Por favor, selecione pelo menos um período de análise.")
            self.gui_task_done() # Re-enable buttons
            self.run_button.config(state="normal")
            return

        # Setup display for the new run
        self.setup_results_display(list(selected_timeframes.keys()))

        # Clear previous results from the treeview
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)

        thread = threading.Thread(
            target=self.run_backtest_logic,
            args=(symbol, start_date, end_date, selected_timeframes),
            daemon=True
        )
        thread.start()

    def run_backtest_logic(self, symbol, start_date, end_date, timeframes_config):
        try:
            with open('backend/config.json', 'r') as f:
                config = json.load(f)
            crypto_config = next((c for c in config.get("cryptos_to_monitor", []) if c['symbol'] == symbol), {})
            alert_config = crypto_config.get('alert_config', {})
            if not alert_config:
                self.queue.put({"type": "status", "msg": f"AVISO: Nenhuma configuração de alerta para {symbol}."})
        except Exception as e:
            self.queue.put({"type": "error", "msg": f"ERRO ao ler config.json: {e}"})
            self.queue.put({"type": "task_done"})
            return

        # --- Cache Logic ---
        cache_key = generate_cache_key(symbol, start_date, end_date, alert_config, timeframes_config)
        cached_results = load_from_cache(cache_key)

        if cached_results:
            alerts = cached_results.get("alerts")
            # We still fetch historical data for the chart, not from cache.
            _, df = analyze_historical_alerts(symbol, start_date, end_date, alert_config, timeframes_config={})
        else:
            alerts, df = analyze_historical_alerts(symbol, start_date, end_date, alert_config, timeframes_config)
            if alerts:
                save_to_cache(cache_key, {"alerts": alerts}) # Cache new results

        self.backtest_df = df # Store historical data for the chart

        if not alerts:
            self.queue.put({"type": "status", "msg": f"Nenhum alerta encontrado para {symbol}."})
        else:
            formatted_signals = []
            for alert in alerts:
                if self.stop_event.is_set():
                    self.queue.put({"type": "status", "msg": "Análise interrompida pelo usuário."})
                    break
                self.queue.put({"type": "alert", "data": alert})
                # Re-format for the chart generator
                formatted_signals.append({
                    "timestamp": pd.to_datetime(alert["timestamp"]),
                    "price": alert["snapshot"]["price"],
                    "message": alert["description"]
                })
            self.backtest_signals = formatted_signals

        # Signal that the task is finished
        self.queue.put({"type": "task_done"})

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

        timeframes = list(self.summary_labels.keys()) # Get dynamically set timeframes
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
