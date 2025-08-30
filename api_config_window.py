# api_config_window.py (agora uma janela de configurações completa)

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkb

class ApiConfigWindow(ttkb.Toplevel):
    def __init__(self, master, parent_app): 
        super().__init__(master) # master já é a MainApplication
        self.parent_app = parent_app
        self.title("Configurações Gerais e Chaves de API")
        self.geometry("700x400") # PADRÃO COMPACTO
        self.transient(self.master)
        self.grab_set()

        self.bitquery_api_key_var = tk.StringVar(value=self.parent_app.config.get('bitquery_api_key', ''))
        self.telegram_token_var = tk.StringVar(value=self.parent_app.config.get('telegram_bot_token', ''))
        self.telegram_chat_id_var = tk.StringVar(value=self.parent_app.config.get('telegram_chat_id', ''))

        self.setup_ui()
        self.parent_app.center_toplevel_on_main(self)

    def setup_ui(self):
        main_frame = ttkb.Frame(self, padding=15)
        main_frame.pack(expand=True, fill='both')

        notebook = ttkb.Notebook(main_frame)
        notebook.pack(expand=True, fill='both')

        # --- Aba 1: Chaves de API ---
        api_tab = ttkb.Frame(notebook, padding=15)
        notebook.add(api_tab, text='Chaves de API')

        bitquery_frame = ttkb.Frame(api_tab)
        bitquery_frame.pack(fill='x', pady=5)
        ttkb.Label(bitquery_frame, text="Chave da API Bitquery:", width=20).pack(side='left', padx=(0, 10))
        self.bitquery_entry = ttkb.Entry(bitquery_frame, textvariable=self.bitquery_api_key_var)
        self.bitquery_entry.pack(side='left', fill='x', expand=True)
        
        ttkb.Label(api_tab, text="\n(Espaço para futuras chaves, como Binance, etc.)", bootstyle="secondary").pack(pady=10)

        # --- Aba 2: Notificações ---
        notifications_tab = ttkb.Frame(notebook, padding=15)
        notebook.add(notifications_tab, text='Notificações')
        
        telegram_header_frame = ttkb.Frame(notifications_tab)
        telegram_header_frame.pack(fill='x', pady=(5,10))
        
        ttkb.Label(telegram_header_frame, text="Configuração do Telegram", font=("-size 10 -weight bold")).pack(side='left')
        
        help_button = ttkb.Button(telegram_header_frame, text="❓", bootstyle="link", command=self.show_api_help)
        help_button.pack(side='left', padx=5)

        token_frame = ttkb.Frame(notifications_tab)
        token_frame.pack(fill='x', pady=5)
        ttkb.Label(token_frame, text="Bot Token:", width=15).pack(side='left', padx=(0, 10))
        self.token_entry = ttkb.Entry(token_frame, textvariable=self.telegram_token_var)
        self.token_entry.pack(side='left', fill='x', expand=True)

        chat_id_frame = ttkb.Frame(notifications_tab)
        chat_id_frame.pack(fill='x', pady=5)
        ttkb.Label(chat_id_frame, text="Chat ID:", width=15).pack(side='left', padx=(0, 10))
        self.chat_id_entry = ttkb.Entry(chat_id_frame, textvariable=self.telegram_chat_id_var)
        self.chat_id_entry.pack(side='left', fill='x', expand=True)

        # --- Botões de Ação ---
        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', pady=(15, 0), anchor='e')
        
        save_button = ttkb.Button(button_frame, text="Salvar e Fechar", command=self.save_settings, bootstyle="success")
        save_button.pack(side='right')

        cancel_button = ttkb.Button(button_frame, text="Cancelar", command=self.destroy, bootstyle="secondary-outline")
        cancel_button.pack(side='right', padx=10)

    def show_api_help(self):
        ApiHelpWindow(self)

    def save_settings(self):
        # Acessa self.parent_app.config para salvar os valores
        self.parent_app.config['bitquery_api_key'] = self.bitquery_api_key_var.get()
        self.parent_app.config['telegram_bot_token'] = self.telegram_token_var.get()
        self.parent_app.config['telegram_chat_id'] = self.telegram_chat_id_var.get()
        
        self.parent_app.save_config() # Chama o método save_config do MainApplication
        
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!", parent=self)
        self.destroy()

class ApiHelpWindow(ttkb.Toplevel):
    def __init__(self, parent): # parent é a ApiConfigWindow, que já é uma Toplevel
        super().__init__(parent)
        self.title("Como Obter as Chaves de API e IDs")
        self.geometry("800x600") # PADRÃO GRANDE
        self.transient(parent)
        self.grab_set()

        main_frame = ttkb.Frame(self, padding=10)
        main_frame.pack(expand=True, fill='both')

        text_widget = tk.Text(main_frame, wrap='word', font=("Segoe UI", 11), relief='flat', state='disabled', padx=10, pady=10)
        scrollbar = ttkb.Scrollbar(main_frame, orient='vertical', command=text_widget.yview, bootstyle="round-dark")
        text_widget['yscrollcommand'] = scrollbar.set
        
        scrollbar.pack(side='right', fill='y')
        text_widget.pack(side='left', expand=True, fill='both')

        help_content = """
Como Obter as Chaves e IDs Necessários

Siga este guia para configurar as integrações do programa.

----------------------------------------------------------------------
1. Telegram (Para receber alertas no seu celular)
----------------------------------------------------------------------

Você precisa de duas coisas: um "Bot Token" e um "Chat ID".

#### Para obter o Bot Token:
1.  Abra o Telegram e procure por um bot chamado "BotFather" (ele tem um selo de verificação azul).
2.  Inicie uma conversa com ele e digite `/newbot`.
3.  Siga as instruções: dê um nome para o seu bot (ex: "Meu Bot de Alertas Cripto") e depois um nome de usuário para ele (deve terminar com "bot", ex: `MeuAlertaCripto_bot`).
4.  O BotFather irá te fornecer um token. É uma longa sequência de letras e números. Copie este token e cole no campo "Bot Token".

#### Para obter o Chat ID:
1.  Depois de criar o bot, procure pelo nome de usuário dele no Telegram e inicie uma conversa com ele. Envie qualquer mensagem, como "oi".
2.  Agora, procure por outro bot chamado "userinfobot".
3.  Inicie uma conversa com o "userinfobot" e ele irá imediatamente te mostrar suas informações, incluindo seu "Id". Este é o seu Chat ID.
4.  Copie o número do ID e cole no campo "Chat ID".

----------------------------------------------------------------------
2. Bitquery (Para análise de fluxo de capital on-chain)
----------------------------------------------------------------------

A chave da Bitquery nos permite ver dados da blockchain, como o balanço de moedas nas exchanges.

1.  Acesse o site: https://bitquery.io/
2.  Clique em "Sign Up" e crie uma conta (o plano gratuito é suficiente).
3.  Após fazer login, você verá seu "Dashboard". No menu lateral, procure por "API KEY" ou algo similar.
4.  O site irá gerar uma chave de API para você.
5.  Copie essa chave e cole no campo "Chave da API Bitquery".
"""
        text_widget.config(state='normal')
        text_widget.insert('1.0', help_content)
        text_widget.config(state='disabled')