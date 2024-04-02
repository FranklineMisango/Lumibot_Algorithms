from config import ALPACA_CONFIG
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
import webbrowser as web
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("agg") 
from Algorithms import buy_hold
from Algorithms import single_stock
from Algorithms import swing_high
from Algorithms import trend 

st.set_page_config(layout="wide")
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
        
            if option == "Buy & Hold (Strategy & Backtesting)":
                pass
            if option == "Swing High":
                pass
            if option == "ma-cross strategy":
                pass
            if option == "Trend":
                pass            
            if option == "GLD signal":
                pass   
            if option == "Portfolio earnings":
                pass
            if option == "single stock backtest":
                pass
                
                
main()
