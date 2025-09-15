#!/bin/bash

echo "Iniciando servidores da aplicação MonitorCripto..."

# A execução será no diretório atual

# --- Iniciar o Backend ---
echo "Iniciando o Backend em uma sessão 'screen'..."
# Cria uma nova sessão screen chamada 'backend', entra nela, ativa o venv e inicia o uvicorn
screen -dmS backend bash -c 'source .venv/bin/activate; uvicorn backend.api_server:app --port 8000'

# --- Iniciar o Frontend ---
echo "Iniciando o Frontend em uma sessão 'screen'..."
# Cria uma nova sessão screen chamada 'frontend', entra nela e inicia o servidor npm
# Nota: No servidor, geralmente usamos 'npm start' em vez de 'npm run dev'
screen -dmS frontend bash -c 'npm run dev'

echo "Servidores iniciados! Verificando as sessões ativas..."
sleep 2 # Dá um tempinho para as sessões aparecerem

# Mostra as sessões que estão a correr para confirmar
screen -ls

echo "Processo concluído!"