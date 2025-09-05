import json
import os
import sys
import time
import logging

def get_application_path():
    """Retorna o caminho do diretório da aplicação, compatível com PyInstaller."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

STATE_FILE_PATH = os.path.join(get_application_path(), "app_state.json")

def load_app_state():
    """Carrega o estado da aplicação a partir de app_state.json."""
    if not os.path.exists(STATE_FILE_PATH):
        return {'last_api_fetch_timestamp': 0}
    try:
        with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {'last_api_fetch_timestamp': 0}

def save_app_state(state):
    """Salva o estado da aplicação em app_state.json."""
    try:
        with open(STATE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        logging.info("Estado da aplicação salvo com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar o estado da aplicação: {e}")

def get_last_fetch_timestamp():
    """Retorna o timestamp da última busca de API."""
    state = load_app_state()
    return state.get('last_api_fetch_timestamp', 0)

def update_last_fetch_timestamp():
    """Atualiza o timestamp da última busca de API para o tempo atual."""
    state = load_app_state()
    state['last_api_fetch_timestamp'] = time.time()
    save_app_state(state)

MAPPING_CACHE_FILE = os.path.join(get_application_path(), "coin_mapping.json")

def load_coin_mapping_cache():
    """
    Carrega o mapeamento de nomes de moedas do cache se não tiver mais de 24 horas.
    Retorna o mapeamento ou None se o cache estiver velho ou não existir.
    """
    if not os.path.exists(MAPPING_CACHE_FILE):
        return None

    try:
        with open(MAPPING_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        last_updated = cache_data.get("timestamp", 0)
        if (time.time() - last_updated) < 86400:  # 24 horas em segundos
            logging.info("Mapeamento de moedas carregado do cache.")
            return cache_data.get("mapping")
        else:
            logging.info("Cache de mapeamento de moedas está expirado.")
            return None
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def save_coin_mapping_cache(mapping):
    """
    Salva o mapeamento de nomes de moedas no cache com o timestamp atual.
    """
    cache_data = {
        "timestamp": time.time(),
        "mapping": mapping
    }
    try:
        with open(MAPPING_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4)
        logging.info("Cache de mapeamento de moedas salvo com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar o cache de mapeamento de moedas: {e}")
