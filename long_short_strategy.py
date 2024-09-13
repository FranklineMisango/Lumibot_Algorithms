import os
import yfinance as yf
import threading
from dotenv import load_dotenv
load_dotenv()
import datetime
import alpaca_trade_api as tradeapi
import time
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import csv
from datetime import datetime as dt
from datetime import timedelta



API_KEY = os.environ.get('APCA_API_KEY_ID')
API_SECRET = os.environ.get('APCA_API_SECRET_KEY')
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"

EMAIL_USER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('YOUR_EMAIL_ADDRESS')

#Helper functions
def send_email(self):
        msg = MIMEMultipart()
        msg['From'] = 'Frankline & Co. HFT Day Trading Bot'
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = "Daily Trade Report"
        body = "Hello Trader, Attached is the Daily trade report from Day Trading."
        msg.attach(MIMEText(body, 'plain'))
        filename = "orders.csv"
        with open(filename, "w", newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Stock", "Quantity", "Side", "Status"])
            writer.writerows(self.orders_log)
        attachment = open(filename, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_RECEIVER, text)
        server.quit()
    
def mail_alert(mail_content, sleep_time):
    # The mail addresses and password
    sender_address = EMAIL_USER
    sender_pass = EMAIL_PASSWORD
    receiver_address = os.environ.get("YOUR_EMAIL_ADDRESS")

    # Setup MIME
    message = MIMEMultipart()
    message['From'] = 'Frankline & Co. HFT Day Trading Bot'
    message['To'] = receiver_address
    message['Subject'] = 'Frankline & Co. HFT Important Day Updates'
    
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


class LongShort:
    def __init__(self):

        #TODO - Add more stocks to the stockUniverse with diverse leverage

        self.alpaca = tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')
        
        stockUniverse =     ['AAPL', 'MSFT', 'NVDA', 'GOOG', 'META', 'ADBE', 'CSCO', 'CRM', 'INTC', 'ORCL' 
                            'JPM', 'BAC', 'GS', 'MS', 'C', 'WFC', 'AXP', 'BLK', 'SCHW', 'SPGI',
                            'JNJ', 'PFE', 'UNH', 'ABT', 'MRK', 'AMGN', 'TMO', 'GILD', 'CVS', 'MDT',
                            'AMZN', 'TSLA', 'NKE', 'MCD', 'HD', 'LOW', 'DIS', 'SBUX', 'NFLX', 'PCLN',
                            'GOOGL', 'META', 'DIS', 'NFLX', 'T', 'VZ', 'CMCSA', 'ATVI', 'TTWO', 'SNAP',
                            'BA', 'CAT', 'HON', 'GE', 'LMT', 'UPS', 'RTX', 'MMM', 'DE', 'NOC',
                            'PG', 'KO', 'PEP', 'WMT', 'COST', 'CAG', 'MDLZ', 'CL', 'SJM', 'GIS',
                            'XOM', 'CVX', 'BP', 'SLB', 'EOG', 'OXY', 'PXD', 'VLO', 'KMI', 'PSX',
                            'NEE', 'DUK', 'SO', 'D', 'EXC', 'SRE', 'AEP', 'ED', 'PCG', 'XEL',
                            'AMT', 'PLD', 'SPG', 'EQIX', 'O', 'VTR', 'DRE', 'AVB', 'PSA', 'WPC']
        
        self.allStocks = [[stock, 0] for stock in stockUniverse]
        self.long = []
        self.short = []
        self.qShort = None
        self.qLong = None
        self.adjustedQLong = None
        self.adjustedQShort = None
        self.blacklist = set()
        self.longAmount = 0
        self.shortAmount = 0
        self.timeToClose = None
        self.orders_log = []

    def run(self):
        self.log_portfolio("start")
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.cancel_order(order.id)
        print("Waiting for market to open...")
        tAMO = threading.Thread(target=self.awaitMarketOpen)
        tAMO.start()
        tAMO.join()
        print("Market opened.")
        mail_content = 'The bot started running on {} at {} UTC'.format(dt.now().strftime('%Y-%m-%d'), dt.now().strftime('%H:%M:%S'))
        mail_alert(mail_content, 0)

        while True:
            clock = self.alpaca.get_clock()
            closingTime = clock.next_close.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            self.timeToClose = closingTime - currTime
            if self.timeToClose < (60 * 15):
                print("Market closing soon. Closing positions.")
                positions = self.alpaca.list_positions()
                for position in positions:
                    orderSide = 'sell' if position.side == 'long' else 'buy'
                    qty = abs(int(float(position.qty)))
                    respSO = []
                    tSubmitOrder = threading.Thread(target=self.submitOrder, args=(qty, position.symbol, orderSide, respSO))
                    tSubmitOrder.start()
                    tSubmitOrder.join()
                print("Sleeping until market close (15 minutes).")
                time.sleep(60 * 15)
                self.log_portfolio("end")
                self.send_email()
            else:
                tRebalance = threading.Thread(target=self.rebalance)
                tRebalance.start()
                tRebalance.join()
                time.sleep(60)

    def awaitMarketOpen(self):
        isOpen = self.alpaca.get_clock().is_open
        while not isOpen:
            clock = self.alpaca.get_clock()
            openingTime = clock.next_open.replace(tzinfo=datetime.timezone.utc).timestamp()
            currTime = clock.timestamp.replace(tzinfo=datetime.timezone.utc).timestamp()
            timeToOpen = int((openingTime - currTime) / 60)
            print(f"{timeToOpen} minutes til market open.")
            time.sleep(60)
            isOpen = self.alpaca.get_clock().is_open

    def rebalance(self):
        tRerank = threading.Thread(target=self.rerank)
        tRerank.start()
        tRerank.join()
        orders = self.alpaca.list_orders(status="open")
        for order in orders:
            self.alpaca.cancel_order(order.id)
        print(f"We are taking a long position in: {self.long}")
        print(f"We are taking a short position in: {self.short}")
        executed = [[], []]
        positions = self.alpaca.list_positions()
        self.blacklist.clear()
        for position in positions:
            if self.long.count(position.symbol) == 0:
                if self.short.count(position.symbol) == 0:
                    side = "sell" if position.side == "long" else "buy"
                    respSO = []
                    tSO = threading.Thread(target=self.submitOrder, args=(abs(int(float(position.qty))), position.symbol, side, respSO))
                    tSO.start()
                    tSO.join()
                else:
                    if position.side == "long":
                        side = "sell"
                        respSO = []
                        tSO = threading.Thread(target=self.submitOrder, args=(int(float(position.qty)), position.symbol, side, respSO))
                        tSO.start()
                        tSO.join()
                    else:
                        if abs(int(float(position.qty))) == self.qShort:
                            pass
                        else:
                            diff = abs(int(float(position.qty))) - self.qShort
                            side = "buy" if diff > 0 else "sell"
                            respSO = []
                            tSO = threading.Thread(target=self.submitOrder, args=(abs(diff), position.symbol, side, respSO))
                            tSO.start()
                            tSO.join()
                        executed[1].append(position.symbol)
                        self.blacklist.add(position.symbol)
            else:
                if position.side == "short":
                    respSO = []
                    tSO = threading.Thread(target=self.submitOrder, args=(abs(int(float(position.qty))), position.symbol, "buy", respSO))
                    tSO.start()
                    tSO.join()
                else:
                    if int(float(position.qty)) == self.qLong:
                        pass
                    else:
                        diff = abs(int(float(position.qty))) - self.qLong
                        side = "sell" if diff > 0 else "buy"
                        respSO = []
                        tSO = threading.Thread(target=self.submitOrder, args=(abs(diff), position.symbol, side, respSO))
                        tSO.start()
                        tSO.join()
                    executed[0].append(position.symbol)
                    self.blacklist.add(position.symbol)
        respSendBOLong = []
        tSendBOLong = threading.Thread(target=self.sendBatchOrder, args=(self.qLong, self.long, "buy", respSendBOLong))
        tSendBOLong.start()
        tSendBOLong.join()
        if respSendBOLong:
            respSendBOLong[0][0] += executed[0]
            if len(respSendBOLong[0][1]) > 0:
                respGetTPLong = []
                thread = threading.Thread(target=self.getTotalPrice, args=(self.long, respGetTPLong))
                thread.start()
                thread.join()
                if respGetTPLong and len(respGetTPLong) > 0:
                    self.qLong = int(self.longAmount // respGetTPLong[0])
                else:
                    print("Error: respGetTPLong is empty or does not contain valid data.")
        respSendBOShort = []
        tSendBOShort = threading.Thread(target=self.sendBatchOrder, args=(self.qShort, self.short, "sell", respSendBOShort))
        tSendBOShort.start()
        tSendBOShort.join()
        if respSendBOShort:
            respSendBOShort[0][0] += executed[1]
            if len(respSendBOShort[0][1]) > 0:
                respGetTPShort = []
                thread = threading.Thread(target=self.getTotalPrice, args=(self.short, respGetTPShort))
                thread.start()
                thread.join()
                if respGetTPShort[0] > 0:
                    self.adjustedQShort = self.shortAmount // respGetTPShort[0]
                else:
                    self.adjustedQShort = -1
            else:
                self.adjustedQShort = -1
        if self.adjustedQLong is not None and self.adjustedQLong > -1:
            self.qLong = int(self.adjustedQLong - self.qLong)
            for stock in respSendBOLong[0][0]:
                respResendBOLong = []
                tResendBOLong = threading.Thread(target=self.submitOrder, args=(self.qLong, stock, "buy", respResendBOLong))
                tResendBOLong.start()
                tResendBOLong.join()
        if self.adjustedQShort is not None and self.adjustedQShort > -1:
            self.qShort = int(self.adjustedQShort - self.qShort)
            for stock in respSendBOShort[0][0]:
                respResendBOShort = []
                tResendBOShort = threading.Thread(target=self.submitOrder, args=(self.qShort, stock, "sell", respResendBOShort))
                tResendBOShort.start()
                tResendBOShort.join()

    def rerank(self):
        tRank = threading.Thread(target=self.rank)
        tRank.start()
        tRank.join()
        longShortAmount = len(self.allStocks) // 4
        self.long = []
        self.short = []
        for i, stockField in enumerate(self.allStocks):
            if i < longShortAmount:
                self.short.append(stockField[0])
            elif i > (len(self.allStocks) - 1 - longShortAmount):
                self.long.append(stockField[0])
        equity = int(float(self.alpaca.get_account().equity))
        self.shortAmount = equity * 0.45
        self.longAmount = equity - self.shortAmount
        respGetTPLong = []
        thread = threading.Thread(target=self.getTotalPrice, args=(self.long, respGetTPLong))
        thread.start()
        thread.join()
        respGetTPShort = []
        thread = threading.Thread(target=self.getTotalPrice, args=(self.short, respGetTPShort))
        thread.start()
        thread.join()
        self.qLong = int(self.longAmount // respGetTPLong[0])
        self.qShort = int(self.shortAmount // respGetTPShort[0])

    def getTotalPrice(self, stocks, resp):
        totalPrice = 0
        for stock in stocks:
            try:
                stock_data = yf.Ticker(stock)
                bars = stock_data.history(period='1d', interval='1m')
                if not bars.empty:
                    totalPrice += bars['Close'].iloc[-1]
                else:
                    print(f"No price data found for {stock}, skipping...")
            except Exception as e:
                print(f"Failed to download data for {stock}: {e}")
        resp.append(totalPrice)

    def sendBatchOrder(self, qty, stocks, side, resp):
        executed = []
        incomplete = []
        for stock in stocks:
            if self.blacklist.isdisjoint({stock}):
                respSO = []
                tSubmitOrder = threading.Thread(target=self.submitOrder, args=(qty, stock, side, respSO))
                tSubmitOrder.start()
                tSubmitOrder.join()
                if respSO and not respSO[0]:
                    incomplete.append(stock)
                else:
                    executed.append(stock)
                respSO.clear()
        resp.append([executed, incomplete])

    def submitOrder(self, qty, stock, side, resp):
        if qty is None:
            print("Quantity is None, cannot submit order.")
            resp.append(False)
            return
        if qty > 0:
            try:
                self.alpaca.submit_order(stock, qty, side, "market", "day")
                print(f"Market order of | {qty} {stock} {side} | completed.")
                self.orders_log.append([stock, qty, side, "completed"])
                resp.append(True)
            except Exception as e:
                print(f"Order of | {qty} {stock} {side} | did not go through: {e}")
                self.orders_log.append([stock, qty, side, f"failed: {e}"])
                resp.append(False)
        else:
            print(f"Quantity is 0, order of | {qty} {stock} {side} | not completed.")
            self.orders_log.append([stock, qty, side, "not completed: qty is 0"])
            resp.append(True)

    def log_portfolio(self, time_of_day):
        positions = self.alpaca.list_positions()
        with open(f'portfolio_{time_of_day}.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Symbol", "Qty", "Side"])
            for position in positions:
                writer.writerow([position.symbol, position.qty, position.side])

    
    def getPercentChanges(self):
        length = 10
        for i, stock in enumerate(self.allStocks):
            data = yf.download(stock[0], period='1d', interval='1m')
            if len(data) >= length:
                open_price = data.iloc[0]['Open']
                close_price = data.iloc[-1]['Close']
                self.allStocks[i][1] = (close_price - open_price) / open_price
            else:
                self.allStocks[i][1] = 0

    def rank(self):
        tGetPC = threading.Thread(target=self.getPercentChanges)
        tGetPC.start()
        tGetPC.join()
        self.allStocks.sort(key=lambda x: x[1])

# Run the LongShort class
ls = LongShort()
ls.run()