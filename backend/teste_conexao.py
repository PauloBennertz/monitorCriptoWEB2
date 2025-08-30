# teste_conexao.py

import requests
import time

# O mesmo endereço que a biblioteca pycoingecko usa para o "ping"
url = "https://api.coingecko.com/api/v3/ping"

print("Tentando conectar a api.coingecko.com...")

try:
    start_time = time.time()
    # Timeout de 15 segundos para não esperar para sempre
    response = requests.get(url, timeout=15)
    end_time = time.time()

    # Verifica se a resposta foi bem-sucedida (código 200)
    response.raise_for_status()

    print("\n--- SUCESSO! ---")
    print(f"Resposta recebida em: {end_time - start_time:.2f} segundos.")
    print(f"Status da API: {response.json()}")

except requests.exceptions.Timeout:
    print("\n--- FALHA ---")
    print("Erro: A conexão demorou demais para responder (Timeout).")
    print("Isso geralmente indica um bloqueio de firewall ou problema de rede.")

except requests.exceptions.RequestException as e:
    print("\n--- FALHA ---")
    print(f"Erro de conexão: {e}")
    print("Isso pode ser um problema de internet, DNS ou um bloqueio de firewall/antivírus.")

# Pausa para que a janela do terminal não feche imediatamente
input("\nPressione Enter para sair...")