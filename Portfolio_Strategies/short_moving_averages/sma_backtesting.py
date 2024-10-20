import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from langchain_core.tools import tool
import datetime as dt

#High Level helper functions for the SMA strategy : Dont modify
def get_stock_data(stock, start, end):
        """
        Fetches stock data from Yahoo Finance.
        """
        return yf.download(stock, start, end)

# Trading statistics calculation
def calculate_trading_statistics(df, buy_sell_logic, additional_logic=None):
    """
    Calculates trading statistics based on buy/sell logic.
    """
    position = 0
    percentChange = []
    buyP = sellP = 0  # Initialize buyP and sellP
    for i in df.index:
        close = df.loc[i, "Adj Close"]
        if buy_sell_logic(df, i, position):
            position = 0 if position == 1 else 1
            buyP = close if position == 1 else buyP
            sellP = close if position == 0 else sellP
            if position == 0:
                perc = (sellP / buyP - 1) * 100
                percentChange.append(perc)
        if additional_logic: additional_logic(df, i)
    return calculate_statistics_from_percent_change(percentChange)

# Compute statistics from percent change
def calculate_statistics_from_percent_change(percentChange):
    """
    Computes statistics from percentage change in stock prices.
    """
    gains = sum(p for p in percentChange if p > 0)
    losses = sum(p for p in percentChange if p < 0)
    numGains = sum(1 for p in percentChange if p > 0)
    numLosses = sum(1 for p in percentChange if p < 0)
    totReturn = round(np.prod([((p / 100) + 1) for p in percentChange]) * 100 - 100, 2)
    avgGain = gains / numGains if numGains > 0 else 0
    avgLoss = losses / numLosses if numLosses > 0 else 0
    maxReturn = max(percentChange) if numGains > 0 else 0
    maxLoss = min(percentChange) if numLosses > 0 else 0
    ratioRR = -avgGain / avgLoss if numLosses > 0 else "inf"
    batting_avg = numGains / (numGains + numLosses) if numGains + numLosses > 0 else 0
    return {
        "total_return": totReturn,
        "avg_gain": avgGain,
        "avg_loss": avgLoss,
        "max_return": maxReturn,
        "max_loss": maxLoss,
        "gain_loss_ratio": ratioRR,
        "num_trades": numGains + numLosses,
        "batting_avg": batting_avg
    }

# SMA strategy logic
def sma_strategy_logic(df, i, position):
    """
    Logic for Simple Moving Average (SMA) trading strategy.
    """
    SMA_short, SMA_long = df["SMA_20"], df["SMA_50"]
    return (SMA_short[i] > SMA_long[i] and position == 0) or (SMA_short[i] < SMA_long[i] and position == 1)

@tool
def tool_sma_strategy(ticker:str, years:int, start_date:dt.time, end_date:dt.time):
    ''' This program allows you to backtest the Simple Moving Average (SMA) strategy. '''
    stock = ticker
    num_of_years = years
    start = start_date
    end = end_date
    df = get_stock_data(stock, start, end)

    # Implementing SMA strategy
    df["SMA_20"] = df["Adj Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Adj Close"].rolling(window=50).mean()
    sma_stats = calculate_trading_statistics(df, sma_strategy_logic)
    st.write("Simple Moving Average Strategy Stats:", sma_stats)

def norm_sma_strategy(ticker, years, start_date, end_date):
    ''' This program allows you to backtest the Simple Moving Average (SMA) strategy. '''
    stock = ticker
    num_of_years = years
    start = start_date
    end = end_date
    df = get_stock_data(stock, start, end)

    # Implementing SMA strategy
    df["SMA_20"] = df["Adj Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Adj Close"].rolling(window=50).mean()
    sma_stats = calculate_trading_statistics(df, sma_strategy_logic)
    st.write("Simple Moving Average Strategy Stats:", sma_stats)