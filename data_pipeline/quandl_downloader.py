"""
Quandl data downloader for Lean format
Supports various datasets with historical data and basic analysis
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional
from tqdm import tqdm
import json

from config import (
    QUANDL_API_KEY, EQUITY_DATA_PATH, CRYPTO_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

class QuandlDownloader:
    """Download financial data from Quandl and convert to Lean format"""
    
    def __init__(self):
        if not QUANDL_API_KEY:
            logger.warning("Quandl API key not found. Rate limits will apply.")
        
        self.api_key = QUANDL_API_KEY
        self.base_url = "https://www.quandl.com/api/v3"
        self.rate_limit_delay = 1 if QUANDL_API_KEY else 2  # Slower without API key
        
        self.session = requests.Session()
    
    def get_dataset(self, dataset_code: str, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get dataset from Quandl"""
        try:
            url = f"{self.base_url}/datasets/{dataset_code}/data.json"
            
            params = {}
            if self.api_key:
                params['api_key'] = self.api_key
            if start_date:
                params['start_date'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                params['end_date'] = end_date.strftime('%Y-%m-%d')
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'dataset_data' not in data or not data['dataset_data']['data']:
                logger.warning(f"No data found for dataset {dataset_code}")
                return []
            
            dataset_data = data['dataset_data']
            column_names = dataset_data['column_names']
            rows = dataset_data['data']
            
            # Convert to our format
            bars = []
            for row in rows:
                try:
                    # First column is usually date
                    timestamp = datetime.strptime(row[0], '%Y-%m-%d')
                    timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                    
                    # Try to find OHLCV columns or use available data
                    bar_data = {'timestamp': timestamp}
                    
                    # Map common column patterns
                    for i, col_name in enumerate(column_names[1:], 1):  # Skip date column
                        if i < len(row) and row[i] is not None:
                            col_lower = col_name.lower()
                            if 'open' in col_lower:
                                bar_data['open'] = float(row[i])
                            elif 'high' in col_lower:
                                bar_data['high'] = float(row[i])
                            elif 'low' in col_lower:
                                bar_data['low'] = float(row[i])
                            elif 'close' in col_lower or 'price' in col_lower or 'value' in col_lower:
                                bar_data['close'] = float(row[i])
                            elif 'volume' in col_lower:
                                bar_data['volume'] = int(float(row[i]))
                    
                    # If we don't have OHLC, use the first numeric value as all OHLC
                    if 'close' not in bar_data:
                        for i, value in enumerate(row[1:], 1):
                            if value is not None and isinstance(value, (int, float)):
                                bar_data.update({
                                    'open': float(value),
                                    'high': float(value),
                                    'low': float(value),
                                    'close': float(value)
                                })
                                break
                    
                    # Fill missing OHLC with close price
                    if 'close' in bar_data:
                        close_price = bar_data['close']
                        bar_data.setdefault('open', close_price)
                        bar_data.setdefault('high', close_price)
                        bar_data.setdefault('low', close_price)
                        bar_data.setdefault('volume', 0)
                        
                        bars.append(bar_data)
                
                except (ValueError, IndexError, TypeError) as e:
                    logger.debug(f"Skipping row due to parsing error: {e}")
                    continue
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return sorted(bars, key=lambda x: x['timestamp'])
            
        except Exception as e:
            logger.error(f"Error getting Quandl dataset {dataset_code}: {str(e)}")
            return []
    
    def get_dataset_metadata(self, dataset_code: str) -> Dict:
        """Get metadata for a Quandl dataset"""
        try:
            url = f"{self.base_url}/datasets/{dataset_code}/metadata.json"
            
            params = {}
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'dataset' in data:
                return data['dataset']
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting metadata for {dataset_code}: {str(e)}")
            return {}
    
    def search_datasets(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for datasets on Quandl"""
        try:
            url = f"{self.base_url}/datasets.json"
            
            params = {
                'query': query,
                'per_page': limit
            }
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'datasets' in data:
                return data['datasets']
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching Quandl datasets: {str(e)}")
            return []
    
    def download_datasets(self, dataset_codes: List[str], start_date: datetime, end_date: datetime):
        """Download multiple datasets from Quandl"""
        logger.info(f"Starting Quandl download for {len(dataset_codes)} datasets")
        
        for dataset_code in tqdm(dataset_codes, desc="Downloading Quandl datasets"):
            try:
                data = self.get_dataset(dataset_code, start_date, end_date)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Determine data path based on dataset type
                        if any(keyword in dataset_code.lower() for keyword in ['crypto', 'bitcoin', 'btc', 'eth']):
                            data_path = os.path.join(CRYPTO_DATA_PATH, 'quandl', 'daily')
                        else:
                            data_path = os.path.join(EQUITY_DATA_PATH, 'quandl', 'daily')
                        
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        clean_code = dataset_code.replace('/', '_').lower()
                        output_path = os.path.join(data_path, f"{clean_code}.zip")
                        csv_filename = f"{clean_code}_daily_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, dataset_code, cleaned_data[0]['timestamp'], 'daily')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} data points for {dataset_code}")
                
            except Exception as e:
                logger.error(f"Error downloading {dataset_code}: {str(e)}")
                continue
    
    def download_dataset_metadata(self, dataset_codes: List[str]):
        """Download metadata for multiple datasets"""
        logger.info(f"Downloading metadata for {len(dataset_codes)} datasets")
        
        metadata_list = []
        
        for dataset_code in tqdm(dataset_codes, desc="Getting metadata"):
            try:
                metadata = self.get_dataset_metadata(dataset_code)
                if metadata:
                    metadata_list.append(metadata)
                    
            except Exception as e:
                logger.error(f"Error getting metadata for {dataset_code}: {str(e)}")
                continue
        
        # Save metadata
        if metadata_list:
            data_path = os.path.join(EQUITY_DATA_PATH, 'quandl', 'metadata')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"metadata_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(metadata_list, f, indent=2, default=str)
            
            logger.info(f"Saved metadata for {len(metadata_list)} datasets")
    
    def get_popular_datasets(self) -> List[str]:
        """Get list of popular Quandl datasets"""
        return [
            'WIKI/AAPL',        # Apple Inc
            'WIKI/MSFT',        # Microsoft Corp
            'WIKI/GOOGL',       # Alphabet Inc
            'FRED/GDP',         # US GDP
            'FRED/UNRATE',      # US Unemployment Rate
            'FRED/CPIAUCSL',    # US CPI
            'OPEC/ORB',         # OPEC Oil Price
            'LBMA/GOLD',        # Gold Price
            'CHRIS/CME_ES1',    # E-mini S&P 500 Futures
            'CHRIS/CME_CL1',    # Crude Oil Futures
            'CHRIS/CME_GC1',    # Gold Futures
            'CHRIS/ICE_CC1',    # Cocoa Futures
            'CHRIS/ICE_CT1',    # Cotton Futures
            'BCHAIN/MKPRU',     # Bitcoin Market Price
            'BITFINEX/BTCUSD',  # Bitcoin/USD
            'CURRFX/EURUSD',    # EUR/USD
            'CURRFX/GBPUSD',    # GBP/USD
            'ECB/EURUSD',       # EUR/USD ECB
            'BOE/XUDLERD',      # GBP effective exchange rate
            'BOJ/USD_JPY'       # USD/JPY
        ]