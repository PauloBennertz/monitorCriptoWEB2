import logging
import os
import json
import subprocess
import sys
from threading import Lock
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import requests
import time
from fastapi.responses import FileResponse
import tempfile

# Importando as duas funções do nosso gerador de gráfico
from backend.chart_generator import generate_chart_image, generate_interactive_chart_html

# This ensures that the 'backend' package can be found by Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Import core logic from the existing application ---
from backend.monitoring_service import (
    get_klines_data,
    get_ticker_data,
    get_market_caps_coingecko,
    _analyze_symbol,
    fetch_all_binance_symbols_startup,
    get_cached_coin_list,
    get_btc_dominance
)
from backend import app_state
from backend import coin_manager
from backend.backtester import Backtester
from backend.data_fetcher import fetch_historical_data
from backend.historical_analyzer import analyze_historical_alerts
from backend.indicators import calculate_sma
from backend.notification_service import send_telegram_alert

class ChartGenerationRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    alerts: List[Dict[str, Any]]

# --- Basic Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Crypto Monitor Pro API",
    description="API server for the Crypto Monitor Pro web application.",
    version="1.0.0"
)

# --- Global cache for coin data ---
all_coins = []
coingecko_mapping = {}

@app.on_event("startup")
async def startup_event():
    """
    Load the coin list and create the mapping at startup.
    This data is cached and will be refreshed periodically.
    """
    global all_coins, coingecko_mapping
    logging.info("Application startup: Loading initial coin data...")
    all_coins = get_cached_coin_list()
    if all_coins:
        coingecko_mapping = {coin['symbol'].upper(): coin['name'] for coin in all_coins}
        logging.info(f"Loaded {len(all_coins)} coins and created mapping.")
    else:
        logging.error("Failed to load coin list at startup. Some functionalities might be limited.")

# --- CORS (Cross-Origin Resource Sharing) Configuration ---
origins = ["*"]

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

# --- File Paths and Locks ---
CONFIG_FILE_PATH = os.path.join(BASE_PATH, "config.json")
ALERT_HISTORY_FILE_PATH = os.path.join(BASE_PATH, "alert_history.json")
HISTORY_LOCK = Lock()
CONFIG_LOCK = Lock()


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
        historical_data = await fetch_historical_data(request.symbol, request.start_date, request.end_date)
        if historical_data.empty:
            raise HTTPException(status_code=404, detail="No historical data found for the given parameters.")

        strategy = MovingAverageCrossoverStrategy()
        backtester = Backtester(historical_data, strategy, request.initial_capital)
        chart_result = backtester.run(coin_id=request.symbol)

        if chart_result is None:
            raise HTTPException(status_code=500, detail="Backtest run failed and did not produce a chart.")

        if isinstance(chart_result, dict) and 'error' in chart_result:
            logging.error(f"Chart generation failed: {chart_result.get('message')}")
            raise HTTPException(status_code=503, detail=chart_result.get('message', 'Chart generation service is unavailable.'))

        return json.loads(chart_result)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error during backtest execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


# --- Historical Alert Analysis Endpoint ---
class HistoricalAlertsRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    alert_config: Dict[str, Any]

@app.post("/api/historical_alerts")
async def get_historical_alerts(request: HistoricalAlertsRequest):
    """
    Runs a historical analysis to find what alerts would have been triggered for a given
    symbol, date range, and alert configuration.
    """
    try:
        logging.info(f"Received historical alert analysis request for {request.symbol}")

        triggered_alerts = await analyze_historical_alerts(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            alert_config=request.alert_config
        )

        return {"alerts": triggered_alerts}

    except Exception as e:
        logging.error(f"Error during historical alert analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred during analysis: {str(e)}")


def convert_nan_to_none(obj):
    """
    Recursively converts float('nan') to None in a dictionary or list,
    as NaN is not a valid JSON value.
    """
    if isinstance(obj, dict):
        return {k: convert_nan_to_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_nan_to_none(i) for i in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


@app.get("/api/historical_klines")
async def historical_klines_endpoint(
    symbol: str = Query(..., title="Crypto Symbol (e.g., BTCUSDT)"),
    start_date: str = Query(..., title="Start Date (YYYY-MM-DD)"),
    end_date: str = Query(..., title="End Date (YYYY-MM-DD)"),
    interval: str = Query("1h", title="Kline Interval (e.g., 1h, 1d)")
):
    """
    Busca dados históricos de K-lines e os retorna no formato numérico (timestamp em ms)
    otimizado para bibliotecas de gráficos de alta performance como Lightweight Charts.
    """
    try:
        df = await fetch_historical_data(symbol, start_date, end_date, interval=interval)

        if df.empty:
            return []

        df['open_time'] = (df.index.astype(int) / 10**6).astype(int)
        
        df_final = df.reset_index(drop=True)[['open_time', 'open', 'high', 'low', 'close', 'volume']]
        
        return convert_nan_to_none(df_final.to_dict('records'))

    except Exception as e:
        logging.error(f"Erro ao buscar dados históricos K-lines para o gráfico: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados históricos K-lines: {e}")


@app.get("/api/historical_data")
async def get_historical_data_endpoint(
    symbol: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    """
    Fetches raw historical k-line data for a given symbol and date range.
    """
    try:
        historical_data = await fetch_historical_data(symbol, start_date, end_date)
        if historical_data.empty:
            raise HTTPException(status_code=404, detail="No historical data found for the given parameters.")

        historical_data.reset_index(inplace=True)
        historical_data['timestamp'] = historical_data['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        return historical_data.to_dict(orient='records')

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred while fetching historical data: {str(e)}")


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

        if not all_coins:
            logging.warning("Coin list is not available. Market cap and coin names may be missing.")

        market_caps = get_market_caps_coingecko(symbols, all_coins)

        results = []
        for symbol in symbols:
            market_cap = market_caps.get(symbol)
            analysis = _analyze_symbol(symbol, ticker_data, market_cap, coingecko_mapping)
            results.append(analysis)
        return results
    except Exception as e:
        logging.error(f"An error occurred while fetching crypto data: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


@app.get("/api/alert_configs")
async def get_alert_configs():
    """
    Returns the contents of the monitoring configuration file.
    """
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            logging.warning("config.json not found.")
            return {"cryptos_to_monitor": [], "market_analysis_config": {}}

        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            try:
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
        if 'cryptos_to_monitor' not in config_data or 'market_analysis_config' not in config_data:
            raise HTTPException(status_code=400, detail="Invalid configuration structure.")

        with CONFIG_LOCK:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        logging.info("Successfully saved configuration to config.json")
        return {"message": "Configuration saved successfully."}
    except HTTPException:
        raise
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
            config = {"cryptos_to_monitor": [], "market_analysis_config": {}}
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        config = json.loads(content)

            monitored_symbols = [c['symbol'] for c in config['cryptos_to_monitor']]
            if request.symbol in monitored_symbols:
                logging.warning(f"Attempted to add existing coin {request.symbol}. No action taken.")
                return {"message": f"Coin {request.symbol} is already monitored."}

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
            if not os.path.exists(CONFIG_FILE_PATH):
                raise HTTPException(status_code=404, detail="Configuration file not found.")

            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)

            initial_count = len(config['cryptos_to_monitor'])
            config['cryptos_to_monitor'] = [
                c for c in config['cryptos_to_monitor'] if c.get('symbol') != symbol
            ]

            if len(config['cryptos_to_monitor']) == initial_count:
                logging.warning(f"Attempted to remove non-existent coin {symbol}.")
                raise HTTPException(status_code=404, detail=f"Coin {symbol} not found in monitored list.")

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

        send_telegram_alert(bot_token, chat_id, test_message)

        return {"message": "Mensagem de teste enviada com sucesso!"}

    except HTTPException:
        raise

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


@app.get("/api/coin_details/{symbol}")
async def get_coin_details(symbol: str):
    """
    Fornece APENAS os alertas recentes de uma moeda específica para o modal.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date_alerts = end_date - timedelta(days=7)
        recent_alerts = []

        if os.path.exists(ALERT_HISTORY_FILE_PATH):
            with HISTORY_LOCK:
                with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                    try:
                        history = json.load(f)
                        if isinstance(history, list):
                            symbol_alerts = [
                                alert for alert in history
                                if alert.get('symbol') == symbol and
                                pd.to_datetime(alert.get('timestamp')).tz_convert('UTC') >= start_date_alerts
                            ]
                            recent_alerts = sorted(symbol_alerts, key=lambda x: x['timestamp'], reverse=True)
                    except (json.JSONDecodeError, IndexError, TypeError):
                        pass

        return {"alerts": recent_alerts}

    except Exception as e:
        logging.error(f"Error fetching alert details for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred while fetching alert details for {symbol}: {str(e)}")


async def get_chart_data(symbol: str):
    """
    Busca dados históricos e alertas para um símbolo, usado pelos endpoints de download.
    """
    end_date = datetime.now(timezone.utc)
    start_date_data = end_date - timedelta(days=30)
    
    df = await fetch_historical_data(symbol, start_date_data.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), interval='1h')
    if df.empty:
        raise HTTPException(status_code=404, detail="Nenhum dado histórico encontrado para gerar o gráfico.")

    history = []
    if os.path.exists(ALERT_HISTORY_FILE_PATH):
        with open(ALERT_HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

    start_date_alerts = end_date - timedelta(days=7)
    recent_alerts = [
        alert for alert in history
        if isinstance(alert, dict) and alert.get('symbol') == symbol and
        pd.to_datetime(alert.get('timestamp')).tz_convert('UTC') >= start_date_alerts
    ]
    
    chart_alerts = [{'timestamp': pd.to_datetime(a['timestamp']), 'price': a['snapshot']['price'], 'message': a['condition']} for a in recent_alerts]
    
    return df, chart_alerts

@app.get("/api/coin_details/{symbol}/chart_image")
async def get_coin_details_chart_image(symbol: str, background_tasks: BackgroundTasks):
    """
    Gera um gráfico e o retorna como uma IMAGEM PNG de altíssima resolução para download.
    """
    image_path = None
    try:
        df, chart_alerts = await get_chart_data(symbol)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            image_path = tmpfile.name
        
        generate_chart_image(df, chart_alerts, output_path=image_path, symbol=symbol)
        background_tasks.add_task(os.remove, image_path)

        return FileResponse(image_path, media_type='image/png', filename=f"{symbol}_chart_{datetime.now().strftime('%Y-%m-%d')}.png")
    except Exception as e:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        logging.error(f"Erro ao gerar imagem do gráfico para {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar imagem do gráfico: {str(e)}")


@app.get("/api/coin_details/{symbol}/chart_html")
async def get_coin_details_chart_html(symbol: str, background_tasks: BackgroundTasks):
    """
    Gera um gráfico interativo e o retorna como um ARQUIVO HTML para download.
    """
    html_path = None
    try:
        df, chart_alerts = await get_chart_data(symbol)

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmpfile:
            html_path = tmpfile.name
        
        generate_interactive_chart_html(df, chart_alerts, output_path=html_path, symbol=symbol)
        background_tasks.add_task(os.remove, html_path)
        
        return FileResponse(html_path, media_type='text/html', filename=f"{symbol}_interactive_chart_{datetime.now().strftime('%Y-%m-%d')}.html")
    except Exception as e:
        if html_path and os.path.exists(html_path):
            os.remove(html_path)
        logging.error(f"Erro ao gerar HTML do gráfico para {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar HTML do gráfico: {str(e)}")


@app.post("/api/historical_analysis/chart_html")
async def get_historical_analysis_chart_html(request: ChartGenerationRequest, background_tasks: BackgroundTasks):
    """Gera um gráfico a partir dos resultados da análise histórica e retorna um HTML interativo."""
    html_path = None
    try:
        df = await fetch_historical_data(request.symbol, request.start_date, request.end_date, interval='1h')
        if df.empty:
            raise HTTPException(status_code=404, detail="Nenhum dado histórico encontrado para o período.")

        # Make the alert processing more robust to handle different data structures
        chart_alerts = []
        for alert in request.alerts:
            # Intelligently find the price, whether it's at the top level or nested
            price = alert.get('price') or alert.get('snapshot', {}).get('price')
            if price is not None:
                chart_alerts.append({
                    'timestamp': pd.to_datetime(alert['timestamp']),
                    'price': price,
                    'message': alert.get('condition') or alert.get('description', 'Alerta')
                })

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmpfile:
            html_path = tmpfile.name
        
        generate_interactive_chart_html(df, chart_alerts, output_path=html_path, symbol=request.symbol)
        background_tasks.add_task(os.remove, html_path)
        
        return FileResponse(html_path, media_type='text/html', filename=f"{request.symbol}_analysis_interactive_chart.html")
        
    except Exception as e:
        if html_path and os.path.exists(html_path):
            os.remove(html_path)
        logging.error(f"Erro ao gerar HTML da análise histórica para {request.symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar HTML da análise: {str(e)}")

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