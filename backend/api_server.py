import logging
import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any

# --- Import core logic from the existing application ---
# These imports will be used to power the API endpoints.
# We will need to adapt the functions to work in an API context.
from .monitoring_service import (
    get_klines_data,
    get_ticker_data,
    get_market_caps_coingecko,
    _analyze_symbol, # Renaming to 'analyze_symbol' for clarity
    fetch_all_binance_symbols_startup,
    get_coingecko_global_mapping
)
from . import app_state
from . import coin_manager

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Crypto Monitor Pro API",
    description="API server for the Crypto Monitor Pro web application.",
    version="1.0.0"
)

# --- CORS (Cross-Origin Resource Sharing) Configuration ---
# This allows the React frontend (running on http://localhost:5173) to communicate with this API.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- Caching ---
# Simple in-memory cache to hold data that doesn't change often, like the coin list.
# This avoids hitting the APIs repeatedly for the same information.
api_cache = {}

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Welcome to the Crypto Monitor Pro API!"}

@app.get("/api/all_tradable_coins", response_model=List[str])
async def get_all_tradable_coins():
    """
    Provides a list of all available USDT trading pairs from Binance.
    The list is cached to improve performance.
    """
    if "all_coins" in api_cache:
        return api_cache["all_coins"]

    logging.info("Fetching all tradable coins from Binance...")
    try:
        # We pass an empty dict for config as it's only used for fallback.
        symbols = fetch_all_binance_symbols_startup({})
        if not symbols:
            raise HTTPException(status_code=500, detail="Failed to fetch symbols from Binance.")

        api_cache["all_coins"] = symbols
        return symbols
    except Exception as e:
        logging.error(f"Error fetching all tradable coins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crypto_data", response_model=List[Dict[str, Any]])
async def get_crypto_data(symbols: List[str] = Query(..., description="A list of crypto symbols to fetch data for (e.g., ['BTCUSDT', 'ETHUSDT'])")):
    """
    The main endpoint to get analyzed data for a list of cryptocurrencies.
    """
    logging.info(f"Received request for crypto data for symbols: {symbols}")

    if not symbols:
        return []

    try:
        # This is a simplified workflow for now. More robust implementation will follow.
        # 1. Get 24h ticker data for all coins (one API call)
        ticker_data = get_ticker_data()
        if not ticker_data:
            raise HTTPException(status_code=503, detail="Could not fetch ticker data from Binance.")

        # 2. Get CoinGecko mapping (cached)
        coingecko_mapping = get_coingecko_global_mapping()

        # 3. Get market caps for the requested symbols
        market_caps = get_market_caps_coingecko(symbols, coingecko_mapping)

        # 4. Analyze each symbol
        results = []
        for symbol in symbols:
            market_cap = market_caps.get(symbol)
            # The _analyze_symbol function contains the core logic we need.
            analysis = _analyze_symbol(symbol, ticker_data, market_cap)
            results.append(analysis)

        return results
    except Exception as e:
        logging.error(f"An error occurred while fetching crypto data: {e}")
        # Using a 500 error but could be more specific depending on the exception
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- Configuration and Alert History Endpoints ---

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ALERT_HISTORY_FILE_PATH = os.path.join(os.path.dirname(__file__), "alert_history.json")

@app.get("/api/alert_configs", response_model=Dict[str, Any])
async def get_alert_configs():
    """Reads and returns the entire application configuration from config.json."""
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found.")
    except Exception as e:
        logging.error(f"Error reading config file: {e}")
        raise HTTPException(status_code=500, detail="Error reading configuration file.")

@app.post("/api/alert_configs")
async def set_alert_configs(new_config: Dict[str, Any]):
    """Receives a new configuration and overwrites config.json."""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2)
        return {"message": "Configuration saved successfully."}
    except Exception as e:
        logging.error(f"Error writing to config file: {e}")
        raise HTTPException(status_code=500, detail="Error saving configuration file.")

@app.get("/api/alerts", response_model=List[Dict[str, Any]])
async def get_alerts():
    """Reads and returns the alert history from alert_history.json."""
    try:
        if not os.path.exists(ALERT_HISTORY_FILE_PATH):
            return []
        with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error reading alert history file: {e}")
        raise HTTPException(status_code=500, detail="Error reading alert history file.")

# To run this server, use the following command in your terminal:
# uvicorn backend.api_server:app --reload --port 8000
