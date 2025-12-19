"""
Stooq Data Downloader

This module downloads financial data from Stooq.com, which provides free access
to historical stock data, forex, indices, and commodities. Stooq offers both
API access and CSV downloads for various international markets.

Supported data types:
- Stocks (US, European, Asian markets)
- Forex (currency pairs)
- Indices (market indices)
- Commodities (gold, oil, etc.)
- Cryptocurrencies

Data sources:
- Stooq API (free access)
- CSV downloads
- Historical data

Author: Data Pipeline Team
"""

import os
import requests
import pandas as pd
import zipfile
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
import io

from config import (
    STOOQ_DATA_PATH, DEFAULT_STOOQ_STOCKS, DEFAULT_STOOQ_FOREX, 
    DEFAULT_STOOQ_INDICES, DEFAULT_STOOQ_COMMODITIES
)
from utils import convert_to_lean_format, create_zip_file, setup_logging, format_symbol_for_lean, DataValidator

logger = setup_logging()

class StooqDownloader:
    """
    Stooq data downloader for various financial instruments
    
    Stooq provides free access to historical data through CSV downloads
    and a simple API interface.
    """
    
    def __init__(self):
        """Initialize the Stooq downloader"""
        self.base_url = 'https://stooq.com/q/d/l/'
        self.api_url = 'https://stooq.com/q/l/'
        self.data_path = STOOQ_DATA_PATH
        self.validator = DataValidator()
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_path, exist_ok=True)
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/csv,application/csv,text/plain,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Rate limiting: 1 second between requests
        self.request_delay = 1.0
        self.last_request_time = 0
        
        logger.info("Stooq downloader initialized")
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make a rate-limited request to Stooq"""
        try:
            self._wait_for_rate_limit()
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None
    
    def _format_stooq_symbol(self, symbol: str, market: str = '') -> str:
        """
        Format symbol for Stooq API
        
        Args:
            symbol: Symbol to format
            market: Market suffix (e.g., '.us', '.uk', '.de')
            
        Returns:
            Formatted symbol for Stooq
        """
        # Convert symbol to uppercase
        symbol = symbol.upper()
        
        # Add market suffix if provided
        if market and not symbol.endswith(market):
            symbol += market
        
        return symbol
    
    def _parse_stooq_date(self, date_str: str) -> datetime:
        """Parse Stooq date format (YYYYMMDD)"""
        try:
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Unable to parse date: {date_str}")
    
    def get_historical_data_csv(self, symbol: str, start_date: datetime, end_date: datetime, 
                               interval: str = 'd') -> Optional[pd.DataFrame]:
        """
        Get historical data from Stooq CSV download
        
        Args:
            symbol: Symbol to download (e.g., 'AAPL.US', 'EURUSD')
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval ('d' for daily, 'w' for weekly, 'm' for monthly)
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            # Format dates for Stooq (YYYYMMDD)
            d1 = start_date.strftime('%Y%m%d')
            d2 = end_date.strftime('%Y%m%d')
            
            # Construct URL for CSV download
            url = f"{self.base_url}?s={symbol}&d1={d1}&d2={d2}&i={interval}"
            
            logger.info(f"Fetching historical data for {symbol} from {start_date.date()} to {end_date.date()}")
            
            response = self._make_request(url)
            if not response:
                return None
            
            # Check if response contains CSV data
            if 'Date,Open,High,Low,Close,Volume' not in response.text:
                logger.warning(f"Invalid CSV response for {symbol}")
                return None
            
            # Parse CSV data
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            
            # Clean and format data
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Convert Date column to datetime
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            # Ensure all required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Missing column {col} for {symbol}")
                    return None
            
            # Convert to numeric
            for col in required_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove rows with NaN values
            df.dropna(inplace=True)
            
            # Sort by date
            df.sort_index(inplace=True)
            
            # Validate data
            if self.validator.validate_ohlcv_data(df):
                logger.info(f"Successfully retrieved {len(df)} records for {symbol}")
                return df
            else:
                logger.warning(f"Data validation failed for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    def get_current_quote_api(self, symbol: str) -> Optional[Dict]:
        """
        Get current quote from Stooq API
        
        Args:
            symbol: Symbol to get quote for
            
        Returns:
            Dictionary with current quote data or None if failed
        """
        try:
            # Construct API URL
            url = f"{self.api_url}?s={symbol}&f=sd2t2ohlcv&h&e=csv"
            
            response = self._make_request(url)
            if not response:
                return None
            
            # Parse CSV response
            csv_data = io.StringIO(response.text)
            df = pd.read_csv(csv_data)
            
            if df.empty:
                return None
            
            # Extract quote data
            row = df.iloc[0]
            quote_data = {
                'symbol': symbol,
                'date': row.get('Date', ''),
                'time': row.get('Time', ''),
                'open': float(row.get('Open', 0)),
                'high': float(row.get('High', 0)),
                'low': float(row.get('Low', 0)),
                'close': float(row.get('Close', 0)),
                'volume': int(row.get('Volume', 0))
            }
            
            logger.info(f"Current quote for {symbol}: {quote_data['close']}")
            return quote_data
            
        except Exception as e:
            logger.error(f"Error getting current quote for {symbol}: {str(e)}")
            return None
    
    def get_stock_data(self, symbol: str, start_date: datetime, end_date: datetime,
                      market: str = '.US') -> Optional[pd.DataFrame]:
        """
        Get stock data from Stooq
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date for data
            end_date: End date for data
            market: Market suffix (e.g., '.US', '.UK', '.DE')
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        formatted_symbol = self._format_stooq_symbol(symbol, market)
        return self.get_historical_data_csv(formatted_symbol, start_date, end_date)
    
    def get_forex_data(self, pair: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Get forex data from Stooq
        
        Args:
            pair: Currency pair (e.g., 'EURUSD', 'GBPUSD')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        # Format forex pair for Stooq
        formatted_pair = pair.replace('/', '').upper()
        return self.get_historical_data_csv(formatted_pair, start_date, end_date)
    
    def get_index_data(self, index: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Get index data from Stooq
        
        Args:
            index: Index symbol (e.g., '^SPX', '^DJI', '^IXIC')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        return self.get_historical_data_csv(index, start_date, end_date)
    
    def get_commodity_data(self, commodity: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Get commodity data from Stooq
        
        Args:
            commodity: Commodity symbol (e.g., 'GC.F', 'CL.F')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        return self.get_historical_data_csv(commodity, start_date, end_date)
    
    def get_crypto_data(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Get cryptocurrency data from Stooq
        
        Args:
            symbol: Crypto symbol (e.g., 'BTCUSD', 'ETHUSD')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        formatted_symbol = symbol.replace('-', '').upper()
        return self.get_historical_data_csv(formatted_symbol, start_date, end_date)
    
    def download_stock_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime,
                              market: str = '.US'):
        """Download multiple stock symbols and save in Lean format"""
        logger.info(f"Starting download of {len(symbols)} stock symbols from Stooq")
        
        for symbol in symbols:
            try:
                df = self.get_stock_data(symbol, start_date, end_date, market)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(symbol, 'equity')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'equity')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_equity_stooq.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Stock data for {symbol} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_forex_pairs(self, pairs: List[str], start_date: datetime, end_date: datetime):
        """Download multiple forex pairs and save in Lean format"""
        logger.info(f"Starting download of {len(pairs)} forex pairs from Stooq")
        
        for pair in pairs:
            try:
                df = self.get_forex_data(pair, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(pair.replace('/', ''), 'forex')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'forex')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_forex_stooq.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Forex data for {pair} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {pair}")
                    
            except Exception as e:
                logger.error(f"Error downloading {pair}: {str(e)}")
                continue
    
    def download_indices(self, indices: List[str], start_date: datetime, end_date: datetime):
        """Download multiple indices and save in Lean format"""
        logger.info(f"Starting download of {len(indices)} indices from Stooq")
        
        for index in indices:
            try:
                df = self.get_index_data(index, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(index.replace('^', ''), 'index')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'index')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_index_stooq.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Index data for {index} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {index}")
                    
            except Exception as e:
                logger.error(f"Error downloading {index}: {str(e)}")
                continue
    
    def download_commodities(self, commodities: List[str], start_date: datetime, end_date: datetime):
        """Download multiple commodities and save in Lean format"""
        logger.info(f"Starting download of {len(commodities)} commodities from Stooq")
        
        for commodity in commodities:
            try:
                df = self.get_commodity_data(commodity, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(commodity.replace('.F', ''), 'cfd')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'cfd')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_cfd_stooq.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Commodity data for {commodity} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {commodity}")
                    
            except Exception as e:
                logger.error(f"Error downloading {commodity}: {str(e)}")
                continue
    
    def download_crypto_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime):
        """Download multiple crypto symbols and save in Lean format"""
        logger.info(f"Starting download of {len(symbols)} crypto symbols from Stooq")
        
        for symbol in symbols:
            try:
                df = self.get_crypto_data(symbol, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(symbol.replace('USD', ''), 'crypto')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'crypto')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_crypto_stooq.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Crypto data for {symbol} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def get_available_symbols(self, market: str = 'US') -> List[str]:
        """
        Get list of available symbols from Stooq
        
        Args:
            market: Market to get symbols for ('US', 'UK', 'DE', etc.)
            
        Returns:
            List of available symbols
        """
        # Note: This is a placeholder implementation
        # Stooq doesn't provide a direct API for listing all symbols
        # In practice, you would need to maintain a list of known symbols
        # or scrape their website for symbol lists
        
        symbols = {
            'US': ['AAPL.US', 'MSFT.US', 'GOOGL.US', 'AMZN.US', 'TSLA.US'],
            'UK': ['LLOY.UK', 'BARC.UK', 'VOD.UK', 'BP.UK', 'SHEL.UK'],
            'DE': ['SAP.DE', 'ASME.DE', 'ALV.DE', 'SIE.DE', 'BAS.DE']
        }
        
        return symbols.get(market, [])
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'session'):
            self.session.close()