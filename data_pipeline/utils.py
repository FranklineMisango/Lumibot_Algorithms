"""
Utility functions for data pipeline
"""

import os
import csv
import zipfile
import pandas as pd
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import logging
from tqdm import tqdm

from config import LEAN_PRICE_MULTIPLIER, LEAN_CRYPTO_PRICE_MULTIPLIER

# Configuration for progress bars
STATIC_PROGRESS_BARS = False  # Set to True for static progress bars

def static_tqdm(iterable, **kwargs):
    """Wrapper for tqdm that can be configured to be static"""
    if STATIC_PROGRESS_BARS:
        # Static progress bar - only shows start and end
        kwargs.update({
            'disable': False,
            'dynamic_ncols': False,
            'ncols': 80,
            'bar_format': '{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}'
        })
    return tqdm(iterable, **kwargs)

def setup_logging(log_level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data_pipeline.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_directory_exists(path: str):
    """Ensure directory exists, create if not"""
    os.makedirs(path, exist_ok=True)

def milliseconds_since_midnight(dt: datetime) -> int:
    """Convert datetime to milliseconds since midnight"""
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = dt - midnight
    return int(delta.total_seconds() * 1000)

def format_lean_date(date: datetime) -> str:
    """Format date for Lean file naming"""
    return date.strftime("%Y%m%d")

def create_lean_tradebar_csv(data: List[Dict], symbol: str, date: datetime, resolution: str, asset_type: str = 'equity') -> str:
    """Create Lean format CSV content for TradeBar data"""
    csv_content = []
    
    # Determine price multiplier based on asset type
    if asset_type in ['equity', 'index', 'future']:
        price_multiplier = LEAN_PRICE_MULTIPLIER  # 10000 for deci-cents
    else:  # crypto, cfd, etc.
        price_multiplier = LEAN_CRYPTO_PRICE_MULTIPLIER  # 1 for actual prices
    
    for bar in data:
        if resolution == 'daily':
            # For daily data, use full date format YYYYMMDD HH:MM
            time_str = bar['timestamp'].strftime("%Y%m%d %H:%M")
        else:
            # For intraday data, use milliseconds since midnight
            time_str = milliseconds_since_midnight(bar['timestamp'])
        
        # Format: Time, Open, High, Low, Close, Volume
        if price_multiplier == 1:
            # Keep as float for crypto/actual prices
            row = [
                time_str,
                float(bar['open']),
                float(bar['high']),
                float(bar['low']),
                float(bar['close']),
                int(bar['volume'])
            ]
        else:
            # Convert to integer for equity/scaled prices
            row = [
                time_str,
                int(bar['open'] * price_multiplier),
                int(bar['high'] * price_multiplier),
                int(bar['low'] * price_multiplier),
                int(bar['close'] * price_multiplier),
                int(bar['volume'])
            ]
        csv_content.append(row)
    
    return csv_content

def create_lean_crypto_csv(data: List[Dict], symbol: str, date: datetime, resolution: str) -> str:
    """Create Lean format CSV content for Crypto data"""
    csv_content = []
    
    for bar in data:
        # For crypto data, LEAN expects full datetime format for all resolutions
        # This avoids the milliseconds parsing issue in LEAN's crypto parser
        time_str = bar['timestamp'].strftime("%Y%m%d %H:%M")
        
        # Format: Time, Open, High, Low, Close, Volume
        row = [
            time_str,
            float(bar['open']),  # Keep actual prices for crypto
            float(bar['high']),
            float(bar['low']),
            float(bar['close']),
            float(bar['volume'])
        ]
        csv_content.append(row)
    
    return csv_content

def create_lean_quotebar_csv(data: List[Dict], symbol: str, date: datetime, resolution: str, asset_type: str = 'forex') -> str:
    """Create Lean format CSV content for QuoteBar data"""
    csv_content = []
    
    # Determine price multiplier based on asset type
    if asset_type in ['forex']:
        price_multiplier = LEAN_PRICE_MULTIPLIER  # 10000 for forex precision
    else:
        price_multiplier = LEAN_CRYPTO_PRICE_MULTIPLIER  # 1 for actual prices
    
    for bar in data:
        if resolution == 'daily':
            # For daily data, use full date format YYYYMMDD HH:MM
            time_str = bar['timestamp'].strftime("%Y%m%d %H:%M")
        else:
            # For intraday data, use milliseconds since midnight
            time_str = milliseconds_since_midnight(bar['timestamp'])
        
        # For quotes, treat each snapshot as OHLC = the price
        if price_multiplier == 1:
            # Keep as float for actual prices
            bid_price = float(bar['bid_price'])
            ask_price = float(bar['ask_price'])
        else:
            # Convert to integer for scaled prices
            bid_price = int(bar['bid_price'] * price_multiplier)
            ask_price = int(bar['ask_price'] * price_multiplier)
        
        # Format: Time, BidOpen, BidHigh, BidLow, BidClose, AskOpen, AskHigh, AskLow, AskClose
        row = [
            time_str,
            bid_price, bid_price, bid_price, bid_price,  # Bid OHLC
            ask_price, ask_price, ask_price, ask_price   # Ask OHLC
        ]
        csv_content.append(row)
    
    return csv_content

def write_lean_zip_file(csv_content: List[List], output_path: str, csv_filename: str):
    """Write CSV content to a zip file in Lean format"""
    ensure_directory_exists(os.path.dirname(output_path))
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create CSV content string
        csv_string = ""
        for row in csv_content:
            csv_string += ",".join(str(item) for item in row) + "\n"
        
        # Add CSV to zip file
        zip_file.writestr(csv_filename, csv_string)

def validate_symbol(symbol: str, asset_type: str) -> bool:
    """Validate symbol format"""
    if asset_type == 'equity':
        return symbol.isalpha() and len(symbol) <= 10
    elif asset_type == 'crypto':
        return len(symbol) > 6 and symbol.endswith('USDT')
    return False

def get_trading_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """Get list of trading days between start and end date"""
    trading_days = []
    current_date = start_date
    
    while current_date <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:
            trading_days.append(current_date)
        current_date += timedelta(days=1)
    
    return trading_days

def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> datetime:
    """Convert datetime from one timezone to another"""
    from_timezone = pytz.timezone(from_tz)
    to_timezone = pytz.timezone(to_tz)
    
    # Localize the datetime to the source timezone
    localized_dt = from_timezone.localize(dt) if dt.tzinfo is None else dt
    
    # Convert to target timezone
    converted_dt = localized_dt.astimezone(to_timezone)
    
    return converted_dt

class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def validate_ohlcv_data(data: Dict) -> bool:
        """Validate OHLCV data structure"""
        required_fields = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate OHLC logic
        if not (data['low'] <= data['open'] <= data['high'] and 
                data['low'] <= data['close'] <= data['high']):
            return False
        
        # Validate volume is non-negative
        if data['volume'] < 0:
            return False
        
        return True
    
    @staticmethod
    def clean_ohlcv_data(data: List[Dict]) -> List[Dict]:
        """Clean and validate OHLCV data"""
        cleaned_data = []
        
        for bar in data:
            if DataValidator.validate_ohlcv_data(bar):
                cleaned_data.append(bar)
        
        return cleaned_data
    
    @staticmethod
    def validate_quote_data(data: Dict) -> bool:
        """Validate quote data structure"""
        required_fields = ['bid_price', 'bid_size', 'ask_price', 'ask_size', 'timestamp']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate prices are positive
        if data['bid_price'] <= 0 or data['ask_price'] <= 0:
            return False
        
        # Validate sizes are non-negative
        if data['bid_size'] < 0 or data['ask_size'] < 0:
            return False
        
        return True
    
    @staticmethod
    def clean_quote_data(data: List[Dict]) -> List[Dict]:
        """Clean and validate quote data"""
        cleaned_data = []
        
        for quote in data:
            if DataValidator.validate_quote_data(quote):
                cleaned_data.append(quote)
        
        return cleaned_data

def format_symbol_for_lean(symbol: str, asset_type: str) -> str:
    """Format symbol for Lean compatibility"""
    # Remove special characters and convert to uppercase
    symbol = ''.join(c for c in symbol if c.isalnum() or c in ['_', '-']).upper()
    
    # Add asset type suffix if not already present
    if asset_type == 'equity' and not symbol.endswith('_EQUITY'):
        symbol += '_EQUITY'
    elif asset_type == 'forex' and not symbol.endswith('_FOREX'):
        symbol += '_FOREX'
    elif asset_type == 'crypto' and not symbol.endswith('_CRYPTO'):
        symbol += '_CRYPTO'
    elif asset_type == 'index' and not symbol.endswith('_INDEX'):
        symbol += '_INDEX'
    elif asset_type == 'cfd' and not symbol.endswith('_CFD'):
        symbol += '_CFD'
    
    return symbol

def convert_to_lean_format(df: pd.DataFrame, symbol: str, asset_type: str) -> List[List]:
    """Convert pandas DataFrame to Lean format CSV content"""
    lean_data = []
    
    for index, row in df.iterrows():
        try:
            # Convert timestamp to Lean format
            if isinstance(index, pd.Timestamp):
                timestamp = index.to_pydatetime()
            else:
                timestamp = pd.to_datetime(index).to_pydatetime()
            
            # Format timestamp based on asset type
            if asset_type in ['equity', 'index', 'cfd']:
                # Daily format: YYYYMMDD HH:MM
                time_str = timestamp.strftime("%Y%m%d %H:%M")
            else:
                # Intraday format: milliseconds since midnight
                time_str = str(milliseconds_since_midnight(timestamp))
            
            # Get OHLCV values
            open_price = float(row['Open'])
            high_price = float(row['High'])
            low_price = float(row['Low'])
            close_price = float(row['Close'])
            volume = int(row['Volume'])
            
            # Convert prices to Lean format (deci-cents for equity, actual prices for others)
            if asset_type in ['equity', 'index']:
                multiplier = LEAN_PRICE_MULTIPLIER
            else:
                multiplier = 1
            
            lean_row = [
                time_str,
                int(open_price * multiplier),
                int(high_price * multiplier),
                int(low_price * multiplier),
                int(close_price * multiplier),
                volume
            ]
            
            lean_data.append(lean_row)
            
        except Exception as e:
            logger.warning(f"Error converting row for {symbol}: {str(e)}")
            continue
    
    return lean_data

def create_zip_file(lean_data: List[List], zip_path: str, symbol: str):
    """Create a zip file containing Lean format CSV data"""
    ensure_directory_exists(os.path.dirname(zip_path))
    
    # Create CSV content
    csv_content = "Time,Open,High,Low,Close,Volume\n"
    for row in lean_data:
        csv_content += ",".join(str(item) for item in row) + "\n"
    
    # Create CSV filename
    csv_filename = f"{symbol.lower()}_trade.csv"
    
    # Create zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(csv_filename, csv_content)
