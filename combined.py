import matplotlib
matplotlib.use('agg')  # Set Matplotlib to use the 'agg' backend

from lumibot.brokers import Alpaca
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
from single_stock import single
import webbrowser as web
import yfinance as yf
from portfolio import portfolio

st.title("🦜🔗 Algorithmic Trading Framework using Lumibots API")
message = "This project is intended for users with an intermediate knowledge of Finance"
st.warning(message)

selected_app = st.sidebar.selectbox("Select App", ["Portfolio Analysis", "App 2", "App 3", "App 4", "App 5"])

# Run the selected app
if selected_app == "Portfolio Analysis":
    portfolio()
if selected_app =="App 2":
    single()