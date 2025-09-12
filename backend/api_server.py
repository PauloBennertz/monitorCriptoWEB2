import logging
import os
import json
import subprocess
import sys
from threading import Lock
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# This ensures that the 'backend' package can be found by Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Import core logic from the existing application ---
# These imports will be used to power the API endpoints.
# We will need to adapt the functions to work in an API context.
from backend.monitoring_service import (
    get_klines_data,
    get_ticker_data,
    get_market_caps_coingecko,
    _analyze_symbol, # Renaming to 'analyze_symbol' for clarity
    fetch_all_binance_symbols_startup,
    get_coingecko_global_mapping,
    get_btc_dominance
)
from backend import app_state
from backend import coin_manager

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
    "http://12_7.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"], # Allow all headers
)

# --- Determine base path for data files ---
def get_base_path():
    # If the application is run as a bundle, the PyInstaller bootloader
    # sets the sys._MEIPASS attribute to the temporary folder where the app is unpacked.
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    # Otherwise, it's running from source, so we can use the script's directory.
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

# --- Caching ---
# Simple in-memory cache to hold data that doesn't change often, like the coin list.
# This avoids hitting the APIs repeatedly for the same information.
api_cache = {}

# --- API Endpoints ---

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

from backend.monitoring_service import fetch_all_binance_symbols_startup

@app.get("/api/all_tradable_coins", response_model=List[Coin])
async def get_all_tradable_coins():
    """
    Provides a filtered list of coins that are tradable on Binance with a USDT pair.
    The list is enriched with names from CoinGecko.
    """
    logging.info("Fetching all tradable coins...")
    try:
        # 1. Fetch all symbols ending in USDT from Binance
        # We pass an empty config because we don't need the fallback logic here.
        binance_symbols = fetch_all_binance_symbols_startup({})
        if not binance_symbols:
            raise HTTPException(status_code=503, detail="Could not fetch symbol list from Binance.")

        # Create a set of base assets for efficient lookup (e.g., {'BTC', 'ETH'})
        tradable_base_assets = {s.replace('USDT', '') for s in binance_symbols}

        # 2. Get the full list of coins from CoinGecko (cached by the manager)
        all_coingecko_coins = coin_manager_instance.get_all_coins()
        if not all_coingecko_coins:
            raise HTTPException(status_code=500, detail="Failed to fetch coin list from CoinManager.")

        # 3. Filter the CoinGecko list to include only coins tradable on Binance
        # Also, ensure we use the uppercase symbol consistent with Binance.
        filtered_coins = [
            {
                "id": coin['id'],
                "symbol": coin['symbol'].upper(), # Use the uppercase symbol
                "name": coin['name']
            }
            for coin in all_coingecko_coins
            if coin['symbol'].upper() in tradable_base_assets
        ]

        # Sort the list alphabetically by name for a better user experience
        sorted_filtered_coins = sorted(filtered_coins, key=lambda x: x['name'])

        logging.info(f"Returning {len(sorted_filtered_coins)} tradable coins.")
        return sorted_filtered_coins

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
            analysis = _analyze_symbol(symbol, ticker_data, market_cap, coingecko_mapping)
            results.append(analysis)

        return results
    except Exception as e:
        logging.error(f"An error occurred while fetching crypto data: {e}")
        # Using a 500 error but could be more specific depending on the exception
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- Configuration and Alert History Endpoints ---

CONFIG_FILE_PATH = os.path.join(BASE_PATH, "config.json")
ALERT_HISTORY_FILE_PATH = os.path.join(BASE_PATH, "alert_history.json")
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
        # --- Symbol Normalization ---
        # A safeguard to correct common client-side formatting errors like 'BTCUSDUSDT'
        normalized_symbol = coin.symbol.upper()
        if "USDUSDT" in normalized_symbol:
            normalized_symbol = normalized_symbol.replace("USDUSDT", "USDT")

        with open(CONFIG_FILE_PATH, 'r+', encoding='utf-8') as f:
            config_data = json.load(f)

            # Find the 'cryptos_to_monitor' list and add the new symbol if not present
            if 'cryptos_to_monitor' not in config_data:
                config_data['cryptos_to_monitor'] = []

            # Robust check for existing coin using the normalized symbol
            monitored_list = config_data.get('cryptos_to_monitor', [])
            is_present = any(
                (isinstance(c, dict) and c.get('symbol') == normalized_symbol) or
                (isinstance(c, str) and c == normalized_symbol)
                for c in monitored_list
            )

            if not is_present:
                # Add the new coin with a default alert configuration
                monitored_list.append({
                    "symbol": normalized_symbol, # Use the normalized symbol
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
                logging.info(f"Added new coin to monitor: {normalized_symbol}")
                return {"message": f"Coin {normalized_symbol} added successfully."}
            else:
                logging.warning(f"Attempted to add existing coin: {normalized_symbol}")
                return {"message": f"Coin {normalized_symbol} is already being monitored."}

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


@app.post("/api/start-backtester")
async def start_backtester():
    """
    Starts the gui_backtester.py script as a separate process.
    """
    logging.info("Received request to start the backtester GUI.")
    try:
        # Construct the full path to the script relative to the server's base path.
        script_path = os.path.join(BASE_PATH, "gui_backtester.py")

        # Determine the correct python executable to use (the one running the server).
        python_executable = sys.executable

        if not os.path.exists(script_path):
            logging.error(f"Backtester script not found at: {script_path}")
            raise HTTPException(status_code=404, detail=f"Backtester script not found at path: {script_path}")

        # Use Popen to run the script in a new process without blocking the server.
        # It's launched in the background.
        subprocess.Popen([python_executable, script_path])

        logging.info(f"Successfully launched script: {script_path}")
        return {"message": "Backtester GUI started successfully."}
    except Exception as e:
        logging.error(f"Failed to start the backtester GUI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# To run this server, use the following command in your terminal:
# uvicorn backend.api_server:app --reload --port 8000

# --- Serve Static Files ---
# This must be placed after all API routes. It serves the built React frontend.
if hasattr(sys, '_MEIPASS'):
    # In bundled app, static files are at the root of the temporary directory (_MEIPASS).
    static_files_path = sys._MEIPASS
else:
    # In development, static files are in the 'dist' directory, relative to the project root.
    # The script is in backend/, so we go up one level to the project root, then into 'dist'.
    static_files_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dist'))

if os.path.exists(static_files_path):
    app.mount("/", StaticFiles(directory=static_files_path, html=True), name="static")
else:
    logging.warning(f"Static files directory not found at '{static_files_path}'. The frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
