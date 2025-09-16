@echo off
setlocal

echo Attempting to stop Vite (Frontend) and Uvicorn (Backend) servers...

REM Encerra o servidor Vite (node.exe) pela janela que o executa
echo Stopping Vite Server...
taskkill /FI "WINDOWTITLE eq Vite Server (Frontend)" /F /T
IF %ERRORLEVEL% NEQ 0 (
    echo WARNING: Could not find or terminate Vite Server by window title.
    echo Please check if 'Vite Server (Frontend)' window is open or use Task Manager.
) ELSE (
    echo Vite Server (Frontend) terminated.
)

REM Encerra o servidor Uvicorn (python.exe) pela janela que o executa
echo Stopping Uvicorn Server...
taskkill /FI "WINDOWTITLE eq Uvicorn Server (Backend)" /F /T
IF %ERRORLEVEL% NEQ 0 (
    echo WARNING: Could not find or terminate Uvicorn Server by window title.
    echo Please check if 'Uvicorn Server (Backend)' window is open or use Task Manager.
) ELSE (
    echo Uvicorn Server (Backend) terminated.
)

echo Server shutdown process complete.

endlocal
pause