"""
Tiingo data downloader for Lean format
Supports stocks, forex, crypto with basic fundamentals and news
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional, Any
from tqdm import tqdm
import json

import sys
import os
sys.path.append(os.path.dirname(__file__))

from config import (
    TIINGO_API_KEY, EQUITY_DATA_PATH, CRYPTO_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

logger = setup_logging()

class TiingoDownloader:
    """Download financial data from Tiingo and convert to Lean format"""
    
    def __init__(self):
        if not TIINGO_API_KEY:
            raise ValueError("Tiingo API key not found. Please set TIINGO_API_KEY environment variable.")
        
        self.api_key = TIINGO_API_KEY
        self.base_url = "https://api.tiingo.com/tiingo"
        self.rate_limit_delay = 0.1  # Tiingo allows high rate limits
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        })
    
    def get_stock_data(self, symbol: str, start_date: datetime, end_date: datetime, frequency: str = 'daily') -> List[Dict]:
        """Get stock data from Tiingo"""
        try:
            # Tiingo's free tier daily endpoint only supports daily frequency
            if frequency != 'daily':
                logger.warning(f"Tiingo daily endpoint only supports daily frequency, not {frequency}. Skipping {symbol}")
                return []
            
            url = f"{self.base_url}/daily/{symbol}/prices"
            
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'format': 'json'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No data found for {symbol}")
                return []
            
            # Convert to our format
            bars = []
            for item in data:
                timestamp = datetime.strptime(item['date'][:10], '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': int(item['volume']) if item['volume'] else 0
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting stock data for {symbol}: {str(e)}")
            return []
    
    def get_crypto_data(self, symbol: str, start_date: datetime, end_date: datetime, frequency: str = 'daily') -> List[Dict]:
        """Get crypto data from Tiingo"""
        try:
            url = f"{self.base_url}/crypto/prices"
            
            params = {
                'tickers': symbol,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'resampleFreq': frequency
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or not data[0].get('priceData'):
                logger.warning(f"No crypto data found for {symbol}")
                return []
            
            # Convert to our format
            bars = []
            for item in data[0]['priceData']:
                timestamp = datetime.strptime(item['date'][:10], '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item['volume']) if item['volume'] else 0
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting crypto data for {symbol}: {str(e)}")
            return []
    
    def get_forex_data(self, pair: str, start_date: datetime, end_date: datetime, frequency: str = 'daily') -> List[Dict]:
        """Get forex data from Tiingo"""
        try:
            url = f"{self.base_url}/fx/{pair}/prices"
            
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'resampleFreq': frequency
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No forex data found for {pair}")
                return []
            
            # Convert to our format
            bars = []
            for item in data:
                timestamp = datetime.strptime(item['date'][:10], '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': 0  # Forex doesn't have volume
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting forex data for {pair}: {str(e)}")
            return []
    
    def get_fundamentals(self, symbol: str) -> Dict:
        """Get fundamental data for a symbol"""
        try:
            url = f"{self.base_url}/fundamentals/{symbol}/statements"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No fundamentals found for {symbol}")
                return {}
            
            # Extract key metrics
            fundamentals = {
                'symbol': symbol,
                'companyName': data.get('companyName', ''),
                'sector': data.get('sector', ''),
                'industry': data.get('industry', ''),
                'fundamentals': data
            }
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return fundamentals
            
        except Exception as e:
            logger.error(f"Error getting fundamentals for {symbol}: {str(e)}")
            return {}
    
    def get_income_statement(self, symbol: str, period: str = 'annual', limit: int = 5) -> Dict:
        """Get income statement data for a symbol"""
        try:
            url = f"{self.base_url}/fundamentals/{symbol}/income-statement"
            
            params = {
                'period': period,  # 'annual' or 'quarterly'
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No income statement data found for {symbol}")
                return {}
            
            # Structure the response
            income_statement = {
                'symbol': symbol,
                'period': period,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return income_statement
            
        except Exception as e:
            logger.error(f"Error getting income statement for {symbol}: {str(e)}")
            return {}
    
    def get_balance_sheet(self, symbol: str, period: str = 'annual', limit: int = 5) -> Dict:
        """Get balance sheet data for a symbol"""
        try:
            url = f"{self.base_url}/fundamentals/{symbol}/balance-sheet"
            
            params = {
                'period': period,  # 'annual' or 'quarterly'
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No balance sheet data found for {symbol}")
                return {}
            
            # Structure the response
            balance_sheet = {
                'symbol': symbol,
                'period': period,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return balance_sheet
            
        except Exception as e:
            logger.error(f"Error getting balance sheet for {symbol}: {str(e)}")
            return {}
    
    def get_cash_flow(self, symbol: str, period: str = 'annual', limit: int = 5) -> Dict:
        """Get cash flow statement data for a symbol"""
        try:
            url = f"{self.base_url}/fundamentals/{symbol}/cash-flow"
            
            params = {
                'period': period,  # 'annual' or 'quarterly'
                'limit': limit
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No cash flow data found for {symbol}")
                return {}
            
            # Structure the response
            cash_flow = {
                'symbol': symbol,
                'period': period,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return cash_flow
            
        except Exception as e:
            logger.error(f"Error getting cash flow for {symbol}: {str(e)}")
            return {}
    
    def get_options_data(self, symbol: str) -> Dict:
        """Get options data for a symbol from Tiingo"""
        try:
            url = f"{self.base_url}/options/{symbol}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No options data found for {symbol}")
                return {}
            
            # Structure the response
            options_data = {
                'symbol': symbol,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return options_data
            
        except Exception as e:
            logger.error(f"Error getting options data for {symbol}: {str(e)}")
            return {}
    
    def get_bonds_data(self, symbol: str, start_date: datetime, end_date: datetime, frequency: str = 'daily') -> List[Dict]:
        """Get bonds data from Tiingo"""
        try:
            # Tiingo may have bond data through their institutional feeds
            # For now, try to get bond ETF data
            url = f"{self.base_url}/daily/{symbol}/prices"
            
            params = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'format': 'json',
                'resampleFreq': frequency
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No bonds data found for {symbol}")
                return []
            
            # Convert to our format with bond-specific fields
            bars = []
            for item in data:
                timestamp = datetime.strptime(item['date'][:10], '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': int(item['volume']) if item['volume'] else 0,
                    'asset_type': 'bond',
                    'yield': 0.0,  # Not available in basic data
                    'duration': 0.0  # Not available in basic data
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting bonds data for {symbol}: {str(e)}")
            return []
    
    def get_financial_statements(self, symbol: str, period: str = 'annual', limit: int = 5) -> Dict:
        """Get comprehensive financial statements for a symbol"""
        try:
            logger.info(f"Fetching comprehensive financial statements for {symbol}")
            
            # Get all financial statements
            income_statement = self.get_income_statement(symbol, period, limit)
            balance_sheet = self.get_balance_sheet(symbol, period, limit)
            cash_flow = self.get_cash_flow(symbol, period, limit)
            earnings = self.get_earnings_data(symbol, limit)
            
            # Combine all data
            financial_statements = {
                'symbol': symbol,
                'period': period,
                'timestamp': datetime.now().isoformat(),
                'income_statement': income_statement.get('data', []),
                'balance_sheet': balance_sheet.get('data', []),
                'cash_flow': cash_flow.get('data', []),
                'earnings': earnings.get('data', []),
                'metadata': {
                    'source': 'tiingo',
                    'data_points': {
                        'income_statement': len(income_statement.get('data', [])),
                        'balance_sheet': len(balance_sheet.get('data', [])),
                        'cash_flow': len(cash_flow.get('data', [])),
                        'earnings': len(earnings.get('data', []))
                    }
                }
            }
            
            logger.info(f"Successfully retrieved financial statements for {symbol}")
            return financial_statements
            
        except Exception as e:
            logger.error(f"Error getting comprehensive financial statements for {symbol}: {str(e)}")
            return {}
    
    def get_comprehensive_fundamentals(self, symbol: str, include_financials: bool = True) -> Dict:
        """Get comprehensive fundamental data including financial statements"""
        try:
            logger.info(f"Fetching comprehensive fundamentals for {symbol}")
            
            # Get basic fundamentals
            basic_fundamentals = self.get_fundamentals(symbol)
            
            comprehensive_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'tiingo',
                'basic_fundamentals': basic_fundamentals,
                'financial_statements': {},
                'quality_score': None
            }
            
            if include_financials:
                # Get financial statements
                financial_statements = self.get_financial_statements(symbol)
                comprehensive_data['financial_statements'] = financial_statements
                
                # Assess data quality if we have financial data
                if financial_statements and any(financial_statements.get(key, []) for key in ['income_statement', 'balance_sheet', 'cash_flow']):
                    logger.info(f"Successfully retrieved financial statements for {symbol}")
            
            logger.info(f"Successfully retrieved comprehensive fundamentals for {symbol}")
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive fundamentals for {symbol}: {str(e)}")
            return {}
    
    def get_news(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get news data from Tiingo"""
        try:
            url = f"{self.base_url}/news"
            
            params = {
                'limit': limit
            }
            
            if symbol:
                params['tickers'] = symbol
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning("No news found")
                return []
            
            # Format news data
            news_items = []
            for item in data:
                news_items.append({
                    'symbol': symbol or 'GENERAL',
                    'title': item.get('title', ''),
                    'description': item.get('description', ''),
                    'url': item.get('url', ''),
                    'publishedDate': item.get('publishedDate', ''),
                    'crawlDate': item.get('crawlDate', ''),
                    'source': item.get('source', ''),
                    'tickers': item.get('tickers', [])
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error getting news: {str(e)}")
            return []
    
    def download_stock_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, frequency: str = 'daily'):
        """Download stock data for multiple symbols"""
        logger.info(f"Starting Tiingo stock download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading Tiingo stocks"):
            try:
                data = self.get_stock_data(symbol, start_date, end_date, frequency)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'tiingo', 'stocks', frequency)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                        csv_filename = f"{symbol.lower()}_{frequency}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], frequency, 'equity')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_crypto_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, frequency: str = 'daily'):
        """Download crypto data for multiple symbols"""
        logger.info(f"Starting Tiingo crypto download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading Tiingo crypto"):
            try:
                data = self.get_crypto_data(symbol, start_date, end_date, frequency)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(CRYPTO_DATA_PATH, 'tiingo', frequency)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                        csv_filename = f"{symbol.lower()}_{frequency}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], frequency, 'crypto')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_forex_pairs(self, pairs: List[str], start_date: datetime, end_date: datetime, frequency: str = 'daily'):
        """Download forex data for multiple pairs"""
        logger.info(f"Starting Tiingo forex download for {len(pairs)} pairs")
        
        for pair in tqdm(pairs, desc="Downloading Tiingo forex"):
            try:
                data = self.get_forex_data(pair, start_date, end_date, frequency)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'forex', 'tiingo', frequency)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{pair.lower()}.zip")
                        csv_filename = f"{pair.lower()}_{frequency}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, pair, cleaned_data[0]['timestamp'], frequency, 'forex')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {pair}")
                
            except Exception as e:
                logger.error(f"Error downloading {pair}: {str(e)}")
                continue
    
    def download_fundamentals(self, symbols: List[str]):
        """Download fundamental data for multiple symbols"""
        logger.info(f"Starting Tiingo fundamentals download for {len(symbols)} symbols")
        
        fundamentals_data = []
        
        for symbol in tqdm(symbols, desc="Downloading fundamentals"):
            try:
                fundamentals = self.get_fundamentals(symbol)
                
                if fundamentals:
                    fundamentals_data.append(fundamentals)
                
            except Exception as e:
                logger.error(f"Error downloading fundamentals for {symbol}: {str(e)}")
                continue
        
        # Save fundamentals data
        if fundamentals_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'fundamentals', 'tiingo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"fundamentals_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(fundamentals_data, f, indent=2, default=str)
            
            logger.info(f"Saved fundamentals for {len(fundamentals_data)} symbols")
    
    def download_options_data(self, symbols: List[str]):
        """Download options data for multiple symbols"""
        logger.info(f"Starting Tiingo options download for {len(symbols)} symbols")
        
        options_data = []
        
        for symbol in tqdm(symbols, desc="Downloading Tiingo options"):
            try:
                options = self.get_options_data(symbol)
                
                if options:
                    options_data.append(options)
                
            except Exception as e:
                logger.error(f"Error downloading options for {symbol}: {str(e)}")
                continue
        
        # Save options data
        if options_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'options', 'tiingo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"options_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(options_data, f, indent=2, default=str)
            
            logger.info(f"Saved options data for {len(options_data)} symbols")
    
    def download_bonds_data(self, symbols: List[str], start_date: datetime, end_date: datetime, frequency: str = 'daily'):
        """Download bonds data for multiple symbols"""
        logger.info(f"Starting Tiingo bonds download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading Tiingo bonds"):
            try:
                data = self.get_bonds_data(symbol, start_date, end_date, frequency)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'bonds', 'tiingo', frequency)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                        csv_filename = f"{symbol.lower()}_{frequency}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], frequency)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for bonds {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading bonds data for {symbol}: {str(e)}")
                continue
    
    def download_comprehensive_stock_data(self, symbols: List[str], start_date: datetime, 
                                        end_date: datetime, frequency: str = 'daily',
                                        include_fundamentals: bool = True):
        """Download comprehensive stock data including OHLCV, fundamentals, and quality assessment"""
        logger.info(f"Starting comprehensive Tiingo stock download for {len(symbols)} symbols")
        
        results = []
        
        for symbol in tqdm(symbols, desc="Downloading comprehensive stock data"):
            try:
                # Get OHLCV data
                ohlcv_data = self.get_stock_data(symbol, start_date, end_date, frequency)
                
                if ohlcv_data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(ohlcv_data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'tiingo', 'comprehensive', frequency)
                        ensure_directory_exists(data_path)
                        
                        # Save OHLCV data
                        output_path = os.path.join(data_path, f"{symbol.lower()}.zip")
                        csv_filename = f"{symbol.lower()}_{frequency}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], frequency)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            
                            # Get fundamentals if requested
                            fundamentals_data = {}
                            quality_score = None
                            
                            if include_fundamentals:
                                fundamentals_data = self.get_comprehensive_fundamentals(symbol)
                            
                            # Store results
                            result = {
                                'symbol': symbol,
                                'ohlcv_records': len(csv_content),
                                'fundamentals_available': bool(fundamentals_data),
                                'quality_score': None,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            results.append(result)
                            
                            # Save fundamentals data separately
                            if fundamentals_data:
                                fundamentals_path = os.path.join(EQUITY_DATA_PATH, 'fundamentals', 'tiingo', 'comprehensive')
                                ensure_directory_exists(fundamentals_path)
                                
                                fundamentals_file = os.path.join(fundamentals_path, f"{symbol.lower()}_fundamentals.json")
                                
                                with open(fundamentals_file, 'w') as f:
                                    json.dump(fundamentals_data, f, indent=2, default=str)
                            
                            logger.info(f"Saved comprehensive data for {symbol}: {len(csv_content)} records")
            
            except Exception as e:
                logger.error(f"Error downloading comprehensive data for {symbol}: {str(e)}")
                continue
        
        # Save summary report
        if results:
            summary_path = os.path.join(EQUITY_DATA_PATH, 'tiingo', 'comprehensive')
            ensure_directory_exists(summary_path)
            
            summary_file = os.path.join(summary_path, f"download_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            summary = {
                'download_timestamp': datetime.now().isoformat(),
                'total_symbols': len(symbols),
                'successful_downloads': len(results),
                'average_quality_score': sum(r['quality_score'] for r in results if r['quality_score']) / len([r for r in results if r['quality_score']]) if any(r['quality_score'] for r in results) else None,
                'results': results
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Comprehensive download completed. Summary saved to {summary_file}")
        
        return results