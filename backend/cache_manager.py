import json
import hashlib
import os
from typing import Optional, Any, Dict

# Define um diretório para os arquivos de cache na raiz do projeto
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '.cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def generate_cache_key(symbol: str, start_date: str, end_date: str, alert_config: Dict[str, Any], timeframes_config: Dict[str, int]) -> str:
    """
    Gera uma chave de cache única baseada nos parâmetros do backtest.
    """
    # Cria uma representação em string consistente dos parâmetros
    # O sort_keys=True garante que a ordem das chaves não altere o hash
    params_str = json.dumps({
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'alert_config': alert_config,
        'timeframes_config': timeframes_config
    }, sort_keys=True)

    # Usa SHA256 para criar um hash da string de parâmetros
    return hashlib.sha256(params_str.encode('utf-8')).hexdigest()

def save_to_cache(cache_key: str, data: Any):
    """
    Salva os dados em um arquivo de cache.
    """
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Resultado do backtest salvo com sucesso no cache: {cache_file}")
    except Exception as e:
        print(f"Erro ao salvar no arquivo de cache {cache_file}: {e}")

def load_from_cache(cache_key: str) -> Optional[Any]:
    """
    Carrega os dados de um arquivo de cache, se ele existir.
    """
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                print(f"Carregando resultado do backtest do cache: {cache_file}")
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar do arquivo de cache {cache_file}: {e}")
            return None
    return None
