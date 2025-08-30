import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
try:
    import winsound
except ImportError:
    winsound = None
import ttkbootstrap as ttkb

TOOLTIP_DEFINITIONS = {
    "preco_baixo": "Alerta quando o preço da moeda cai e atinge o valor que você definiu.",
    "preco_alto": "Alerta quando o preço da moeda sobe e atinge o valor que você definiu.",
    "rsi_sobrevendido": "RSI (Índice de Força Relativa) abaixo de 30. Sugere que o ativo pode estar desvalorizado.",
    "rsi_sobrecomprado": "RSI (Índice de Força Relativa) acima de 70. Sugere que o ativo pode estar supervalorizado.",
    "bollinger_abaixo": "O preço fechou abaixo da linha inferior das Bandas de Bollinger.",
    "bollinger_acima": "O preço fechou acima da linha superior das Bandas de Bollinger.",
    "macd_cruz_baixa": "Cruzamento de Baixa do MACD. A linha MACD cruza para baixo da linha de sinal.",
    "macd_cruz_alta": "Cruzamento de Alta do MACD. A linha MACD cruza para cima da linha de sinal.",
    "mme_cruz_morte": "Cruz da Morte (MME 50 cruza para baixo da 200).",
    "mme_cruz_dourada": "Cruz Dourada (MME 50 cruza para cima da 200).",
    "fuga_capital_significativa": "Volume de negociação alto combinado com queda de preço. Sugere grande saída de capital.",
    "entrada_capital_significativa": "Volume de negociação alto combinado com alta de preço. Sugere grande entrada de capital.",
    "hilo_compra": "Sinal de compra do indicador HiLo. O preço cruzou acima da média móvel das máximas.",
    "hilo_venda": "Sinal de venda do indicador HiLo. O preço cruzou abaixo da média móvel das mínimas."
}

ALERT_SUMMARIES = {
    # RSI
    'RSI_SOBRECOMPRA': "RSI > 70: Ativo pode estar supervalorizado, risco de correção.",
    'RSI_SOBREVENDA': "RSI < 30: Ativo pode estar desvalorizado, potencial de alta.",
    # Bandas de Bollinger
    'PRECO_ACIMA_BANDA_SUPERIOR': "Preço acima da Banda de Bollinger Superior: Alta volatilidade, possível sobrecompra.",
    'PRECO_ABAIXO_BANDA_INFERIOR': "Preço abaixo da Banda de Bollinger Inferior: Alta volatilidade, possível sobrevenda.",
    # MACD
    'CRUZAMENTO_MACD_ALTA': "MACD cruzou para cima da linha de sinal: Sinal de momentum de alta.",
    'CRUZAMENTO_MACD_BAIXA': "MACD cruzou para baixo da linha de sinal: Sinal de momentum de baixa.",
    # Médias Móveis
    'CRUZ_DOURADA': "MME 50 cruzou acima da MME 200: Forte sinal de tendência de alta.",
    'CRUZ_DA_MORTE': "MME 50 cruzou abaixo da MME 200: Forte sinal de tendência de baixa.",
    # Padrão de Volume
    'VOLUME_ANORMAL': "Volume de negociação significativamente acima da média. Indica forte interesse ou evento.",
    # Padrão de Velas (Exemplo)
    'MARTELO_ALTA': "Padrão de vela 'Martelo': Pode indicar uma reversão de baixa para alta.",
    'ESTRELA_CADENTE_BAIXA': "Padrão de vela 'Estrela Cadente': Pode indicar uma reversão de alta para baixa."
}

def get_application_path():
    """Retorna o caminho do diretório da aplicação, compatível com PyInstaller."""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS  # Modo --onefile
        else:
            return os.path.dirname(sys.executable)  # Modo --onedir
    return os.path.dirname(os.path.abspath(__file__))

class CryptoCard(ttkb.Frame):
    """Componente visual para exibir os dados de uma criptomoeda."""
    def __init__(self, parent, symbol, coin_name=""):
        """Inicializa o card com o símbolo e nome da moeda."""
        super().__init__(parent, padding=15, bootstyle="secondary")
        self.symbol = symbol
        self.previous_price = 0.0

        header_frame = ttkb.Frame(self, bootstyle="secondary")
        header_frame.pack(fill='x', pady=(0, 10))
        
        self.symbol_label = ttkb.Label(header_frame, text=symbol, font=("Segoe UI", 16, "bold"), bootstyle="info")
        self.symbol_label.pack(side='left')
        self.full_name_label = ttkb.Label(header_frame, text=f"({coin_name})", font=("Segoe UI", 11), bootstyle="secondary")
        self.full_name_label.pack(side='left', padx=5, pady=(4,0))

        ttkb.Separator(self, bootstyle="dark").pack(fill='x', pady=(5, 10))

        price_frame = ttkb.Frame(self, bootstyle="secondary")
        price_frame.pack(fill='x', pady=(0, 10))
        
        ttkb.Label(price_frame, text="Preço:", font=("Segoe UI", 12), bootstyle="secondary").pack(side='left')
        self.price_value = ttkb.Label(price_frame, text="Carregando...", font=("Segoe UI", 14, "bold"), bootstyle="light")
        self.price_value.pack(side='right')

        self.data_labels = {"current_price": self.price_value}
        data_frame = ttkb.Frame(self, bootstyle="secondary")
        data_frame.pack(fill='x', pady=5)
        
        left_col = ttkb.Frame(data_frame, bootstyle="secondary")
        right_col = ttkb.Frame(data_frame, bootstyle="secondary")
        left_col.pack(side='left', fill='x', expand=True, padx=(0, 5))
        right_col.pack(side='right', fill='x', expand=True, padx=(5, 0))
        
        left_labels = {"price_change_24h": "Variação (24h):", "volume_24h": "Volume (24h):", "rsi_value": "RSI:"}
        right_labels = {"bollinger_signal": "Bollinger:", "macd_signal": "MACD:", "mme_cross": "MME:", "hilo_signal": "HiLo:"}

        for key, text in left_labels.items():
            self._create_label_pair(left_col, key, text)
        for key, text in right_labels.items():
            self._create_label_pair(right_col, key, text)

    def _create_label_pair(self, parent, key, text):
        """Cria um par de labels (descrição e valor) para um indicador."""
        indicator_frame = ttkb.Frame(parent, bootstyle="secondary")
        indicator_frame.pack(fill='x', pady=3)
        ttkb.Label(indicator_frame, text=text, font=("Segoe UI", 10), bootstyle="secondary").pack(side='left')
        value_label = ttkb.Label(indicator_frame, text="Carregando...", font=("Segoe UI", 10, "bold"), bootstyle="light")
        value_label.pack(side='right')
        self.data_labels[key] = value_label

class Tooltip:
    """Cria uma caixa de dicas que aparece ao passar o mouse sobre um widget."""
    def __init__(self, widget):
        """Inicializa o tooltip para um widget específico."""
        self.widget = widget
        self.tooltip_window = None

    def show_tooltip(self, text):
        """Exibe a caixa de dicas com o texto fornecido."""
        self.hide_tooltip()
        if not text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ttkb.Label(self.tooltip_window, text=text, justify='left', background="#1c1c1c", foreground="white", relief='solid', borderwidth=1, font=("Helvetica", 10, "normal"), padding=8, wraplength=400)
        label.pack(ipadx=1)

    def hide_tooltip(self):
        """Destrói a janela da caixa de dicas, se existir."""
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = None

class StartupConfigDialog(ttkb.Toplevel):
    """Janela de diálogo para a configuração inicial da sessão de monitoramento."""
    def __init__(self, parent, all_symbols_list, config):
        """Inicializa a janela de configuração inicial."""
        super().__init__(parent)
        self.title("Configuração de Sessão de Monitoramento")
        self.config = config
        self.all_symbols_master = all_symbols_list
        self.session_started = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.grab_set()
        self.geometry("800x600")

        main_frame = ttkb.Frame(self, padding=15, relief="solid", borderwidth=1)
        main_frame.pack(expand=True, fill='both')

        telegram_frame = ttkb.LabelFrame(main_frame, text="Configuração do Telegram", padding=15)
        telegram_frame.pack(fill='x', pady=(0, 15))
        
        ttkb.Label(telegram_frame, text="Bot Token:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.token_var = tk.StringVar(value=self.config.get("telegram_bot_token", ""))
        self.token_entry = ttkb.Entry(telegram_frame, textvariable=self.token_var, width=60)
        self.token_entry.grid(row=0, column=1, sticky='ew', padx=5)
        
        ttkb.Label(telegram_frame, text="Chat ID:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.chat_id_var = tk.StringVar(value=self.config.get("telegram_chat_id", ""))
        self.chat_id_entry = ttkb.Entry(telegram_frame, textvariable=self.chat_id_var, width=60)
        self.chat_id_entry.grid(row=1, column=1, sticky='ew', padx=5)
        telegram_frame.columnconfigure(1, weight=1)

        paned_window = ttkb.PanedWindow(main_frame, orient='horizontal')
        paned_window.pack(fill='both', expand=True)

        left_pane = ttkb.Frame(paned_window, padding=5)
        paned_window.add(left_pane, weight=1)

        ttkb.Label(left_pane, text="Moedas Disponíveis").pack(anchor='w')
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_available_list)
        search_entry = ttkb.Entry(left_pane, textvariable=self.search_var)
        search_entry.pack(fill='x', pady=(5, 10))
        
        self.available_listbox = tk.Listbox(left_pane, selectmode='extended', exportselection=False, height=15)
        self.available_listbox.pack(fill='both', expand=True)

        buttons_frame = ttkb.Frame(paned_window)
        paned_window.add(buttons_frame)
        
        ttkb.Button(buttons_frame, text=">>", command=self._add_symbols, bootstyle="outline").pack(pady=20, padx=10)
        ttkb.Button(buttons_frame, text="<<", command=self._remove_symbols, bootstyle="outline").pack(pady=20, padx=10)

        right_pane = ttkb.Frame(paned_window, padding=5)
        paned_window.add(right_pane, weight=1)
        
        ttkb.Label(right_pane, text="Moedas Monitoradas").pack(anchor='w')
        self.monitored_listbox = tk.Listbox(right_pane, selectmode='extended', exportselection=False)
        self.monitored_listbox.pack(fill='both', expand=True, pady=(5,0))

        start_button = ttkb.Button(main_frame, text="Iniciar Monitoramento", command=self.on_start, bootstyle="success", padding=10)
        start_button.pack(side='bottom', pady=(15, 0))

        self._populate_lists()
        self.center_window()

    def _populate_lists(self):
        """Preenche as listas de moedas disponíveis e monitoradas."""
        self.available_listbox.delete(0, tk.END)
        self.monitored_listbox.delete(0, tk.END)
        monitored_symbols = {crypto.get('symbol') for crypto in self.config.get("cryptos_to_monitor", []) if crypto.get('symbol')}
        for symbol in sorted(self.all_symbols_master):
            if symbol not in monitored_symbols: self.available_listbox.insert(tk.END, symbol)
        for symbol in sorted(list(monitored_symbols)): self.monitored_listbox.insert(tk.END, symbol)

    def _filter_available_list(self, *args):
        """Filtra a lista de moedas disponíveis com base na busca."""
        search_term = self.search_var.get().upper()
        self.available_listbox.delete(0, tk.END)
        monitored_symbols = set(self.monitored_listbox.get(0, tk.END))
        if not search_term:
            filtered_symbols = [s for s in sorted(self.all_symbols_master) if s not in monitored_symbols]
        else:
            filtered_symbols = [s for s in self.all_symbols_master if search_term in s.upper() and s not in monitored_symbols]
        for symbol in filtered_symbols: self.available_listbox.insert(tk.END, symbol)

    def _add_symbols(self):
        """Adiciona os símbolos selecionados à lista de moedas monitoradas."""
        selected_indices = self.available_listbox.curselection()
        if not selected_indices: return
        symbols_to_move = [self.available_listbox.get(i) for i in selected_indices]
        for symbol in sorted(symbols_to_move): self.monitored_listbox.insert(tk.END, symbol)
        for i in sorted(selected_indices, reverse=True): self.available_listbox.delete(i)

    def _remove_symbols(self):
        """Remove os símbolos selecionados da lista de moedas monitoradas."""
        selected_indices = self.monitored_listbox.curselection()
        if not selected_indices: return
        symbols_to_move = [self.monitored_listbox.get(i) for i in selected_indices]
        for symbol in symbols_to_move:
             all_items = list(self.available_listbox.get(0, tk.END))
             all_items.append(symbol)
             all_items.sort()
             self.available_listbox.delete(0, tk.END)
             for item in all_items: self.available_listbox.insert(tk.END, item)
        for i in sorted(selected_indices, reverse=True): self.monitored_listbox.delete(i)
        self._filter_available_list()

    def on_save(self):
        """Salva a configuração da sessão e fecha a janela."""
        self.config["telegram_bot_token"] = self.token_var.get()
        self.config["telegram_chat_id"] = self.chat_id_var.get()
        new_monitored_symbols = set(self.monitored_listbox.get(0, tk.END))
        current_configs = {crypto['symbol']: crypto for crypto in self.config.get("cryptos_to_monitor", []) if 'symbol' in crypto}
        new_config_list = []
        for symbol in sorted(list(new_monitored_symbols)):
            if symbol in current_configs:
                new_config_list.append(current_configs[symbol])
            else:
                default_alert_config = {"notes": "", "sound": "sons/Alerta.mp3", "conditions": { "preco_baixo": {"enabled": False, "value": 0.0}, "preco_alto": {"enabled": False, "value": 0.0}, "rsi_sobrevendido": {"enabled": True, "value": 30.0}, "rsi_sobrecomprado": {"enabled": True, "value": 70.0}, "bollinger_abaixo": {"enabled": True}, "bollinger_acima": {"enabled": True}, "macd_cruz_baixa": {"enabled": True}, "macd_cruz_alta": {"enabled": True}, "mme_cruz_morte": {"enabled": True}, "mme_cruz_dourada": {"enabled": True}, "hilo_compra": {"enabled": True}, "hilo_venda": {"enabled": True}, "fuga_capital_significativa": {"enabled": False, "value": "0.5, -2.0"}, "entrada_capital_significativa": {"enabled": False, "value": "0.3, 1.0"} }, "triggered_conditions": []}
                new_config_list.append({"symbol": symbol, "alert_config": default_alert_config})
        self.parent_app.config["cryptos_to_monitor"] = new_config_list
        self.parent_app.save_config()
        self.parent_app.update_coin_cards_display()
        messagebox.showinfo("Sucesso", "Lista de moedas atualizada.", parent=self)
        self.destroy()

    def on_close(self):
        """Define o estado da sessão como não iniciada ao fechar a janela."""
        self.session_started = False
        self.destroy()
    
    def center_window(self):
        """Centraliza a janela na tela."""
        self.update_idletasks()
        self.resizable(True, True)
        min_width, min_height = 700, 500
        self.minsize(min_width, min_height)
        width, height = self.winfo_width(), self.winfo_height()
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

class AlertConfigDialog(ttkb.Toplevel):
    """Janela de diálogo para configurar os alertas de uma moeda específica."""
    def __init__(self, parent_app, symbol, alert_config_data=None):
        """Inicializa a janela de configuração de alertas."""
        super().__init__(parent_app) 
        self.parent_app = parent_app
        self.result = None
        self.title(f"Configurar Alertas para {symbol}")
        self.geometry("700x750")
        self.transient(self.master)
        self.grab_set()
        self.symbol = symbol
        self.config_data = alert_config_data if alert_config_data else self._get_default_config()
        self.vars = {} 
        
        main_container = ttkb.Frame(self, bootstyle="dark", padding=15, relief="solid", borderwidth=1)
        main_container.pack(expand=True, fill="both")
        
        header_frame = ttkb.Frame(main_container, bootstyle="dark")
        header_frame.pack(fill="x", pady=(0, 15))
        
        ttkb.Label(header_frame, text=f"Alertas para {symbol}", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side="left")
        ttkb.Label(header_frame, text="Configure os parâmetros dos alertas", font=("Segoe UI", 12), bootstyle="secondary").pack(side="left", padx=(10, 0))

        common_frame = ttkb.LabelFrame(main_container, text="Configurações Gerais", padding=15, bootstyle="dark")
        common_frame.pack(side="top", fill="x", pady=(0, 15))
        
        notes_frame = ttkb.Frame(common_frame, bootstyle="dark")
        notes_frame.pack(fill="x", pady=5)
        
        ttkb.Label(notes_frame, text="Observações:", font=("Segoe UI", 10, "bold"), bootstyle="light").pack(side="left")
        self.notes_var = ttkb.StringVar(value=self.config_data.get('notes', ''))
        self.notes_entry = ttkb.Entry(notes_frame, textvariable=self.notes_var, font=("Segoe UI", 10), bootstyle="dark")
        self.notes_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        sound_frame = ttkb.Frame(common_frame, bootstyle="dark")
        sound_frame.pack(fill="x", pady=10)
        
        ttkb.Label(sound_frame, text="Arquivo de Som:", font=("Segoe UI", 10, "bold"), bootstyle="light").pack(side="left")
        
        sound_controls = ttkb.Frame(sound_frame, bootstyle="dark")
        sound_controls.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        self.sound_var = ttkb.StringVar(value=self.config_data.get('sound', 'sons/Alerta.mp3'))
        self.sound_entry = ttkb.Entry(sound_controls, textvariable=self.sound_var, state="readonly", font=("Segoe UI", 10), bootstyle="dark")
        self.sound_entry.pack(side="left", fill="x", expand=True)
        
        ttkb.Button(sound_controls, text="Procurar", command=self.browse_sound_file, bootstyle="info").pack(side="left", padx=5)
        ttkb.Button(sound_controls, text="Testar", command=self.preview_sound, bootstyle="success").pack(side="left")

        cooldown_frame = ttkb.Frame(common_frame, bootstyle="dark")
        cooldown_frame.pack(fill="x", pady=10)

        ttkb.Label(cooldown_frame, text="Cooldown do Alerta (minutos):", font=("Segoe UI", 10, "bold"), bootstyle="light").pack(side="left")

        self.cooldown_var = tk.IntVar(value=self.config_data.get('alert_cooldown_minutes', 60))
        cooldown_spinbox = ttkb.Spinbox(cooldown_frame, from_=1, to=1440, textvariable=self.cooldown_var, width=8)
        cooldown_spinbox.pack(side="left", padx=(10, 0))

        cooldown_tooltip = Tooltip(cooldown_spinbox)
        cooldown_spinbox.bind("<Enter>", lambda e, tt=cooldown_tooltip: tt.show_tooltip("Tempo mínimo (em minutos) entre alertas para a mesma condição."))
        cooldown_spinbox.bind("<Leave>", lambda e, tt=cooldown_tooltip: tt.hide_tooltip())

        ttkb.Separator(main_container, bootstyle="info").pack(fill="x", pady=10)
        
        conditions_header = ttkb.Frame(main_container, bootstyle="dark")
        conditions_header.pack(fill="x", pady=(0, 10))
        
        ttkb.Label(conditions_header, text="Gatilhos de Alerta", font=("Segoe UI", 14, "bold"), bootstyle="info").pack(side="left")

        help_button = ttkb.Button(conditions_header, text="Ajuda", bootstyle="secondary")
        help_button.pack(side="right")
        
        tooltip = Tooltip(help_button)
        help_button.bind("<Enter>", lambda e: tooltip.show_tooltip("Configure os alertas que deseja receber para esta moeda."))
        help_button.bind("<Leave>", lambda e: tooltip.hide_tooltip())
        
        conditions_outer_frame = ttkb.Frame(main_container, bootstyle="dark")
        conditions_outer_frame.pack(side="top", fill="both", expand=True)
        
        canvas = tk.Canvas(conditions_outer_frame, borderwidth=0, highlightthickness=0, bg="#2a2a2a")
        scrollbar = ttkb.Scrollbar(conditions_outer_frame, orient="vertical", command=canvas.yview, bootstyle="round-dark")
        conditions_frame = ttkb.Frame(canvas, bootstyle="dark", padding=(10, 0))
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas_frame_id = canvas.create_window((0, 0), window=conditions_frame, anchor="nw")
        conditions_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame_id, width=e.width))
        
        self.canvas = canvas  # Salvar referência do canvas
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        self._create_condition_widgets(conditions_frame)
        
        btn_frame = ttkb.Frame(main_container, bootstyle="dark", padding=(0, 15, 0, 0))
        btn_frame.pack(side="bottom", fill="x")
        
        ttkb.Button(btn_frame, text="Salvar", command=self.on_save, bootstyle="success").pack(side="left", padx=5)
        ttkb.Button(btn_frame, text="Cancelar", command=self.destroy, bootstyle="danger-outline").pack(side="left", padx=5)

        self.parent_app.center_toplevel_on_main(self)
        self.minsize(650, 700)
        self.resizable(True, True)

    def _on_mousewheel(self, event):
        """Permite a rolagem da lista de condições com o scroll do mouse."""
        # A direção da rolagem pode variar entre sistemas operacionais
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")

    def _get_default_config(self):
        """Retorna uma estrutura de configuração de alerta padrão."""
        return {"notes": "", "sound": "sons/Alerta.mp3", "alert_cooldown_minutes": 60, "conditions": {"preco_baixo": {"enabled": False, "value": 0.0}, "preco_alto": {"enabled": False, "value": 0.0}, "rsi_sobrevendido": {"enabled": False, "value": 30.0}, "rsi_sobrecomprado": {"enabled": False, "value": 70.0}, "bollinger_abaixo": {"enabled": False}, "bollinger_acima": {"enabled": False}, "macd_cruz_baixa": {"enabled": False}, "macd_cruz_alta": {"enabled": False}, "mme_cruz_morte": {"enabled": False}, "mme_cruz_dourada": {"enabled": False}, "hilo_compra": {"enabled": False}, "hilo_venda": {"enabled": False}}, "triggered_conditions": {}}

    def _create_condition_widgets(self, parent_frame):
        """Cria e organiza os widgets para cada condição de alerta."""
        icons = {'preco_baixo': '⬇️', 'preco_alto': '⬆️', 'rsi_sobrevendido': '🟢', 'rsi_sobrecomprado': '🔴', 'bollinger_abaixo': '↘️', 'bollinger_acima': '↗️', 'macd_cruz_baixa': '📉', 'macd_cruz_alta': '📈', 'mme_cruz_morte': '☠️', 'mme_cruz_dourada': '🌟', 'fuga_capital_significativa': '💸', 'entrada_capital_significativa': '💰', 'hilo_compra': '🟢', 'hilo_venda': '🔴'}
        condition_definitions = {'preco_baixo': {'text': 'Preço Abaixo de ($)', 'has_value': True, 'default': 0.0, 'icon': icons['preco_baixo'], 'category': 'price'}, 'preco_alto': {'text': 'Preço Acima de ($)', 'has_value': True, 'default': 0.0, 'icon': icons['preco_alto'], 'category': 'price'}, 'rsi_sobrevendido': {'text': 'RSI Sobrevendido (<=)', 'has_value': True, 'default': 30.0, 'icon': icons['rsi_sobrevendido'], 'category': 'indicator'}, 'rsi_sobrecomprado': {'text': 'RSI Sobrecomprado (>=)', 'has_value': True, 'default': 70.0, 'icon': icons['rsi_sobrecomprado'], 'category': 'indicator'}, 'bollinger_abaixo': {'text': 'Abaixo da Banda Inferior', 'has_value': False, 'icon': icons['bollinger_abaixo'], 'category': 'indicator'}, 'bollinger_acima': {'text': 'Acima da Banda Superior', 'has_value': False, 'icon': icons['bollinger_acima'], 'category': 'indicator'}, 'macd_cruz_baixa': {'text': 'MACD: Cruzamento de Baixa', 'has_value': False, 'icon': icons['macd_cruz_baixa'], 'category': 'indicator'}, 'macd_cruz_alta': {'text': 'MACD: Cruzamento de Alta', 'has_value': False, 'icon': icons['macd_cruz_alta'], 'category': 'indicator'}, 'mme_cruz_morte': {'text': 'MME: Cruz da Morte (50/200)', 'has_value': False, 'icon': icons['mme_cruz_morte'], 'category': 'indicator'}, 'mme_cruz_dourada': {'text': 'MME: Cruz Dourada (50/200)', 'has_value': False, 'icon': icons['mme_cruz_dourada'], 'category': 'indicator'}, 'hilo_compra': {'text': 'HiLo: Sinal de Compra', 'has_value': False, 'icon': icons['hilo_compra'], 'category': 'indicator'}, 'hilo_venda': {'text': 'HiLo: Sinal de Venda', 'has_value': False, 'icon': icons['hilo_venda'], 'category': 'indicator'}, 'fuga_capital_significativa': {'text': 'Fuga de Capital (Vol %, Var %)', 'has_value': True, 'default': "0.5, -2.0", 'icon': icons['fuga_capital_significativa'], 'category': 'volume', 'info_tooltip': 'Ex: "0.5, -2.0" para 0.5% do Cap.Merc. e variação menor que -2%.'}, 'entrada_capital_significativa': {'text': 'Entrada de Capital (Vol %, Var %)', 'has_value': True, 'default': "0.3, 1.0", 'icon': icons['entrada_capital_significativa'], 'category': 'volume', 'info_tooltip': 'Ex: "0.3, 1.0" para 0.3% do Cap.Merc. e variação maior que 1%.'}}
        categories = {'price': {'title': 'Alertas de Preço', 'color': 'info', 'icon': '💲'}, 'indicator': {'title': 'Alertas de Indicadores Técnicos', 'color': 'warning', 'icon': '📊'}, 'volume': {'title': 'Alertas de Volume e Capital', 'color': 'success', 'icon': '📈'}}

        categorized_conditions = {}
        for key, details in condition_definitions.items():
            category = details.get('category', 'other')
            if category not in categorized_conditions: categorized_conditions[category] = []
            categorized_conditions[category].append((key, details))
        
        row = 0
        for category, cat_info in categories.items():
            if category in categorized_conditions:
                category_frame = ttkb.Frame(parent_frame, bootstyle="dark")
                category_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(15, 5))
                ttkb.Label(category_frame, text=f"{cat_info['icon']} {cat_info['title']}", font=("Segoe UI", 12, "bold"), bootstyle=cat_info['color']).pack(side="left")
                ttkb.Separator(parent_frame, bootstyle=cat_info['color']).grid(row=row+1, column=0, columnspan=2, sticky='ew', pady=(0, 10))
                row += 2
                
                for key, details in categorized_conditions[category]:
                    current_cond_config = self.config_data.get('conditions', {}).get(key, {})
                    enabled_var = tk.BooleanVar(value=current_cond_config.get('enabled', False))
                    value_var = None
                    
                    condition_frame = ttkb.Frame(parent_frame, bootstyle="dark")
                    condition_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=5)
                    
                    if details['has_value']:
                        default_value = str(details.get('default', 0.0))
                        current_value = current_cond_config.get('value', default_value)
                        value_var = tk.StringVar(value=current_value) if key in ['fuga_capital_significativa', 'entrada_capital_significativa'] else tk.DoubleVar(value=float(current_value))
                    
                    self.vars[key] = {'enabled': enabled_var, 'value': value_var}
                    
                    cb = ttkb.Checkbutton(condition_frame, text=f"{details.get('icon', '')} {details['text']}", variable=enabled_var, bootstyle=f"{cat_info['color']}")
                    cb.pack(side="left", padx=(5, 10))
                    
                    tooltip_text = TOOLTIP_DEFINITIONS.get(key, "Sem descrição.")
                    if 'info_tooltip' in details: tooltip_text += f"\n\nDica: {details['info_tooltip']}"
                    tooltip = Tooltip(cb)
                    cb.bind("<Enter>", lambda e, text=tooltip_text, tt=tooltip: tt.show_tooltip(text))
                    cb.bind("<Leave>", lambda e, tt=tooltip: tt.hide_tooltip())
                    
                    if details['has_value']:
                        entry = ttkb.Entry(condition_frame, textvariable=value_var, width=15, font=("Segoe UI", 10), bootstyle="dark")
                        entry.pack(side="right", padx=5)
                        cb.config(command=lambda e=entry, v=enabled_var: e.config(state='normal' if v.get() else 'disabled'))
                        entry.config(state='normal' if enabled_var.get() else 'disabled')
                    row += 1
        parent_frame.columnconfigure(0, weight=1)

    def browse_sound_file(self):
        """Abre uma caixa de diálogo para o usuário selecionar um arquivo de som .wav."""
        app_path = get_application_path()
        initial_dir = os.path.join(app_path, 'sons')
        if not os.path.isdir(initial_dir): initial_dir = app_path
        if filepath := filedialog.askopenfilename(title="Selecione um arquivo .wav", initialdir=initial_dir, filetypes=[("Arquivos de Som", "*.wav")]):
            self.sound_var.set(os.path.relpath(filepath, app_path))

    def preview_sound(self):
        """Toca o som de alerta selecionado como uma prévia."""
        if not (sound_path_str := self.sound_var.get()):
            messagebox.showwarning("Aviso", "Nenhum arquivo de som selecionado.", parent=self); return

        if not winsound:
            messagebox.showwarning("Aviso", "O módulo de som não está disponível neste sistema.", parent=self)
            return

        sound_path = sound_path_str if os.path.isabs(sound_path_str) else os.path.join(get_application_path(), sound_path_str)
        if os.path.exists(sound_path):
            try: winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e: messagebox.showerror("Erro", f"Não foi possível tocar o som:\n{e}", parent=self)
        else: messagebox.showerror("Erro", "Arquivo de som não encontrado.", parent=self)
    
    def on_save(self):
        """Valida e salva a configuração de alerta."""
        final_config = {"symbol": self.symbol, "alert_config": {"notes": self.notes_var.get(), "sound": self.sound_var.get(), "alert_cooldown_minutes": self.cooldown_var.get(), "conditions": {}, "triggered_conditions": self.config_data.get('triggered_conditions', [])}}
        for key, var_dict in self.vars.items():
            is_enabled = var_dict['enabled'].get()
            condition_data = {"enabled": is_enabled}
            if var_dict['value'] is not None:
                try:
                    value = var_dict['value'].get()
                    if key in ['preco_baixo', 'preco_alto', 'rsi_sobrevendido', 'rsi_sobrecomprado']:
                        value = float(value)
                        if is_enabled and value <= 0 and key in ['preco_baixo', 'preco_alto']:
                             messagebox.showerror("Erro de Validação", f"O valor para '{key.replace('_',' ').title()}' deve ser maior que zero.", parent=self); return
                    elif key in ['fuga_capital_significativa', 'entrada_capital_significativa']:
                        parts = str(value).split(',')
                        if len(parts) != 2 or not all(self._is_float(p.strip()) for p in parts):
                            messagebox.showerror("Erro de Validação", f"Formato inválido para '{key.replace('_',' ').title()}'. Use 'num,num'.", parent=self); return
                    condition_data["value"] = value
                except (tk.TclError, ValueError):
                    messagebox.showerror("Erro de Validação", f"Por favor, insira um número válido para '{key.replace('_',' ').title()}'.", parent=self); return
            final_config["alert_config"]["conditions"][key] = condition_data
        self.result = final_config
        self.destroy()

    def _is_float(self, s):
        """Verifica se uma string pode ser convertida para float."""
        try: float(s); return True
        except ValueError: return False

class AlertManagerWindow(ttkb.Toplevel):
    """Janela para gerenciar (adicionar/remover/configurar) todas as moedas monitoradas."""
    def __init__(self, parent_app, coin_manager):
        """Inicializa o gerenciador de alertas."""
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.coin_manager = coin_manager
        self.title("Gerenciador de Alertas")
        self.geometry("1200x700")
        self.minsize(900, 600)
        self.resizable(True, True)
        self.transient(self.master)
        self.grab_set()
        
        main_container = ttkb.Frame(self, padding=15, bootstyle="dark", relief="solid", borderwidth=1)
        main_container.pack(expand=True, fill='both')
        
        header_frame = ttkb.Frame(main_container, bootstyle="dark")
        header_frame.pack(fill='x', pady=(0, 15))
        
        ttkb.Label(header_frame, text="GERENCIADOR DE ALERTAS", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side="left")
        ttkb.Label(header_frame, text="Configuração personalizada por moeda", font=("Segoe UI", 12), bootstyle="secondary").pack(side="left", padx=(10, 0))

        self.paned_window = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        self.paned_window.pack(expand=True, fill='both')
        
        symbols_container = ttkb.Frame(self.paned_window, padding=5, bootstyle="dark")
        self.paned_window.add(symbols_container, weight=1)
        
        symbols_header = ttkb.Frame(symbols_container, bootstyle="dark")
        symbols_header.pack(fill='x', pady=(0, 10))
        
        ttkb.Label(symbols_header, text="Moedas Monitoradas", font=("Segoe UI", 13, "bold"), bootstyle="light").pack(side="left")
        
        search_frame = ttkb.Frame(symbols_container, bootstyle="dark")
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttkb.Label(search_frame, text="🔍", font=("Segoe UI", 12), bootstyle="secondary").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttkb.Entry(search_frame, textvariable=self.search_var, bootstyle="dark")
        search_entry.pack(side="left", fill="x", expand=True)
        
        symbols_frame = ttkb.Frame(symbols_container, bootstyle="dark")
        symbols_frame.pack(fill='both', expand=True)
        
        self.symbols_tree = ttkb.Treeview(symbols_frame, columns=('symbol',), show='headings', bootstyle="dark", height=20)
        self.symbols_tree.heading('symbol', text='Símbolo')
        self.symbols_tree.column('symbol', width=150, anchor=tk.W)
        
        symbols_scrollbar = ttkb.Scrollbar(symbols_frame, orient="vertical", command=self.symbols_tree.yview, bootstyle="round-dark")
        self.symbols_tree.configure(yscrollcommand=symbols_scrollbar.set)
        self.symbols_tree.pack(side="left", expand=True, fill='both')
        symbols_scrollbar.pack(side="right", fill='y')
        self.symbols_tree.bind("<<TreeviewSelect>>", self.on_symbol_selected)
        
        ttkb.Button(symbols_container, text="Adicionar/Remover Moedas", command=self.manage_monitored_symbols, bootstyle="success").pack(side='bottom', fill='x', pady=(10, 0))

        alerts_container = ttkb.Frame(self.paned_window, padding=5, bootstyle="dark")
        self.paned_window.add(alerts_container, weight=2)
        
        alerts_header = ttkb.Frame(alerts_container, bootstyle="dark")
        alerts_header.pack(fill='x', pady=(0, 10))
        
        self.alert_title = ttkb.Label(alerts_header, text="Condições de Alerta", font=("Segoe UI", 13, "bold"), bootstyle="light")
        self.alert_title.pack(side="left")
        self.selected_coin = ttkb.Label(alerts_header, text="", font=("Segoe UI", 13, "bold"), bootstyle="warning")
        self.selected_coin.pack(side="left", padx=(10, 0))
        
        alerts_table_frame = ttkb.LabelFrame(alerts_container, text="Condições de Alerta Ativadas", padding=15, bootstyle="dark")
        alerts_table_frame.pack(expand=True, fill='both', pady=(0, 15))
        
        self.conditions_tree = ttkb.Treeview(alerts_table_frame, columns=('condition', 'value'), show='headings', bootstyle="dark", height=15)
        self.conditions_tree.heading('condition', text='Condição')
        self.conditions_tree.column('condition', width=300, anchor=tk.W)
        self.conditions_tree.heading('value', text='Valor/Estado')
        self.conditions_tree.column('value', width=200, anchor=tk.W)
        
        conditions_scrollbar = ttkb.Scrollbar(alerts_table_frame, orient="vertical", command=self.conditions_tree.yview, bootstyle="round-dark")
        self.conditions_tree.configure(yscrollcommand=conditions_scrollbar.set)
        self.conditions_tree.pack(side="left", expand=True, fill='both')
        conditions_scrollbar.pack(side="right", fill='y')
        
        alerts_controls_frame = ttkb.Frame(alerts_container, bootstyle="dark", padding=5)
        alerts_controls_frame.pack(fill='x')
        
        self.config_alert_btn = ttkb.Button(alerts_controls_frame, text="Configurar Alertas", command=self.open_config_alert_dialog, bootstyle="info", state="disabled")
        self.config_alert_btn.pack(side='left', padx=5)
        
        ttkb.Button(alerts_controls_frame, text="Ajuda", bootstyle="secondary").pack(side='right', padx=5)
        
        status_bar = ttkb.Frame(main_container, bootstyle="dark", padding=(0, 10, 0, 0))
        status_bar.pack(fill='x', side="bottom")
        ttkb.Label(status_bar, text="Selecione uma moeda para visualizar ou configurar seus alertas", font=("Segoe UI", 10), bootstyle="secondary").pack(side="left")
        
        self._populate_symbols_tree()
        self.search_var.trace_add("write", self._filter_symbols)
        self.parent_app.center_toplevel_on_main(self)
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Permite a rolagem contextual com o scroll do mouse."""
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget is None:
            return

        if self.symbols_tree.winfo_ismapped() and (widget == self.symbols_tree or widget.winfo_parent() == self.symbols_tree.winfo_parent()):
            target_tree = self.symbols_tree
        elif self.conditions_tree.winfo_ismapped() and (widget == self.conditions_tree or widget.winfo_parent() == self.conditions_tree.winfo_parent()):
            target_tree = self.conditions_tree
        else:
            return

        if event.num == 5 or event.delta == -120:
            target_tree.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            target_tree.yview_scroll(-1, "units")

    def _filter_symbols(self, *args):
        """Filtra a lista de moedas na treeview com base no texto de busca."""
        search_term = self.search_var.get().lower()

        # Limpa a seleção e a árvore
        self.symbols_tree.selection_remove(self.symbols_tree.selection())
        for i in self.symbols_tree.get_children():
            self.symbols_tree.delete(i)

        # Repopula com base no filtro
        monitored_symbols = [crypto.get('symbol') for crypto in self.parent_app.config.get("cryptos_to_monitor", []) if crypto.get('symbol')]
        for symbol in sorted(monitored_symbols):
            if search_term in symbol.lower():
                self.symbols_tree.insert('', tk.END, iid=symbol, values=(f"💰 {symbol}",))

        self.on_symbol_selected()
        
    def _populate_symbols_tree(self):
        """Preenche a árvore de símbolos com as moedas atualmente monitoradas."""
        self.symbols_tree.selection_remove(self.symbols_tree.selection())
        for i in self.symbols_tree.get_children(): self.symbols_tree.delete(i)
        monitored_symbols = [crypto.get('symbol') for crypto in self.parent_app.config.get("cryptos_to_monitor", []) if crypto.get('symbol')]
        for symbol in sorted(monitored_symbols): self.symbols_tree.insert('', tk.END, iid=symbol, values=(f"💰 {symbol}",))
        self.on_symbol_selected()

    def on_symbol_selected(self, event=None):
        """Atualiza o painel de detalhes quando um símbolo é selecionado."""
        selected_items = self.symbols_tree.selection()
        if not selected_items:
            for i in self.conditions_tree.get_children(): self.conditions_tree.delete(i)
            self.config_alert_btn['state'] = 'disabled'
            return
        self.config_alert_btn['state'] = 'normal'
        self._populate_conditions_summary(selected_items[0])
        
    def _populate_conditions_summary(self, symbol):
        """Preenche a tabela de resumo de condições para o símbolo selecionado."""
        for i in self.conditions_tree.get_children(): self.conditions_tree.delete(i)
        crypto_config = next((c for c in self.parent_app.config.get("cryptos_to_monitor", []) if c.get('symbol') == symbol), None)
        if not crypto_config or 'alert_config' not in crypto_config:
            self.conditions_tree.insert('', tk.END, values=("Nenhuma configuração encontrada.", ""))
            return
        conditions = crypto_config['alert_config'].get('conditions', {})
        any_enabled = False
        for key, details in conditions.items():
            if details.get('enabled'):
                any_enabled = True
                value_str = f"{details.get('value', '')}" if 'value' in details else "Ativado"
                self.conditions_tree.insert('', tk.END, values=(key.replace('_', ' ').title(), value_str))
        if not any_enabled: self.conditions_tree.insert('', tk.END, values=("Nenhuma condição habilitada.", ""))

    def get_selected_symbol(self):
        """Retorna o símbolo atualmente selecionado na árvore."""
        return self.symbols_tree.selection()[0] if self.symbols_tree.selection() else None
        
    def open_config_alert_dialog(self):
        """Abre a janela de configuração de alertas para o símbolo selecionado."""
        if not (selected_symbol := self.get_selected_symbol()): return
        crypto_config = next((c for c in self.parent_app.config.get("cryptos_to_monitor", []) if c.get('symbol') == selected_symbol), None)
        dialog = AlertConfigDialog(self.parent_app, selected_symbol, alert_config_data=crypto_config.get('alert_config'))
        self.wait_window(dialog)
        if dialog.result:
            symbol_to_update = dialog.result.pop('symbol')
            found = False
            for crypto in self.parent_app.config.get("cryptos_to_monitor", []):
                if crypto.get('symbol') == symbol_to_update:
                    crypto['alert_config'] = dialog.result['alert_config']; found = True; break
            if not found: self.parent_app.config["cryptos_to_monitor"].append(dialog.result)
            self.parent_app.save_config()
            messagebox.showinfo("Sucesso", "Configuração de alerta salva!", parent=self)
            self._populate_conditions_summary(selected_symbol)

    def manage_monitored_symbols(self):
        """Abre a janela de diálogo para adicionar/remover moedas."""
        dialog = ManageSymbolsDialog(self, self.coin_manager)
        self.wait_window(dialog)
        self._populate_symbols_tree()

class ManageSymbolsDialog(ttkb.Toplevel):
    """Janela de diálogo para adicionar e remover moedas da lista de monitoramento."""
    def __init__(self, parent_manager, coin_manager):
        """Inicializa o diálogo de gerenciamento de moedas."""
        super().__init__(parent_manager.parent_app)
        self.parent_app = parent_manager.parent_app
        self.parent_manager = parent_manager
        self.coin_manager = coin_manager
        self.title("Gerenciar Moedas Monitoradas")
        self.geometry("800x600")
        self.transient(self.master)
        self.grab_set()
        main_frame = ttkb.Frame(self, padding=15, relief="solid", borderwidth=1)
        main_frame.pack(expand=True, fill='both')
        left_frame = ttkb.LabelFrame(main_frame, text="Moedas Disponíveis", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        self.available_search_var = ttkb.StringVar()
        self.available_search_var.trace_add("write", self._filter_available)
        self.available_entry = ttkb.Entry(left_frame, textvariable=self.available_search_var)
        self.available_entry.pack(fill='x', pady=(0, 5))
        self.available_listbox = tk.Listbox(left_frame, selectmode='extended', exportselection=False)
        self.available_listbox.pack(fill='both', expand=True)
        buttons_frame = ttkb.Frame(main_frame, padding=10)
        buttons_frame.pack(side='left', fill='y', anchor='center')
        ttkb.Button(buttons_frame, text="Adicionar >>", command=self._add_symbols, bootstyle="success-outline").pack(pady=5)
        ttkb.Button(buttons_frame, text="<< Remover", command=self._remove_symbols, bootstyle="danger-outline").pack(pady=5)
        right_frame = ttkb.LabelFrame(main_frame, text="Moedas Monitoradas", padding=10)
        right_frame.pack(side='left', fill='both', expand=True, padx=(5, 0))
        self.monitored_search_var = ttkb.StringVar()
        self.monitored_search_var.trace_add("write", self._filter_monitored)
        self.monitored_entry = ttkb.Entry(right_frame, textvariable=self.monitored_search_var)
        self.monitored_entry.pack(fill='x', pady=(0, 5))
        self.monitored_listbox = tk.Listbox(right_frame, selectmode='extended', exportselection=False)
        self.monitored_listbox.pack(fill='both', expand=True)
        bottom_frame = ttkb.Frame(self, padding=10)
        bottom_frame.pack(side='bottom', fill='x')
        ttkb.Button(bottom_frame, text="Salvar Alterações", command=self.on_save, bootstyle="success").pack(side='left')
        ttkb.Button(bottom_frame, text="Cancelar", command=self.destroy, bootstyle="secondary").pack(side='left', padx=10)
        self._populate_lists()
        self.parent_app.center_toplevel_on_main(self)
        self.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Permite a rolagem contextual com o scroll do mouse."""
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget is None:
            return

        if widget == self.available_listbox or widget.winfo_parent() == self.available_listbox.winfo_parent():
            target_listbox = self.available_listbox
        elif widget == self.monitored_listbox or widget.winfo_parent() == self.monitored_listbox.winfo_parent():
            target_listbox = self.monitored_listbox
        else:
            return

        if event.num == 5 or event.delta == -120:
            target_listbox.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            target_listbox.yview_scroll(-1, "units")
            
    def _populate_lists(self):
        """Preenche as listas de moedas disponíveis e monitoradas usando a lista da Binance."""
        self.all_symbols_master = sorted(self.parent_app.all_symbols)
        monitored_symbols = {crypto['symbol'] for crypto in self.parent_app.config.get("cryptos_to_monitor", [])}

        self.available_listbox.delete(0, tk.END)
        self.monitored_listbox.delete(0, tk.END)

        for symbol in self.all_symbols_master:
            if symbol not in monitored_symbols:
                self.available_listbox.insert(tk.END, symbol)

        for symbol in sorted(list(monitored_symbols)):
            self.monitored_listbox.insert(tk.END, symbol)
        
    def _filter_available(self, *args):
        """Filtra a lista de moedas disponíveis com base na busca."""
        search_term = self.available_search_var.get().lower()
        self.available_listbox.delete(0, tk.END)
        monitored_symbols = set(self.monitored_listbox.get(0, tk.END))

        for symbol in self.all_symbols_master:
            if search_term in symbol.lower() and symbol not in monitored_symbols:
                self.available_listbox.insert(tk.END, symbol)

    def _filter_monitored(self, *args):
        """Filtra a lista de moedas monitoradas com base na busca."""
        search_term = self.monitored_search_var.get().lower()
        self.monitored_listbox.delete(0, tk.END)

        # We need the original list of monitored symbols from the config to filter from
        all_monitored_symbols = {crypto['symbol'] for crypto in self.parent_app.config.get("cryptos_to_monitor", [])}

        for symbol in sorted(list(all_monitored_symbols)):
            if search_term in symbol.lower():
                self.monitored_listbox.insert(tk.END, symbol)

    def _add_symbols(self):
        """Adiciona os símbolos selecionados à lista de moedas monitoradas."""
        selected_indices = self.available_listbox.curselection()
        if not selected_indices: return
        symbols_to_move = [self.available_listbox.get(i) for i in selected_indices]

        # Adicionar à lista de monitorados e ordenar
        current_monitored = list(self.monitored_listbox.get(0, tk.END))
        for symbol in symbols_to_move:
            if symbol not in current_monitored:
                current_monitored.append(symbol)

        self.monitored_listbox.delete(0, tk.END)
        for symbol in sorted(current_monitored):
            self.monitored_listbox.insert(tk.END, symbol)

        # Remover da lista de disponíveis
        for i in sorted(selected_indices, reverse=True):
            self.available_listbox.delete(i)

    def _remove_symbols(self):
        """Remove os símbolos selecionados da lista de moedas monitoradas."""
        selected_indices = self.monitored_listbox.curselection()
        if not selected_indices: return
        symbols_to_move = [self.monitored_listbox.get(i) for i in selected_indices]

        # Adicionar de volta à lista de disponíveis e ordenar
        current_available = list(self.available_listbox.get(0, tk.END))
        for symbol in symbols_to_move:
            if symbol not in current_available:
                current_available.append(symbol)
        
        self.available_listbox.delete(0, tk.END)
        for symbol in sorted(current_available):
            self.available_listbox.insert(tk.END, symbol)

        # Remover da lista de monitorados
        for i in sorted(selected_indices, reverse=True):
            self.monitored_listbox.delete(i)

    def on_save(self):
        """Salva a nova lista de moedas monitoradas na configuração."""
        new_monitored_symbols = set(self.monitored_listbox.get(0, tk.END))
        current_configs = {crypto['symbol']: crypto for crypto in self.parent_app.config.get("cryptos_to_monitor", [])}

        new_config_list = []
        for symbol in sorted(list(new_monitored_symbols)):
            if symbol in current_configs:
                new_config_list.append(current_configs[symbol])
            else:
                # Adicionar uma configuração padrão para a nova moeda
                new_config_list.append({
                    "symbol": symbol,
                    "alert_config": self._get_default_alert_config()
                })

        self.parent_app.config["cryptos_to_monitor"] = new_config_list
        self.parent_app.save_config()
        self.parent_app.update_coin_cards_display() # Atualiza a tela principal
        self.parent_manager._populate_symbols_tree() # Atualiza a lista no AlertManagerWindow
        messagebox.showinfo("Sucesso", "Lista de moedas atualizada.", parent=self)
        self.destroy()

    def _get_default_alert_config(self):
        """Retorna uma configuração de alerta padrão para uma nova moeda."""
        return {
            "notes": "",
            "sound": "sons/Alerta.mp3",
            "alert_cooldown_minutes": 60,
            "conditions": {
                "preco_baixo": {"enabled": False, "value": 0.0},
                "preco_alto": {"enabled": False, "value": 0.0},
                "rsi_sobrevendido": {"enabled": True, "value": 30.0},
                "rsi_sobrecomprado": {"enabled": True, "value": 70.0},
                "bollinger_abaixo": {"enabled": True},
                "bollinger_acima": {"enabled": True},
                "macd_cruz_baixa": {"enabled": True},
                "macd_cruz_alta": {"enabled": True},
                "mme_cruz_morte": {"enabled": True},
                "mme_cruz_dourada": {"enabled": True},
                "hilo_compra": {"enabled": True},
                "hilo_venda": {"enabled": True},
                "fuga_capital_significativa": {"enabled": False, "value": "0.5, -2.0"},
                "entrada_capital_significativa": {"enabled": False, "value": "0.3, 1.0"}
            },
            "triggered_conditions": {}
        }

class AlertHistoryWindow(ttkb.Toplevel):
    """Janela para exibir o histórico de todos os alertas disparados."""
    def __init__(self, parent_app):
        """Inicializa a janela de histórico de alertas."""
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title("Histórico de Alertas")
        self.geometry("1100x600")
        self.transient(self.master)
        self.grab_set()
        self.resizable(True, True)

        # Adiciona a capacidade de maximizar a janela
        self.maximizable = True
        
        main_container = ttkb.Frame(self, padding=15, bootstyle="dark", relief="solid", borderwidth=1)
        main_container.pack(expand=True, fill='both')
        
        header_frame = ttkb.Frame(main_container, bootstyle="dark")
        header_frame.pack(fill='x', pady=(0, 15))
        
        ttkb.Label(header_frame, text="HISTÓRICO DE ALERTAS", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side="left")
        ttkb.Label(header_frame, text="Registro cronológico de todos os alertas disparados", font=("Segoe UI", 12), bootstyle="secondary").pack(side="left", padx=(15, 0))

        filter_frame = ttkb.Frame(main_container, bootstyle="dark")
        filter_frame.pack(fill='x', pady=(0, 15))
        
        search_frame = ttkb.Frame(filter_frame, bootstyle="dark")
        search_frame.pack(side="left", fill='x', expand=True)
        
        ttkb.Label(search_frame, text="🔍", font=("Segoe UI", 12), bootstyle="secondary").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttkb.Entry(search_frame, textvariable=self.search_var, width=30, font=("Segoe UI", 10), bootstyle="dark")
        self.search_entry.pack(side="left", padx=(0, 15))

        self.placeholder_text = "Buscar por símbolo ou tipo de alerta..."
        self._add_placeholder()

        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._add_placeholder)
        
        period_frame = ttkb.Frame(filter_frame, bootstyle="dark")
        period_frame.pack(side="right")
        
        ttkb.Label(period_frame, text="Período:", font=("Segoe UI", 10), bootstyle="light").pack(side="left", padx=(0, 5))
        self.period_var = tk.StringVar(value="all")
        period_combobox = ttkb.Combobox(period_frame, values=["Todos", "Hoje", "7 dias", "30 dias"], textvariable=self.period_var, width=10, bootstyle="dark")
        period_combobox.pack(side="left", padx=(0, 10))
        period_combobox.current(0)
        
        tree_container = ttkb.Frame(main_container, bootstyle="dark")
        tree_container.pack(expand=True, fill='both', pady=(0, 15))
        
        self.tree = ttkb.Treeview(tree_container, columns=('timestamp', 'symbol', 'trigger'), show='headings', bootstyle="dark", height=15)
        self.tree.heading('timestamp', text='Data/Hora'); self.tree.column('timestamp', width=180, anchor='w')
        self.tree.heading('symbol', text='Símbolo'); self.tree.column('symbol', width=120, anchor='w')
        self.tree.heading('trigger', text='Gatilho do Alerta'); self.tree.column('trigger', width=450, anchor='w')
        
        vsb = ttkb.Scrollbar(tree_container, orient="vertical", command=self.tree.yview, bootstyle="round-dark")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', expand=True, fill='both')
        vsb.pack(side='right', fill='y')
        
        self.details_frame = ttkb.LabelFrame(main_container, text="Detalhes do Alerta", padding=15, height=150, bootstyle="dark")
        self.details_frame.pack(fill='x')
        self.details_frame.pack_propagate(False)
        self.details_placeholder = ttkb.Label(self.details_frame, text="Selecione um alerta para ver os detalhes", font=("Segoe UI", 11), bootstyle="secondary")
        self.details_placeholder.pack(pady=40)
        
        btn_frame = ttkb.Frame(main_container, bootstyle="dark", padding=(0, 15, 0, 0))
        btn_frame.pack(fill='x')
        
        self.analyze_btn = ttkb.Button(btn_frame, text="Análise Detalhada", command=self._open_analysis, bootstyle="info", state="disabled")
        self.analyze_btn.pack(side='left', padx=5)
        ttkb.Button(btn_frame, text="Atualizar", command=self._load_history, bootstyle="secondary").pack(side='left', padx=5)
        ttkb.Button(btn_frame, text="Limpar Histórico", command=self._clear_history, bootstyle="danger-outline").pack(side='left', padx=5)
        ttkb.Button(btn_frame, text="Fechar", command=self.destroy, bootstyle="secondary-outline").pack(side='right', padx=5)
        
        status_bar = ttkb.Frame(main_container, bootstyle="dark", padding=(0, 15, 0, 0))
        status_bar.pack(fill='x', side="bottom")
        self.status_label = ttkb.Label(status_bar, text="", font=("Segoe UI", 10), bootstyle="secondary")
        self.status_label.pack(side="left")

        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.search_var.trace_add("write", self._filter_history)
        self.period_var.trace_add("write", self._filter_history)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self._load_history()
        self.parent_app.center_toplevel_on_main(self)

    def _add_placeholder(self, event=None):
        if not self.search_var.get():
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.config(bootstyle="secondary")

    def _clear_placeholder(self, event=None):
        if self.search_var.get() == self.placeholder_text:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(bootstyle="dark")

    def _on_mousewheel(self, event):
        """Permite a rolagem da lista de histórico com o scroll do mouse."""
        if event.num == 5 or event.delta == -120:
            self.tree.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.tree.yview_scroll(-1, "units")

    def _load_history(self):
        """Carrega e exibe o histórico de alertas na tabela."""
        for item in self.tree.get_children(): self.tree.delete(item)
        self.history_data = self.parent_app.alert_history
        for i, record in enumerate(self.history_data):
            try:
                dt = datetime.fromisoformat(record.get('timestamp', ''))
                formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
            except:
                formatted_time = record.get('timestamp', 'N/A')
            trigger = record.get('trigger', 'N/A')
            trigger_icon = "💲" if 'preço' in trigger.lower() else "📊" if 'rsi' in trigger.lower() else "📈" if 'bollinger' in trigger.lower() else "📉" if 'macd' in trigger.lower() else "✖️" if 'cruz' in trigger.lower() else "💰" if 'capital' in trigger.lower() else "⚠️"
            self.tree.insert('', tk.END, iid=i, values=(formatted_time, record.get('symbol', 'N/A'), f"{trigger_icon} {trigger}"), tags=('alert',))
        self.tree.tag_configure('alert', background="#1e1e2d")
        self.status_label.config(text=f"{len(self.history_data)} alertas encontrados")
        self._on_selection()

    def _filter_history(self, *args):
        """Filtra o histórico exibido com base nos critérios de busca e período."""
        for item in self.tree.get_children(): self.tree.delete(item)
        search_term = self.search_var.get().lower()
        if search_term == self.placeholder_text.lower():
            search_term = ""

        period = self.period_var.get()
        
        from datetime import datetime, timedelta
        filtered_data = self.history_data
        if period != "Todos":
            cutoff = datetime.now().date()
            if period == "7 dias": cutoff -= timedelta(days=7)
            elif period == "30 dias": cutoff -= timedelta(days=30)
            filtered_data = [r for r in self.history_data if self._get_date_from_record(r) >= cutoff]
            
        if search_term:
            filtered_data = [r for r in filtered_data if search_term in r.get('symbol','').lower() or search_term in r.get('trigger','').lower()]
            
        for i, record in enumerate(filtered_data):
            try:
                dt = datetime.fromisoformat(record.get('timestamp', ''))
                formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = record.get('timestamp', 'N/A')

            trigger = record.get('trigger', 'N/A')
            trigger_icon = "💲" if 'preço' in trigger.lower() else "📊" if 'rsi' in trigger.lower() else "📈" if 'bollinger' in trigger.lower() else "📉" if 'macd' in trigger.lower() else "✖️" if 'cruz' in trigger.lower() else "💰" if 'capital' in trigger.lower() else "⚠️"

            # Usar um iid único para cada item na visualização filtrada
            self.tree.insert('', tk.END, iid=f"item_{i}", values=(formatted_time, record.get('symbol', 'N/A'), f"{trigger_icon} {trigger}"), tags=('alert',))
            
        self.status_label.config(text=f"{len(self.tree.get_children())} alertas encontrados")
            
    def _get_date_from_record(self, record):
        """Extrai um objeto de data de um registro de alerta para filtragem."""
        try: return datetime.fromisoformat(record.get('timestamp', '')).date()
        except: return datetime(1970, 1, 1).date()

    def _on_selection(self, event=None):
        """Exibe detalhes resumidos de um alerta quando ele é selecionado na tabela."""
        selected_item = self.tree.selection()
        for widget in self.details_frame.winfo_children(): widget.destroy()
        
        if not selected_item:
            self.analyze_btn['state'] = 'disabled'
            ttkb.Label(self.details_frame, text="Selecione um alerta para ver os detalhes", font=("Segoe UI", 11), bootstyle="secondary").pack(pady=40)
            return
            
        self.analyze_btn['state'] = 'normal'
        record = self.history_data[int(selected_item[0])]
        
        details_content = ttkb.Frame(self.details_frame, bootstyle="dark")
        details_content.pack(fill="both", expand=True)
        left_col, right_col = ttkb.Frame(details_content, bootstyle="dark"), ttkb.Frame(details_content, bootstyle="dark")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right_col.pack(side="left", fill="both", expand=True)
        
        try: dt = datetime.fromisoformat(record.get('timestamp', '')); formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
        except: formatted_time = record.get('timestamp', 'N/A')
            
        ttkb.Label(left_col, text="Símbolo:", font=("Segoe UI", 10, "bold"), bootstyle="secondary").grid(row=0, column=0, sticky="w", pady=3)
        ttkb.Label(left_col, text=record.get('symbol', 'N/A'), font=("Segoe UI", 10, "bold"), bootstyle="info").grid(row=0, column=1, sticky="w", pady=3, padx=5)
        ttkb.Label(left_col, text="Gatilho:", font=("Segoe UI", 10, "bold"), bootstyle="secondary").grid(row=1, column=0, sticky="w", pady=3)
        trigger_label = ttkb.Label(left_col, text=record.get('trigger', 'N/A'), font=("Segoe UI", 10), bootstyle="light", wraplength=400)
        trigger_label.grid(row=1, column=1, sticky="w", pady=3, padx=5)

        ttkb.Label(right_col, text="Data/Hora:", font=("Segoe UI", 10, "bold"), bootstyle="secondary").grid(row=0, column=0, sticky="w", pady=3)
        ttkb.Label(right_col, text=formatted_time, font=("Segoe UI", 10), bootstyle="light").grid(row=0, column=1, sticky="w", pady=3, padx=5)

        has_data = 'data' in record and record['data']
        ttkb.Label(right_col, text="Dados de análise:", font=("Segoe UI", 10, "bold"), bootstyle="secondary").grid(row=1, column=0, sticky="w", pady=3)
        ttkb.Label(right_col, text="Disponíveis" if has_data else "Não disponíveis", font=("Segoe UI", 10), bootstyle="success" if has_data else "danger").grid(row=1, column=1, sticky="w", pady=3, padx=5)

        left_col.columnconfigure(1, weight=1); right_col.columnconfigure(1, weight=1)

    def _open_analysis(self):
        """Abre uma janela com a análise detalhada do alerta selecionado."""
        if not (selected_item := self.tree.selection()): return
        record = self.history_data[int(selected_item[0])]
        if 'data' in record and record['data']: AlertAnalysisWindow(self, record['data'])
        else: messagebox.showinfo("Sem Dados", "Não há dados de análise detalhada para este alerta.", parent=self)

    def _clear_history(self):
        """Limpa todo o histórico de alertas após confirmação do usuário."""
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja apagar todo o histórico de alertas?\n\nEsta ação não pode ser desfeita.", parent=self):
            self.parent_app.alert_history.clear()
            self.parent_app.save_alert_history()
            self._load_history()
            self.status_label.config(text="Histórico de alertas apagado")
            for widget in self.details_frame.winfo_children(): widget.destroy()
            ttkb.Label(self.details_frame, text="Histórico de alertas vazio", font=("Segoe UI", 11), bootstyle="secondary").pack(pady=40)

class AlertAnalysisWindow(ttkb.Toplevel):
    """Janela que exibe uma análise detalhada dos dados no momento de um alerta."""
    def __init__(self, parent, analysis_data):
        """Inicializa a janela de análise de alerta."""
        super().__init__(parent)
        symbol = analysis_data.get('symbol', 'N/A')
        self.title(f"Análise Detalhada - {symbol}")
        self.geometry("700x500")
        self.transient(parent)
        self.grab_set()
        
        main_container = ttkb.Frame(self, bootstyle="dark", padding=15, relief="solid", borderwidth=1)
        main_container.pack(expand=True, fill='both')
        
        header_frame = ttkb.Frame(main_container, bootstyle="dark")
        header_frame.pack(fill='x', pady=(0, 20))
        ttkb.Label(header_frame, text=f"Análise Detalhada: {symbol}", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side="left")
        
        data = analysis_data
        price_panel = ttkb.Frame(main_container, bootstyle="dark")
        price_panel.pack(fill='x', pady=(0, 20))
        
        price_value = data.get('current_price', 0.0)
        price_change = data.get('price_change_24h', 0.0)
        price_change_color = "success" if price_change >= 0 else "danger"
        price_change_icon = "▲" if price_change >= 0 else "▼"

        price_frame = ttkb.LabelFrame(price_panel, text="Preço no Alerta", bootstyle="dark", padding=10)
        price_frame.pack(side="left", fill='y', expand=True, padx=(0, 10))
        ttkb.Label(price_frame, text=f"${price_value:,.4f}" if price_value else "N/A", font=("Segoe UI", 22, "bold"), bootstyle="light").pack(pady=5)
        
        change_frame = ttkb.LabelFrame(price_panel, text="Variação 24h", bootstyle="dark", padding=10)
        change_frame.pack(side="left", fill='y', expand=True, padx=10)
        ttkb.Label(change_frame, text=f"{price_change_icon} {price_change:.2f}%" if price_change else "N/A", font=("Segoe UI", 22, "bold"), bootstyle=price_change_color).pack(pady=5)
        
        volume_value = data.get('volume_24h', 0.0)
        volume_text = f"${volume_value/1_000_000_000:.2f}B" if volume_value >= 1e9 else f"${volume_value/1_000_000:.2f}M" if volume_value >= 1e6 else f"${volume_value/1_000:.2f}K" if volume_value else "N/A"
        volume_frame = ttkb.LabelFrame(price_panel, text="Volume 24h", bootstyle="dark", padding=10)
        volume_frame.pack(side="left", fill='y', expand=True, padx=(10, 0))
        ttkb.Label(volume_frame, text=volume_text, font=("Segoe UI", 22, "bold"), bootstyle="secondary").pack(pady=5)
        
        ttkb.Separator(main_container, bootstyle="info").pack(fill='x', pady=10)
        
        ttkb.Label(main_container, text="Indicadores Técnicos", font=("Segoe UI", 14, "bold"), bootstyle="light").pack(anchor="w", pady=(10, 15))
        
        indicators_grid = ttkb.Frame(main_container, bootstyle="dark")
        indicators_grid.pack(fill='both', expand=True)
        
        indicators = {"rsi_value": {"label": "RSI", "icon": "📊", "format": lambda v: f"{v:.2f}" if v else "N/A", "color": lambda v: "success" if v and v <= 30 else "danger" if v and v >= 70 else "light"}, "bollinger_signal": {"label": "Bollinger", "icon": "📈", "format": str, "color": lambda v: "light"}, "macd_signal": {"label": "MACD", "icon": "📉", "format": str, "color": lambda v: "success" if v == "Cruzamento de Alta" else "danger" if v == "Cruzamento de Baixa" else "light"}, "mme_cross": {"label": "MME", "icon": "✖️", "format": str, "color": lambda v: "success" if v == "Cruz Dourada" else "danger" if v == "Cruz da Morte" else "light"}}

        for i, (key, details) in enumerate(indicators.items()):
            value = data.get(key)
            indicator_card = ttkb.LabelFrame(indicators_grid, text=f"{details['icon']} {details['label']}", bootstyle="dark", padding=10)
            indicator_card.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            ttkb.Label(indicator_card, text=details["format"](value), font=("Segoe UI", 14, "bold"), bootstyle=details["color"](value)).pack(pady=5)
                
        indicators_grid.columnconfigure((0, 1), weight=1)

        notes_frame = ttkb.LabelFrame(main_container, text="Conclusão da Análise", bootstyle="dark", padding=15)
        notes_frame.pack(fill='x', pady=(15, 0))
        
        trigger_text = "Alerta gerado com base nos critérios configurados."
        if (value := data.get('rsi_value')) and value <= 30: trigger_text = f"RSI em condição de sobrevendido ({value:.2f}). Potencial ponto de reversão de baixa."
        elif (value := data.get('rsi_value')) and value >= 70: trigger_text = f"RSI em condição de sobrecomprado ({value:.2f}). Potencial ponto de reversão de alta."
        elif data.get("macd_signal") == "Cruzamento de Alta": trigger_text = "Cruzamento de alta no MACD. Possível tendência de alta."
        elif data.get("macd_signal") == "Cruzamento de Baixa": trigger_text = "Cruzamento de baixa no MACD. Possível tendência de baixa."

        ttkb.Label(notes_frame, text=trigger_text, font=("Segoe UI", 11), bootstyle="light", wraplength=620).pack(pady=10, fill='x')
        
        ttkb.Button(main_container, text="Fechar", command=self.destroy, bootstyle="secondary").pack(side="right", pady=(15, 0))