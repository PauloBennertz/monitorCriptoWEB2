import os
import subprocess
import sys

def build_exe():
    """Script para gerar o executável do Monitor de Criptomoedas"""

    print("🚀 Iniciando build do executável...")

    # Comando PyInstaller
    cmd = [
        'pyinstaller',
        '--onefile',  # Arquivo único
        '--windowed',  # Sem console
        '--name=MonitorCriptomoedas',
        '--add-data=version.txt;.', # Incluir o arquivo de versão
        '--add-data=icons;icons',  # Incluir pasta de ícones
        '--add-data=sons;sons',    # Incluir pasta de sons
        '--add-data=config.json;.',  # Incluir arquivo de configuração
        '--hidden-import=ttkbootstrap',
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=requests',
        '--hidden-import=pycoingecko',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=threading',
        '--hidden-import=queue',
        '--hidden-import=json',
        '--hidden-import=os',
        '--hidden-import=sys',
        '--hidden-import=time',
        '--hidden-import=logging',
        '--hidden-import=datetime',
        '--hidden-import=collections',
        '--hidden-import=hashlib',
        '--hidden-import=dataclasses',
        '--hidden-import=typing',
        '--hidden-import=io',
        '--hidden-import=asyncio',
        '--clean',  # Limpar cache
        'main_app.py'
    ]

    try:
        print("📦 Executando PyInstaller...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Executável gerado com sucesso!")
        print("📁 Arquivo criado em: dist/MonitorCriptomoedas.exe")

        # Verificar se o arquivo foi criado
        exe_path = "dist/MonitorCriptomoedas.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)  # Tamanho em MB
            print(f"📊 Tamanho do executável: {size:.1f} MB")
        else:
            print("❌ Erro: Executável não foi criado")

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro durante o build: {e}")
        print(f"📋 Saída de erro: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

    return True

if __name__ == "__main__":
    build_exe()