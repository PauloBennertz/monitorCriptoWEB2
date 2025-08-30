# capital_flow_window.py (VERSÃO COM BOTÃO DE CONFIGURAÇÕES E INJEÇÃO DE DEPENDÊNCIA)

import tkinter as tk
import ttkbootstrap as ttkb
import threading
import io
import sys
from datetime import datetime
from tkinter import messagebox

# Importa a função principal de análise de capital e a nova janela de configuração
try:
    from capital_flow import run_full_analysis
    from market_analysis_config_window import MarketAnalysisConfigWindow
except ImportError as e:
    messagebox.showerror("Erro de Importação", f"Não foi possível carregar módulos essenciais de análise: {e}")
    # Fallback para caso os arquivos não sejam encontrados
    def run_full_analysis(config, cg_client=None, data_cache_instance=None, rate_limiter_instance=None):
        print("ERRO CRÍTICO: O arquivo 'capital_flow.py' não foi encontrado ou sua assinatura de função está incorreta.")
    def MarketAnalysisConfigWindow(parent_app):
        messagebox.showerror("Erro", "O arquivo 'market_analysis_config_window.py' não foi encontrado.", parent=parent_app)
        return None

class CapitalFlowWindow(ttkb.Toplevel): # CORREÇÃO: Usar ttkb.Toplevel para consistência de estilo
    def __init__(self, master, parent_app, cg_client, data_cache_instance, rate_limiter_instance):
        super().__init__(master) # master já é a MainApplication
        self.parent_app = parent_app
        self.cg_client = cg_client
        self.data_cache = data_cache_instance
        self.rate_limiter = rate_limiter_instance

        self.title("Análise de Fluxo de Capital por Categoria")
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
        self.text_widget = tk.Text(text_frame, wrap='word', font=("Consolas", 11),
                                   bg="#23272b", fg="#f8f9fa", insertbackground="#f8f9fa",
                                   state='disabled', relief='flat')
        scrollbar = ttkb.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget['yscrollcommand'] = scrollbar.set
        scrollbar.pack(side='right', fill='y')
        self.text_widget.pack(side='left', expand=True, fill='both')

        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(fill='x')

        self.run_button = ttkb.Button(button_frame, text="🔄 Atualizar Análise",
                                      command=self.start_analysis_thread, bootstyle="info")
        self.run_button.pack(side='left', expand=True, fill='x', padx=(0, 5))

        self.config_button = ttkb.Button(button_frame, text="⚙️ Configurações",
                                         command=self.open_settings, bootstyle="secondary")
        self.config_button.pack(side='left', padx=(5, 0))

    def open_settings(self):
        """Abre a nova janela de configurações."""
        # Passa a instância do parent_app (MainApplication)
        if MarketAnalysisConfigWindow:
            # CORREÇÃO: Passa self.parent_app diretamente
            MarketAnalysisConfigWindow(self.parent_app)
        else:
            messagebox.showerror("Erro", "A janela de configuração de análise de mercado não está disponível.", parent=self)


    def start_analysis_thread(self):
        """Inicia a análise de fluxo de capital em uma thread separada para não bloquear a UI."""
        self.run_button['state'] = 'disabled'
        self.run_button['text'] = 'Analisando...'
        threading.Thread(target=self.run_analysis,
                         args=(self.parent_app.config, self.cg_client, self.data_cache, self.rate_limiter),
                         daemon=True).start()

    def run_analysis(self, config, cg_client, data_cache, rate_limiter):
        """
        Executa a análise de fluxo de capital.
        Os argumentos cg_client, data_cache e rate_limiter são recebidos da thread.
        """
        self.update_text_widget("", clear=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"Iniciando análise... (Última atualização: {timestamp})\n" + "="*80 + "\n\n"
        self.update_text_widget(header)

        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            run_full_analysis(config, cg_client, data_cache, rate_limiter)
        except Exception as e:
            print(f"\n--- ERRO INESPERADO NA JANELA ---\nOcorreu um erro não tratado: {e}")
        finally:
            sys.stdout = old_stdout

        result_text = captured_output.getvalue()
        # CORREÇÃO: Chama after diretamente na instância da MainApplication
        self.after(0, self.update_text_widget, result_text)
        self.after(0, self.finalize_analysis_ui)


    def update_text_widget(self, text, clear=False):
        self.text_widget['state'] = 'normal'
        if clear:
            self.text_widget.delete('1.0', tk.END)
        self.text_widget.insert(tk.END, text)
        self.text_widget['state'] = 'disabled'
        self.text_widget.see(tk.END)

    def finalize_analysis_ui(self):
        self.run_button['state'] = 'normal'
        self.run_button['text'] = '🔄 Atualizar Análise'