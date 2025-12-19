"""
Investing.com Data Downloader

This module downloads financial data from Investing.com using the investpy library.
Supports stocks, bonds, ETFs, funds, commodities, currencies, crypto, and indices
from multiple countries and markets.

Supported data types:
- Stocks (equity prices from various countries)
- Bonds (government and corporate bonds)
- ETFs (exchange-traded funds)
- Funds (mutual funds)
- Commodities (gold, oil, etc.)
- Currencies (forex pairs)
- Cryptocurrency
- Indices (market indices)
- Economic calendar events

Author: Data Pipeline Team
"""

import os
import pandas as pd
import zipfile
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time

try:
    import investpy
    INVESTPY_AVAILABLE = True
except ImportError:
    INVESTPY_AVAILABLE = False
    print("Warning: investpy library not installed. Run: pip install investpy")

from config import (
    INVESTING_DATA_PATH, DEFAULT_INVESTING_STOCKS,
    DEFAULT_INVESTING_FOREX, DEFAULT_INVESTING_COMMODITIES, DEFAULT_INVESTING_CRYPTO,
    DEFAULT_INVESTING_INDICES
)
from utils import convert_to_lean_format, create_zip_file, setup_logging, format_symbol_for_lean, DataValidator

logger = setup_logging()

class InvestingComDownloader:
    """
    Investing.com data downloader using the investpy library
    
    Provides access to financial data from Investing.com including stocks,
    bonds, ETFs, funds, commodities, currencies, crypto, and indices.
    """
    
    def __init__(self):
        """Initialize the Investing.com downloader"""
        if not INVESTPY_AVAILABLE:
            raise ImportError("investpy library is required. Install with: pip install investpy")
        
        self.data_path = INVESTING_DATA_PATH
        self.validator = DataValidator()
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_path, exist_ok=True)
        
        # Rate limiting: 1 second between requests to be respectful
        self.request_delay = 1.0
        self.last_request_time = 0
        
        logger.info("Investing.com downloader initialized with investpy library")
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _format_date(self, date: datetime) -> str:
        """Format datetime to investpy date format (dd/mm/yyyy)"""
        return date.strftime('%d/%m/%Y')
    
    def get_stock_data(self, symbol: str, country: str = 'United States', 
                      start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get stock price data from Investing.com
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            country: Country name (e.g., 'United States', 'Spain')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching stock data for {symbol} ({country}) from {from_date} to {to_date}")
            
            df = investpy.get_stock_historical_data(
                stock=symbol,
                country=country,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Standardize column names
                df = df.rename(columns={
                    'Open': 'Open',
                    'High': 'High', 
                    'Low': 'Low',
                    'Close': 'Close',
                    'Volume': 'Volume'
                })
                
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {symbol}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {symbol}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return None
    
    def get_forex_data(self, pair: str, start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get forex pair data from Investing.com
        
        Args:
            pair: Currency pair (e.g., 'EUR/USD', 'GBP/USD')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching forex data for {pair} from {from_date} to {to_date}")
            
            df = investpy.get_currency_cross_historical_data(
                currency_cross=pair,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {pair}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {pair}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting forex data for {pair}: {str(e)}")
            return None
    
    def get_commodity_data(self, commodity: str, start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get commodity price data from Investing.com
        
        Args:
            commodity: Commodity name (e.g., 'Gold', 'Crude Oil WTI')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching commodity data for {commodity} from {from_date} to {to_date}")
            
            df = investpy.get_commodity_historical_data(
                commodity=commodity,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {commodity}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {commodity}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting commodity data for {commodity}: {str(e)}")
            return None
    
    def get_crypto_data(self, symbol: str, start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get cryptocurrency data from Investing.com
        
        Args:
            symbol: Crypto symbol (e.g., 'Bitcoin', 'Ethereum')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching crypto data for {symbol} from {from_date} to {to_date}")
            
            df = investpy.get_crypto_historical_data(
                crypto=symbol,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {symbol}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {symbol}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting crypto data for {symbol}: {str(e)}")
            return None
    
    def get_index_data(self, index: str, country: str = 'United States', 
                      start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get index data from Investing.com
        
        Args:
            index: Index name (e.g., 'S&P 500', 'Nasdaq 100')
            country: Country name (e.g., 'United States', 'Germany')
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching index data for {index} ({country}) from {from_date} to {to_date}")
            
            df = investpy.get_index_historical_data(
                index=index,
                country=country,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {index}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {index}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting index data for {index}: {str(e)}")
            return None
    
    def get_etf_data(self, etf: str, country: str = 'United States',
                    start_date: datetime = None, end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        Get ETF data from Investing.com
        
        Args:
            etf: ETF name (e.g., 'SPDR S&P 500', 'iShares Core MSCI World')
            country: Country name
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            self._wait_for_rate_limit()
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            from_date = self._format_date(start_date)
            to_date = self._format_date(end_date)
            
            logger.info(f"Fetching ETF data for {etf} ({country}) from {from_date} to {to_date}")
            
            df = investpy.get_etf_historical_data(
                etf=etf,
                country=country,
                from_date=from_date,
                to_date=to_date
            )
            
            if df is not None and not df.empty:
                # Validate data
                if self.validator.validate_ohlcv_data(df):
                    logger.info(f"Successfully retrieved {len(df)} records for {etf}")
                    return df
                else:
                    logger.warning(f"Data validation failed for {etf}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting ETF data for {etf}: {str(e)}")
            return None
    
    def get_economic_calendar(self, from_date: datetime = None, to_date: datetime = None, 
                             countries: List[str] = None) -> List[Dict]:
        """
        Get economic calendar events from Investing.com
        
        Args:
            from_date: Start date for events
            to_date: End date for events
            countries: List of country names to filter
            
        Returns:
            List of economic events
        """
        try:
            self._wait_for_rate_limit()
            
            if from_date is None:
                from_date = datetime.now()
            if to_date is None:
                to_date = from_date + timedelta(days=7)
            
            from_date_str = self._format_date(from_date)
            to_date_str = self._format_date(to_date)
            
            logger.info(f"Fetching economic calendar from {from_date_str} to {to_date_str}")
            
            df = investpy.get_economic_calendar(
                from_date=from_date_str,
                to_date=to_date_str,
                countries=countries or ['United States']
            )
            
            if df is not None and not df.empty:
                # Convert to list of dictionaries
                events = df.to_dict('records')
                logger.info(f"Retrieved {len(events)} economic events")
                return events
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting economic calendar: {str(e)}")
            return []
    
    def download_stock_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, country: str = 'United States'):
        """Download multiple stock symbols and save in Lean format"""
        logger.info(f"Starting download of {len(symbols)} stock symbols from {country}")
        
        for symbol in symbols:
            try:
                df = self.get_stock_data(symbol, country, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(symbol, 'equity')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'equity')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_equity_investing.zip"
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
        logger.info(f"Starting download of {len(pairs)} forex pairs")
        
        for pair in pairs:
            try:
                df = self.get_forex_data(pair, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(pair.replace('/', ''), 'forex')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'forex')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_forex_investing.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Forex data for {pair} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {pair}")
                    
            except Exception as e:
                logger.error(f"Error downloading {pair}: {str(e)}")
                continue
    
    def download_commodities(self, commodities: List[str], start_date: datetime, end_date: datetime):
        """Download multiple commodities and save in Lean format"""
        logger.info(f"Starting download of {len(commodities)} commodities")
        
        for commodity in commodities:
            try:
                df = self.get_commodity_data(commodity, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(commodity, 'cfd')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'cfd')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_cfd_investing.zip"
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
        logger.info(f"Starting download of {len(symbols)} crypto symbols")
        
        for symbol in symbols:
            try:
                df = self.get_crypto_data(symbol, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(symbol, 'crypto')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'crypto')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_crypto_investing.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Crypto data for {symbol} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_indices(self, indices: List[str], start_date: datetime, end_date: datetime, country: str = 'United States'):
        """Download multiple indices and save in Lean format"""
        logger.info(f"Starting download of {len(indices)} indices from {country}")
        
        for index in indices:
            try:
                df = self.get_index_data(index, country, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(index, 'index')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'index')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_index_investing.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"Index data for {index} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {index}")
                    
            except Exception as e:
                logger.error(f"Error downloading {index}: {str(e)}")
                continue
    
    def download_etfs(self, etfs: List[str], start_date: datetime, end_date: datetime, country: str = 'United States'):
        """Download multiple ETFs and save in Lean format"""
        logger.info(f"Starting download of {len(etfs)} ETFs from {country}")
        
        for etf in etfs:
            try:
                df = self.get_etf_data(etf, country, start_date, end_date)
                
                if df is not None and not df.empty:
                    # Convert to Lean format and save
                    lean_symbol = format_symbol_for_lean(etf, 'equity')
                    lean_data = convert_to_lean_format(df, lean_symbol, 'equity')
                    
                    # Create zip file
                    zip_filename = f"{lean_symbol.lower()}_etf_investing.zip"
                    zip_path = os.path.join(self.data_path, zip_filename)
                    create_zip_file(lean_data, zip_path, lean_symbol)
                    
                    logger.info(f"ETF data for {etf} saved to {zip_path}")
                else:
                    logger.warning(f"No data retrieved for {etf}")
                    
            except Exception as e:
                logger.error(f"Error downloading {etf}: {str(e)}")
                continue
    
    def download_economic_calendar(self, from_date: datetime = None, to_date: datetime = None, 
                                  countries: List[str] = None):
        """Download economic calendar events and save to JSON file"""
        try:
            events = self.get_economic_calendar(from_date, to_date, countries)
            
            if events:
                # Save events to JSON file
                calendar_filename = f"investing_economic_calendar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                calendar_path = os.path.join(self.data_path, calendar_filename)
                
                with open(calendar_path, 'w', encoding='utf-8') as f:
                    json.dump(events, f, indent=2, ensure_ascii=False, default=str)
                
                logger.info(f"Economic calendar saved to {calendar_path}")
            else:
                logger.warning("No economic events retrieved")
                
        except Exception as e:
            logger.error(f"Error downloading economic calendar: {str(e)}")