"""
Utility functions for Akash Network data collection
"""

import os
import json
import yaml
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import sys


class Config:
    """Configuration loader and manager"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            return {}

    def get(self, *keys, default=None):
        """Get nested configuration value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
        return value


class AkashAPIClient:
    """Client for interacting with Akash Network REST API"""

    def __init__(self, config: Config):
        self.config = config
        self.rest_apis = config.get('akash', 'rest_api', default=[])
        self.timeout = config.get('akash', 'timeout', default=30)
        self.max_retries = config.get('akash', 'max_retries', default=3)
        self.retry_delay = config.get('akash', 'retry_delay', default=2)
        self.current_api_index = 0

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / config.get('rate_limiting', 'requests_per_second', default=5)

    def get_current_api(self) -> str:
        """Get the current REST API endpoint"""
        if not self.rest_apis:
            raise ValueError("No REST API endpoints configured")
        return self.rest_apis[self.current_api_index]

    def switch_api(self):
        """Switch to next API endpoint"""
        self.current_api_index = (self.current_api_index + 1) % len(self.rest_apis)
        logger.info(f"Switched to API endpoint: {self.get_current_api()}")

    def _rate_limit(self):
        """Apply rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to Akash API with retry logic"""
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                base_url = self.get_current_api()
                url = f"{base_url}{endpoint}"

                logger.debug(f"Request to {url} (attempt {attempt + 1}/{self.max_retries})")

                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={'Accept': 'application/json'}
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    logger.warning(f"API unavailable (503), switching endpoint...")
                    self.switch_api()
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    return None

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(self.retry_delay * (attempt + 1))

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < self.max_retries - 1:
                    self.switch_api()
                    time.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"Failed to fetch data after {self.max_retries} attempts")
        return None

    def paginated_request(self, endpoint: str, page_size: int = 100) -> List[Dict]:
        """Make paginated requests to collect all data"""
        all_data = []
        page_key = None
        max_pages = self.config.get('collection', 'max_pages', default=100)
        page_count = 0

        while page_count < max_pages:
            params = {'pagination.limit': page_size}
            if page_key:
                params['pagination.key'] = page_key

            response = self.request(endpoint, params)

            if not response:
                break

            # Handle different response structures
            data_items = []
            if 'deployments' in response:
                data_items = response['deployments']
            elif 'leases' in response:
                data_items = response['leases']
            elif 'providers' in response:
                data_items = response['providers']
            elif 'orders' in response:
                data_items = response['orders']
            elif 'bids' in response:
                data_items = response['bids']

            if data_items:
                all_data.extend(data_items)
                logger.info(f"Fetched {len(data_items)} items (page {page_count + 1})")

            # Check for next page
            pagination = response.get('pagination', {})
            next_key = pagination.get('next_key')

            if not next_key or next_key == page_key:
                break

            page_key = next_key
            page_count += 1

        logger.info(f"Total items fetched: {len(all_data)}")
        return all_data


class DataStorage:
    """Handle data storage to various backends"""

    def __init__(self, config: Config):
        self.config = config
        self.backend = config.get('storage', 'backend', default='json')
        self.base_path = Path(config.get('storage', 'file', 'base_path', default='./collected_data'))
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, data: Any, filename: str, data_type: str = 'collection'):
        """Save data to configured backend"""
        if self.backend == 'json':
            self._save_json(data, filename)
        elif self.backend == 'csv':
            self._save_csv(data, filename)
        elif self.backend == 'mongodb':
            self._save_mongodb(data, filename)
        elif self.backend == 'postgresql':
            self._save_postgresql(data, filename)
        else:
            logger.error(f"Unknown storage backend: {self.backend}")

    def _save_json(self, data: Any, filename: str):
        """Save data as JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = self.base_path / f"{filename}_{timestamp}.json"

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")

    def _save_csv(self, data: Any, filename: str):
        """Save data as CSV"""
        try:
            import pandas as pd

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.base_path / f"{filename}_{timestamp}.csv"

            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)

            df.to_csv(filepath, index=False)
            logger.info(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save CSV: {e}")

    def _save_mongodb(self, data: Any, collection_name: str):
        """Save data to MongoDB"""
        try:
            from pymongo import MongoClient

            conn_str = self.config.get('storage', 'mongodb', 'connection_string')
            db_name = self.config.get('storage', 'mongodb', 'database')

            client = MongoClient(conn_str)
            db = client[db_name]
            collection = db[collection_name]

            if isinstance(data, list):
                result = collection.insert_many(data)
                logger.info(f"Inserted {len(result.inserted_ids)} documents to MongoDB")
            else:
                result = collection.insert_one(data)
                logger.info(f"Inserted document to MongoDB: {result.inserted_id}")

        except Exception as e:
            logger.error(f"Failed to save to MongoDB: {e}")

    def _save_postgresql(self, data: Any, table_name: str):
        """Save data to PostgreSQL"""
        logger.warning("PostgreSQL storage not yet implemented")
        # TODO: Implement PostgreSQL storage

    def load_latest(self, filename_pattern: str) -> Optional[Any]:
        """Load the most recent data file matching pattern"""
        try:
            files = sorted(self.base_path.glob(f"{filename_pattern}_*.json"), reverse=True)
            if files:
                with open(files[0], 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
        return None


def setup_logging(config: Config):
    """Setup logging configuration"""
    log_level = config.get('logging', 'level', default='INFO')
    log_file = config.get('logging', 'file', default='./logs/data_collection.log')
    rotation = config.get('logging', 'rotation', default='100 MB')
    retention = config.get('logging', 'retention', default=10)

    # Create logs directory
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove default logger
    logger.remove()

    # Add console logger
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # Add file logger
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        rotation=rotation,
        retention=retention
    )

    logger.info("Logging initialized")


def get_akt_price(config: Config) -> float:
    """Fetch current AKT/USD price from CoinGecko"""
    try:
        price_api = config.get('processing', 'cost_calculation', 'price_api')
        response = requests.get(price_api, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = data.get('akash-network', {}).get('usd', 0)
            logger.info(f"Current AKT price: ${price}")
            return price
    except Exception as e:
        logger.warning(f"Failed to fetch AKT price: {e}, using default")

    return config.get('processing', 'cost_calculation', 'akt_usd_rate', default=3.5)


def calculate_cost(amount_uakt: int, akt_price: float) -> float:
    """Calculate USD cost from uAKT amount"""
    # 1 AKT = 1,000,000 uAKT
    akt_amount = amount_uakt / 1_000_000
    return akt_amount * akt_price
