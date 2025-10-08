@echo off
setlocal

echo Starting Vite frontend and Uvicorn backend servers in a single window...
echo Outputs will be mixed.
echo This might take a few moments.

REM Inicia o Vite em segundo plano (não vai aparecer em uma janela separada)
echo Starting Vite server (frontend) in background...
start /b cmd /c "call venv\Scripts\activate.bat && .\node_modules\.bin\vite --host"



REM Ativa o ambiente virtual (para o Uvicorn)
call venv\Scripts\activate.bat


echo Opening browser...
start http://127.0.0.1:5173

REM Inicia o Uvicorn no mesmo terminal (não em uma nova janela)
echo Starting Uvicorn server (backend) in foreground...
uvicorn backend.api_server:app --reload --port 8000

REM A linha acima vai assumir o controle do terminal.
REM Pressione CTRL+C nesta janela para parar AMBOS os servidores.
REM O comando 'start /b' para o Vite garante que ele seja um processo filho
REM e geralmente é encerrado quando o processo pai (Uvicorn neste caso) é encerrado
REM com CTRL+C, mas nem sempre é garantido.

endlocal