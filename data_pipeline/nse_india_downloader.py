"""
NSE India data downloader for Lean format
Supports Indian equities and derivatives using CSV downloads
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
import zipfile
import io
from bs4 import BeautifulSoup
import nsepy as nse

from config import (
    EQUITY_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

class NSEIndiaDownloader:
    """Download Indian equity and derivatives data from NSE and convert to Lean format"""
    
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        self.rate_limit_delay = 1  # Be respectful to NSE servers
        self.session = requests.Session()
        
        # Set headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Initialize session by visiting NSE homepage
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session with NSE"""
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            logger.info("NSE session initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize NSE session: {str(e)}")
    
    def get_equity_data_nsepy(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get equity data using nsepy library"""
        try:
            # Use nsepy to get data
            data = nse.get_history(
                symbol=symbol,
                start=start_date.date(),
                end=end_date.date()
            )
            
            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return []
            
            # Convert to our format
            bars = []
            for index, row in data.iterrows():
                timestamp = index.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting equity data for {symbol}: {str(e)}")
            return []
    
    def get_index_data_nsepy(self, index_name: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get index data using nsepy library"""
        try:
            # Use nsepy to get index data
            data = nse.get_index_history(
                index_name=index_name,
                start=start_date.date(),
                end=end_date.date()
            )
            
            if data.empty:
                logger.warning(f"No data found for index {index_name}")
                return []
            
            # Convert to our format
            bars = []
            for index, row in data.iterrows():
                timestamp = index.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': 0  # Index doesn't have volume
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting index data for {index_name}: {str(e)}")
            return []
    
    def get_derivatives_data_nsepy(self, symbol: str, start_date: datetime, end_date: datetime, expiry_date: datetime = None, option_type: str = None, strike_price: float = None) -> List[Dict]:
        """Get derivatives data using nsepy library"""
        try:
            if option_type and strike_price:
                # Option data
                data = nse.get_option_history(
                    symbol=symbol,
                    start=start_date.date(),
                    end=end_date.date(),
                    expiry=expiry_date.date() if expiry_date else None,
                    option_type=option_type,
                    strike_price=strike_price
                )
            else:
                # Futures data
                data = nse.get_futures_history(
                    symbol=symbol,
                    start=start_date.date(),
                    end=end_date.date(),
                    expiry=expiry_date.date() if expiry_date else None
                )
            
            if data.empty:
                logger.warning(f"No derivatives data found for {symbol}")
                return []
            
            # Convert to our format
            bars = []
            for index, row in data.iterrows():
                timestamp = index.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting derivatives data for {symbol}: {str(e)}")
            return []
    
    def get_equity_list(self) -> List[str]:
        """Get list of equity symbols from NSE"""
        try:
            # Use nsepy to get equity list
            equity_list = nse.get_equity_list()
            return equity_list['SYMBOL'].tolist() if not equity_list.empty else []
            
        except Exception as e:
            logger.error(f"Error getting equity list: {str(e)}")
            return []
    
    def get_index_list(self) -> List[str]:
        """Get list of available indices"""
        try:
            # Common NSE indices
            indices = [
                'NIFTY 50', 'NIFTY NEXT 50', 'NIFTY 100', 'NIFTY 200', 'NIFTY 500',
                'NIFTY MIDCAP 50', 'NIFTY MIDCAP 100', 'NIFTY SMALLCAP 50', 'NIFTY SMALLCAP 100',
                'NIFTY AUTO', 'NIFTY BANK', 'NIFTY ENERGY', 'NIFTY FINANCIAL SERVICES',
                'NIFTY FMCG', 'NIFTY IT', 'NIFTY MEDIA', 'NIFTY METAL', 'NIFTY PHARMA',
                'NIFTY PSU BANK', 'NIFTY REALTY', 'NIFTY PRIVATE BANK'
            ]
            return indices
            
        except Exception as e:
            logger.error(f"Error getting index list: {str(e)}")
            return []
    
    def download_equity_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime):
        """Download equity data for multiple symbols"""
        logger.info(f"Starting NSE equity download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading NSE equities"):
            try:
                data = self.get_equity_data_nsepy(symbol, start_date, end_date)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'india', 'nse', 'equity', 'daily')
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                        csv_filename = f"{symbol.lower()}_daily_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], 'daily')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_index_symbols(self, indices: List[str], start_date: datetime, end_date: datetime):
        """Download index data for multiple indices"""
        logger.info(f"Starting NSE index download for {len(indices)} indices")
        
        for index_name in tqdm(indices, desc="Downloading NSE indices"):
            try:
                data = self.get_index_data_nsepy(index_name, start_date, end_date)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'india', 'nse', 'indices', 'daily')
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        clean_name = index_name.replace(' ', '_').lower()
                        output_path = os.path.join(data_path, f"{clean_name}.zip")
                        csv_filename = f"{clean_name}_daily_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, index_name, cleaned_data[0]['timestamp'], 'daily')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {index_name}")
                
            except Exception as e:
                logger.error(f"Error downloading {index_name}: {str(e)}")
                continue
    
    def download_futures_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, expiry_dates: List[datetime] = None):
        """Download futures data for multiple symbols"""
        logger.info(f"Starting NSE futures download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading NSE futures"):
            try:
                if expiry_dates:
                    for expiry_date in expiry_dates:
                        data = self.get_derivatives_data_nsepy(symbol, start_date, end_date, expiry_date)
                        
                        if data:
                            # Clean and validate data
                            cleaned_data = DataValidator.clean_ohlcv_data(data)
                            
                            if cleaned_data:
                                # Create directory structure
                                data_path = os.path.join(EQUITY_DATA_PATH, 'india', 'nse', 'futures', 'daily')
                                ensure_directory_exists(data_path)
                                
                                # Save data
                                expiry_str = expiry_date.strftime('%Y%m%d')
                                output_path = os.path.join(data_path, f"{symbol.lower()}_{expiry_str}.zip")
                                csv_filename = f"{symbol.lower()}_{expiry_str}_daily_trade.csv"
                                
                                csv_content = create_lean_tradebar_csv(cleaned_data, f"{symbol}_{expiry_str}", cleaned_data[0]['timestamp'], 'daily')
                                
                                if csv_content:
                                    write_lean_zip_file(csv_content, output_path, csv_filename)
                                    logger.info(f"Saved {len(csv_content)} bars for {symbol} expiry {expiry_str}")
                else:
                    # Download current month futures
                    data = self.get_derivatives_data_nsepy(symbol, start_date, end_date)
                    
                    if data:
                        # Clean and validate data
                        cleaned_data = DataValidator.clean_ohlcv_data(data)
                        
                        if cleaned_data:
                            # Create directory structure
                            data_path = os.path.join(EQUITY_DATA_PATH, 'india', 'nse', 'futures', 'daily')
                            ensure_directory_exists(data_path)
                            
                            # Save data
                            output_path = os.path.join(data_path, f"{symbol.lower()}_current.zip")
                            csv_filename = f"{symbol.lower()}_current_daily_trade.csv"
                            
                            csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], 'daily')
                            
                            if csv_content:
                                write_lean_zip_file(csv_content, output_path, csv_filename)
                                logger.info(f"Saved {len(csv_content)} bars for {symbol} current futures")
                
            except Exception as e:
                logger.error(f"Error downloading futures for {symbol}: {str(e)}")
                continue
    
    def download_options_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, option_specs: List[Dict] = None):
        """Download options data for multiple symbols"""
        logger.info(f"Starting NSE options download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading NSE options"):
            try:
                if option_specs:
                    for spec in option_specs:
                        if spec['symbol'] == symbol:
                            data = self.get_derivatives_data_nsepy(
                                symbol, 
                                start_date, 
                                end_date, 
                                spec.get('expiry_date'),
                                spec.get('option_type'),
                                spec.get('strike_price')
                            )
                            
                            if data:
                                # Clean and validate data
                                cleaned_data = DataValidator.clean_ohlcv_data(data)
                                
                                if cleaned_data:
                                    # Create directory structure
                                    data_path = os.path.join(EQUITY_DATA_PATH, 'india', 'nse', 'options', 'daily')
                                    ensure_directory_exists(data_path)
                                    
                                    # Save data
                                    expiry_str = spec['expiry_date'].strftime('%Y%m%d') if spec.get('expiry_date') else 'current'
                                    option_name = f"{symbol}_{expiry_str}_{spec.get('strike_price', 0)}_{spec.get('option_type', 'CE')}"
                                    output_path = os.path.join(data_path, f"{option_name.lower()}.zip")
                                    csv_filename = f"{option_name.lower()}_daily_trade.csv"
                                    
                                    csv_content = create_lean_tradebar_csv(cleaned_data, option_name, cleaned_data[0]['timestamp'], 'daily')
                                    
                                    if csv_content:
                                        write_lean_zip_file(csv_content, output_path, csv_filename)
                                        logger.info(f"Saved {len(csv_content)} bars for {option_name}")
                
            except Exception as e:
                logger.error(f"Error downloading options for {symbol}: {str(e)}")
                continue
    
    def get_corporate_actions(self, symbol: str) -> Dict:
        """Get corporate actions data for a symbol"""
        try:
            # Use nsepy to get corporate actions
            from nsepy import get_corp_actions
            
            actions = get_corp_actions(symbol=symbol)
            
            if actions.empty:
                return {}
            
            return {
                'symbol': symbol,
                'corporate_actions': actions.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error getting corporate actions for {symbol}: {str(e)}")
            return {}
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """Get fundamental data for a symbol (limited data available)"""
        try:
            # NSE doesn't provide detailed fundamentals via API
            # This is a placeholder for basic company info
            
            fundamentals = {
                'symbol': symbol,
                'exchange': 'NSE',
                'country': 'India',
                'currency': 'INR'
            }
            
            return fundamentals
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {symbol}: {str(e)}")
            return {}