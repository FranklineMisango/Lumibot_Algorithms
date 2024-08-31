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

#load all tickers from the global folder
ticker_files = glob.glob('Tickers/*')
tickers = []
for file in ticker_files:
    with open(file, 'r') as f:
        tickers.extend(f.read().upper().split())

global TICKERS 
TICKERS = tickers

#smtp mail configuration
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def get_minute_data(tickers):
    def save_min_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
        start_time = end_time - timedelta(minutes=2)
        
        data = yf.download(ticker, start=start_time, end=end_time, interval='1m')
        data.index = data.index.strftime('%Y-%m-%d %H:%M')
        data = data[~data.index.duplicated(keep='first')]
        
        data.to_csv(f'tick_data/{ticker}.csv')
        
    for ticker in tickers:
        save_min_data(ticker)

def get_past30_data(tickers):
    def save_30_data(ticker):
        end_time = dt.now().astimezone(timezone('America/New_York'))
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


def ROC(ask, timeframe):
        if timeframe == 30:
            rocs = (ask[ask.shape[0] - 1] - ask[0])/(ask[0])
        else:
            rocs = (ask[ask.shape[0] - 1] - ask[ask.shape[0] -2])/(ask[ask.shape[0] - 2])
        return rocs*1000

# Returns a list of most recent ROCs for all tickers
def return_ROC_list(tickers, timeframe):
    ROC_tickers = []
    for i in range(len(tickers)):
        df = pd.read_csv('tick_data/{}.csv'.format(tickers[i]))
        df.set_index('timestamp', inplace= True)
        df.index = pd.to_datetime(df.index, format ='%Y-%m-%d').strftime('%Y-%m-%d %H:%M')
        ROC_tickers.append(ROC(df['ask_price'], timeframe)) # [-1] forlast value (latest)
    return ROC_tickers

# compared ASK vs LTP
def compare_ask_ltp(tickers, timeframe):
    
        if len(tickers) != 0:
            buy_stock = ''
            ROCs = return_ROC_list(tickers, timeframe)
            max_ROC = max(ROCs)

            if max_ROC <= 0:
                return 0
            max_ROC_index = ROCs.index(max_ROC)

            for i in range(len(tickers)):
                buy_stock_init = tickers[max_ROC_index]
                df = pd.read_csv('tick_data/{}.csv'.format(buy_stock_init))
                df.set_index('timestamp', inplace= True)
                df.index = pd.to_datetime(df.index, format ='%Y-%m-%d').strftime('%Y-%m-%d %H:%M')

                # list to keep track of number of ask_prices > price
                buy_condition = []
                ask_col = df.columns.get_loc('ask_price')
                price_col = df.columns.get_loc('price')
                for i in range(df.shape[0] - 2, df.shape[0]):
                    buy_condition.append(df.iloc[i, ask_col] > df.iloc[i,price_col])

                if buy_condition[-1] == True:
                    buy_stock = buy_stock_init
                    return buy_stock
                else:
                    tickers.pop(max_ROC_index)
                    ROCs.pop(max_ROC_index)
                    if(len(tickers)==0):
                        return -1
                    max_ROC = max(ROCs)
                    max_ROC_index =  ROCs.index(max_ROC)
        else: tickers = TICKERS

# returns which stock to buy
def stock_to_buy(tickers, timeframe):
        entry_buy = compare_ask_ltp(tickers, timeframe)
        return entry_buy

def algo(tickers):

    # Calculates ROC
    # Checks for stock with highest ROC and if ask_price > price
    # Returns ticker to buy
    if os.path.isfile('FirstTrade.csv'):
        timeframe = 1
    else:
        timeframe = 30
    stock = stock_to_buy(tickers, timeframe)
    return stock


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
    message['From'] = 'Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'HFT Second-Bot'
    
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
                        continue

                    else:
                        
                        num_stocks = len(api.list_positions())
                        current_stocks = []
                        mail_content_list = []
                        
                        for pos in range(num_stocks):
                            current_stocks.append(api.list_positions()[pos].symbol)
                        
                        for stock in current_stocks:
                            mail_content = check_rets(stock)
                            mail_content_list.append(mail_content)
                        
                        if any(mail_content_list):
                            for mail in mail_content_list:
                                if mail != 0:
                                    mail_alert(mail, 0)
                        else:
                            time.sleep(3)
                else:
                    if ((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S') < '10:00:00':
                        print("The market is not open yet")
                        time_to_10 = int(str(dt.strptime('10:00:00', '%H:%M:%S') - dt.strptime(((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[1])*60 + int(str(dt.strptime('10:00:00', '%H:%M:%S') - dt.strptime(((dt.now().astimezone(timezone('America/New_York')))).strftime('%H:%M:%S'), '%H:%M:%S')).split(':')[2])
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