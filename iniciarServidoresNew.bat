@echo off

cd /d D:\Importantes\crypto-monitor-WEB

call .\.venv\Scripts\activate.bat

start "Frontend Server" cmd /k npm run dev --host

start "Backend Server" cmd /k uvicorn backend.api_server:app --reload --port 8000

start http://localhost:5173/

pause
