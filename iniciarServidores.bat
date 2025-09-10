#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  echo "Activating virtual environment..."
  source ./.venv/bin/activate
else
  echo "Virtual environment .venv not found. Skipping activation."
fi

# Start Uvicorn server in the background
echo "Starting Uvicorn server..."
uvicorn backend.api_server:app --reload --port 8000 > uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "Uvicorn server started with PID $UVICORN_PID"

# Start Vite server in the background
echo "Starting Vite server..."
npm run dev -- --host > vite.log 2>&1 &
VITE_PID=$!
echo "Vite server started with PID $VITE_PID"

echo "Servers are starting in the background."
echo "You can view their logs in uvicorn.log and vite.log"
echo "To stop the servers, run: kill $UVICORN_PID $VITE_PID"
