import requests
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import ttkbootstrap as ttkb
import webbrowser
import threading
import os
import sys
import json
import subprocess
from packaging.version import parse as parse_version
import hashlib
from backend.chart_generator import generate_chart 

# --- Constantes ---
GITHUB_API_URL = "https://api.github.com/repos/PauloBennertz/MonitorCriptomoedas3.2/releases/latest"
CONFIG_FILE_NAME = "config.json"
UPDATER_SCRIPT_NAME = "updater.bat"
DOWNLOADED_FILE_NAME = "update.exe"

# --- UI Classes ---
class UpdateNotificationWindow(tk.Toplevel):
    # ... (código existente, sem alterações) ...
    """ Janela que notifica o usuário sobre uma nova atualização. """
    def __init__(self, parent, version, notes, assets):
        super().__init__(parent)
        self.parent = parent
        self.version = version
        self.notes = notes
        self.assets = assets
        self.result = "later"
        self.title("Nova Versão Disponível!")
        self.geometry("700x850")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.create_widgets()
        self.center_on_parent()

    def create_widgets(self):
        main_frame = ttkb.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        ttkb.Label(main_frame, text=f"🎉 Atualização para a v{self.version}", font=("Segoe UI", 16, "bold"), bootstyle="info").pack(anchor="w")
        ttkb.Label(main_frame, text="Novidades da versão:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(15, 5))

        notes_frame = ttkb.Frame(main_frame, bootstyle="secondary", padding=2)
        notes_frame.pack(fill="both", expand=True)
        text_widget = scrolledtext.ScrolledText(notes_frame, wrap="word", relief="flat", font=("Segoe UI", 10))
        text_widget.insert("1.0", self.notes)
        text_widget.config(state="disabled")
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        button_frame = ttkb.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        ttkb.Button(button_frame, text="🚀 Atualizar Agora", command=self._update_now, bootstyle="success", width=20).pack(side="right", padx=(10, 0))
        ttkb.Button(button_frame, text="🔄 Atualizar ao Reiniciar", command=self._update_on_startup, bootstyle="primary-outline", width=22).pack(side="right", padx=(10, 0))
        ttkb.Button(button_frame, text="Lembrar Depois", command=self._on_closing, bootstyle="secondary", width=18).pack(side="left")

    def _update_now(self): self.result = "now"; self.destroy()
    def _update_on_startup(self): self.result = "startup"; self.destroy()
    def _on_closing(self): self.result = "later"; self.destroy()

    def center_on_parent(self):
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")


class DownloadProgressWindow(tk.Toplevel):
    """ Janela para mostrar o progresso do download. """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Baixando Atualização...")
        self.geometry("500x200")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None) # Impede o fechamento

        main_frame = ttkb.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)

        self.status_label = ttkb.Label(main_frame, text="Iniciando download...", font=("Segoe UI", 11))
        self.status_label.pack(pady=(10, 5))

        self.progress = ttkb.Progressbar(main_frame, mode='determinate', length=350)
        self.progress.pack(pady=10, fill="x", expand=True)

        self.percent_label = ttkb.Label(main_frame, text="0%", font=("Segoe UI", 10))
        self.percent_label.pack()

        self.center_on_parent()

    def update_progress(self, value, total):
        percent = int((value / total) * 100)
        self.progress['value'] = percent
        self.percent_label.config(text=f"{percent}%")
        self.status_label.config(text=f"Baixando... ({value/1024/1024:.2f} MB / {total/1024/1024:.2f} MB)")

    def center_on_parent(self):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - self.winfo_width()) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

# --- Lógica de Atualização ---

def check_for_updates(root, current_version, on_startup=False):
    """ Verifica atualizações. Se on_startup for True, força a atualização se a flag estiver ativa. """
    config_path = _get_config_path()
    # Checa a flag de atualização ao iniciar
    if on_startup and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            if config.get('update_on_startup'):
                print("Flag 'update_on_startup' encontrada. Resetando e tentando atualizar...")
                # Reseta a flag ANTES de tentar a atualização para evitar loops
                _set_update_on_startup_flag(False)
                # Força a verificação e o download
                threading.Thread(target=_perform_check, args=(root, current_version, True), daemon=True).start()
                return  # Impede a verificação normal de ser executada
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erro ao ler o arquivo de configuracao: {e}")

    # Verificação normal (manual ou na inicialização sem a flag)
    threading.Thread(target=_perform_check, args=(root, current_version, False), daemon=True).start()

def _perform_check(root, current_version, force_update=False):
    """ Realiza a chamada à API e compara as versões. """
    try:
        response = requests.get(GITHUB_API_URL, timeout=15)
        response.raise_for_status()
        latest_release = response.json()
        tag_name = latest_release.get("tag_name", "0.0.0")
        latest_version_str = tag_name.lstrip('v')

        if force_update or parse_version(latest_version_str) > parse_version(current_version):
            assets = latest_release.get("assets", [])
            if force_update:
                # Se forçado (vindo do update_on_startup), não mostra notificação, baixa direto.
                root.after(0, download_and_install, root, assets)
            else:
                # Se for verificação normal, mostra a notificação para o usuário decidir.
                release_notes = latest_release.get("body", "")
                root.after(0, show_update_notification, root, latest_version_str, release_notes, assets)
    except Exception as e:
        print(f"Erro ao verificar atualizações: {e}")

def show_update_notification(root, version, notes, assets):
    """ Mostra a janela de notificação e processa a escolha do usuário. """
    alert_consolidator = getattr(getattr(root, 'app', None), 'alert_consolidator', None)

    if alert_consolidator:
        alert_consolidator.suppress_alerts = True

    win = UpdateNotificationWindow(root, version, notes, assets)
    root.wait_window(win)

    if alert_consolidator:
        alert_consolidator.suppress_alerts = False

    if win.result == "now":
        download_and_install(root, assets)
    elif win.result == "startup":
        _set_update_on_startup_flag(True)

def _get_config_path():
    return os.path.join(get_application_path(), CONFIG_FILE_NAME)

def _set_update_on_startup_flag(status: bool):
    """ Define a flag no config.json. """
    config_path = _get_config_path()
    try:
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f: config = json.load(f)
        config['update_on_startup'] = status
        with open(config_path, 'w') as f: json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar flag de atualização: {e}")

# --- Lógica de Download e Instalação ---

def download_and_install(root, assets):
    """ Encontra o asset .exe, baixa, verifica o checksum e inicia o processo de atualização. """
    exe_asset = None
    checksum_asset = None
    for asset in assets:
        name = asset.get('name', '').lower()
        if name.endswith('.exe'):
            exe_asset = asset
        elif name.endswith('.sha256'):
            checksum_asset = asset

    if not exe_asset:
        messagebox.showerror("Erro de Atualização", "Nenhum arquivo .exe encontrado na nova versão.")
        return

    download_url = exe_asset.get('browser_download_url')
    checksum_url = checksum_asset.get('browser_download_url') if checksum_asset else None

    if not download_url:
        messagebox.showerror("Erro de Atualização", "URL para download não encontrada.")
        return

    progress_window = DownloadProgressWindow(root)

    def download_thread():
        try:
            expected_checksum = None
            if checksum_url:
                try:
                    checksum_response = requests.get(checksum_url, timeout=15)
                    checksum_response.raise_for_status()
                    expected_checksum = checksum_response.text.split()[0].lower()
                except Exception as e:
                    print(f"Alerta: Nao foi possivel baixar o checksum: {e}")
                    # Nao bloqueia a atualização se o checksum falhar, mas avisa no console.
                    # Em um cenario ideal, poderiamos querer bloquear.

            download_path = os.path.join(get_application_path(), DOWNLOADED_FILE_NAME)
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            sha256_hash = hashlib.sha256()

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    sha256_hash.update(chunk)
                    bytes_downloaded += len(chunk)
                    if total_size > 0:
                        progress_window.update_progress(bytes_downloaded, total_size)

            if expected_checksum:
                calculated_checksum = sha256_hash.hexdigest()
                if calculated_checksum != expected_checksum:
                    progress_window.destroy()
                    os.remove(download_path)  # Limpa o arquivo corrompido
                    messagebox.showerror("Erro de Atualização", "A verificação de integridade (checksum) falhou. O arquivo baixado pode estar corrompido ou ter sido adulterado. A atualização foi cancelada por segurança.")
                    return

            progress_window.destroy()
            root.after(0, launch_updater_and_exit, root)

        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Erro no Download", f"Falha ao baixar a atualização: {e}")

    threading.Thread(target=download_thread, daemon=True).start()

def create_updater_script():
    """ Cria o script .bat que substituirá o executável de forma mais robusta. """
    app_path = get_application_path()
    current_exe_path = sys.executable
    current_exe_name = os.path.basename(current_exe_path)
    downloaded_exe_path = os.path.join(app_path, DOWNLOADED_FILE_NAME)
    backup_exe_path = os.path.join(app_path, f"{os.path.splitext(current_exe_name)[0]}.bak")

    script_content = f"""
@echo off
setlocal
chcp 65001 > nul

set "APP_PID={os.getpid()}"
set "CURRENT_EXE={current_exe_path}"
set "CURRENT_EXE_NAME={current_exe_name}"
set "DOWNLOADED_EXE={downloaded_exe_path}"
set "BACKUP_EXE={backup_exe_path}"

echo.
echo =================================
echo == ATUALIZADOR DE APLICATIVO ==
echo =================================
echo.

echo Encerrando a aplicacao (PID: %APP_PID%)...
taskkill /F /PID %APP_PID% > nul 2>&1

echo Aguardando o processo finalizar...
:wait_for_exit
timeout /t 1 /nobreak > nul
tasklist /FI "PID eq %APP_PID%" 2>NUL | find /I "%APP_PID%" > NUL
if not errorlevel 1 (
    echo Processo ainda em execucao, aguardando...
    goto wait_for_exit
)
echo Processo finalizado com sucesso.

echo.
echo Criando backup do executavel atual...
if exist "%BACKUP_EXE%" (
    del "%BACKUP_EXE%"
)
move /Y "%CURRENT_EXE%" "%BACKUP_EXE%"
if errorlevel 1 (
    echo ERRO: Falha ao criar backup do executavel atual.
    echo A atualizacao foi abortada.
    pause
    exit /b 1
)
echo Backup criado: %BACKUP_EXE%

echo.
echo Substituindo pelo novo executavel...
move /Y "%DOWNLOADED_EXE%" "%CURRENT_EXE%"
if errorlevel 1 (
    echo ERRO: Nao foi possivel mover o novo executavel para o diretorio do aplicativo.
    echo Restaurando a versao anterior a partir do backup...
    move /Y "%BACKUP_EXE%" "%CURRENT_EXE%"
    echo A versao anterior foi restaurada.
    pause
    exit /b 1
)
echo Novo executavel instalado com sucesso.

echo.
echo Reiniciando o aplicativo...
start "" /B "%CURRENT_EXE%"

echo.
echo Verificando se a nova versao iniciou...
timeout /t 5 /nobreak > nul

rem Verifica se o processo com o mesmo nome esta rodando.
rem Isso e uma heuristica e pode nao ser 100%% confiavel se houver outros processos com o mesmo nome.
tasklist /FI "IMAGENAME eq %CURRENT_EXE_NAME%" /NH | find /I "%CURRENT_EXE_NAME%" > nul
if errorlevel 1 (
    echo.
    echo ATENCAO: A nova versao do aplicativo parece ter falhado ao iniciar.
    echo Restaurando a versao anterior para garantir que voce possa usar o programa...
    taskkill /F /IM "%CURRENT_EXE_NAME%" > nul 2>&1
    timeout /t 1 /nobreak > nul
    move /Y "%BACKUP_EXE%" "%CURRENT_EXE%"
    echo A versao anterior foi restaurada.
    echo Por favor, tente iniciar o aplicativo manualmente. Se o erro persistir, procure suporte.
    pause
    exit /b 1
)

echo.
echo Atualizacao parece ter sido bem-sucedida!
echo Limpando arquivo de backup...
del "%BACKUP_EXE%" > nul 2>&1

echo.
echo O atualizador sera autodestruido agora.
(goto) 2>nul & del "%~f0"

endlocal
"""
    script_path = os.path.join(app_path, UPDATER_SCRIPT_NAME)
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        return script_path
    except Exception as e:
        print(f"Erro critico ao criar o script de atualizacao: {e}")
        return None

def launch_updater_and_exit(root):
    """ Cria e executa o script de atualização, depois fecha a aplicação. """

    messagebox.showinfo("Atualização Concluída", "Download concluido, o programa sera reiniciado.")

    try:
        updater_script_path = create_updater_script()
        # Usar DETACHED_PROCESS para que o script não seja filho do processo principal
        subprocess.Popen([updater_script_path], creationflags=subprocess.DETACHED_PROCESS, shell=True)
        # Força o fechamento da aplicação
        root.destroy()
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Erro Crítico", f"Nao foi possível iniciar o atualizador: {e}")
