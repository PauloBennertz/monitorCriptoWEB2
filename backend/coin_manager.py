import os
import json
import time
import logging
from datetime import datetime, timedelta
from pycoingecko import CoinGeckoAPI
from .app_state import get_application_path

class CoinManager:
    def __init__(self, update_interval_hours=24):
        self.coin_list_path = os.path.join(get_application_path(), "all_coins.json")
        self.update_interval = timedelta(hours=update_interval_hours)
        self.cg = CoinGeckoAPI()
        self.all_coins = self._load_or_fetch_coins()

    def _fetch_coins_from_api(self):
        """Fetches the complete list of coins from the CoinGecko API."""
        logging.info("Fetching coin list from CoinGecko API...")
        try:
            coins = self.cg.get_coins_list()
            with open(self.coin_list_path, 'w', encoding='utf-8') as f:
                json.dump(coins, f, indent=2)
            logging.info(f"Successfully fetched and saved {len(coins)} coins.")
            return coins
        except Exception as e:
            logging.error(f"Failed to fetch coin list from CoinGecko: {e}")
            return None

    def _load_or_fetch_coins(self):
        """Loads the coin list from the local cache or fetches it if outdated or non-existent."""
        if os.path.exists(self.coin_list_path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(self.coin_list_path))
            if datetime.now() - file_mod_time < self.update_interval:
                logging.info("Loading coin list from local cache.")
                with open(self.coin_list_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

        return self._fetch_coins_from_api()

    def get_all_coins(self):
        """Returns the list of all coins."""
        return self.all_coins

    def get_coin_display_list(self):
        """Returns a list of formatted strings for display (e.g., 'Bitcoin (BTC)')."""
        if not self.all_coins:
            return []

        # Sort by name for user-friendly display
        sorted_coins = sorted(self.all_coins, key=lambda x: x['name'])

        return [f"{coin['name']} ({coin['symbol'].upper()})" for coin in sorted_coins]

    def get_symbol_from_display_name(self, display_name):
        """Extracts the symbol from the display name format."""
        try:
            return display_name.split('(')[-1].replace(')', '').strip()
        except:
            return None
