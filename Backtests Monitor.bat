@echo off
REM Altera para a pasta raiz do projeto
cd /d "d:\Programas\MonitorCriptoWEB2"

REM Ativa o ambiente virtual para garantir que use as bibliotecas instaladas
call venv\Scripts\activate

REM Executa o programa Python como módulo
python -m backend.gui_backtester

pause