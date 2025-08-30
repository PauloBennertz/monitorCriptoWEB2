import requests
import os
import sys
import datetime
try:
    import winsound
except ImportError:
    winsound = None
import json
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from collections import deque
import threading
import time
from core_components import ALERT_SUMMARIES

def get_application_path():
    """Obtém o caminho base da aplicação, seja executável ou script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# ==========================================
# SISTEMA DE CONSOLIDAÇÃO DE ALERTAS
# ==========================================
class AlertConsolidator:
    def __init__(self, parent_window, app_instance=None):
        self.parent_window = parent_window
        self.app_instance = app_instance  # Instância do CryptoApp para acessar config
        self.pending_alerts = deque()
        self.consolidated_window = None
        self.alert_lock = threading.Lock()
        self.is_showing = False
        self.suppress_alerts = False  # Nova flag para pausar alertas
        self.last_alert_time = 0  # Para agrupar alertas por tempo
        
        # Inicia thread para processar alertas consolidados
        self.alert_thread = threading.Thread(target=self._process_alerts, daemon=True)
        self.alert_thread.start()
    
    def add_alert(self, symbol, trigger, message, sound=None):
        """Adiciona um alerta à fila de consolidação."""
        with self.alert_lock:
            alert_data = {
                'symbol': symbol,
                'trigger': trigger,
                'message': message,
                'sound': sound,
                'timestamp': datetime.datetime.now().strftime("%H:%M:%S")
            }
            self.pending_alerts.append(alert_data)
            print(f"LOG: Alerta adicionado à fila de consolidação: {symbol} - {trigger}")
    
    def _process_alerts(self):
        """Processa alertas em background sem bloquear a thread principal."""
        while True:
            alerts_to_show = []
            should_show = False

            with self.alert_lock:
                if self.pending_alerts and not self.is_showing and not self.suppress_alerts:
                    current_time = time.time()

                    # Decide se deve iniciar um novo lote de alertas
                    if self.last_alert_time == 0 or (current_time - self.last_alert_time) > 3.0:
                        should_show = True

            # Se decidimos mostrar, esperamos um pouco para agrupar mais alertas
            if should_show:
                time.sleep(2.0) # Dorme fora do lock para não bloquear a adição de novos alertas
                
                with self.alert_lock:
                    # Coleta todos os alertas que chegaram nesse meio tempo
                    while self.pending_alerts:
                        alerts_to_show.append(self.pending_alerts.popleft())

                    if alerts_to_show:
                        self.last_alert_time = time.time()
                        # Agenda a exibição da janela na thread principal
                        self.parent_window.after(0, self._show_consolidated_alerts, alerts_to_show)

            time.sleep(0.3) # Loop de verificação principal
    
    def _show_consolidated_alerts(self, alerts):
        """Mostra uma janela consolidada com todos os alertas."""
        if self.consolidated_window:
            self.consolidated_window.destroy()
        
        self.is_showing = True
        
        # Cria janela consolidada
        self.consolidated_window = ttkb.Toplevel(self.parent_window)
        self.consolidated_window.title("🚨 Alertas Consolidados")
        self.consolidated_window.geometry("600x400")
        self.consolidated_window.resizable(True, True)
        
        # Centraliza a janela
        self._center_window(self.consolidated_window)
        
        # Configura a janela
        self.consolidated_window.transient(self.parent_window)
        # self.consolidated_window.grab_set() # Removido/comentado para evitar travamento
        self.consolidated_window.lift()
        self.consolidated_window.attributes('-topmost', True)
        self.consolidated_window.after_idle(self.consolidated_window.attributes, '-topmost', False) # Opcional: para que não fique sempre no topo
        self.consolidated_window.focus_set() # Garante que a janela de alerta receba o foco
        
        # Frame principal
        main_frame = ttkb.Frame(self.consolidated_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttkb.Label(main_frame, text=f"🚨 {len(alerts)} Alerta(s) Detectado(s)", 
                                font=("-weight bold", 14), bootstyle="danger")
        title_label.pack(pady=(0, 10))
        
        # Frame para scroll
        self.canvas = tk.Canvas(main_frame, highlightthickness=0, bg="#2a2a2a")
        scrollbar = ttkb.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview, bootstyle="round-dark")
        scrollable_frame = ttkb.Frame(self.canvas, bootstyle="dark")
        
        scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Agrupa alertas por símbolo
        grouped_alerts = {}
        for alert in alerts:
            symbol = alert['symbol']
            if symbol not in grouped_alerts:
                grouped_alerts[symbol] = []
            grouped_alerts[symbol].append(alert)

        # Adiciona cada grupo de alertas
        for i, (symbol, symbol_alerts) in enumerate(grouped_alerts.items()):
            # Frame para o grupo de alertas de uma moeda
            group_frame = ttkb.Frame(scrollable_frame, padding="10", bootstyle="dark")
            group_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Cabeçalho da moeda
            coin_header_frame = ttkb.Frame(group_frame, bootstyle="dark")
            coin_header_frame.pack(fill=tk.X)
            
            symbol_label = ttkb.Label(coin_header_frame, text=f"📊 {symbol}",
                                     font=("-weight bold", 14), bootstyle="primary")
            symbol_label.pack(side="left")
            
            # Adiciona cada alerta individual para a moeda
            for alert in symbol_alerts:
                alert_frame = ttkb.Frame(group_frame, padding="5", bootstyle="dark")
                alert_frame.pack(fill=tk.X, pady=2, padx=10)

                # Cabeçalho do alerta (trigger e timestamp)
                header_frame = ttkb.Frame(alert_frame, bootstyle="dark")
                header_frame.pack(fill=tk.X)

                trigger_label = ttkb.Label(header_frame, text=f"🔔 {alert['trigger']}",
                                          font=("-weight bold", 11), bootstyle="warning")
                trigger_label.pack(side="left")

                time_label = ttkb.Label(header_frame, text=f"⏰ {alert['timestamp']}",
                                       font=("", 9), bootstyle="secondary")
                time_label.pack(side="right")

                # Mensagem do alerta
                message_label = ttkb.Label(alert_frame, text=alert['message'],
                                          wraplength=520, justify=tk.LEFT)
                message_label.pack(fill=tk.X, pady=(5, 0))

                # Resumo do Alerta
                summary_text = ALERT_SUMMARIES.get(alert['trigger'], "Consulte o Guia para mais detalhes.")
                if summary_text:
                    summary_label = ttkb.Label(
                        alert_frame,
                        text=f"💡 {summary_text}",
                        wraplength=520,
                        justify=tk.LEFT,
                        font=("", 8, "italic"),
                        bootstyle="secondary"
                    )
                    summary_label.pack(fill=tk.X, pady=(5, 5))

            # Separador entre moedas
            if i < len(grouped_alerts) - 1:
                separator = ttkb.Separator(scrollable_frame, orient="horizontal")
                separator.pack(fill=tk.X, pady=10)
        
        # Botões de ação
        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Botão OK
        ok_button = ttkb.Button(button_frame, text="✅ OK", 
                               command=self._close_consolidated_window,
                               bootstyle="success", width=15)
        ok_button.pack(side="right", padx=(5, 0))
        
        # Configura fechamento da janela e rolagem do mouse
        self.consolidated_window.protocol("WM_DELETE_WINDOW", self._close_consolidated_window)
        self.consolidated_window.bind("<MouseWheel>", self._on_mousewheel)
        
        # Toca som consolidado automaticamente
        self._play_consolidated_sound(alerts)
        
        # Envia para Telegram se configurado
        self._send_consolidated_telegram(alerts)
        
        print(f"LOG: Janela consolidada mostrada com {len(alerts)} alerta(s)")
    
    def _play_consolidated_sound(self, alerts):
        """Toca som consolidado para todos os alertas."""
        # Se há múltiplos alertas, usa som especial
        if len(alerts) > 1:
            # Som especial para múltiplos alertas
            multiple_alerts_sound = os.path.join("sons", "multiplos_alertas.wav")
            if os.path.exists(os.path.join(get_application_path(), multiple_alerts_sound)):
                play_alert_sound(multiple_alerts_sound)
            else:
                # Fallback para som padrão se arquivo não existir
                play_alert_sound(os.path.join("sons", "Alerta.mp3"))
        else:
            # Para um único alerta, usa o som configurado
            for alert in alerts:
                if alert.get('sound'):
                    play_alert_sound(alert['sound'])
                    break
    
    def _send_consolidated_telegram(self, alerts):
        """Envia alertas consolidados para o Telegram."""
        # Tenta acessar a configuração
        try:
            if self.app_instance and hasattr(self.app_instance, 'config'):
                bot_token = self.app_instance.config.get('telegram_bot_token')
                chat_id = self.app_instance.config.get('telegram_chat_id')
            elif hasattr(self.parent_window, 'config'):
                bot_token = self.parent_window.config.get('telegram_bot_token')
                chat_id = self.parent_window.config.get('telegram_chat_id')
            else:
                print("LOG: Não foi possível acessar configurações do Telegram")
                return
        except Exception as e:
            print(f"ERRO: Erro ao acessar configurações do Telegram: {e}")
            return
        
        if not bot_token or "AQUI" in str(bot_token) or not chat_id or "AQUI" in str(chat_id):
            return
        
        # Agrupa alertas por símbolo para uma mensagem mais clara
        grouped_alerts = {}
        for alert in alerts:
            symbol = alert['symbol']
            if symbol not in grouped_alerts:
                grouped_alerts[symbol] = []
            grouped_alerts[symbol].append(alert)

        # Cria mensagem consolidada
        message = f"🚨 *{len(alerts)} Alerta(s) Consolidado(s)*\n\n"
        
        # Resumo por moeda
        for symbol, symbol_alerts in grouped_alerts.items():
            message += f"📊 *{symbol}* ({len(symbol_alerts)} alerta(s))\n"
            for alert in symbol_alerts:
                message += f"  - {alert['trigger']} às {alert['timestamp']}\n"
            message += "\n"

        # Adiciona detalhes completos de cada alerta
        message += "--- *Detalhes* ---\n\n"
        for alert in alerts:
            message += f"*{alert['symbol']}* - {alert['trigger']}\n"
            # Remove a parte inicial "ALERTA: ..." da mensagem para não ser redundante
            clean_message = alert['message'].split('\n\n', 1)[-1]
            message += f"```{clean_message}```\n\n"
        
        send_telegram_alert(bot_token, chat_id, message)
    
    def _on_mousewheel(self, event):
        """Permite a rolagem da janela de alertas com o scroll do mouse."""
        if hasattr(self, 'canvas'):
            # A direção da rolagem pode variar entre sistemas operacionais
            if event.num == 5 or event.delta == -120:
                self.canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta == 120:
                self.canvas.yview_scroll(-1, "units")

    def _close_consolidated_window(self):
        """Fecha a janela consolidada."""
        if self.consolidated_window:
            self.consolidated_window.destroy()
            self.consolidated_window = None
        self.is_showing = False
        print("LOG: Janela consolidada fechada")
    
    def _center_window(self, window):
        """Centraliza a janela na tela."""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

# ==========================================
# FUNÇÕES DE ALERTA GLOBAIS (MANTIDAS PARA COMPATIBILIDADE)
# ==========================================
def play_alert_sound(sound_path_str):
    """Toca um arquivo de som de alerta .wav."""
    if not sound_path_str:
        print("LOG: Nenhum caminho de som fornecido.")
        return
    if not winsound:
        print("LOG: winsound module not available, cannot play sound.")
        return

    sound_path = sound_path_str if os.path.isabs(sound_path_str) else os.path.join(get_application_path(), sound_path_str)
    sound_path = os.path.normpath(sound_path)

    if os.path.exists(sound_path):
        try:
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            print(f"LOG: Tocando som de alerta: {sound_path}")
        except Exception as e:
            print(f"ERRO: Não foi possível tocar o som '{sound_path}': {e}")
    else:
        print(f"ERRO: Arquivo de som não encontrado em '{sound_path}'.")

def send_telegram_alert(bot_token, chat_id, message):
    """Envia uma mensagem de alerta para um chat do Telegram."""
    if not bot_token or "AQUI" in str(bot_token) or not chat_id or "AQUI" in str(chat_id):
        print("LOG: Token ou Chat ID do Telegram não configurado. Pulando notificação.")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("LOG: Alerta enviado para o Telegram.")
    except Exception as e:
        print(f"--> ERRO ao enviar para o Telegram: {e}")