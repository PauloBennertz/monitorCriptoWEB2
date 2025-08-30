# token_movers_window.py (VERSÃO FINAL COM INJEÇÃO DE DEPENDÊNCIA)

import tkinter as tk
import ttkbootstrap as ttkb
import threading
from datetime import datetime
from tkinter import messagebox

try:
    from token_movers import run_token_analysis
except ImportError as e:
    messagebox.showerror("Erro de Importação", f"Não foi possível carregar o módulo 'token_movers.py': {e}")
    # Fallback para caso o arquivo não seja encontrado ou sua assinatura esteja incorreta
    def run_token_analysis(config, cg_client=None, data_cache_instance=None, rate_limiter_instance=None):
        raise ImportError("ERRO CRÍTICO: O arquivo 'token_movers.py' não foi encontrado ou sua assinatura de função está incorreta.")

class TokenMoversWindow(ttkb.Toplevel): # Usar ttkb.Toplevel para consistência de estilo
    def __init__(self, master, parent_app, cg_client, data_cache_instance, rate_limiter_instance):
        super().__init__(master) # master já é a MainApplication
        self.parent_app = parent_app
        self.cg_client = cg_client
        self.data_cache = data_cache_instance
        self.rate_limiter = rate_limiter_instance

        self.title("Análise de Ganhadores e Perdedores (Tokens)")

        self.geometry("1200x750")
        self.minsize(900, 600)

        self.setup_ui()
        self.parent_app.center_toplevel_on_main(self)
        self.transient(self.master)
        self.grab_set()


    def setup_ui(self):
        main_frame = ttkb.Frame(self, padding=15, relief="solid", borderwidth=1)
        main_frame.pack(expand=True, fill='both')

        text_frame = ttkb.Frame(main_frame, relief="solid", borderwidth=1)
        text_frame.pack(expand=True, fill='both', pady=(0, 10))
        self.text_widget = tk.Text(text_frame, wrap='word', font=("Consolas", 12), bg="#23272b", fg="#f8f9fa", insertbackground="#f8f9fa", state='disabled', relief='flat', borderwidth=0)
        scrollbar = ttkb.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side='right', fill='y')
        self.text_widget.pack(side='left', expand=True, fill='both')

        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(fill='x')

        self.run_button = ttkb.Button(button_frame, text="🔄 Atualizar Análise", command=self.start_analysis_thread, bootstyle="info")
        self.run_button.pack(side='left', expand=True, fill='x', padx=(0, 5))

        self.config_button = ttkb.Button(button_frame, text="⚙️ Configurações", command=self.open_settings, bootstyle="secondary")
        self.config_button.pack(side='left', padx=(5, 0))

        # --- DEFINIÇÃO DOS ESTILOS (TAGS) ---
        self.text_widget.tag_configure("header", font=("Consolas", 14, "bold"), foreground="#17a2b8") # Ciano
        self.text_widget.tag_configure("gainer_icon", font=("Consolas", 12), foreground="#28a745") # Verde
        self.text_widget.tag_configure("loser_icon", font=("Consolas", 12), foreground="#dc3545") # Vermelho
        self.text_widget.tag_configure("info", font=("Consolas", 10), foreground="#6c757d") # Cinza
        self.text_widget.tag_configure("faint", font=("Consolas", 11), foreground="#6c757d") # Cinza mais claro
        self.text_widget.tag_configure("symbol", font=("Consolas", 12, "bold"))

    def open_settings(self):
        # Implementação futura da janela de configurações para Token Movers
        messagebox.showinfo("Em Breve", "A janela de configuração para esta análise será implementada a seguir.", parent=self)

    def start_analysis_thread(self):
        """Inicia a análise de ganhadores e perdedores em uma thread separada para não bloquear a UI."""
        self.clear_text_widget()
        self.text_widget['state'] = 'normal'
        self.text_widget.insert(tk.END, "🚀 Analisando, por favor aguarde...")
        self.text_widget['state'] = 'disabled'
        self.run_button['state'] = 'disabled'
        self.run_button['text'] = 'Analisando...'
        threading.Thread(target=self.run_analysis,
                         args=(self.parent_app.config, self.cg_client, self.data_cache, self.rate_limiter),
                         daemon=True).start()

    def run_analysis(self, config, cg_client, data_cache, rate_limiter):
        """
        Executa a análise de ganhadores e perdedores.
        Os argumentos cg_client, data_cache e rate_limiter são recebidos da thread.
        """
        try:
            gainers, losers, status_message = run_token_analysis(config, cg_client, data_cache, rate_limiter)
            self.after(0, self.display_results, gainers, losers, status_message)
        except Exception as e:
            self.after(0, self.display_error, str(e))
        finally:
            self.after(0, self.finalize_analysis_ui)

    def display_results(self, gainers, losers, status_message):
        self.clear_text_widget()
        self.text_widget['state'] = 'normal'

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        self.text_widget.insert(tk.END, f"Última atualização: {timestamp}\n", "info")
        self.text_widget.insert(tk.END, status_message + "\n\n", "info")

        if gainers is not None and not gainers.empty:
            self.text_widget.insert(tk.END, f"✅ TOP {len(gainers)} - MAIORES GANHADORES (24h)\n", "header")
            for _, row in gainers.iterrows():
                self.format_and_insert_line(row, "gainer")

        if losers is not None and not losers.empty:
            self.text_widget.insert(tk.END, f"\n❌ TOP {len(losers)} - MAIORES PERDEDORES (24h)\n", "header")
            for _, row in losers.iterrows():
                self.format_and_insert_line(row, "loser")

        self.text_widget['state'] = 'disabled'

    def format_and_insert_line(self, row, line_type):
        market_cap_f = f"${row['market_cap']/1_000_000_000:.2f}B" if row['market_cap'] >= 1_000_000_000 else f"${row['market_cap']/1_000_000:.2f}M"
        volume_f = f"${row['total_volume']/1_000_000_000:.2f}B" if row['total_volume'] >= 1_000_000_000 else f"${row['total_volume']/1_000_000:.2f}M"

        symbol_text = f"  {row['name']} ({row['symbol'].upper()})".ljust(35)
        change_text = f"{row['price_change_percentage_24h']:+.2f}%".rjust(8)

        self.text_widget.insert(tk.END, symbol_text, "symbol")
        self.text_widget.insert(tk.END, f" {change_text} ", "gainer_icon" if line_type == "gainer" else "loser_icon")
        self.text_widget.insert(tk.END, f"| Cap: {market_cap_f.rjust(8)} | Vol: {volume_f.rjust(8)}\n", "faint")

    def display_error(self, error_message):
        self.clear_text_widget()
        self.text_widget['state'] = 'normal'
        self.text_widget.insert(tk.END, "Ocorreu um erro durante a análise:\n\n", "loser_icon")
        self.text_widget.insert(tk.END, error_message, "info")
        self.text_widget['state'] = 'disabled'

    def clear_text_widget(self):
        self.text_widget['state'] = 'normal'
        self.text_widget.delete('1.0', tk.END)
        self.text_widget['state'] = 'disabled'

    def finalize_analysis_ui(self):
        self.run_button['state'] = 'normal'
        self.run_button['text'] = '🔄 Atualizar Análise'