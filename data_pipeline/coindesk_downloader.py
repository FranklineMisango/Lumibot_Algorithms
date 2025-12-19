"""
CoinDesk data downloader for Lean format
Supports crypto data and crypto news
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
    CRYPTO_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

class CoinDeskDownloader:
    """Download crypto data and news from CoinDesk"""
    
    def __init__(self):
        self.base_url = "https://api.coindesk.com/v1"
        self.rate_limit_delay = 1  # Be respectful
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_bitcoin_price_index(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get Bitcoin Price Index from CoinDesk"""
        try:
            url = f"{self.base_url}/bpi/historical/close.json"
            
            params = {}
            if start_date:
                params['start'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                params['end'] = end_date.strftime('%Y-%m-%d')
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if 'bpi' not in data:
                logger.warning("No BPI data found")
                return []
            
            # Convert to our format
            bars = []
            for date_str, price in data['bpi'].items():
                timestamp = datetime.strptime(date_str, '%Y-%m-%d')
                timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                
                bars.append({
                    'timestamp': timestamp,
                    'open': float(price),
                    'high': float(price),
                    'low': float(price),
                    'close': float(price),
                    'volume': 0  # CoinDesk BPI doesn't provide volume
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting Bitcoin price index: {str(e)}")
            return []
    
    def get_current_price(self, currency: str = 'USD') -> Dict:
        """Get current Bitcoin price"""
        try:
            url = f"{self.base_url}/bpi/currentprice/{currency}.json"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            if 'bpi' not in data or currency.upper() not in data['bpi']:
                logger.warning(f"No current price found for {currency}")
                return {}
            
            price_data = data['bpi'][currency.upper()]
            
            return {
                'symbol': f'BTC-{currency.upper()}',
                'price': price_data['rate_float'],
                'currency': currency.upper(),
                'last_updated': data['time']['updated']
            }
            
        except Exception as e:
            logger.error(f"Error getting current price: {str(e)}")
            return {}
    
    def get_crypto_news(self, limit: int = 10) -> List[Dict]:
        """Get crypto news from CoinDesk (this would require web scraping as CoinDesk doesn't have a public news API)"""
        try:
            # CoinDesk doesn't provide a public news API, so we'd need to scrape their website
            # For demonstration, we'll return mock data structure
            
            news_url = "https://www.coindesk.com"
            
            # This would require web scraping with BeautifulSoup
            # For now, return empty list as actual implementation would be complex
            
            logger.warning("CoinDesk news API not fully implemented - would require web scraping")
            return []
            
        except Exception as e:
            logger.error(f"Error getting crypto news: {str(e)}")
            return []
    
    def download_bitcoin_data(self, start_date: datetime, end_date: datetime):
        """Download Bitcoin price index data"""
        logger.info("Starting CoinDesk Bitcoin download")
        
        try:
            data = self.get_bitcoin_price_index(start_date, end_date)
            
            if data:
                # Clean and validate data
                cleaned_data = DataValidator.clean_ohlcv_data(data)
                
                if cleaned_data:
                    # Create directory structure
                    data_path = os.path.join(CRYPTO_DATA_PATH, 'coindesk', 'daily')
                    ensure_directory_exists(data_path)
                    
                    # Save data
                    output_path = os.path.join(data_path, "btc_usd.zip")
                    csv_filename = "btc_usd_daily_trade.csv"
                    
                    csv_content = create_lean_tradebar_csv(cleaned_data, 'BTC-USD', cleaned_data[0]['timestamp'], 'daily')
                    
                    if csv_content:
                        write_lean_zip_file(csv_content, output_path, csv_filename)
                        logger.info(f"Saved {len(csv_content)} Bitcoin price points")
            
        except Exception as e:
            logger.error(f"Error downloading Bitcoin data: {str(e)}")
    
    def download_current_prices(self, currencies: List[str] = ['USD', 'EUR', 'GBP']):
        """Download current Bitcoin prices in multiple currencies"""
        logger.info("Getting current Bitcoin prices")
        
        current_prices = []
        
        for currency in currencies:
            try:
                price_data = self.get_current_price(currency)
                if price_data:
                    current_prices.append(price_data)
                    
            except Exception as e:
                logger.error(f"Error getting price for {currency}: {str(e)}")
                continue
        
        # Save current prices
        if current_prices:
            data_path = os.path.join(CRYPTO_DATA_PATH, 'coindesk', 'current')
            ensure_directory_exists(data_path)
            
            output_path = os.path.join(data_path, f"current_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(output_path, 'w') as f:
                json.dump(current_prices, f, indent=2, default=str)
            
            logger.info(f"Saved current prices for {len(current_prices)} currencies")