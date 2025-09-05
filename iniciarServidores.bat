@echo off
setlocal

REM Define o caminho para a pasta do projeto
set PROJECT_DIR=D:\Importantes\crypto-monitor-WEB

REM Define as URLs para abrir

set VITE_URL=http://localhost:5173/

REM Muda para o diretório do projeto
cd /d "%PROJECT_DIR%"

REM Ativa o ambiente virtual (.venv)
call .\.venv\Scripts\activate.bat

REM Inicia o servidor Uvicorn em uma nova janela de terminal
start "Uvicorn Server" cmd /k "uvicorn backend.api_server:app --reload --port 8000"

REM Inicia o servidor Vite em uma nova janela de terminal
start "Vite Server" cmd /k "npm run dev --host"

REM Aguarda alguns segundos para os servidores iniciarem
timeout /t 5 /nobreak >nul

REM Abre as URLs nos navegadores padrão
start "" "%UVICORN_URL%"
start "" "%VITE_URL%"

echo.
echo Servidores Uvicorn (porta 8000) e Vite (porta 5173) iniciados.
echo Pressione qualquer tecla para parar e fechar esta janela.

pause >nul
endlocal