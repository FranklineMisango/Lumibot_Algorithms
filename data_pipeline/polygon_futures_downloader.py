"""
Polygon.io Futures Data Downloader for QuantConnect Lean format
Supports ES, NQ, YM, RTY and other futures contracts
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from polygon import RESTClient
from tqdm import tqdm
import time
from typing import List, Dict, Any, Optional

from config import (
    POLYGON_API_KEY, 
    DATA_ROOT,
    LEAN_PRICE_MULTIPLIER,
)
from utils import ensure_directory_exists, setup_logging


class PolygonFuturesDownloader:
    """Download futures data from Polygon.io and convert to QuantConnect Lean format"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or POLYGON_API_KEY
        if not self.api_key:
            raise ValueError("Polygon API key is required. Set POLYGON_API_KEY environment variable.")
        
        self.client = RESTClient(api_key=self.api_key)
        self.data_path = os.path.join(DATA_ROOT, 'future')
        self.logger = setup_logging()
        
        # Rate limiting for free tier
        self.min_request_interval = 15  # 15 seconds between requests
        self.last_request_time = 0
        
        # Futures contract mappings
        self.futures_exchanges = {
            'ES': 'cme',    # E-mini S&P 500
            'NQ': 'cme',    # E-mini NASDAQ-100
            'YM': 'cbot',   # E-mini Dow Jones
            'RTY': 'ice',   # E-mini Russell 2000
            'CL': 'nymex',  # Crude Oil
            'GC': 'comex',  # Gold
            'SI': 'comex',  # Silver
            'NG': 'nymex',  # Natural Gas
            'ZB': 'cbot',   # Treasury Bond
            'ZN': 'cbot',   # Treasury Note
        }
        
    def _rate_limit(self):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            self.logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_futures_ticker(self, symbol: str, expiration_month: str = None) -> str:
        """Get the full futures ticker for Polygon API"""
        # For current/front month contract, we can try the base symbol
        # Polygon format is usually like ES or ESZ2024 for specific months
        
        if expiration_month:
            return f"{symbol}{expiration_month}"
        else:
            # Try to get the continuous/front month contract
            return symbol
    
    def get_futures_data(self, symbol: str, start_date: datetime, end_date: datetime, 
                        resolution: str = 'daily') -> pd.DataFrame:
        """Download futures price data"""
        self._rate_limit()
        
        try:
            # Format dates for Polygon API
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Determine timespan based on resolution
            timespan_map = {
                'minute': 'minute',
                'hour': 'hour', 
                'daily': 'day'
            }
            timespan = timespan_map.get(resolution, 'day')
            
            self.logger.info(f"Fetching {symbol} futures data from {start_str} to {end_str}")
            
            # Get aggregated bars
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan=timespan,
                from_=start_str,
                to=end_str,
                limit=50000
            )
            
            if not aggs:
                self.logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            data = []
            for bar in aggs:
                data.append({
                    'timestamp': pd.Timestamp(bar.timestamp, unit='ms', tz='UTC'),
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume or 0
                })
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df = df.set_index('timestamp')
            df = df.sort_index()
            
            self.logger.info(f"Downloaded {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error downloading futures data for {symbol}: {e}")
            return pd.DataFrame()
    
    def format_for_lean(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Convert data to QuantConnect Lean format"""
        if df.empty:
            return df
        
        lean_df = df.copy()
        
        # For futures, Lean typically uses actual prices (not multiplied like stocks)
        # But we may need to adjust based on the specific contract specifications
        price_columns = ['open', 'high', 'low', 'close']
        
        # ES futures are priced in points (e.g., 4500.00)
        # Lean might expect these as integers, so multiply by 100 for tick precision
        if symbol.startswith('ES'):
            multiplier = 100  # ES trades in 0.25 point increments
        elif symbol.startswith('NQ'):
            multiplier = 100  # NQ trades in 0.25 point increments  
        else:
            multiplier = LEAN_PRICE_MULTIPLIER  # Default for other futures
        
        for col in price_columns:
            lean_df[col] = (lean_df[col] * multiplier).round().astype(int)
        
        # Ensure volume is integer
        lean_df['volume'] = lean_df['volume'].astype(int)
        
        # Reorder columns for Lean format (futures use OHLCV)
        column_order = ['open', 'high', 'low', 'close', 'volume']
        lean_df = lean_df[column_order]
        
        return lean_df
    
    def get_lean_filepath(self, symbol: str, date: datetime, resolution: str) -> str:
        """Generate file path for Lean format"""
        symbol_lower = symbol.lower()
        
        # Get exchange for this symbol
        base_symbol = symbol[:2].upper()  # ES, NQ, etc.
        exchange = self.futures_exchanges.get(base_symbol, 'cme').lower()
        
        # Create directory structure: future/exchange/resolution/symbol/
        directory = os.path.join(self.data_path, exchange, resolution, symbol_lower)
        ensure_directory_exists(directory)
        
        # File naming: YYYYMMDD_symbol_resolution.csv
        date_str = date.strftime('%Y%m%d')
        filename = f"{date_str}_{symbol_lower}_{resolution}.csv"
        
        return os.path.join(directory, filename)
    
    def save_to_lean_format(self, df: pd.DataFrame, symbol: str, resolution: str):
        """Save data in QuantConnect Lean format"""
        if df.empty:
            self.logger.warning(f"No data to save for {symbol}")
            return
        
        # Group by date and save separate files
        for date, day_data in df.groupby(df.index.date):
            filepath = self.get_lean_filepath(symbol, pd.Timestamp(date), resolution)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save without timestamp column for Lean format
            day_data.to_csv(filepath, header=False, index=False)
            self.logger.debug(f"Saved {len(day_data)} records to {filepath}")
        
        self.logger.info(f"Saved {len(df)} total records for {symbol}")
    
    def download_futures_symbol(self, symbol: str, start_date: datetime, end_date: datetime,
                               resolution: str = 'daily'):
        """Download futures data for a single symbol"""
        self.logger.info(f"Downloading {resolution} futures data for {symbol}")
        
        # Get the appropriate ticker
        ticker = self.get_futures_ticker(symbol)
        
        # Download price data
        df = self.get_futures_data(ticker, start_date, end_date, resolution)
        
        if df.empty:
            self.logger.warning(f"No data available for {symbol}")
            return
        
        # Format for Lean
        lean_df = self.format_for_lean(df, symbol)
        
        # Save to files
        self.save_to_lean_format(lean_df, symbol, resolution)
    
    def download_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime,
                        resolution: str = 'daily'):
        """Download futures data for multiple symbols"""
        self.logger.info(f"Starting futures download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc=f"Downloading {resolution} futures"):
            try:
                self.download_futures_symbol(symbol, start_date, end_date, resolution)
                
                # Small delay between symbols to respect rate limits
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error downloading futures for {symbol}: {e}")
                continue
        
        self.logger.info("Futures download completed")
