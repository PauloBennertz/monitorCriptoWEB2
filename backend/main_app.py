import sys
import os
import json
import threading
import queue
import logging
import time
import webbrowser
from urllib.parse import quote
from datetime import datetime

# Importações do PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QLabel, QGridLayout, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont

# --- Importações do seu projeto original ---
# (Assumindo que esses arquivos estão no mesmo diretório ou no python path)
# (Alguns podem precisar de pequenas adaptações, mas a lógica principal é mantida)
from notification_service import send_telegram_alert, AlertConsolidator
import robust_services
from monitoring_service import (
    run_monitoring_cycle,
    get_coingecko_global_mapping,
    fetch_all_binance_symbols_startup,
    get_btc_dominance
)
from core_components import (
    get_application_path,
    CryptoCard,
    AlertHistoryWindow,
    AlertManagerWindow,
    StartupConfigDialog
)
from api_config_window import ApiConfigWindow
from capital_flow_window import CapitalFlowWindow
from token_movers_window import TokenMoversWindow
from sound_config_window import SoundConfigWindow
from dynamic_view_window import DynamicViewWindow
from coin_manager import CoinManager
from help_window import HelpWindow
from app_state import get_last_fetch_timestamp, update_last_fetch_timestamp
from update_checker import check_for_updates

def get_app_version():
    """Lê a versão de um arquivo version.txt, com fallback."""
    try:
        # Usamos get_application_path para funcionar tanto em dev quanto no .exe
        version_path = os.path.join(get_application_path(), 'version.txt')
        with open(version_path, 'r') as f:
            version = f.read().strip()
            # Retorna a versão lida se não for uma string vazia, senão o fallback.
            return version if version else "3.2"
    except FileNotFoundError:
        # Fallback para ambientes onde o arquivo pode não existir (ex: dev sem o arquivo)
        return "3.2"
    except Exception as e:
        # Logar outros erros potenciais pode ser útil
        print(f"Erro ao ler o arquivo de versão: {e}")
        return "3.2"

APP_VERSION = get_app_version()

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Biblioteca Faltando", "A biblioteca 'Pillow' é necessária. Instale com 'pip install Pillow'")
    sys.exit()

class LoadingWindow(tk.Toplevel):
    """Janela de carregamento para feedback ao usuário durante a inicialização."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Carregando...")
        self.geometry("300x150")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Impede o fechamento

        main_frame = ttkb.Frame(self, padding=20)
        main_frame.pack(expand=True, fill="both")

        self.label = ttkb.Label(main_frame, text="Iniciando...", font=("Segoe UI", 11))
        self.label.pack(pady=(10, 5))

        self.progress = ttkb.Progressbar(main_frame, mode='indeterminate', length=250)
        self.progress.pack(pady=10)
        self.progress.start(10)
        self.center_on_screen()

    def update_text(self, text):
        self.label.config(text=text)
        self.update_idletasks()

    def center_on_screen(self):
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def close(self):
        self.destroy()

class CryptoApp:
    """Classe principal da aplicação que gerencia a UI e os serviços de backend."""
    def __init__(self, root, config, all_symbols, coin_manager, coingecko_mapping):
        """Inicializa a aplicação, configura a UI e inicia os serviços."""
        self.root = root
        self.config = config
        self.coingecko_mapping = coingecko_mapping
        self.signals = WorkerSignals()
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()

    def run(self):
        """Inicia o monitoramento."""
        # A função run_monitoring_cycle precisa ser adaptada para usar os sinais
        # em vez de uma queue para a UI. Por simplicidade, vamos simular isso.
        
        # O ideal é modificar run_monitoring_cycle para aceitar um objeto de 'sinais'
        # e chamar self.signals.data_updated.emit(payload) em vez de data_queue.put().
        
        # Exemplo de adaptação:
        logging.info("Serviço de monitoramento em background iniciado.")
        while not self.stop_event.is_set():
            # Aqui entraria a lógica de run_monitoring_cycle
            # Simulando a recepção de dados:
            monitored_symbols = [c['symbol'] for c in self.config.get('cryptos_to_monitor', [])]
            for symbol in monitored_symbols:
                # Simulação de dados recebidos
                mock_data = {
                    'symbol': symbol,
                    'current_price': 50000.0 * (1 + (time.time() % 10 - 5) / 100),
                    'price_change_24h': (time.time() % 10 - 5),
                    'volume_24h': 1000000000,
                    'rsi_value': 50 + (time.time() % 40 - 20)
                }
                self.signals.data_updated.emit(mock_data)
                time.sleep(0.1) # Simula o tempo entre buscas

            interval = self.config.get('check_interval_seconds', 300)
            self.signals.countdown.emit(interval)
            
            for i in range(interval):
                if self.stop_event.is_set(): break
                time.sleep(1)

    def setup_ui(self):
        """Constrói todos os elementos da interface gráfica principal."""
        self.root.title("Crypto Monitor Pro")
        self.root.geometry("1280x800")
        
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="⚙️ Gerenciar Alertas", command=self.show_alert_manager)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Sair", command=self.on_closing)
        
        analysis_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="📊 Análise de Mercado", menu=analysis_menu)
        analysis_menu.add_command(label="💹 Fluxo de Capital (Categorias)", command=self.show_capital_flow_window)
        analysis_menu.add_command(label="📈 Ganhadores e Perdedores", command=self.show_token_movers_window)
        analysis_menu.add_command(label="🔔 Histórico de Alertas", command=self.show_alert_history_window)
        analysis_menu.add_separator()
        analysis_menu.add_command(label="✨ Visão Dinâmica", command=self.show_dynamic_view_window)
        
        config_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="⚙️ Configurações", menu=config_menu)
        config_menu.add_command(label="🔊 Configurar Sons", command=self.show_sound_config_window)
        config_menu.add_command(label="Chaves de API", command=self.show_api_config_window)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Guia de Indicadores", command=self.show_help_window)
        help_menu.add_separator()
        help_menu.add_command(label="Verificar Atualizações", command=self.check_for_updates_manual)
        help_menu.add_command(label="📧 Enviar Feedback, Erros e Sugestões", command=self.send_feedback)

        header_frame = ttkb.Frame(self.root, bootstyle="dark")
        header_frame.pack(side="top", fill="x")
        
        title_frame = ttkb.Frame(header_frame, bootstyle="dark", padding=10)
        title_frame.pack(side="top", fill="x")
        
        ttkb.Label(title_frame, text="CRYPTO MONITOR PRO", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(side="left")
        
        status_frame = ttkb.Frame(header_frame, padding=(15, 10), bootstyle="secondary")
        status_frame.pack(side="top", fill="x")

        dominance_frame = ttkb.Frame(status_frame, bootstyle="secondary")
        dominance_frame.pack(side="left")
        
        ttkb.Label(dominance_frame, text="₿", font=("Arial", 16, "bold"), bootstyle="warning").pack(side="left", padx=(0, 5))
        ttkb.Label(dominance_frame, text="Dominância BTC:", font=("Segoe UI", 11, "bold"), bootstyle="light").pack(side="left")

        self.dominance_label = ttkb.Label(dominance_frame, text="Carregando...", font=("Segoe UI", 12, "bold"), bootstyle="warning", width=12)
        self.dominance_label.pack(side="left", padx=(8, 0))
        
        ttkb.Separator(status_frame, orient="vertical", bootstyle="light").pack(side="left", fill="y", padx=15, pady=5)
        
        api_status_frame = ttkb.Frame(status_frame, bootstyle="secondary")
        api_status_frame.pack(side="left")
        
        ttkb.Label(api_status_frame, text="Status API:", font=("Segoe UI", 11), bootstyle="light").pack(side="left")

        self.update_status_label = ttkb.Label(api_status_frame, text="", font=("Segoe UI", 11, "bold"), bootstyle="secondary")
        self.update_status_label.pack(side="left", padx=(8, 0))
        
        self.update_button = ttkb.Button(status_frame, text="🔄 Atualizar Dados", command=self.manual_update_prices, bootstyle="info", width=18)
        self.update_button.pack(side="right", padx=(0, 10))

        countdown_frame = ttkb.Frame(status_frame, bootstyle="secondary")
        countdown_frame.pack(side="right", padx=(0, 10))

        ttkb.Label(countdown_frame, text="Próxima atualização:", font=("Segoe UI", 11), bootstyle="light").pack(side="left", padx=(0, 5))
        self.countdown_label = ttkb.Label(countdown_frame, text="--:--", font=("Segoe UI", 11, "bold"), bootstyle="secondary")
        self.countdown_label.pack(side="left")
        
        self.check_api_status()
        
        main_container = ttkb.Frame(self.root, bootstyle="dark")
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        coins_header = ttkb.Frame(main_container, bootstyle="dark")
        coins_header.pack(fill="x", pady=(0, 10))
        
        ttkb.Label(coins_header, text="Suas Criptomoedas Monitoradas", font=("Segoe UI", 14, "bold"), bootstyle="info").pack(side="left")
        
        main_frame = ttkb.Frame(main_container, bootstyle="dark", padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(main_frame, highlightthickness=0, bg="#2a2a2a")
        self.scrollbar = ttkb.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview, bootstyle="rounded")
        self.scrollable_frame = ttkb.Frame(self.canvas, bootstyle="dark")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        canvas_window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(canvas_window_id, width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.root.bind('<MouseWheel>', self._on_mousewheel)
        
        footer_frame = ttkb.Frame(self.root, padding=(15, 8), bootstyle="dark")
        footer_frame.pack(side="bottom", fill="x")
        
        ttkb.Label(footer_frame, text=f"Sessão iniciada: {datetime.now().strftime('%d/%m/%Y %H:%M')}", font=("Segoe UI", 9), bootstyle="secondary").pack(side="left")
        ttkb.Label(footer_frame, text="© 2025 Crypto Monitor Pro", font=("Segoe UI", 9), bootstyle="secondary").pack(side="right")

        self.update_coin_cards_display()
        
    def update_coin_cards_display(self):
        """Cria e posiciona os cards na grade."""
        # Limpa o layout antigo
        for i in reversed(range(self.cards_layout.count())): 
            self.cards_layout.itemAt(i).widget().setParent(None)
        
        monitored_symbols = [c['symbol'] for c in self.config.get('cryptos_to_monitor', [])]
        self.coin_cards = {}
        
        num_columns = 4 # Ajuste conforme necessário

        for i, symbol in enumerate(monitored_symbols):
            base_asset = symbol.replace('USDT', '').upper()
            coin_name = self.coingecko_mapping.get(base_asset, base_asset) 
            
            card = CryptoCardWidget(symbol, coin_name)
            self.coin_cards[symbol] = card
            
            row, col = divmod(i, num_columns)
            self.cards_layout.addWidget(card, row, col)

    def start_monitoring_thread(self):
        """Cria e inicia a thread para o worker de monitoramento."""
        self.monitoring_thread = QThread()
        self.worker = MonitoringWorker(self.config, self.coingecko_mapping)
        self.worker.moveToThread(self.monitoring_thread)

        # Conectar sinais e slots
        self.monitoring_thread.started.connect(self.worker.run)
        self.worker.signals.data_updated.connect(self.update_card_data)
        # self.worker.signals.alert.connect(self.handle_alert) -> Implementar
        # self.worker.signals.countdown.connect(self.update_countdown) -> Implementar

        self.monitoring_thread.start()
        logging.info("Thread de monitoramento iniciada.")

    def update_card_data(self, data):
        """Slot para receber dados da thread e atualizar o card correspondente."""
        symbol = data.get('symbol')
        card = self.coin_cards.get(symbol)
        if card:
            card.update_data(data)

    def closeEvent(self, event):
        """Função chamada ao fechar a janela."""
        reply = QMessageBox.question(self, 'Sair', 'Deseja realmente fechar o programa?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            logging.info("Fechando a aplicação...")
            self.stop_monitoring_event.set()
            if self.monitoring_thread: self.monitoring_thread.join(timeout=5)
            self.save_config()
            self.save_alert_history()
            self.root.destroy()
            sys.exit()

    def save_config(self):
        """Salva a configuração atual no arquivo config.json."""
        config_path = os.path.join(get_application_path(), "config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=2)
            logging.info("Configurações salvas com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao salvar configurações: {e}")

    def load_alert_history(self):
        """Carrega o histórico de alertas do arquivo alert_history.json."""
        history_path = os.path.join(get_application_path(), "alert_history.json")
        try:
            with open(history_path, 'r', encoding='utf-8') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_alert_history(self):
        """Salva o histórico de alertas atual no arquivo alert_history.json."""
        history_path = os.path.join(get_application_path(), "alert_history.json")
        try:
            with open(history_path, 'w', encoding='utf-8') as f: json.dump(self.alert_history, f, indent=2)
            logging.info("Histórico de alertas salvo com sucesso.")
        except Exception as e:
            logging.error(f"Não foi possível salvar o histórico de alertas: {e}")

    def log_and_save_alert(self, symbol, trigger, data):
        """Adiciona uma nova entrada de alerta ao histórico."""
        alert_entry = {'timestamp': datetime.now().isoformat(), 'symbol': symbol, 'trigger': trigger, 'data': data}
        self.alert_history.insert(0, alert_entry)
        if len(self.alert_history) > 200: self.alert_history = self.alert_history[:200]

    def show_alert_manager(self):
        """Abre a janela do gerenciador de alertas."""
        AlertManagerWindow(self, self.coin_manager)

    def show_capital_flow_window(self):
        """Abre a janela de análise de fluxo de capital."""
        from pycoingecko import CoinGeckoAPI
        cg_client = CoinGeckoAPI()
        CapitalFlowWindow(self.root, self, cg_client, robust_services.data_cache, robust_services.rate_limiter)

    def show_token_movers_window(self):
        """Abre a janela de análise de ganhadores e perdedores."""
        from pycoingecko import CoinGeckoAPI
        cg_client = CoinGeckoAPI()
        TokenMoversWindow(self.root, self, cg_client, robust_services.data_cache, robust_services.rate_limiter)

    def show_alert_history_window(self):
        """Abre a janela do histórico de alertas."""
        AlertHistoryWindow(self)

    def show_dynamic_view_window(self):
        """Abre a janela de visão dinâmica."""
        DynamicViewWindow(self.root)
    
    def show_sound_config_window(self):
        """Abre a janela de configuração de sons."""
        from sound_config_window import SoundConfigWindow
        SoundConfigWindow(self.root, self)

    def show_api_config_window(self):
        """Abre a janela de configuração de chaves de API."""
        ApiConfigWindow(self.root, self)

    def show_help_window(self):
        """Abre a janela de ajuda com o guia de indicadores."""
        HelpWindow(self)

    def check_for_updates_manual(self):
        """Verifica manualmente se há atualizações."""
        check_for_updates(self.root, self.version, on_startup=False)

    def send_feedback(self):
        """Abre o cliente de e-mail padrão para enviar feedback."""
        try:
            recipient = "monitorcriptopro@gmail.com"
            subject = "Feedback/Sugestão para Crypto Monitor Pro"
            body = """
Por favor, descreva seu feedback, relate um erro ou faça uma sugestão.
Se estiver relatando um erro, inclua os passos para reproduzi-lo.


----------------------------------------------------

"""
            encoded_subject = quote(subject)
            encoded_body = quote(body)
            webbrowser.open(f"mailto:{recipient}?subject={encoded_subject}&body={encoded_body}", new=1)
            logging.info("Tentativa de abrir cliente de e-mail para feedback.")
        except Exception as e:
            logging.error(f"Não foi possível abrir o cliente de e-mail: {e}")
            messagebox.showerror("Erro", "Não foi possível abrir o seu cliente de e-mail padrão. Por favor, envie seu feedback manualmente para feedback.devjulio@gmail.com")

    def center_toplevel_on_main(self, toplevel_window):
        """Centraliza uma janela Toplevel em relação à janela principal."""
        self.root.update_idletasks()
        main_x, main_y = self.root.winfo_x(), self.root.winfo_y()
        main_width, main_height = self.root.winfo_width(), self.root.winfo_height()
        top_width, top_height = toplevel_window.winfo_width(), toplevel_window.winfo_height()
        x = main_x + (main_width - top_width) // 2
        y = main_y + (main_height - top_height) // 2
        screen_width, screen_height = toplevel_window.winfo_screenwidth(), toplevel_window.winfo_screenheight()
        x = max(0, min(x, screen_width - top_width))
        y = max(0, min(y, screen_height - top_height))
        toplevel_window.geometry(f"+{x}+{y}")
        
    def update_dominance_display(self):
        """Busca e atualiza o label da dominância do BTC em uma thread separada."""
        def update_task():
            try:
                logging.info("Buscando dominância do BTC...")
                dominance = get_btc_dominance()
                logging.info(f"Valor da dominância recebido: {dominance}")
                self.root.after(0, lambda: self.dominance_label.config(text=dominance))
            except Exception as e:
                logging.error(f"Erro ao atualizar dominância BTC: {e}")
                self.root.after(60000, self.update_dominance_display)
                return
            self.root.after(300000, self.update_dominance_display)
        threading.Thread(target=update_task, daemon=True).start()

    def manual_update_prices(self):
        """Inicia uma atualização manual dos preços, verificando os limites da API."""
        can_update, status_message = robust_services.rate_limiter.can_perform_manual_update()
        if not can_update:
            self.update_status_label.config(text=f"⚠️ {status_message}", bootstyle="danger")
            self.root.after(5000, lambda: self.update_status_label.config(text=""))
            return
        
        status_text = f"🔄 {status_message}"
        self.update_status_label.config(text=status_text, bootstyle="info")
        self.root.after(1000, lambda: self._start_manual_update())
    
    def _start_manual_update(self):
        """Prepara e inicia a thread de atualização manual."""
        self.update_button.config(state='disabled', text='Atualizando...')
        self.update_status_label.config(text="Atualizando preços...", bootstyle="warning")
        threading.Thread(target=self._perform_manual_update, daemon=True).start()
    
    def _perform_manual_update(self):
        """Executa a lógica de atualização manual dos preços em uma thread."""
        try:
            robust_services.rate_limiter.set_manual_update_mode(True)
            robust_services.data_cache.cache.clear()
            logging.info("Cache limpo para atualização manual.")
            
            monitored_symbols = [c['symbol'] for c in self.config.get('cryptos_to_monitor', [])]
            
            from monitoring_service import run_single_symbol_update
            for i, symbol in enumerate(monitored_symbols):
                robust_services.rate_limiter.wait_if_needed()
                run_single_symbol_update(symbol, self.config, self.data_queue, self.coingecko_mapping)
                time.sleep(0.2)
                if (i + 1) % 5 == 0:
                    self.root.after(0, lambda i=i: self.update_status_label.config(text=f"Atualizando... ({i+1}/{len(monitored_symbols)})"))
            
            self.update_dominance_display()
            self.root.after(0, self._update_complete)
            
        except Exception as e:
            logging.error(f"Erro durante atualização manual: {e}")
            self.root.after(0, self._update_error, str(e))
        finally:
            robust_services.rate_limiter.set_manual_update_mode(False)
    
    def _update_complete(self):
        """Atualiza a UI após a conclusão bem-sucedida da atualização manual."""
        self.update_button.config(state='normal', text='🔄 Atualizar Preços')
        self.update_status_label.config(text="✓ Atualizado", bootstyle="success")
        self.root.after(3000, lambda: self.update_status_label.config(text=""))
    
    def check_api_status(self):
        """Verifica periodicamente o status do rate limit da API e atualiza a UI."""
        try:
            can_update, status_message = robust_services.rate_limiter.can_perform_manual_update()
            if can_update:
                self.update_button.config(state='normal', text='🔄 Atualizar Preços', bootstyle="info")
                self.update_status_label.config(text="API: OK", bootstyle="success")
            else:
                self.update_button.config(state='disabled', text='⏸️ API Limitada', bootstyle="secondary")
                self.update_status_label.config(text=f"API: {status_message}", bootstyle="danger")
                self._pulse_button(self.update_button, 'danger')
            self.root.after(10000, self.check_api_status)
        except Exception as e:
            logging.error(f"Erro ao verificar status da API: {e}")
            self.update_status_label.config(text="API: Erro", bootstyle="danger")
            self.root.after(10000, self.check_api_status)
    
    def show_api_tooltip(self, usage):
        """Mostra um tooltip com informações detalhadas do uso da API."""
        tooltip_text = f"Status da API:\n1 min: {usage['requests_1min']}/{usage['limit_1min']} ({usage['1min']:.1f}%)\n5 min: {usage['requests_5min']}/{usage['limit_5min']} ({usage['5min']:.1f}%)"
        x, y, _, _ = self.update_button.bbox("insert")
        x += self.update_button.winfo_rootx() + 25
        y += self.update_button.winfo_rooty() + 20
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttkb.Label(self.tooltip, text=tooltip_text, justify=tk.LEFT, background="#ffffe0", foreground="black", relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9), padding=5)
        label.pack()
        self.root.after(3000, lambda: self.tooltip.destroy() if hasattr(self, 'tooltip') else None)

    def _update_error(self, error_msg):
        """Atualiza a UI em caso de erro na atualização manual."""
        self.update_button.config(state='normal', text='🔄 Atualizar Preços')
        self.update_status_label.config(text="✗ Erro", bootstyle="danger")
        self.root.after(5000, lambda: self.update_status_label.config(text=""))

    def start_countdown(self, seconds):
        if self.countdown_job:
            self.root.after_cancel(self.countdown_job)

        def update_timer(s):
            mins, secs = divmod(s, 60)
            self.countdown_label.config(text=f"{mins:02d}:{secs:02d}")
            if s > 0:
                self.countdown_job = self.root.after(1000, update_timer, s - 1)
            else:
                self.countdown_label.config(text="Atualizando...")

        update_timer(seconds)

    def _on_mousewheel(self, event):
        """Permite a rolagem da lista de cards com o scroll do mouse."""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def _pulse_button(self, button, color_style):
        """Cria um efeito de pulsação visual em um botão."""
        if hasattr(button, '_pulsing') and button._pulsing: return
        button._pulsing = True
        original_style = button.cget('bootstyle')
        def animate_pulse(count=0):
            if not button.winfo_exists():
                button._pulsing = False
                return
            if count % 2 == 0: button.config(bootstyle=f"{color_style}")
            else: button.config(bootstyle=f"{color_style}-outline")
            if button._pulsing: self.root.after(500, lambda: animate_pulse(count + 1))
            else: button.config(bootstyle=original_style)
        animate_pulse()

def get_current_config():
    """Carrega a configuração do aplicativo a partir do arquivo config.json."""
    config_path = os.path.join(get_application_path(), "config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"cryptos_to_monitor": [], "telegram_bot_token": "", "telegram_chat_id": "", "check_interval_seconds": 300}

def fetch_initial_data(config, data_queue):
    """Busca todos os dados iniciais necessários para a aplicação em uma thread separada."""
    try:
        last_fetch_time = get_last_fetch_timestamp()
        current_time = time.time()

        # Se a última busca foi a menos de 5 minutos (300s), pula a busca
        if current_time - last_fetch_time < 300:
            data_queue.put({'status': 'skipped', 'data': "Busca de dados recentes. Usando cache."})
            # Mesmo pulando, precisamos dos dados para iniciar a app. Assumimos que estão em cache.
            # Esta parte pode precisar de mais robustez se o cache puder estar vazio.
            all_symbols = fetch_all_binance_symbols_startup(config) # Pode vir do cache da exchangeInfo
            mapping = get_coingecko_global_mapping() # Pode vir do cache da lista de moedas
            data_queue.put({'status': 'done', 'data': {'symbols': all_symbols, 'mapping': mapping}})
            return

        data_queue.put({'status': 'symbols', 'data': None})
        all_symbols = fetch_all_binance_symbols_startup(config)

        data_queue.put({'status': 'mapping', 'data': None})
        mapping = get_coingecko_global_mapping()

        update_last_fetch_timestamp() # Atualiza o timestamp após uma busca bem sucedida

        data_queue.put({'status': 'done', 'data': {'symbols': all_symbols, 'mapping': mapping}})
    except Exception as e:
        logging.critical(f"Erro crítico ao buscar dados iniciais: {e}")
        data_queue.put({'status': 'error', 'data': str(e)})

def main():
    """Função principal que inicializa a aplicação PyQt6."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    
    # Carregar configurações e dados iniciais (pode-se adicionar uma tela de splash aqui)
    config = get_current_config()
    all_symbols = fetch_all_binance_symbols_startup(config)
    mapping = get_coingecko_global_mapping()
    coin_manager = CoinManager()

    if not config.get("cryptos_to_monitor"):
        QMessageBox.warning(None, "Configuração Incompleta", "Nenhuma moeda está sendo monitorada. Por favor, adicione moedas através do gerenciador de alertas.")
        # Aqui você poderia abrir a janela de configuração primeiro
        
    main_window = CryptoAppPyQt(config, all_symbols, coin_manager, mapping)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()