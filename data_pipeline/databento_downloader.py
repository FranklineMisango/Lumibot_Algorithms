"""
Databento Futures Data Downloader for QuantConnect Lean format
Supports ES, NQ, YM, RTY, CL, GC and other futures contracts from Databento
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union
from tqdm import tqdm
import time

try:
    import databento as db
    from databento import Schema, Encoding, SType
except ImportError:
    raise ImportError("Please install databento: pip install databento")

from config import (
    DATA_BENTO_API_KEY,
    DATA_BENTO_USER_ID, 
    DATA_BENTO_PROD_NAME,
    DATA_ROOT,
    LEAN_PRICE_MULTIPLIER,
)
from utils import ensure_directory_exists, setup_logging


class DatabentoFuturesDownloader:
    """Download futures data from Databento and convert to QuantConnect Lean format"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or DATA_BENTO_API_KEY
        if not self.api_key:
            raise ValueError("Databento API key is required. Set DATA_BENTO_API_KEY environment variable.")
        
        # Initialize Databento client
        self.client = db.Historical(key=self.api_key)
        self.data_path = os.path.join(DATA_ROOT, 'future')
        self.logger = setup_logging()
        
        # Rate limiting - Databento has generous limits but we'll be conservative
        self.min_request_interval = 1  # 1 second between requests
        self.last_request_time = 0
        
        # Futures contract mappings for exchanges
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
            'ZS': 'cbot',   # Soybeans
            'ZC': 'cbot',   # Corn
            'ZW': 'cbot',   # Wheat
        }
        
        # Price multipliers for different futures contracts
        self.price_multipliers = {
            'ES': 100,      # ES trades in 0.25 point increments, store as cents
            'NQ': 100,      # NQ trades in 0.25 point increments
            'YM': 100,      # YM trades in whole points  
            'RTY': 100,     # RTY trades in 0.1 point increments
            'CL': 1000,     # Oil trades in 0.01 per barrel
            'GC': 100,      # Gold trades in 0.10 per ounce
            'SI': 1000,     # Silver trades in 0.005 per ounce
            'NG': 1000,     # Natural Gas trades in 0.001 per MMBtu
            'ZB': 1000,     # Treasury Bond
            'ZN': 1000,     # Treasury Note  
            'ZS': 100,      # Soybeans in cents per bushel
            'ZC': 100,      # Corn in cents per bushel
            'ZW': 100,      # Wheat in cents per bushel
        }
        
    def _rate_limit(self):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def parse_symbol(self, symbol: str) -> tuple:
        """Parse Databento symbol to extract base symbol and contract details"""
        # Databento symbols can be:
        # - Continuous contracts: 'ES.c.0' (ES front month)
        # - Specific contracts: 'ESZ24' (ES December 2024)
        # - User provided: 'ES.FUT' (convert to continuous)
        
        if '.FUT' in symbol:
            # Convert user-friendly format to Databento continuous format
            base_symbol = symbol.replace('.FUT', '')
            # Use front month continuous contract
            continuous_symbol = f"{base_symbol}.c.0"
            root_symbol = base_symbol
        elif '.c.' in symbol:
            # Already in continuous format
            continuous_symbol = symbol
            root_symbol = symbol.split('.')[0]
        else:
            # Assume it's a specific contract like 'ESZ24'
            continuous_symbol = symbol
            root_symbol = ''.join([c for c in symbol if c.isalpha()])[:2]
            
        return root_symbol, continuous_symbol
    
    def get_symbology_mapping(self, symbols: List[str], start_date: datetime, end_date: datetime) -> Dict[str, str]:
        """Get symbology mapping for continuous futures contracts"""
        try:
            self._rate_limit()
            
            # Use Databento's symbology API to get continuous contract mappings
            # The newer API might have different method names
            # For now, return a simple mapping - this can be enhanced later
            mapping = {symbol: symbol for symbol in symbols}
            return mapping
            
        except Exception as e:
            self.logger.warning(f"Could not get symbology mapping: {e}")
            # Fallback to using symbols as-is
            return {symbol: symbol for symbol in symbols}
    
    def get_futures_data(self, symbol: str, start_date: datetime, end_date: datetime, 
                        resolution: str = 'daily', schema: str = 'ohlcv-1d') -> pd.DataFrame:
        """Download futures price data from Databento"""
        try:
            self._rate_limit()
            
            # Parse the symbol
            root_symbol, databento_symbol = self.parse_symbol(symbol)
            
            # Determine schema based on resolution
            schema_map = {
                'tick': Schema.MBP_1,       # Market by price (tick data)
                'second': Schema.OHLCV_1S,  # 1-second OHLCV
                'minute': Schema.OHLCV_1M,  # 1-minute OHLCV  
                'hour': Schema.OHLCV_1H,    # 1-hour OHLCV
                'daily': Schema.OHLCV_1D    # 1-day OHLCV
            }
            
            schema_to_use = schema_map.get(resolution, Schema.OHLCV_1D)
            
            self.logger.info(f"Fetching {symbol} (Databento: {databento_symbol}) futures data from {start_date.date()} to {end_date.date()} with schema {schema_to_use.name}")
            
            # Download data from Databento  
            data = self.client.timeseries.get_range(
                dataset='GLBX.MDP3',  # CME Globex dataset
                symbols=databento_symbol,  # Use the converted symbol format
                schema=schema_to_use,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                stype_in=SType.CONTINUOUS if '.c.' in databento_symbol else SType.RAW_SYMBOL
            )
            
            # Convert to DataFrame
            if data is None:
                self.logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Convert DBNStore to DataFrame
            try:
                df = data.to_df()
            except Exception as e:
                self.logger.error(f"Error converting data to DataFrame: {e}")
                return pd.DataFrame()
            
            if df.empty:
                self.logger.warning(f"Empty DataFrame for {symbol}")
                return pd.DataFrame()
            
            # Process the data based on schema
            if 'OHLCV' in schema_to_use.name:
                # OHLCV data processing
                df = self._process_ohlcv_data(df, root_symbol)
            else:
                # Tick data processing (if needed)
                df = self._process_tick_data(df, root_symbol)
            
            self.logger.info(f"Downloaded {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error downloading futures data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _process_ohlcv_data(self, df: pd.DataFrame, root_symbol: str) -> pd.DataFrame:
        """Process OHLCV data from Databento"""
        if df.empty:
            return df
        
        # Rename columns to standard format if needed
        column_mapping = {
            'ts_event': 'timestamp',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        }
        
        # Check which columns exist and map them
        available_columns = df.columns.tolist()
        final_mapping = {}
        for old_col, new_col in column_mapping.items():
            if old_col in available_columns:
                final_mapping[old_col] = new_col
        
        df = df.rename(columns=final_mapping)
        
        # Ensure we have required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            self.logger.error(f"Missing required columns: {missing_columns}")
            self.logger.info(f"Available columns: {df.columns.tolist()}")
            return pd.DataFrame()
        
        # Convert timestamp to proper datetime index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        elif 'ts_event' in df.columns:
            df['ts_event'] = pd.to_datetime(df['ts_event'])
            df = df.set_index('ts_event')
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna()
        
        # Sort by timestamp
        df = df.sort_index()
        
        return df[required_columns]
    
    def _process_tick_data(self, df: pd.DataFrame, root_symbol: str) -> pd.DataFrame:
        """Process tick data from Databento (convert to OHLCV if needed)"""
        # For now, we'll focus on OHLCV data
        # Tick data processing can be added later if needed
        self.logger.warning("Tick data processing not yet implemented")
        return pd.DataFrame()
    
    def format_for_lean(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Convert data to QuantConnect Lean format"""
        if df.empty:
            return df
        
        lean_df = df.copy()
        
        # Parse symbol to get root
        root_symbol, _ = self.parse_symbol(symbol)
        
        # Get price multiplier for this contract
        multiplier = self.price_multipliers.get(root_symbol, LEAN_PRICE_MULTIPLIER)
        
        # Apply price multiplier to OHLC data
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in lean_df.columns:
                lean_df[col] = (lean_df[col] * multiplier).round().astype(int)
        
        # Ensure volume is integer
        if 'volume' in lean_df.columns:
            lean_df['volume'] = lean_df['volume'].astype(int)
        
        # Reorder columns for Lean format (OHLCV)
        column_order = ['open', 'high', 'low', 'close', 'volume']
        available_columns = [col for col in column_order if col in lean_df.columns]
        lean_df = lean_df[available_columns]
        
        return lean_df
    
    def get_lean_filepath(self, symbol: str, date: datetime, resolution: str) -> str:
        """Generate file path for Lean format"""
        root_symbol, base_symbol = self.parse_symbol(symbol)
        symbol_lower = base_symbol.lower().replace('.fut', '')
        
        # Get exchange for this symbol
        exchange = self.futures_exchanges.get(root_symbol, 'cme').lower()
        
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
    
    def download_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, 
                        resolution: str = 'daily', save_format: str = 'lean') -> Dict[str, pd.DataFrame]:
        """Download multiple futures symbols"""
        results = {}
        
        self.logger.info(f"Starting download of {len(symbols)} symbols from {start_date.date()} to {end_date.date()}")
        
        for symbol in tqdm(symbols, desc="Downloading futures data"):
            try:
                # Download raw data
                df = self.get_futures_data(symbol, start_date, end_date, resolution)
                
                if not df.empty:
                    # Format for Lean
                    lean_df = self.format_for_lean(df, symbol)
                    
                    if save_format == 'lean':
                        # Save to Lean format
                        self.save_to_lean_format(lean_df, symbol, resolution)
                    
                    results[symbol] = lean_df
                    self.logger.info(f"Successfully processed {symbol}: {len(lean_df)} records")
                else:
                    self.logger.warning(f"No data available for {symbol}")
                    results[symbol] = pd.DataFrame()
                    
            except Exception as e:
                self.logger.error(f"Failed to download {symbol}: {e}")
                results[symbol] = pd.DataFrame()
        
        return results
    
    def get_available_symbols(self, dataset: str = 'GLBX.MDP3') -> List[str]:
        """Get list of available futures symbols from Databento"""
        try:
            self._rate_limit()
            
            # For now, return a predefined list of common futures symbols
            # The exact API for getting available symbols may vary
            common_symbols = [
                'ES.FUT', 'NQ.FUT', 'YM.FUT', 'RTY.FUT',  # Equity Index Futures
                'CL.FUT', 'NG.FUT',                        # Energy Futures
                'GC.FUT', 'SI.FUT',                        # Metals Futures
                'ZB.FUT', 'ZN.FUT',                        # Treasury Futures
                'ZS.FUT', 'ZC.FUT', 'ZW.FUT'              # Agricultural Futures
            ]
            
            return common_symbols
            
        except Exception as e:
            self.logger.error(f"Error getting available symbols: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test connection to Databento API"""
        try:
            # Try to get available datasets
            self._rate_limit()
            
            datasets = self.client.metadata.list_datasets()
            
            if datasets:
                self.logger.info("Successfully connected to Databento API")
                self.logger.info(f"Available datasets: {[d for d in datasets[:5]]}")  # Show first 5
                return True
            else:
                self.logger.error("No datasets returned from Databento API")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Databento API: {e}")
            return False
