import pandas as pd
import datetime
from datetime import datetime as dt
from pytz import timezone
import time
from dotenv import load_dotenv

import alpaca_trade_api as alpaca
import json

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datetime import timedelta
import os.path
import glob
import yfinance as yf

# Load API key

load_dotenv()

ALPACA_API_KEY = os.environ.get('ALPACAKEY')
ALPACA_API_SECRET_KEY =  os.environ.get('ALPACASECRETKEY')

api = alpaca.REST(ALPACA_API_KEY, ALPACA_API_SECRET_KEY, base_url='https://paper-api.alpaca.markets', api_version = 'v2')

# Load all tickers from the global folder
ticker_files = glob.glob('Test_tickers/*')
tickers = []
for file in ticker_files:
    with open(file, 'r') as f:
        file_tickers = f.read().upper().split()
        print(f"Tickers from {file}: {file_tickers}")  # Debug print
        tickers.extend(file_tickers)

print(f"All tickers: {tickers}")  # Debug print

global TICKERS 
TICKERS = tickers

# SMTP mail configuration
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

# Verify validity of 1 min data
def get_minute_data(tickers):
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
        start_time = end_time - timedelta(minutes=2)
        
        try:
            data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
            if data.empty:
                print(f"No price data found for {ticker}")
                return
            data.index = data.index.strftime('%Y-%m-%d %H:%M')
            data = data[~data.index.duplicated(keep='first')]
            data.to_csv(f'Test_tickers/{ticker}.csv')
        except Exception as e:
            print(f"Failed to download data for {ticker}: {e}")
        
    for ticker in tickers:
        save_min_data(ticker)

# Verify validity of 1 min data
def get_past30_data(tickers):
    def save_30_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
        start_time = end_time - timedelta(minutes=30)
        
        try:
            data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
            if data.empty:
                print(f"No price data found for {ticker}")
                return
            data.index = data.index.strftime('%Y-%m-%d %H:%M')
            data = data[~data.index.duplicated(keep='first')]
            data.to_csv(f'tick_data/{ticker}.csv')
        except Exception as e:
            print(f"Failed to download data for {ticker}: {e}")
        
    for ticker in tickers:
        save_30_data(ticker)


def ROC(close, timeframe):
    if timeframe == 30:
        rocs = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
    else:
        rocs = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
    return rocs * 1000

# Returns a list of most recent ROCs for all tickers
def return_ROC_list(tickers):
    ROC_tickers = []
    for i in range(len(tickers)):
        df = pd.read_csv('tick_data/{}.csv'.format(tickers[i]))
        df.set_index('Datetime', inplace=True)
        df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M')
        timeframe = (df.index[-1] - df.index[0]).seconds // 60  # Calculate timeframe in minutes
        ROC_tickers.append(ROC(df['Close'], timeframe))  # Use 'Close' price for ROC calculation
    return ROC_tickers

def compare_close_ltp(tickers):
    if len(tickers) != 0:
        buy_stock = ''
        ROCs = return_ROC_list(tickers)
        ROCs = [roc for roc in ROCs if roc is not None]  # Filter out None values
        if not ROCs:
            return 0
        max_ROC = max(ROCs)

        if max_ROC <= 0:
            return 0
        max_ROC_index = ROCs.index(max_ROC)
        buy_stock = tickers[max_ROC_index]

        df = pd.read_csv('tick_data/{}.csv'.format(buy_stock))
        df.set_index('Datetime', inplace=True)
        df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M')

        if df['Close'].iloc[-1] > df['Close'].iloc[-2]:
            return buy_stock
        else:
            tickers.pop(max_ROC_index)
            return compare_close_ltp(tickers)
    return -1

def stock_to_buy(tickers):
    return compare_close_ltp(tickers)

def execute_trade(ticker):
    # Placeholder for trade execution logic
    print(f"Placing buy order for {ticker}")

def buy(stock_to_buy: str):
    cashBalance = api.get_account().cash
    price_stock = api.get_latest_trade(str(stock_to_buy)).price
    targetPositionSize = ((float(cashBalance)) / (price_stock))  # Calculates required position size
    api.submit_order(str(stock_to_buy), targetPositionSize, "buy", "market", "day")  # Market order to open position

    mail_content = '''ALERT
    
    BUY Order Placed for {}: {} Shares at ${}'''.format(stock_to_buy, targetPositionSize, price_stock)
    
    if os.path.isfile('Orders.csv'):
        df = pd.read_csv('Orders.csv')
        df.drop(columns='Unnamed: 0', inplace=True)
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), stock_to_buy, 'buy',
                                 price_stock, targetPositionSize, targetPositionSize * price_stock, api.get_account().cash] 
    else:    
        df = pd.DataFrame()
        df[['Time', 'Ticker', 'Type', 'Price', 'Quantity', 'Total', 'Acc Balance']] = ''
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), stock_to_buy, 'buy',
                                 price_stock, targetPositionSize, targetPositionSize * price_stock, api.get_account().cash] 
    df.to_csv('Orders.csv')
    return mail_content

def sell(current_stock):
    # sells current_stock
    quantity = float(api.get_position(str(current_stock)).qty)    
    sell_price = api.get_latest_trade(str(current_stock)).price
    api.cancel_all_orders()  # cancels all pending (to be filled) orders 
    api.close_position(str(current_stock))  # sells current stock
    
    mail_content = '''ALERT
    
    SELL Order Placed for {}: {} Shares at ${}'''.format(current_stock, quantity, sell_price)
    
    if os.path.isfile('Orders.csv'):
        df = pd.read_csv('Orders.csv')
        df.drop(columns='Unnamed: 0', inplace=True)
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), current_stock, 'sell',
                                 sell_price, quantity, quantity * sell_price, api.get_account().cash] 
    else:    
        df = pd.DataFrame()
        df[['Time', 'Ticker', 'Type', 'Price', 'Quantity', 'Total', 'Acc Balance']] = ''
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), current_stock, 'sell',
                                 sell_price, quantity, quantity * sell_price, api.get_account().cash] 
    df.to_csv('Orders.csv')
    return mail_content

def check_rets(current_stock):
    # checks returns for stock in portfolio (api.get_positions()[0].symbol)
    returns = float(api.get_position(str(current_stock)).unrealized_plpc) * 100
    if returns >= 2:
        mail_content = sell(current_stock)
    else: 
        mail_content = 0              
    return mail_content

def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = EMAIL_ADDRESS
    sender_pass = EMAIL_PASSWORD
    receiver_address = 'franklinemisango@gmail.com'

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Frankline & Co. HFT Day Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'Frankline & Co. HFT Day Updates'
    
    # The body and the attachments for the mail
    message.attach(MIMEText(mail_content, 'plain'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
    session.starttls()  # enable security

    # login with mail_id and password
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    time.sleep(sleep_time)

def algo(tickers):
    ticker_to_buy = stock_to_buy(tickers)
    if ticker_to_buy and ticker_to_buy != -1:
        buy(ticker_to_buy)
    else:
        print("No suitable stock to buy")


def buy(stock_to_buy: str):
    
    cashBalance = api.get_account().cash
    price_stock = api.get_latest_trade(str(stock_to_buy)).price
    targetPositionSize = ((float(cashBalance)) / (price_stock)) # Calculates required position size
    api.submit_order(str(stock_to_buy), targetPositionSize, "buy", "market", "day") # Market order to open position    
    
    mail_content = '''ALERT
    
    BUY Order Placed for {}: {} Shares at ${}'''.format(stock_to_buy, targetPositionSize, price_stock)
    
    if os.path.isfile('Orders.csv'):
        df = pd.read_csv('Orders.csv')
        df.drop(columns= 'Unnamed: 0', inplace = True)
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), stock_to_buy, 'buy',
                                 price_stock, targetPositionSize, targetPositionSize*price_stock, api.get_account().cash] 
    else:    
        df = pd.DataFrame()
        df[['Time', 'Ticker', 'Type', 'Price', 'Quantity', 'Total', 'Acc Balance']] = ''
        df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), stock_to_buy, 'buy',
                                 price_stock, targetPositionSize, targetPositionSize*price_stock, api.get_account().cash] 
    df.to_csv('Orders.csv')
    return mail_content

def sell(current_stock):
    # sells current_stock
    quantity = float(api.get_position(str(current_stock)).qty)    
    sell_price = api.get_latest_trade(str(current_stock)).price
    api.cancel_all_orders() # cancels all pending (to be filled) orders 
    api.close_position(str(current_stock)) # sells current stock
    
    mail_content = '''ALERT

    SELL Order Placed for {}: {} Shares at ${}'''.format(current_stock, quantity, sell_price)
    
    df = pd.read_csv('Orders.csv')
    df.drop(columns= 'Unnamed: 0', inplace = True)
    df.loc[len(df.index)] = [((dt.now()).astimezone(timezone('America/New_York'))).strftime("%Y-%m-%d %H:%M:%S"), current_stock, 'sell', sell_price, quantity, quantity*sell_price, api.get_account().cash] 
    
#     with open('Orders.csv', 'a') as f:
#         df.to_csv(f, header=f.tell()==0)
    df.to_csv('Orders.csv')
    return mail_content

def check_rets(current_stock):
    # checks returns for stock in portfolio (api.get_positions()[0].symbol)
    returns = float(api.get_position(str(current_stock)).unrealized_plpc)*100
    if (returns >= 2):
        mail_content = sell(current_stock)
    else: 
        mail_content = 0              
    return mail_content

def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = EMAIL_ADDRESS
    sender_pass = EMAIL_PASSWORD
    receiver_address = 'franklinemisango@gmail.com'

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Frankline & Co. HFT Day Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'Frankline & Co. HFT Day Updates'
    
    # The body and the attachments for the mail
    message.attach(MIMEText(mail_content, 'plain'))

    # Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
    session.starttls()  # enable security

    # login with mail_id and password
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    time.sleep(sleep_time)

def main():
    
    if api.get_clock().is_open == True:
    # sends mail when bot starts running
        mail_content = 'The bot started running on {} at {} UTC'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
        mail_alert(mail_content, 0)

    while True:
        
        if api.get_account().pattern_day_trader == True:
            mail_alert('Pattern day trading notification, bot is stopping now', 0)
            break

        tickers = TICKERS
        try:
            print(api.get_clock())
            if api.get_clock().is_open == True:
                # check if we have made the first ever trade yet, if yes, timeframe = 1 min, else trade at 10:00 am
                if os.path.isfile('FirstTrade.csv'):
                    if float(api.get_account().cash) > 10:
                        get_minute_data(tickers)
                        stock_to_buy = algo(tickers)

                        if stock_to_buy == 0:
                            print('All ROCs are <= 0')
                            time.sleep(2)
                            continue
                        elif stock_to_buy == -1:
                            print('All Ask < LTP')
                            time.sleep(2)
                            continue
                        
                        # checks if stock_to_buy exists in positions
                        # doesn't buy if LTP for stock_to_buy > avg_entry_price
                        else:
                            num_stocks = len(api.list_positions())
                            curr_stocks = []

                            if num_stocks != 0:
                                for i in range(num_stocks):
                                    curr_stocks.append(api.list_positions()[i])
                                    
                                if stock_to_buy in curr_stocks:
                                    if api.get_latest_trade(stock_to_buy).price > float(api.get_position(stock_to_buy).avg_entry_price):
                                        print('LTP for {} > Average Entry Price'.format(stock_to_buy))
                                        time.sleep(2)
                                        continue

                        try:
                            if api.get_activities()[0].order_status == 'partially_filled':
                                api.cancel_all_orders()
                        except:
                            pass
                        mail_content = buy(stock_to_buy)
                        mail_alert(mail_content, 5)
                        df = pd.DataFrame()
                        df['First Stock'] = stock_to_buy
                        df.to_csv('FirstTrade.csv')
                else:
                    if ((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S') < '09:30:00':
                        current_time = dt.now().astimezone(timezone('America/New_York'))
                        current_time = current_time.strftime('%I:%M:%S %p')
                        print(f"Current time in NY: {current_time}")
                        print("The market is closed")
                        time_to_10 = int(str(dt.strptime('09:30:00', '%H:%M:%S') - dt.strptime(((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[1])*60 + int(str(dt.strptime('10:00:00', '%H:%M:%S') - dt.strptime(((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[2])
                        time.sleep(time_to_10 - 20)

                    get_past30_data(tickers)
                    stock_to_buy = algo(tickers)

                    if stock_to_buy == 0:
                        print('All ROCs are <= 0')
                        continue
                    elif stock_to_buy == -1:
                        print('All Ask < LTP')
                        continue
                    mail_content = buy(stock_to_buy)
                    mail_alert(mail_content, 5)
                    df = pd.DataFrame()
                    df['First Stock'] = stock_to_buy
                    df.to_csv('FirstTrade.csv')
            else:
                ny_time = dt.now().astimezone(timezone('America/New_York'))
                current_time = ny_time.strftime('%I:%M:%S %p')
                print(f"Current time in NY: {current_time}")
                print("Waiting for the market to open")
                time.sleep(300)
                if api.get_clock().is_open == True:
                    continue
                else:
                    mail_content = 'The market is closed now'
                    mail_alert(mail_content, 0)
                    break
        except Exception as e:
            print(e)
            continue

    if api.get_clock().is_open == False:
        # sends mail when bot starts running
        mail_content = 'The bot stopped running on {} at {} UTC'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
        mail_alert(mail_content, 0)
            
if __name__ == '__main__':
    main()