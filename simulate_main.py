import pandas as pd
import datetime
from datetime import datetime as dt, timedelta
from pytz import timezone
import time
from unittest.mock import MagicMock
import os
import glob
import yfinance as yf

# Mock Alpaca API
class MockAlpacaAPI:
    def __init__(self):
        self.cash = 1000000.0
        self.positions = []
        self.orders = []

    def get_account(self):
        return MagicMock(cash=self.cash, pattern_day_trader=False)

    def get_latest_trade(self, ticker):
        return MagicMock(price=100.0)  # Mock price

    def submit_order(self, symbol, qty, side, type, time_in_force):
        self.orders.append({
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': type,
            'time_in_force': time_in_force
        })
        if side == 'buy':
            self.positions.append({'symbol': symbol, 'qty': qty, 'avg_entry_price': 100.0})
            self.cash -= qty * 100.0  # Mock price
        elif side == 'sell':
            self.positions = [pos for pos in self.positions if pos['symbol'] != symbol]
            self.cash += qty * 100.0  # Mock price

    def get_position(self, symbol):
        for pos in self.positions:
            if pos['symbol'] == symbol:
                return MagicMock(qty=pos['qty'], unrealized_plpc=0.02)  # Mock 2% profit
        return MagicMock(qty=0, unrealized_plpc=0)

    def list_positions(self):
        return self.positions

    def get_clock(self):
        return MagicMock(is_open=True)

    def get_activities(self):
        return []

    def cancel_all_orders(self):
        self.orders = []

    def close_position(self, symbol):
        self.positions = [pos for pos in self.positions if pos['symbol'] != symbol]

# Replace the real Alpaca API with the mock API
api = MockAlpacaAPI()

# Load tickers
ticker_files = glob.glob('Test_tickers/*')
tickers = []
for file in ticker_files:
    with open(file, 'r') as f:
        tickers.extend(f.read().upper().split())

global TICKERS 
TICKERS = tickers

def get_minute_data(tickers):
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York')) - timedelta(days=1)
        start_time = end_time - timedelta(minutes=2)
        
        data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
        data.index = data.index.strftime('%Y-%m-%d %H:%M')
        data = data[~data.index.duplicated(keep='first')]
        
        data.to_csv(f'tick_data/{ticker}.csv')
        
    for ticker in tickers:
        save_min_data(ticker)

def get_past30_data(tickers):
    def save_30_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York')) - timedelta(days=1)
        start_time_1 = end_time - timedelta(minutes=30)
        end_time_1 = end_time - timedelta(minutes=28, seconds=30)
        start_time_2 = end_time - timedelta(minutes=1, seconds=30)
        
        data_1 = yf.download(ticker, start=start_time_1, end=end_time_1, interval='1m')
        data_2 = yf.download(ticker, start=start_time_2, end=end_time, interval='1m')
        
        data_1.index = data_1.index.strftime('%Y-%m-%d %H:%M')
        data_2.index = data_2.index.strftime('%Y-%m-%d %H:%M')
        
        data = pd.concat([data_1, data_2])
        data = data[~data.index.duplicated(keep='first')]
        
        data.to_csv(f'tick_data/{ticker}.csv')
        
    for ticker in tickers:
        save_30_data(ticker)

# Import the rest of the functions from main.py
from main import ROC, return_ROC_list, compare_ask_ltp, stock_to_buy, algo, buy, sell, check_rets, mail_alert

def main():
    est = timezone('US/Eastern')
    yesterday = dt.now(est) - timedelta(days=1)
    start_time = yesterday.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = yesterday.replace(hour=16, minute=0, second=0, microsecond=0)
    current_time = start_time

    while current_time <= end_time:
        if api.get_account().pattern_day_trader == True:
            mail_alert('Pattern day trading notification, bot is stopping now', 0)
            break

        tickers = TICKERS
        try:
            if os.path.isfile('FirstTrade.csv'):
                if float(api.get_account().cash) > 10:
                    get_minute_data(tickers)
                    stock_to_buy = algo(tickers)

                    if stock_to_buy == 0:
                        print('All ROCs are <= 0')
                        current_time += timedelta(minutes=1)
                        continue
                    elif stock_to_buy == -1:
                        print('All Ask < LTP')
                        current_time += timedelta(minutes=1)
                        continue
                    else:
                        num_stocks = len(api.list_positions())
                        curr_stocks = []

                        if num_stocks != 0:
                            for i in range(num_stocks):
                                curr_stocks.append(api.list_positions()[i])
                                
                            if stock_to_buy in curr_stocks:
                                if api.get_latest_trade(stock_to_buy).price > float(api.get_position(stock_to_buy).avg_entry_price):
                                    print('LTP for {} > Average Entry Price'.format(stock_to_buy))
                                    current_time += timedelta(minutes=1)
                                    continue

                    try:
                        if api.get_activities()[0].order_status == 'partially_filled':
                            api.cancel_all_orders()
                    except:
                        pass
                    mail_content = buy(stock_to_buy)
                    mail_alert(mail_content, 5)
                    current_time += timedelta(minutes=1)
                    continue

                else:
                    num_stocks = len(api.list_positions())
                    current_stocks = []
                    mail_content_list = []
                    
                    for pos in range(num_stocks):
                        current_stocks.append(api.list_positions()[pos]['symbol'])
                    
                    for stock in current_stocks:
                        mail_content = check_rets(stock)
                        mail_content_list.append(mail_content)
                    
                    if any(mail_content_list):
                        for mail in mail_content_list:
                            if mail != 0:
                                mail_alert(mail, 0)
                    else:
                        current_time += timedelta(minutes=1)
            else:
                if current_time.strftime('%H:%M:%S') < '10:00:00':
                    time_to_10 = int(str(dt.strptime('10:00:00', '%H:%M:%S') - dt.strptime(current_time.strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[1])*60 + int(str(dt.strptime('10:00:00', '%H:%M:%S') - dt.strptime(current_time.strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[2])
                    current_time += timedelta(seconds=time_to_10 - 20)

                get_past30_data(tickers)
                stock_to_buy = algo(tickers)

                if stock_to_buy == 0:
                    print('All ROCs are <= 0')
                    current_time += timedelta(minutes=1)
                    continue
                elif stock_to_buy == -1:
                    print('All Ask < LTP')
                    current_time += timedelta(minutes=1)
                    continue
                mail_content = buy(stock_to_buy)
                mail_alert(mail_content, 5)
                df = pd.DataFrame()
                df['First Stock'] = stock_to_buy
                df.to_csv('FirstTrade.csv')
        except Exception as e:
            print(e)
            current_time += timedelta(minutes=1)
            continue

        current_time += timedelta(minutes=1)

    mail_content = 'The bot stopped running on {} at {} UTC'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
    mail_alert(mail_content, 0)
            
if __name__ == '__main__':
    main()