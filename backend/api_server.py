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
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import requests
import time

# This ensures that the 'backend' package can be found by Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Import core logic from the existing application ---
from backend.monitoring_service import (
    get_klines_data,
    get_ticker_data,
    get_market_caps_coingecko,
    _analyze_symbol,
    fetch_all_binance_symbols_startup,
    get_coingecko_global_mapping,
    get_btc_dominance
)
from backend import app_state
from backend import coin_manager
from backend.backtester import Backtester, fetch_historical_data
from backend.indicators import calculate_sma
from backend.notification_service import send_telegram_alert

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Crypto Monitor Pro API",
    description="API server for the Crypto Monitor Pro web application.",
    version="1.0.0"
)

# --- CORS (Cross-Origin Resource Sharing) Configuration ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Determine base path for data files ---
def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

# --- Backtesting Components ---

from backend.backtester import MovingAverageCrossoverStrategy

class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000

@app.post("/api/backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    """
    Runs a backtest for a given symbol and date range and returns the chart data.
    """
    try:
        logging.info(f"Received backtest request: {request}")
        historical_data = fetch_historical_data(request.symbol, request.start_date, request.end_date)
        if historical_data.empty:
            raise HTTPException(status_code=404, detail="No historical data found for the given parameters.")

        strategy = MovingAverageCrossoverStrategy()
        backtester = Backtester(historical_data, strategy, request.initial_capital)
        chart_result = backtester.run(coin_id=request.symbol)

        if chart_result is None:
            raise HTTPException(status_code=500, detail="Backtest run failed and did not produce a chart.")

        # The result can be a JSON string (success) or a dict (error from chart_generator)
        if isinstance(chart_result, dict) and 'error' in chart_result:
            logging.error(f"Chart generation failed: {chart_result.get('message')}")
            raise HTTPException(status_code=503, detail=chart_result.get('message', 'Chart generation service is unavailable.'))

        # On success, chart_result is a JSON string. Parse and return it.
        return json.loads(chart_result)

    except HTTPException:
        raise # Re-raise HTTPExceptions to preserve their status code and detail
    except Exception as e:
        logging.error(f"Error during backtest execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")

# --- Existing API Endpoints ---

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

coin_manager_instance = coin_manager.CoinManager()

class Coin(BaseModel):
    id: str
    symbol: str
    name: str

@app.get("/api/all_tradable_coins", response_model=List[Coin])
async def get_all_tradable_coins():
    logging.info("Fetching all tradable coins...")
    try:
        binance_symbols = fetch_all_binance_symbols_startup({})
        if not binance_symbols:
            raise HTTPException(status_code=503, detail="Could not fetch symbol list from Binance.")
        tradable_base_assets = {s.replace('USDT', '') for s in binance_symbols}
        all_coingecko_coins = coin_manager_instance.get_all_coins()
        if not all_coingecko_coins:
            raise HTTPException(status_code=500, detail="Failed to fetch coin list from CoinManager.")
        filtered_coins = [
            {
                "id": coin['id'],
                "symbol": coin['symbol'].upper(),
                "name": coin['name']
            }
            for coin in all_coingecko_coins
            if coin['symbol'].upper() in tradable_base_assets
        ]
        sorted_filtered_coins = sorted(filtered_coins, key=lambda x: x['name'])
        logging.info(f"Returning {len(sorted_filtered_coins)} tradable coins.")
        return sorted_filtered_coins
    except Exception as e:
        logging.error(f"Error fetching all tradable coins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/crypto_data", response_model=List[Dict[str, Any]])
async def get_crypto_data(symbols: List[str] = Query(..., description="A list of crypto symbols to fetch data for (e.g., ['BTCUSDT', 'ETHUSDT'])")):
    logging.info(f"Received request for crypto data for symbols: {symbols}")
    if not symbols:
        return []
    try:
        ticker_data = get_ticker_data()
        if not ticker_data:
            raise HTTPException(status_code=503, detail="Could not fetch ticker data from Binance.")
        coingecko_mapping = get_coingecko_global_mapping()
        market_caps = get_market_caps_coingecko(symbols, coingecko_mapping)
        results = []
        for symbol in symbols:
            market_cap = market_caps.get(symbol)
            analysis = _analyze_symbol(symbol, ticker_data, market_cap, coingecko_mapping)
            results.append(analysis)
        return results
    except Exception as e:
        logging.error(f"An error occurred while fetching crypto data: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

# --- Configuration and Alert History Endpoints ---
CONFIG_FILE_PATH = os.path.join(BASE_PATH, "config.json")
ALERT_HISTORY_FILE_PATH = os.path.join(BASE_PATH, "alert_history.json")
HISTORY_LOCK = Lock()
CONFIG_LOCK = Lock()

@app.get("/api/alert_configs")
async def get_alert_configs():
    """
    Returns the contents of the monitoring configuration file.
    """
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            logging.warning("config.json not found.")
            # It's better to return a default/empty config than to crash the frontend
            return {"cryptos_to_monitor": [], "market_analysis_config": {}}

        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            try:
                # Handle empty file case
                content = f.read()
                if not content.strip():
                    logging.warning("config.json is empty.")
                    return {"cryptos_to_monitor": [], "market_analysis_config": {}}

                config_data = json.loads(content)
                return config_data
            except json.JSONDecodeError:
                logging.error("Failed to decode config.json.")
                raise HTTPException(status_code=500, detail="Failed to parse configuration file.")
    except Exception as e:
        logging.error(f"Error reading configuration file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred while reading config: {str(e)}")

@app.post("/api/alert_configs")
async def save_alert_configs(config_data: Dict[str, Any]):
    """
    Saves the entire monitoring and UI configuration.
    """
    try:
        # Basic validation
        if 'cryptos_to_monitor' not in config_data or 'market_analysis_config' not in config_data:
            raise HTTPException(status_code=400, detail="Invalid configuration structure.")

        with CONFIG_LOCK:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        logging.info("Successfully saved configuration to config.json")
        return {"message": "Configuration saved successfully."}
    except HTTPException:
        raise # Re-raise HTTPException to keep its status code and detail
    except Exception as e:
        logging.error(f"Error saving configuration file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred while saving config: {str(e)}")

class CoinAddRequest(BaseModel):
    symbol: str

@app.post("/api/monitored_coins")
async def add_monitored_coin(request: CoinAddRequest):
    """
    Adds a new coin to the monitoring list in the configuration.
    """
    with CONFIG_LOCK:
        try:
            # 1. Read the existing config
            config = {"cryptos_to_monitor": [], "market_analysis_config": {}}
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        config = json.loads(content)

            # 2. Check if the coin is already monitored
            monitored_symbols = [c['symbol'] for c in config['cryptos_to_monitor']]
            if request.symbol in monitored_symbols:
                logging.warning(f"Attempted to add existing coin {request.symbol}. No action taken.")
                return {"message": f"Coin {request.symbol} is already monitored."}

            # 3. Add the new coin with a default alert configuration
            new_coin_config = {
                "symbol": request.symbol,
                "alert_config": {
                    "conditions": {
                        "rsi_sobrevendido": {"enabled": True, "blinking": True},
                        "rsi_sobrecomprado": {"enabled": True, "blinking": True},
                        "hilo_compra": {"enabled": True, "blinking": True},
                        "mme_cruz_dourada": {"enabled": True, "blinking": True},
                        "mme_cruz_morte": {"enabled": True, "blinking": True},
                        "macd_cruz_alta": {"enabled": True, "blinking": True},
                        "macd_cruz_baixa": {"enabled": True, "blinking": True},
                    }
                }
            }
            config['cryptos_to_monitor'].append(new_coin_config)

            # 4. Write the updated config back to the file
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)

            logging.info(f"Successfully added {request.symbol} to monitored coins.")
            return {"message": f"Coin {request.symbol} added successfully."}

        except Exception as e:
            logging.error(f"Error adding monitored coin: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to add coin to configuration.")

@app.delete("/api/monitored_coins/{symbol}")
async def remove_monitored_coin(symbol: str):
    """
    Removes a coin from the monitoring list in the configuration.
    """
    with CONFIG_LOCK:
        try:
            # 1. Read the existing config
            if not os.path.exists(CONFIG_FILE_PATH):
                raise HTTPException(status_code=404, detail="Configuration file not found.")

            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 2. Find and remove the coin
            initial_count = len(config['cryptos_to_monitor'])
            config['cryptos_to_monitor'] = [
                c for c in config['cryptos_to_monitor'] if c.get('symbol') != symbol
            ]

            if len(config['cryptos_to_monitor']) == initial_count:
                logging.warning(f"Attempted to remove non-existent coin {symbol}.")
                raise HTTPException(status_code=404, detail=f"Coin {symbol} not found in monitored list.")

            # 3. Write the updated config back
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)

            logging.info(f"Successfully removed {symbol} from monitored coins.")
            return {"message": f"Coin {symbol} removed successfully."}

        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error removing monitored coin: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to remove coin from configuration.")


class Alert(BaseModel):
    id: str
    symbol: str
    condition: str
    description: str
    timestamp: str
    snapshot: Dict[str, Any]

@app.get("/api/alerts", response_model=List[Alert])
async def get_alert_history(start_date: Optional[str] = Query(None, description="Start date for filtering (YYYY-MM-DD)"), end_date: Optional[str] = Query(None, description="End date for filtering (YYYY-MM-DD)")):
    try:
        with HISTORY_LOCK:
            if not os.path.exists(ALERT_HISTORY_FILE_PATH): return []
            with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                try:
                    content = f.read()
                    if not content: return []
                    history = json.loads(content)
                    if not isinstance(history, list): history = []
                except json.JSONDecodeError: history = []
            if not history: return []
            if start_date and end_date:
                try:
                    start_dt = datetime.fromisoformat(start_date + "T00:00:00")
                    end_dt = datetime.fromisoformat(end_date + "T23:59:59")
                    filtered_history = [alert for alert in history if start_dt <= datetime.fromisoformat(alert['timestamp']) <= end_dt]
                    return filtered_history
                except (ValueError, TypeError) as e:
                    logging.error(f"Invalid date format provided: {e}")
                    raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")
            return history
    except Exception as e:
        logging.error(f"Error reading or filtering alert history file: {e}")
        raise HTTPException(status_code=500, detail="Error reading or filtering alert history file.")

@app.post("/api/alerts")
async def save_alert(alert: Alert):
    """
    Saves a new alert to the alert history.
    """
    try:
        with HISTORY_LOCK:
            history = []
            if os.path.exists(ALERT_HISTORY_FILE_PATH) and os.path.getsize(ALERT_HISTORY_FILE_PATH) > 0:
                with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                        if not isinstance(history, list):
                            logging.warning("Alert history was not a list, re-initializing.")
                            history = []
                    except json.JSONDecodeError:
                        logging.warning("Could not decode alert history, re-initializing.")
                        history = []

            history.insert(0, alert.model_dump())

            MAX_HISTORY_SIZE = 1000
            if len(history) > MAX_HISTORY_SIZE:
                history = history[:MAX_HISTORY_SIZE]

            with open(ALERT_HISTORY_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4)

        logging.info(f"Successfully saved alert for {alert.symbol}")
        return {"message": "Alert saved successfully"}
    except Exception as e:
        logging.error(f"Error saving alert to history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save alert to history.")

class TelegramConfigRequest(BaseModel):
    bot_token: str
    chat_id: str

@app.get("/api/telegram_config")
async def get_telegram_config():
    """
    Returns the Telegram configuration.
    """
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            return {"bot_token": "", "chat_id": ""}
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            telegram_config = config_data.get("telegram_config", {"bot_token": "", "chat_id": ""})
            return telegram_config
    except Exception as e:
        logging.error(f"Error reading Telegram configuration: {e}")
        raise HTTPException(status_code=500, detail="Failed to read Telegram configuration.")

@app.post("/api/telegram_config")
async def save_telegram_config(telegram_config: TelegramConfigRequest):
    """
    Saves the Telegram configuration.
    """
    with CONFIG_LOCK:
        try:
            config = {}
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        config = json.loads(content)

            config["telegram_config"] = telegram_config.model_dump()

            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)

            logging.info("Successfully saved Telegram configuration.")
            return {"message": "Telegram configuration saved successfully."}
        except Exception as e:
            logging.error(f"Error saving Telegram configuration: {e}")
            raise HTTPException(status_code=500, detail="Failed to save Telegram configuration.")


@app.post("/api/test_telegram")
async def test_telegram_endpoint():
    """
    Envia uma mensagem de teste para o Telegram usando as credenciais configuradas.
    """
    try:
        # Carregar a configuração para obter as credenciais do Telegram
        with CONFIG_LOCK:
            if not os.path.exists(CONFIG_FILE_PATH):
                raise HTTPException(status_code=404, detail="Arquivo de configuração não encontrado.")

            config = {}
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    config = json.loads(content)

        telegram_config = config.get("telegram_config", {})
        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")

        if not bot_token or not chat_id or "AQUI" in str(bot_token) or "AQUI" in str(chat_id):
            raise HTTPException(status_code=400, detail="Token ou Chat ID do Telegram não configurado. Por favor, salve suas credenciais primeiro.")

        test_message = "✅ Mensagem de teste do Crypto Monitor Pro!\n\nSua configuração do Telegram parece estar funcionando corretamente."

        # A função send_telegram_alert agora relança a exceção, permitindo a captura aqui.
        send_telegram_alert(bot_token, chat_id, test_message)

        return {"message": "Mensagem de teste enviada com sucesso!"}

    except HTTPException:
        raise # Re-lança para manter o status e detalhe originais

    except requests.exceptions.RequestException as e:
        error_detail = f"Erro de rede ao contatar o Telegram: {e}"
        if e.response:
            status_code = e.response.status_code
            if status_code == 400:
                error_detail = "Requisição inválida. Verifique se o Chat ID está correto e se o bot foi adicionado ao canal/grupo."
            elif status_code == 401:
                error_detail = "Não autorizado. Verifique se o seu Token de Bot do Telegram é válido."
            elif status_code == 404:
                error_detail = "Não encontrado. Verifique o Chat ID, pois o chat pode não existir."
        logging.error(f"Erro na comunicação com a API do Telegram: {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_detail)

    except Exception as e:
        logging.error(f"Erro inesperado no endpoint de teste do Telegram: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado: {str(e)}")


from backend.indicators import calculate_rsi, calculate_bollinger_bands, calculate_emas, calculate_hilo_signals
@app.get("/api/coin_details/{symbol}")
async def get_coin_details(symbol: str):
    """
    Provides detailed information for a specific coin, including recent alerts and historical data for a chart.
    """
    try:
        # 1. Fetch recent alerts for the symbol from the last 7 days
        end_date = datetime.now(timezone.utc)
        start_date_alerts = end_date - timedelta(days=7)

        recent_alerts = []
        if os.path.exists(ALERT_HISTORY_FILE_PATH):
            with HISTORY_LOCK:
                with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                        if isinstance(history, list):
                            # Filter alerts for the given symbol and within the date range
                            symbol_alerts = [
                                alert for alert in history
                                if alert.get('symbol') == symbol and
                                pd.to_datetime(alert.get('timestamp')).tz_convert('UTC') >= start_date_alerts
                            ]
                            recent_alerts = sorted(symbol_alerts, key=lambda x: x['timestamp'], reverse=True)
                    except (json.JSONDecodeError, IndexError, TypeError):
                        pass

        # 2. Fetch historical data for the last 30 days to have enough data for indicators
        start_date_data = end_date - timedelta(days=30)
        end_date_str = end_date.strftime("%Y-%m-%d")
        start_date_data_str = start_date_data.strftime("%Y-%m-%d")

        historical_data_df = fetch_historical_data(symbol, start_date_data_str, end_date_str, interval='1h')

        if historical_data_df.empty:
            return {"alerts": recent_alerts, "chartData": None, "indicatorsData": {}}

        # 3. Calculate Indicators
        rsi, _, _ = calculate_rsi(historical_data_df)
        upper_band, lower_band, sma_20 = calculate_bollinger_bands(historical_data_df)
        emas = calculate_emas(historical_data_df, periods=[9, 21, 50, 200])

        # We only need the last 7 days of data for the chart itself
        historical_data_df_chart = historical_data_df[historical_data_df.index >= start_date_alerts]

        # 4. Format data for Plotly
        chart_data = {
            'x': historical_data_df_chart.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'open': historical_data_df_chart['open'].tolist(),
            'high': historical_data_df_chart['high'].tolist(),
            'low': historical_data_df_chart['low'].tolist(),
            'close': historical_data_df_chart['close'].tolist(),
            'type': 'candlestick',
            'name': symbol
        }

        indicators_data = {
            'rsi': {'x': rsi.index.strftime('%Y-%m-%d %H:%M:%S').tolist(), 'y': rsi.tolist(), 'name': 'RSI'},
            'bollinger_upper': {'x': upper_band.index.strftime('%Y-%m-%d %H:%M:%S').tolist(), 'y': upper_band.tolist(), 'name': 'BB Upper'},
            'bollinger_lower': {'x': lower_band.index.strftime('%Y-%m-%d %H:%M:%S').tolist(), 'y': lower_band.tolist(), 'name': 'BB Lower'},
            'sma_20': {'x': sma_20.index.strftime('%Y-%m-%d %H:%M:%S').tolist(), 'y': sma_20.tolist(), 'name': 'SMA 20'},
        }
        for period, ema_series in emas.items():
            indicators_data[f'ema_{period}'] = {'x': ema_series.index.strftime('%Y-%m-%d %H:%M:%S').tolist(), 'y': ema_series.tolist(), 'name': f'EMA {period}'}

        # 5. Prepare alerts for annotations
        annotations = []
        for alert in recent_alerts:
            # Find the closest data point in time to place the annotation
            alert_time = pd.to_datetime(alert['timestamp']).tz_convert('UTC')
            if not historical_data_df_chart.empty:
                closest_time_index = historical_data_df_chart.index.get_indexer([alert_time], method='nearest')[0]
                # Check if a valid index was found
                if closest_time_index != -1:
                    closest_time = historical_data_df_chart.index[closest_time_index]
                    price_at_alert = historical_data_df_chart.loc[closest_time]['high']

                    annotations.append({
                        'x': closest_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'y': price_at_alert,
                        'text': alert['condition'], # Using 'condition' as it's more concise
                        'showarrow': True,
                        'arrowhead': 1,
                        'ax': 0,
                        'ay': -40 # Frontend can dynamically adjust this
                    })

        return {
            "alerts": recent_alerts, # Keep sending raw alerts for display in a list
            "chartData": chart_data,
            "indicatorsData": indicators_data,
            "annotations": annotations
        }

    except Exception as e:
        logging.error(f"Error fetching details for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred while fetching details for {symbol}: {str(e)}")

# --- Serve Static Files ---
if hasattr(sys, '_MEIPASS'):
    static_files_path = sys._MEIPASS
else:
    static_files_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dist'))

if os.path.exists(static_files_path):
    app.mount("/", StaticFiles(directory=static_files_path, html=True), name="static")
else:
    logging.warning(f"Static files directory not found at '{static_files_path}'. The frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
