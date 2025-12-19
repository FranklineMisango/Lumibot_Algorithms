import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional, Any
from tqdm import tqdm
import json
import requests

from config import (
    EQUITY_DATA_PATH, CRYPTO_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator, static_tqdm
)

logger = setup_logging()

class YahooFinanceDownloader:
    """Enhanced Yahoo Finance downloader with support for multiple asset types"""
    
    def __init__(self):
        self.rate_limit_delay = 0.5  # Be respectful to Yahoo Finance
        
    def get_stock_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str = '1d') -> List[Dict]:
        """Get stock/ETF/index data from Yahoo Finance with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Add delay between requests to avoid rate limiting
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for {symbol} after rate limit")
                    time.sleep(retry_delay * attempt)
                
                ticker = yf.Ticker(symbol)
                
                # Map interval to yfinance format
                yf_interval_map = {
                    'minute': '1m',
                    'hour': '1h',
                    'daily': '1d',
                    'weekly': '1wk',
                    'monthly': '1mo'
                }
                
                yf_interval = yf_interval_map.get(interval, '1d')
                
                # Download data with longer timeout and error handling
                data = ticker.history(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    interval=yf_interval,
                    auto_adjust=False,
                    prepost=False
                )
                
                if data.empty:
                    logger.warning(f"No data found for {symbol} on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue  # Try again
                    else:
                        return []  # Final attempt failed
                
                # Convert to our format
                bars = []
                for timestamp, row in data.iterrows():
                    # Handle timezone
                    if hasattr(timestamp, 'tz_localize'):
                        if timestamp.tz is None:
                            timestamp = timestamp.tz_localize(LEAN_TIMEZONE_EQUITY)
                        else:
                            timestamp = timestamp.tz_convert(LEAN_TIMEZONE_EQUITY)
                    else:
                        timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                    
                    bars.append({
                        'timestamp': timestamp,
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0
                    })
                
                # Success! Rate limiting for next call
                time.sleep(self.rate_limit_delay)
                logger.info(f"Successfully downloaded {len(bars)} bars for {symbol}")
                return bars
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All attempts failed for {symbol}. Final error: {str(e)}")
                    return []
                # Continue to next attempt
        
        return []  # Should never reach here, but just in case
    
    def get_forex_data(self, pair: str, start_date: datetime, end_date: datetime, interval: str = '1d') -> List[Dict]:
        """Get forex data from Yahoo Finance (e.g., EURUSD=X)"""
        try:
            # Yahoo Finance forex symbols typically end with =X
            if not pair.endswith('=X'):
                pair = f"{pair}=X"
            
            return self.get_stock_data(pair, start_date, end_date, interval)
            
        except Exception as e:
            logger.error(f"Error getting forex data for {pair}: {str(e)}")
            return []
    
    def get_crypto_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str = '1d') -> List[Dict]:
        """Get crypto data from Yahoo Finance (e.g., BTC-USD)"""
        try:
            # Yahoo Finance crypto symbols typically use -USD format
            if not symbol.endswith('-USD'):
                symbol = f"{symbol}-USD"
            
            return self.get_stock_data(symbol, start_date, end_date, interval)
            
        except Exception as e:
            logger.error(f"Error getting crypto data for {symbol}: {str(e)}")
            return []
    
    def get_options_data(self, symbol: str, expiration_date: Optional[str] = None, option_type: Optional[str] = None) -> Dict:
        """Get options data for a symbol"""
        try:
            logger.info(f"Fetching options data for {symbol}")
            
            ticker = yf.Ticker(symbol)
            
            # Get available expiration dates
            if expiration_date is None:
                expirations = ticker.options
                if not expirations:
                    logger.warning(f"No options available for {symbol}")
                    return {}
                
                # Use the nearest expiration date
                expiration_date = expirations[0]
                logger.info(f"Using nearest expiration date: {expiration_date}")
            
            # Get options chain for the expiration date
            options_chain = ticker.option_chain(expiration_date)
            
            options_data = {
                'symbol': symbol,
                'expiration_date': expiration_date,
                'timestamp': datetime.now().isoformat(),
                'calls': [],
                'puts': []
            }
            
            # Process calls
            if hasattr(options_chain, 'calls') and not options_chain.calls.empty:
                calls_data = []
                for _, row in options_chain.calls.iterrows():
                    call_data = {
                        'contract_symbol': row.get('contractSymbol', ''),
                        'strike': float(row.get('strike', 0)),
                        'last_price': float(row.get('lastPrice', 0)),
                        'bid': float(row.get('bid', 0)),
                        'ask': float(row.get('ask', 0)),
                        'change': float(row.get('change', 0)),
                        'percent_change': float(row.get('percentChange', 0)),
                        'volume': int(row.get('volume', 0)) if not pd.isna(row.get('volume', 0)) else 0,
                        'open_interest': int(row.get('openInterest', 0)) if not pd.isna(row.get('openInterest', 0)) else 0,
                        'implied_volatility': float(row.get('impliedVolatility', 0)),
                        'in_the_money': bool(row.get('inTheMoney', False))
                    }
                    calls_data.append(call_data)
                
                options_data['calls'] = calls_data
            
            # Process puts
            if hasattr(options_chain, 'puts') and not options_chain.puts.empty:
                puts_data = []
                for _, row in options_chain.puts.iterrows():
                    put_data = {
                        'contract_symbol': row.get('contractSymbol', ''),
                        'strike': float(row.get('strike', 0)),
                        'last_price': float(row.get('lastPrice', 0)),
                        'bid': float(row.get('bid', 0)),
                        'ask': float(row.get('ask', 0)),
                        'change': float(row.get('change', 0)),
                        'percent_change': float(row.get('percentChange', 0)),
                        'volume': int(row.get('volume', 0)) if not pd.isna(row.get('volume', 0)) else 0,
                        'open_interest': int(row.get('openInterest', 0)) if not pd.isna(row.get('openInterest', 0)) else 0,
                        'implied_volatility': float(row.get('impliedVolatility', 0)),
                        'in_the_money': bool(row.get('inTheMoney', False))
                    }
                    puts_data.append(put_data)
                
                options_data['puts'] = puts_data
            
            # Add summary statistics
            options_data['summary'] = {
                'total_calls': len(options_data['calls']),
                'total_puts': len(options_data['puts']),
                'available_expirations': list(ticker.options) if hasattr(ticker, 'options') else []
            }
            
            logger.info(f"Successfully retrieved options data for {symbol}: {len(options_data['calls'])} calls, {len(options_data['puts'])} puts")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return options_data
            
        except Exception as e:
            logger.error(f"Error getting options data for {symbol}: {str(e)}")
            return {}
    
    def get_bonds_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str = '1d') -> List[Dict]:
        """Get bonds data from Yahoo Finance"""
        try:
            logger.info(f"Fetching bonds data for {symbol}")
            
            # Yahoo Finance bond symbols typically end with =B (e.g., TLT=B for iShares 20+ Year Treasury Bond ETF)
            # or specific bond symbols
            if not symbol.endswith('=B') and not symbol.startswith('^'):
                # Try adding =B suffix for bond ETFs
                bond_symbol = f"{symbol}=B"
            else:
                bond_symbol = symbol
            
            # Get data using the existing stock data method (bonds are treated similarly)
            bars = self.get_stock_data(bond_symbol, start_date, end_date, interval)
            
            if not bars:
                logger.warning(f"No bonds data found for {symbol} (tried {bond_symbol})")
                return []
            
            # Add bond-specific metadata
            for bar in bars:
                bar['asset_type'] = 'bond'
                bar['yield'] = 0.0  # Yahoo Finance doesn't provide yield in historical data
                bar['duration'] = 0.0  # Duration not available in historical data
            
            logger.info(f"Successfully retrieved {len(bars)} bars of bonds data for {symbol}")
            return bars
            
        except Exception as e:
            logger.error(f"Error getting bonds data for {symbol}: {str(e)}")
            return []
    
    def get_treasury_data(self, maturity: str = '10y', start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get US Treasury yield data"""
        try:
            logger.info(f"Fetching treasury data for {maturity} maturity")
            
            # Map maturity to Yahoo Finance symbols
            maturity_map = {
                '1m': '^IRX',    # 13-week treasury bill
                '3m': '^IRX',    # 13-week treasury bill
                '6m': '^IRX',    # 13-week treasury bill
                '1y': '^FVX',    # 5-year treasury note
                '2y': '^IRX',    # 13-week treasury bill (approximation)
                '5y': '^FVX',    # 5-year treasury note
                '10y': '^TNX',   # 10-year treasury note
                '30y': '^TYX'    # 30-year treasury bond
            }
            
            symbol = maturity_map.get(maturity, '^TNX')  # Default to 10-year
            
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            # Get data using existing method
            bars = self.get_stock_data(symbol, start_date, end_date, '1d')
            
            if not bars:
                logger.warning(f"No treasury data found for {maturity} maturity")
                return []
            
            # Add treasury-specific metadata
            for bar in bars:
                bar['asset_type'] = 'treasury'
                bar['maturity'] = maturity
                # The 'close' price represents the yield percentage
                bar['yield_percent'] = bar['close']
            
            logger.info(f"Successfully retrieved {len(bars)} bars of treasury data for {maturity}")
            return bars
            
        except Exception as e:
            logger.error(f"Error getting treasury data for {maturity}: {str(e)}")
            return []
    
    def get_earnings_data(self, symbol: str) -> Dict:
        """Get earnings data for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            earnings_data = {
                'symbol': symbol,
                'earnings_history': {},
                'earnings_calendar': {}
            }
            
            # Get historical earnings
            try:
                earnings = ticker.earnings
                if not earnings.empty:
                    earnings_data['earnings_history'] = earnings.to_dict('index')
            except:
                pass
            
            # Get quarterly earnings
            try:
                quarterly_earnings = ticker.quarterly_earnings
                if not quarterly_earnings.empty:
                    earnings_data['quarterly_earnings'] = quarterly_earnings.to_dict('index')
            except:
                pass
            
            # Get earnings calendar
            try:
                calendar = ticker.calendar
                if calendar is not None and not calendar.empty:
                    earnings_data['earnings_calendar'] = calendar.to_dict('index')
            except:
                pass
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return earnings_data
            
        except Exception as e:
            logger.error(f"Error getting earnings for {symbol}: {str(e)}")
            return {}
    
    def get_financial_statements(self, symbol: str) -> Dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            
            financials = {
                'symbol': symbol,
                'income_statement': {},
                'balance_sheet': {},
                'cash_flow': {},
                'last_updated': datetime.now().isoformat()
            }
            
            # Get income statement
            try:
                income_stmt = ticker.financials
                if not income_stmt.empty:
                    financials['income_statement']['annual'] = income_stmt.to_dict()
            except Exception as e:
                logger.warning(f"Could not get annual income statement for {symbol}: {str(e)}")
            
            try:
                quarterly_income = ticker.quarterly_financials
                if not quarterly_income.empty:
                    financials['income_statement']['quarterly'] = quarterly_income.to_dict()
            except Exception as e:
                logger.warning(f"Could not get quarterly income statement for {symbol}: {str(e)}")
            
            # Get balance sheet
            try:
                balance_sheet = ticker.balance_sheet
                if not balance_sheet.empty:
                    financials['balance_sheet']['annual'] = balance_sheet.to_dict()
            except Exception as e:
                logger.warning(f"Could not get annual balance sheet for {symbol}: {str(e)}")
            
            try:
                quarterly_balance = ticker.quarterly_balance_sheet
                if not quarterly_balance.empty:
                    financials['balance_sheet']['quarterly'] = quarterly_balance.to_dict()
            except Exception as e:
                logger.warning(f"Could not get quarterly balance sheet for {symbol}: {str(e)}")
            
            # Get cash flow statement
            try:
                cash_flow = ticker.cashflow
                if not cash_flow.empty:
                    financials['cash_flow']['annual'] = cash_flow.to_dict()
            except Exception as e:
                logger.warning(f"Could not get annual cash flow for {symbol}: {str(e)}")
            
            try:
                quarterly_cash_flow = ticker.quarterly_cashflow
                if not quarterly_cash_flow.empty:
                    financials['cash_flow']['quarterly'] = quarterly_cash_flow.to_dict()
            except Exception as e:
                logger.warning(f"Could not get quarterly cash flow for {symbol}: {str(e)}")
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return financials
            
        except Exception as e:
            logger.error(f"Error getting financial statements for {symbol}: {str(e)}")
            return {}
    
    def get_comprehensive_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive fundamental data including financial statements"""
        try:
            fundamentals = self.get_fundamental_data(symbol)
            financials = self.get_financial_statements(symbol)
            earnings = self.get_earnings_data(symbol)
            
            comprehensive_data = {
                'symbol': symbol,
                'overview': fundamentals,
                'financial_statements': financials,
                'earnings': earnings,
                'last_updated': datetime.now().isoformat()
            }
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive fundamentals for {symbol}: {str(e)}")
            return {}
    
    def get_news_data(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get news headlines for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                return []
            
            formatted_news = []
            for item in news[:limit]:
                formatted_item = {
                    'symbol': symbol,
                    'title': item.get('title', ''),
                    'publisher': item.get('publisher', ''),
                    'link': item.get('link', ''),
                    'publishTime': item.get('providerPublishTime', 0),
                    'type': item.get('type', ''),
                    'thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '') if item.get('thumbnail') else '',
                    'relatedTickers': item.get('relatedTickers', [])
                }
                formatted_news.append(formatted_item)
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return formatted_news
            
        except Exception as e:
            logger.error(f"Error getting news for {symbol}: {str(e)}")
            return []
    
    def download_stock_symbols(self, symbols: List[str], interval: str, start_date: datetime, end_date: datetime, asset_type: str = 'equity'):
        """Download stock/ETF/index data for multiple symbols"""
        logger.info(f"Starting Yahoo Finance {asset_type} download for {len(symbols)} symbols")
        
        for symbol in static_tqdm(symbols, desc=f"Downloading {asset_type}"):
            try:
                data = self.get_stock_data(symbol, start_date, end_date, interval)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        if asset_type == 'crypto':
                            data_path = os.path.join(CRYPTO_DATA_PATH, 'yahoo', interval)
                        else:
                            data_path = os.path.join(EQUITY_DATA_PATH, asset_type, 'yahoo', interval)
                        
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{symbol.lower().replace('=', '_').replace('-', '_')}.zip")
                        csv_filename = f"{symbol.lower().replace('=', '_').replace('-', '_')}_{interval}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], interval)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_forex_pairs(self, pairs: List[str], interval: str, start_date: datetime, end_date: datetime):
        """Download forex data for multiple pairs"""
        logger.info(f"Starting Yahoo Finance forex download for {len(pairs)} pairs")
        
        for pair in static_tqdm(pairs, desc="Downloading forex"):
            try:
                data = self.get_forex_data(pair, start_date, end_date, interval)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'forex', 'yahoo', interval)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        clean_pair = pair.replace('=X', '').lower()
                        output_path = os.path.join(data_path, f"{clean_pair}.zip")
                        csv_filename = f"{clean_pair}_{interval}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, pair, cleaned_data[0]['timestamp'], interval, 'forex')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {pair}")
                
            except Exception as e:
                logger.error(f"Error downloading {pair}: {str(e)}")
                continue
    
    def download_crypto_symbols(self, symbols: List[str], start_date: datetime, end_date: datetime, interval: str = 'daily'):
        """Download crypto data for multiple symbols (orchestrator-compatible method)"""
        logger.info(f"Starting Yahoo Finance crypto download for {len(symbols)} symbols")
        
        for symbol in static_tqdm(symbols, desc="Downloading crypto"):
            try:
                data = self.get_crypto_data(symbol, start_date, end_date, interval)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(CRYPTO_DATA_PATH, 'yahoo', interval)
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        clean_symbol = symbol.replace('-USD', '').lower()
                        output_path = os.path.join(data_path, f"{clean_symbol}.zip")
                        csv_filename = f"{clean_symbol}_{interval}_trade.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, symbol, cleaned_data[0]['timestamp'], interval)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
    
    def download_fundamentals(self, symbols: List[str]):
        """Download fundamental data for multiple symbols"""
        logger.info(f"Starting Yahoo Finance fundamentals download for {len(symbols)} symbols")
        
        fundamentals_data = []
        
        for symbol in static_tqdm(symbols, desc="Downloading fundamentals"):
            try:
                fundamentals = self.get_fundamental_data(symbol)
                
                if fundamentals:
                    fundamentals_data.append(fundamentals)
                
            except Exception as e:
                logger.error(f"Error downloading fundamentals for {symbol}: {str(e)}")
                continue
        
        # Save fundamentals data
        if fundamentals_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'fundamentals', 'yahoo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"fundamentals_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(fundamentals_data, f, indent=2, default=str)
            
            logger.info(f"Saved fundamentals for {len(fundamentals_data)} symbols")
    
    def download_earnings(self, symbols: List[str]):
        """Download earnings data for multiple symbols"""
        logger.info(f"Starting Yahoo Finance earnings download for {len(symbols)} symbols")
        
        earnings_data = []
        
        for symbol in static_tqdm(symbols, desc="Downloading earnings"):
            try:
                earnings = self.get_earnings_data(symbol)
                
                if earnings:
                    earnings_data.append(earnings)
                
            except Exception as e:
                logger.error(f"Error downloading earnings for {symbol}: {str(e)}")
                continue
        
        # Save earnings data
        if earnings_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'earnings', 'yahoo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"earnings_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(earnings_data, f, indent=2, default=str)
            
            logger.info(f"Saved earnings for {len(earnings_data)} symbols")
    
    def download_news(self, symbols: List[str], limit: int = 10):
        """Download news headlines for multiple symbols"""
        logger.info(f"Starting Yahoo Finance news download for {len(symbols)} symbols")
        
        news_data = []
        
        for symbol in static_tqdm(symbols, desc="Downloading news"):
            try:
                news = self.get_news_data(symbol, limit)
                
                if news:
                    news_data.extend(news)
                
            except Exception as e:
                logger.error(f"Error downloading news for {symbol}: {str(e)}")
                continue
        
        # Save news data
        if news_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'news', 'yahoo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"news_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(news_data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(news_data)} news items")
    
    def download_options_data(self, symbols: List[str]):
        """Download options data for multiple symbols"""
        logger.info(f"Starting Yahoo Finance options download for {len(symbols)} symbols")
        
        options_data = []
        
        for symbol in static_tqdm(symbols, desc="Downloading Yahoo Finance options"):
            try:
                options = self.get_options_data(symbol)
                
                if options:
                    options_data.append(options)
                
            except Exception as e:
                logger.error(f"Error downloading options for {symbol}: {str(e)}")
                continue
        
        # Save options data
        if options_data:
            data_path = os.path.join(EQUITY_DATA_PATH, 'options', 'yahoo')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"options_{datetime.now().strftime('%Y%m%d')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(options_data, f, indent=2, default=str)
            
            logger.info(f"Saved options data for {len(options_data)} symbols")
    
    def download_bonds_data(self, symbols: List[str], start_date: datetime, end_date: datetime, frequency: str = 'daily'):
        """Download bonds data for multiple symbols"""
        logger.info(f"Starting Yahoo Finance bonds download for {len(symbols)} symbols")
        
        for symbol in static_tqdm(symbols, desc="Downloading Yahoo Finance bonds"):
            try:
                data = self.get_bonds_data(symbol, start_date, end_date, frequency)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'bonds', 'yahoo', frequency)
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