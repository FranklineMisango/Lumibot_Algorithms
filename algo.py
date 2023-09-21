from config import ALPACAKEY, ALPACASECRETKEY, APCAAPIBASEURL
from lumibot.brokers import Alpaca
import alpaca as tradeapi
from lumibot.backtesting import YahooDataBacktesting
from lumibot.traders import Trader 
import streamlit as st
from lumibot.strategies import Strategy
import datetime as dt
from dateutil.relativedelta import relativedelta
import os
from datetime import datetime
import pandas as pd
import pandas_datareader as pdr
import numpy as np
import quantstats as qs
import webbrowser as web
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("agg")  


st.title("🦜🔗 Algorithmic Trading Framework using Lumibots API")
message =  "This project is intended for users with an intermediate knowledge of Finance"
st.warning(message)


def main():
    global stocks_all
    global ticker_input
    global quantities_input
    # Retrieve the tickers and quantities from the app state or initialize as empty lists
    if 'tickers' not in st.session_state:
        st.session_state.tickers = []
    if 'quantities' not in st.session_state:
        st.session_state.quantities = []

    # Create a form for the ticker and quantity input
    with st.form(key='ticker_form'):
        col1, col2, col3 = st.columns([4, 4, 2])  # Adjust column widths as needed
        with col1:
            ticker_input = st.text_input("Enter a stock ticker:", key='ticker_input')
        with col2:
            quantities_input = st.number_input("Enter the stock quantity")
        with col3:
            add_ticker_button = st.form_submit_button(label="Add +")
            delete_quantity_button = st.form_submit_button(label="Delete -")
        
        reset_everything_button = st.form_submit_button(label = "Reset")

        # Check if the ticker is already in the list
        is_duplicate = ticker_input in st.session_state.tickers

        # Add the entered ticker and quantity to the lists when the user clicks the "+" button
        if add_ticker_button and not is_duplicate:
            st.session_state.tickers.append(ticker_input)
            st.session_state.quantities.append(quantities_input)
        
        if delete_quantity_button:
            if ticker_input in st.session_state.tickers:

                st.session_state.tickers.remove(ticker_input)
                st.session_state.quantities.pop(int(quantities_input))

        if reset_everything_button:
            if reset_everything_button:
                st.session_state.tickers = []
                st.session_state.quantities = []


        # Display the current list of tickers and quantities as key-value pairs
        st.markdown("**Current ticker(s) and quantity**")
        for ticker, quantity in zip(st.session_state.tickers, st.session_state.quantities):
            st.write(f"{ticker}: {quantity}")

def time():
        global start_date
        global end_date
        global portfolio_size
        # Add the Start Date and End Date
        with st.form(key='start_end_dates'):
            st.header("Backtesting Strategies using Lumibots API")
            st.warning("Read the documentation to understand what each platform does technically")
            portfolio_size = st.number_input("Enter the value of your portfolio in ($):")
            try:
                val = float(portfolio_size)
            except ValueError:
                print("That's not a number! \n Try again:")
                portfolio_size = input("Enter the value of your portfolio in ($):")
            option = st.radio(
                                'Please select the Strategy/services you would like to use (more under development);', (
                                'Buy & Hold (Strategy & Backtesting)' , "Swing High(Strategy)", "Trend", "GLD signal", "Portfolio earnings", "single stock earnings"
                                )
                            )
            col1, col2 = st.columns([2, 2])
            with col1:
                start_date = st.date_input("Start date:")
            with col2:
                end_date = st.date_input("End Date:")

            from datetime import datetime

            if start_date and end_date and st.form_submit_button("Submit"):
                if option == "Buy & Hold (Strategy & Backtesting)":
                    class BuyHold(Strategy):

                        def initialize(self):
                            self.sleeptime = "1D"

                        def on_trading_iteration(self):
                            if self.first_iteration:
                                stocks_and_quantities = [
                                    {"symbol": ticker_input, "quantity": quantities_input},
                                ]
                                for stock_info in stocks_and_quantities:
                                    symbol = stock_info["symbol"]
                                    quantity = stock_info["quantity"]
                                    price = self.get_last_price(symbol)
                                    cost = price * quantity
                                    self.cash = portfolio_size
                                    if self.cash >= cost:
                                        order = self.create_order(symbol, quantity, "buy")
                                        self.submit_order(order)
                    trade = False
                    if trade:
                        broker = Alpaca(ALPACAKEY)
                        strategy = BuyHold(broker=broker)
                        trader = Trader()
                        trader.add_strategy(strategy)
                        trader.run_all()
                    else:
                        start = datetime(start_date.year, start_date.month, start_date.day)  # Convert start_date to datetime
                        end = datetime(end_date.year, end_date.month, end_date.day)  # Convert end_date to datetime
                        BuyHold.backtest(
                            YahooDataBacktesting,
                            start,
                            end
                        )

                if option == "Swing High":
                    class SwingHigh(Strategy):
                        data = {}  # Dictionary to store last price data for each symbol
                        order_numbers = {}  # Dictionary to store order numbers for each symbol
                        shares_per_ticker = {}  # Dictionary to specify the number of shares per ticker

                        def initialize(self):
                            self.symbols = ticker_input# Add other symbols as needed
                            self.shares_per_ticker = {ticker_input: quantities_input}   # Specify the number of shares for each symbol
                            self.sleeptime = "10S"
                        def on_trading_iteration(self):
                            for symbol in self.symbols:
                                if symbol not in self.data:
                                    self.data[symbol] = []

                                entry_price = self.get_last_price(symbol)
                                self.log_message(f"Position for {symbol}: {self.get_position(symbol)}")
                                self.data[symbol].append(entry_price)

                                if len(self.data[symbol]) > 3:
                                    temp = self.data[symbol][-3:]
                                    if temp[-1] > temp[1] > temp[0]:
                                        self.log_message(f"Last 3 prints for {symbol}: {temp}")
                                        order = self.create_order(symbol, quantity=self.shares_per_ticker[symbol], side="buy")
                                        self.submit_order(order)
                                        if symbol not in self.order_numbers:
                                            self.order_numbers[symbol] = 0
                                        self.order_numbers[symbol] += 1
                                        if self.order_numbers[symbol] == 1:
                                            self.log_message(f"Entry price for {symbol}: {temp[-1]}")
                                            entry_price = temp[-1]  # filled price
                                    if self.get_position(symbol) and self.data[symbol][-1] < entry_price * 0.995:
                                        self.sell_all(symbol)
                                        self.order_numbers[symbol] = 0
                                    elif self.get_position(symbol) and self.data[symbol][-1] >= entry_price * 1.015:
                                        self.sell_all(symbol)
                                        self.order_numbers[symbol] = 0

                        def before_market_closes(self):
                            for symbol in self.symbols:
                                self.sell_all(symbol)

                if option == "ma-cross strategy":
                    pass
                if option == "Trend":
                    st.success("Trend analysis for the stock ticker")
                    period = (end_date - start_date).days
                    period_year = f'{period}d'
                    st.write(period_year)

                    portfolio = qs.utils.download_returns(ticker_input, period=period_year)
                    # print(portfolio.head())

                    # print("Available stats:")
                    # print([fx for fx in dir(qs.stats) if fx[0] != "_"])

                    st.write(f"Sharpe: {qs.stats.sharpe(portfolio)}")
                    st.write(f"Best Day: {qs.stats.best(portfolio)}")
                    st.write(f"Best Day: {qs.stats.best(portfolio, aggregate='M')}")

                    qs.extend_pandas()

                    st.write(portfolio.cagr())
                    st.write(portfolio.max_drawdown())
                    st.write(portfolio.monthly_returns())

                if option == "GLD signal":
                    #TODO - Fix the time slices to match user input ; relative duration 
                    gld = pd.DataFrame(yf.download(ticker_input, start_date)['Close'])
                    gld['9-day'] = gld['Close'].rolling(9).mean()
                    gld['21-day'] = gld['Close'].rolling(21).mean()
                    gld['Signal'] = np.where(np.logical_and(gld['9-day'] > gld['21-day'],
                                            gld['9-day'].shift(1) < gld['21-day'].shift(1)),
                                            "BUY", None)
                    gld['Signal'] = np.where(np.logical_and(gld['9-day'] < gld['21-day'],
                                            gld['9-day'].shift(1) > gld['21-day'].shift(1)),
                                            "SELL", gld['Signal'])

                    def signal(df, start=start_date, end=end_date):
                        df = pd.DataFrame(yf.download(ticker_input, start, end)['Close'])
                        df['9-day'] = df['Close'].rolling(9).mean()
                        df['21-day'] = df['Close'].rolling(21).mean()
                        df['Signal'] = np.where(np.logical_and(df['9-day'] > df['21-day'],
                                                df['9-day'].shift(1) < df['21-day'].shift(1)),
                                                "BUY", None)
                        df['Signal'] = np.where(np.logical_and(df['9-day'] < df['21-day'],
                                                df['9-day'].shift(1) > df['21-day'].shift(1)),
                                                "SELL", df['Signal'])
                        return df, df.iloc[-1].Signal

                    st.write(gld)
                    st.write("-" * 10)
                    st.write(gld.iloc[-1].Signal)
                    st.success("Saving the GLD csv")
                    gld.to_csv('gld_signal.csv')
                    data, sig = signal(gld)
                    st.write(data)
                    st.write(sig)
                
                if option == "Portfolio earnings":
                    qs.extend_pandas()

                    index = {"SPY": 1.3, "AGG": -.3}
                    portfolio = qs.utils.make_index(index, period='3y')
                    portfolio.index = portfolio.index.tz_localize(None)
                    
                    # Create the Matplotlib figure and axis
                    fig, ax = plt.subplots()
                    portfolio.plot_earnings(start_balance=portfolio_size)  # Use ax=ax to specify the axis

                    # Display the Matplotlib figure using st.pyplot()
                    st.pyplot(fig)
                    
                
                if option == "single stock backtest":
                    pass



main()
time()
