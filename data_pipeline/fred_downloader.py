"""
FRED (Federal Reserve Economic Data) downloader for Lean format
Supports economic indicators and macroeconomic data
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional
from tqdm import tqdm
import json
from fredapi import Fred

from config import (
    FRED_API_KEY, EQUITY_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_tradebar_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

class FREDDownloader:
    """Download economic data from FRED and convert to Lean format"""
    
    def __init__(self):
        if not FRED_API_KEY:
            raise ValueError("FRED API key not found. Please set FRED_API_KEY environment variable.")
        
        self.fred = Fred(api_key=FRED_API_KEY)
        self.rate_limit_delay = 0.5  # FRED is generous with rate limits
    
    def get_economic_data(self, series_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get economic data series from FRED"""
        try:
            # Get data from FRED
            data = self.fred.get_series(
                series_id,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d')
            )
            
            if data.empty:
                logger.warning(f"No data found for series {series_id}")
                return []
            
            # Convert to our format
            bars = []
            for timestamp, value in data.items():
                if pd.notna(value):
                    timestamp = timestamp.replace(tzinfo=pytz.timezone(LEAN_TIMEZONE_EQUITY))
                    
                    # Economic data doesn't have OHLCV, so we use value as close
                    bars.append({
                        'timestamp': timestamp,
                        'open': float(value),
                        'high': float(value),
                        'low': float(value),
                        'close': float(value),
                        'volume': 0  # Economic data doesn't have volume
                    })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return bars
            
        except Exception as e:
            logger.error(f"Error getting FRED data for {series_id}: {str(e)}")
            return []
    
    def get_series_info(self, series_id: str) -> Dict:
        """Get information about a FRED series"""
        try:
            info = self.fred.get_series_info(series_id)
            return info.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting series info for {series_id}: {str(e)}")
            return {}
    
    def search_series(self, search_text: str, limit: int = 10) -> List[Dict]:
        """Search for FRED series"""
        try:
            results = self.fred.search(search_text, limit=limit)
            return results.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error searching FRED series: {str(e)}")
            return []
    
    def download_economic_series(self, series_ids: List[str], start_date: datetime, end_date: datetime):
        """Download multiple economic data series"""
        logger.info(f"Starting FRED download for {len(series_ids)} series")
        
        for series_id in tqdm(series_ids, desc="Downloading FRED series"):
            try:
                data = self.get_economic_data(series_id, start_date, end_date)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        data_path = os.path.join(EQUITY_DATA_PATH, 'economic', 'fred', 'daily')
                        ensure_directory_exists(data_path)
                        
                        # Save data
                        output_path = os.path.join(data_path, f"{series_id.lower()}.zip")
                        csv_filename = f"{series_id.lower()}_daily_economic.csv"
                        
                        csv_content = create_lean_tradebar_csv(cleaned_data, series_id, cleaned_data[0]['timestamp'], 'daily')
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.info(f"Saved {len(csv_content)} data points for {series_id}")
                
            except Exception as e:
                logger.error(f"Error downloading {series_id}: {str(e)}")
                continue
    
    def get_common_economic_indicators(self) -> List[str]:
        """Get list of common economic indicators"""
        return [
            'GDP',          # Gross Domestic Product
            'GDPC1',        # Real GDP
            'CPIAUCSL',     # Consumer Price Index
            'UNRATE',       # Unemployment Rate
            'FEDFUNDS',     # Federal Funds Rate
            'DGS10',        # 10-Year Treasury Rate
            'DGS2',         # 2-Year Treasury Rate
            'DEXUSEU',      # USD/EUR Exchange Rate
            'DEXJPUS',      # Japan/US Exchange Rate
            'DEXUSUK',      # USD/GBP Exchange Rate
            'HOUST',        # Housing Starts
            'PAYEMS',       # Total Nonfarm Payrolls
            'INDPRO',       # Industrial Production Index
            'UMCSENT',      # Consumer Sentiment
            'VIXCLS',       # VIX Volatility Index
            'M2SL',         # M2 Money Supply
            'TB3MS',        # 3-Month Treasury Bill
            'MORTGAGE30US', # 30-Year Fixed Rate Mortgage
            'DCOILWTICO',   # Crude Oil Prices: West Texas Intermediate
            'GOLDAMGBD228NLBM'  # Gold Fixing Price
        ]