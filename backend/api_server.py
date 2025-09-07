import logging
import os
import json
from threading import Lock
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Import core logic from the existing application ---
# These imports will be used to power the API endpoints.
# We will need to adapt the functions to work in an API context.
from .monitoring_service import (
    get_klines_data,
    get_ticker_data,
    get_market_caps_coingecko,
    _analyze_symbol, # Renaming to 'analyze_symbol' for clarity
    fetch_all_binance_symbols_startup,
    get_coingecko_global_mapping,
    get_btc_dominance
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

@app.get("/api/global_data")
async def get_global_data():
    """
    Provides global market data, such as BTC dominance.
    """
    logging.info("Fetching global market data...")
    try:
        btc_dominance_value = get_btc_dominance()
        return {"btc_dominance": btc_dominance_value}
    except Exception as e:
        logging.error(f"Error fetching global data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Coin Manager Initialization ---
# This manager handles fetching and caching the full list of coins from CoinGecko.
coin_manager_instance = coin_manager.CoinManager()

class Coin(BaseModel):
    id: str
    symbol: str
    name: str

@app.get("/api/all_tradable_coins", response_model=List[Coin])
async def get_all_tradable_coins():
    """
    Provides a list of all available coins from CoinGecko, including names and symbols.
    The list is cached by the CoinManager to improve performance.
    """
    logging.info("Fetching all tradable coins from CoinManager...")
    try:
        # The CoinManager handles its own caching.
        all_coins = coin_manager_instance.get_all_coins()
        if not all_coins:
            raise HTTPException(status_code=500, detail="Failed to fetch coin list from CoinManager.")

        # We need to filter this list to match Binance's USDT pairs if necessary,
        # but for now, returning the full list is better for the UI.
        # This returns a list of dicts like {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin'}
        return all_coins
    except Exception as e:
        logging.error(f"Error fetching all tradable coins from CoinManager: {e}")
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
            analysis = _analyze_symbol(symbol, ticker_data, market_cap, coingecko_mapping)
            results.append(analysis)

        return results
    except Exception as e:
        logging.error(f"An error occurred while fetching crypto data: {e}")
        # Using a 500 error but could be more specific depending on the exception
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- Configuration and Alert History Endpoints ---

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ALERT_HISTORY_FILE_PATH = os.path.join(os.path.dirname(__file__), "alert_history.json")
HISTORY_LOCK = Lock()

class Alert(BaseModel):
    id: str
    symbol: str
    condition: str
    description: str
    timestamp: str
    snapshot: Dict[str, Any]

@app.get("/api/alerts", response_model=List[Alert])
async def get_alert_history(
    start_date: Optional[str] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (YYYY-MM-DD)")
):
    """
    Reads and returns the persistent alert history.
    Can be filtered by a date range.
    """
    try:
        with HISTORY_LOCK:
            if not os.path.exists(ALERT_HISTORY_FILE_PATH):
                return []
            with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                try:
                    content = f.read()
                    if not content:
                        return []
                    history = json.loads(content)
                    if not isinstance(history, list):
                        history = []
                except json.JSONDecodeError:
                    history = []

            if not history:
                return []

            # Filter by date range if parameters are provided
            if start_date and end_date:
                try:
                    # Add time to end_date to include the whole day
                    start_dt = datetime.fromisoformat(start_date + "T00:00:00")
                    end_dt = datetime.fromisoformat(end_date + "T23:59:59")

                    filtered_history = [
                        alert for alert in history
                        if start_dt <= datetime.fromisoformat(alert['timestamp']) <= end_dt
                    ]
                    return filtered_history
                except (ValueError, TypeError) as e:
                    logging.error(f"Invalid date format provided: {e}")
                    raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")

            return history

    except Exception as e:
        logging.error(f"Error reading or filtering alert history file: {e}")
        raise HTTPException(status_code=500, detail="Error reading or filtering alert history file.")

@app.post("/api/alerts")
async def save_alert_to_history(alert: Alert):
    """Saves a triggered alert to the persistent history file."""
    try:
        with HISTORY_LOCK:
            history = []
            if os.path.exists(ALERT_HISTORY_FILE_PATH):
                with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                        if content:
                            history = json.loads(content)
                        if not isinstance(history, list):
                            history = []
                    except json.JSONDecodeError:
                        history = []

            history.insert(0, alert.dict())

            MAX_HISTORY_SIZE = 500
            if len(history) > MAX_HISTORY_SIZE:
                history = history[:MAX_HISTORY_SIZE]

            with open(ALERT_HISTORY_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)

        logging.info(f"Saved alert for {alert.symbol} to history.")
        return {"message": "Alert saved to history."}
    except Exception as e:
        logging.error(f"Error saving alert to history: {e}")
        raise HTTPException(status_code=500, detail="Could not save alert to history.")

@app.delete("/api/alerts/history")
async def clear_alert_history():
    """Clears all alerts from the persistent history file."""
    try:
        with HISTORY_LOCK:
            # Overwrite the file with an empty JSON array
            with open(ALERT_HISTORY_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f)
        logging.info("Alert history has been cleared.")
        return {"message": "Alert history cleared successfully."}
    except Exception as e:
        logging.error(f"Error clearing alert history: {e}")
        raise HTTPException(status_code=500, detail="Could not clear alert history.")

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

# --- Coin Management Endpoints ---

class CoinSymbol(BaseModel):
    symbol: str

@app.post("/api/monitored_coins")
async def add_monitored_coin(coin: CoinSymbol):
    """Adds a new coin to the monitored list in config.json."""
    try:
        with open(CONFIG_FILE_PATH, 'r+', encoding='utf-8') as f:
            config_data = json.load(f)

            # Find the 'cryptos_to_monitor' list and add the new symbol if not present
            if 'cryptos_to_monitor' not in config_data:
                config_data['cryptos_to_monitor'] = []

            # Robust check for existing coin, handling both dict and string formats
            monitored_list = config_data.get('cryptos_to_monitor', [])
            is_present = any(
                (isinstance(c, dict) and c.get('symbol') == coin.symbol) or
                (isinstance(c, str) and c == coin.symbol)
                for c in monitored_list
            )

            if not is_present:
                # Add the new coin with a default alert configuration
                monitored_list.append({
                    "symbol": coin.symbol,
                    "alert_config": {
                        "conditions": {
                            "rsi_sobrevendido": {"enabled": True, "blinking": True},
                            "rsi_sobrecomprado": {"enabled": True, "blinking": True},
                            "hilo_compra": {"enabled": True, "blinking": True},
                            "mme_cruz_dourada": {"enabled": False, "blinking": True},
                            "mme_cruz_morte": {"enabled": False, "blinking": True},
                            "macd_cruz_alta": {"enabled": True, "blinking": True},
                            "macd_cruz_baixa": {"enabled": True, "blinking": True}
                        }
                    }
                })

                f.seek(0)
                json.dump(config_data, f, indent=2)
                f.truncate()
                logging.info(f"Added new coin to monitor: {coin.symbol}")
                return {"message": f"Coin {coin.symbol} added successfully."}
            else:
                logging.warning(f"Attempted to add existing coin: {coin.symbol}")
                return {"message": f"Coin {coin.symbol} is already being monitored."}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found.")
    except Exception as e:
        logging.error(f"Error adding monitored coin: {e}")
        raise HTTPException(status_code=500, detail="Error adding monitored coin.")


@app.delete("/api/monitored_coins/{symbol}")
async def remove_monitored_coin(symbol: str):
    """Removes a coin from the monitored list in config.json."""
    try:
        with open(CONFIG_FILE_PATH, 'r+', encoding='utf-8') as f:
            config_data = json.load(f)

            original_count = len(config_data.get('cryptos_to_monitor', []))
            config_data['cryptos_to_monitor'] = [
                c for c in config_data.get('cryptos_to_monitor', []) if c.get('symbol') != symbol
            ]

            if len(config_data['cryptos_to_monitor']) < original_count:
                f.seek(0)
                json.dump(config_data, f, indent=2)
                f.truncate()
                logging.info(f"Removed coin from monitoring: {symbol}")
                return {"message": f"Coin {symbol} removed successfully."}
            else:
                raise HTTPException(status_code=404, detail=f"Coin {symbol} not found in monitored list.")

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found.")
    except Exception as e:
        logging.error(f"Error removing monitored coin: {e}")
        raise HTTPException(status_code=500, detail="Error removing monitored coin.")


# To run this server, use the following command in your terminal:
# uvicorn backend.api_server:app --reload --port 8000
