@echo off
REM Altera para o diretório onde o projeto está localizado
cd /d D:\VPS\monitorCriptoWEB\
REM Executa o programa Python
python -m backend.gui_backtester

REM Mantém a janela aberta após a execução (opcional, para ver erros)
pause