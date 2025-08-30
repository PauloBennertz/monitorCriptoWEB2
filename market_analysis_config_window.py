# market_analysis_config_window.py (NOVO ARQUIVO)

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb

class MarketAnalysisConfigWindow(ttkb.Toplevel):
    # CORREÇÃO: parent_app é a instância da MainApplication, não precisa de .root
    def __init__(self, parent_app):
        super().__init__(parent_app) # Use parent_app diretamente como master
        self.parent_app = parent_app
        self.title("Configurações da Análise de Mercado")
        self.geometry("500x300")
        self.minsize(400, 220)
        self.transient(self.master)
        self.grab_set()
        
        # Carrega a configuração atual ou define padrões
        # CORREÇÃO: Acessa config do parent_app diretamente
        self.market_analysis_config = self.parent_app.config.get('market_analysis_config', {}) 
        # CORREÇÃO: Garante que o valor seja uma string
        self.min_market_cap_var = tk.StringVar(value=str(self.market_analysis_config.get('min_market_cap', 50000000)))
        # CORREÇÃO: Adiciona a variável top_n_var que estava faltando
        self.top_n_var = tk.IntVar(value=self.market_analysis_config.get('top_n', 25))

        self.setup_ui()
        self.parent_app.center_toplevel_on_main(self)

    def setup_ui(self):
        main_frame = ttkb.Frame(self, padding=20)
        main_frame.pack(expand=True, fill='both')

        # --- Campo Top N ---
        top_n_frame = ttkb.Frame(main_frame)
        top_n_frame.pack(fill='x', pady=10)
        ttkb.Label(top_n_frame, text="Exibir Top N Categorias:", width=25, font=("-weight bold")).pack(side='left')
        self.top_n_spinbox = ttkb.Spinbox(top_n_frame, from_=5, to=100, increment=5, textvariable=self.top_n_var, font=("-weight bold"))
        self.top_n_spinbox.pack(side='left', fill='x', expand=True)

        # --- Campo Capitalização Mínima ---
        mcap_frame = ttkb.Frame(main_frame)
        mcap_frame.pack(fill='x', pady=10)
        ttkb.Label(mcap_frame, text="Capitalização Mínima ($):", width=25, font=("-weight bold")).pack(side='left')
        self.mcap_entry = ttkb.Entry(mcap_frame, textvariable=self.min_market_cap_var, font=("-weight bold"))
        self.mcap_entry.pack(side='left', fill='x', expand=True)
        
        info_label = ttkb.Label(main_frame, text="Ex: 50000000 para $50 Milhões. Filtra o 'ruído'.", bootstyle="secondary")
        info_label.pack(pady=(0, 20))

        # --- Botões ---
        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        save_button = ttkb.Button(button_frame, text="Salvar e Fechar", command=self.save_settings, bootstyle="success")
        save_button.pack(side='right')

        cancel_button = ttkb.Button(button_frame, text="Cancelar", command=self.destroy, bootstyle="secondary")
        cancel_button.pack(side='right', padx=10)

    def save_settings(self):
        """Valida e salva as novas configurações."""
        try:
            top_n = self.top_n_var.get()
            min_mcap_str = self.min_market_cap_var.get()
            
            if not min_mcap_str:
                min_mcap = 0
            else:
                # CORREÇÃO: Tenta converter para int, se falhar, assume 0
                try:
                    min_mcap = int(float(min_mcap_str)) # Converte para float primeiro para lidar com "50.0"
                except ValueError:
                    messagebox.showerror("Erro de Validação", "Por favor, insira um número válido para a Capitalização Mínima.", parent=self)
                    return


            if top_n <= 0 or min_mcap < 0:
                messagebox.showerror("Erro de Validação", "Os valores devem ser positivos.", parent=self)
                return

            # Atualiza o dicionário de configuração principal
            # CORREÇÃO: Atualiza self.parent_app.config diretamente
            self.parent_app.config['market_analysis_config'] = {
                'top_n': top_n,
                'min_market_cap': min_mcap
            }
            
            # Salva o arquivo config.json
            self.parent_app.save_config()
            
            messagebox.showinfo("Sucesso", "Configurações salvas! A próxima análise usará os novos valores.", parent=self)
            self.destroy()

        except (ValueError, tk.TclError): # Catch ValueError também para int(float_str)
            messagebox.showerror("Erro de Validação", "Por favor, insira valores numéricos válidos.", parent=self)