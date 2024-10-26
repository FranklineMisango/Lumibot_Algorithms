import matplotlib.pyplot as plt 
import numpy as np
import plotly.graph_objects as go
from datetime import datetime as dt
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio
from alpaca_trade_api.rest import REST, TimeFrame
import datetime as dt
from requests.exceptions import HTTPError
from lumibot.brokers import Alpaca
from lumibot.strategies import Strategy
from lumibot.traders import Trader
import yfinance as yf
from datetime import datetime
from lumibot.backtesting import YahooDataBacktesting
import os
import alpaca_trade_api as tradeapi
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import csv
import time
import threading
from datetime import datetime as dt
from alpaca.trading.client import TradingClient
import schedule
import matplotlib.pyplot as plt
import datetime
import pytz
from datetime import timedelta
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import AssetStatus,OrderSide, OrderType, TimeInForce, OrderClass, QueryOrderStatus
import pandas as pd
import streamlit as st
import scipy.optimize as sco
from pandas_datareader import data as web
from pypfopt import expected_returns, risk_models, EfficientFrontier

API_KEY = os.environ.get('API_KEY_ALPACA')
API_SECRET = os.environ.get('SECRET_KEY_ALPACA')
APCA_API_BASE_URL = "https://paper-api.alpaca.markets"
EMAIL_USER = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('YOUR_EMAIL_ADDRESS')
paper = True

trading_api =  tradeapi.REST(API_KEY, API_SECRET, APCA_API_BASE_URL, 'v2')

def portfolio_analytics(tickers, portfolio_size, start_date, end_date):
    # Override yfinance with Pandas Datareader's Yahoo Finance API
    def get_historical_prices(symbols, start_date, end_date):
        """Retrieve historical stock prices for specified symbols."""
        return yf.download(symbols, start=start_date, end=end_date)['Adj Close']

    def calculate_daily_returns(prices):
        """Calculate daily returns from stock prices."""
        return np.log(prices / prices.shift(1))

    def calculate_monthly_returns(daily_returns):
        """Calculate monthly returns from daily returns."""
        return np.exp(daily_returns.groupby(lambda date: date.month).sum()) - 1

    def calculate_annual_returns(daily_returns):
        """Calculate annual returns from daily returns."""
        return np.exp(daily_returns.groupby(lambda date: date.year).sum()) - 1

    def portfolio_variance(returns, weights=None):
        """Calculate the variance of a portfolio."""
        if weights is None:
            weights = np.ones(len(returns.columns)) / len(returns.columns)
        covariance_matrix = np.cov(returns.T)
        return np.dot(weights, np.dot(covariance_matrix, weights))

    def sharpe_ratio(returns, weights=None, risk_free_rate=0.001):
        """Calculate the Sharpe ratio of a portfolio."""
        if weights is None:
            weights = np.ones(len(returns.columns)) / len(returns.columns)
        port_var = portfolio_variance(returns, weights)
        port_return = np.dot(returns.mean(), weights)
        return (port_return - risk_free_rate) / np.sqrt(port_var)

    # Fetch historical data
    historical_prices = get_historical_prices(tickers, start_date, end_date)

    # Calculate returns
    daily_returns = calculate_daily_returns(historical_prices)
    monthly_returns = calculate_monthly_returns(daily_returns)
    annual_returns = calculate_annual_returns(daily_returns)

    # Calculate portfolio metrics
    portfolio_variance_value = portfolio_variance(annual_returns)
    portfolio_sharpe_ratio = sharpe_ratio(daily_returns)

    # Display results
    print(f"Portfolio Variance: {portfolio_variance_value}")
    print(f"Portfolio Sharpe Ratio: {portfolio_sharpe_ratio}")

    # Plot historical prices using Plotly
    fig = go.Figure()
    for symbol in tickers:
        fig.add_trace(go.Scatter(x=historical_prices.index, y=historical_prices[symbol], mode='lines', name=symbol))

    fig.update_layout(title="Historical Prices",
                    xaxis_title="Date",
                    yaxis_title="Adjusted Closing Price",
                    legend_title="Symbols")
    fig.show()

    # Portfolio Optimization
    returns = historical_prices.pct_change()
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    num_portfolios = 50000
    risk_free_rate = 0.021

    def random_portfolios(num_portfolios, mean_returns, cov_matrix, risk_free_rate):
        results = np.zeros((3, num_portfolios))
        weights_record = []
        for i in range(num_portfolios):
            weights = np.random.random(len(tickers))
            weights /= np.sum(weights)
            weights_record.append(weights)
            portfolio_std_dev, portfolio_return = portfolio_performance(weights, mean_returns, cov_matrix)
            results[0, i] = portfolio_std_dev
            results[1, i] = portfolio_return
            results[2, i] = (portfolio_return - risk_free_rate) / portfolio_std_dev
        return results, weights_record

    def portfolio_performance(weights, mean_returns, cov_matrix):
        returns = np.sum(mean_returns * weights) * 252
        std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
        return std_dev, returns

    def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
        p_var, p_ret = portfolio_performance(weights, mean_returns, cov_matrix)
        return -(p_ret - risk_free_rate) / p_var

    def max_sharpe_ratio(mean_returns, cov_matrix, risk_free_rate):
        num_assets = len(mean_returns)
        args = (mean_returns, cov_matrix, risk_free_rate)
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bound = (0.0, 1.0)
        bounds = tuple(bound for asset in range(num_assets))
        result = sco.minimize(neg_sharpe_ratio, num_assets * [1.0 / num_assets,], args=args, method="SLSQP", bounds=bounds, constraints=constraints)
        return result

    def portfolio_volatility(weights, mean_returns, cov_matrix):
        return portfolio_performance(weights, mean_returns, cov_matrix)[0]

    def min_variance(mean_returns, cov_matrix):
        num_assets = len(mean_returns)
        args = (mean_returns, cov_matrix)
        bounds = tuple((0.0, 1.0) for asset in range(num_assets))
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        result = sco.minimize(portfolio_volatility, [1./num_assets]*num_assets, args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        return result

    def efficient_return(mean_returns, cov_matrix, target_return):
        num_assets = len(mean_returns)
        args = (mean_returns, cov_matrix)
        bounds = tuple((0.0, 1.0) for asset in range(num_assets))
        constraints = [{'type': 'eq', 'fun': lambda x: portfolio_performance(x, mean_returns, cov_matrix)[1] - target_return}, {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        result = sco.minimize(portfolio_volatility, [1./num_assets]*num_assets, args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        return result

    def efficient_frontier(mean_returns, cov_matrix, returns_range):
        efficient_portfolios = []
        for ret in returns_range:
            efficient_portfolios.append(efficient_return(mean_returns, cov_matrix, ret))
        return efficient_portfolios

    target_returns = np.linspace(0.0, 0.5, 100)
    efficient_portfolios = efficient_frontier(mean_returns, cov_matrix, target_returns)

    volatility = [p['fun'] for p in efficient_portfolios]
    returns = [portfolio_performance(p['x'], mean_returns, cov_matrix)[1] for p in efficient_portfolios]

    fig_efficient_frontier = go.Figure()
    fig_efficient_frontier.add_trace(go.Scatter(x=volatility, y=returns, mode='lines', name='Efficient Frontier'))
    fig_efficient_frontier.add_trace(go.Scatter(x=[p['fun'] for p in min_variance(mean_returns, cov_matrix)], y=[p['x'].mean() for p in min_variance(mean_returns, cov_matrix)], mode='markers', marker=dict(size=10, color='red'), name='Minimum Variance Portfolio'))
    fig_efficient_frontier.update_layout(title='Efficient Frontier', xaxis_title='Volatility', yaxis_title='Return')
    fig_efficient_frontier.show()

    # Portfolio VAR Simulation
    Time = 1440  # Number of trading days in minutes
    pvalue = portfolio_size  # Portfolio value in dollars
    num_of_years = (end_date - start_date).days / 365.25

    price_data = [web.DataReader(ticker, start=start_date, end=end_date, data_source='yahoo')['Adj Close'] for ticker in tickers]
    df_stocks = pd.concat(price_data, axis=1)
    df_stocks.columns = tickers

    mu = expected_returns.mean_historical_return(df_stocks)
    Sigma = risk_models.sample_cov(df_stocks)

    ef = EfficientFrontier(mu, Sigma, weight_bounds=(0,1))
    sharpe_pwt = ef.max_sharpe()
    cleaned_weights = ef.clean_weights()

    cum_returns = ((df_stocks.pct_change() + 1).cumprod() - 1)
    fig_cum_returns = go.Figure()
    for column in cum_returns.columns:
        fig_cum_returns.add_trace(go.Scatter(x=cum_returns.index, y=cum_returns[column], mode='lines', name=column))
    fig_cum_returns.update_layout(title='Cumulative Returns', xaxis_title='Date', yaxis_title='Cumulative Returns')
    fig_cum_returns.show()

    ticker_returns = cum_returns.pct_change().dropna()
    weighted_returns = ticker_returns.dot(np.array(list(cleaned_weights.values())))
    portfolio_return = weighted_returns.mean()
    portfolio_vol = weighted_returns.std()

    simulated_daily_returns = [np.random.normal(portfolio_return / Time, portfolio_vol / np.sqrt(Time), Time) for _ in range(10000)]

    fig_returns_range = go.Figure()
    for i in range(10000):
        fig_returns_range.add_trace(go.Scatter(y=simulated_daily_returns[i], mode='lines', name=f'Simulation {i+1}'))
    fig_returns_range.add_trace(go.Scatter(y=np.percentile(simulated_daily_returns, 5), mode='lines', name='5th Percentile', line=dict(color='red', dash='dash')))
    fig_returns_range.add_trace(go.Scatter(y=np.percentile(simulated_daily_returns, 95), mode='lines', name='95th Percentile', line=dict(color='green', dash='dash')))
    fig_returns_range.add_trace(go.Scatter(y=np.mean(simulated_daily_returns), mode='lines', name='Mean', line=dict(color='blue')))
    fig_returns_range.update_layout(title=f'Range of Returns in a Day of {Time} Minutes', xaxis_title='Minute', yaxis_title='Returns')
    fig_returns_range.show()

    fig_hist_returns = go.Figure()
    fig_hist_returns.add_trace(go.Histogram(x=simulated_daily_returns.flatten(), nbinsx=15))
    fig_hist_returns.add_trace(go.Scatter(x=[np.percentile(simulated_daily_returns, 5), np.percentile(simulated_daily_returns, 5)], y=[0, 1500], mode='lines', name='5th Percentile', line=dict(color='red', dash='dash')))
    fig_hist_returns.add_trace(go.Scatter(x=[np.percentile(simulated_daily_returns, 95), np.percentile(simulated_daily_returns, 95)], y=[0, 1500], mode='lines', name='95th Percentile', line=dict(color='green', dash='dash')))
    fig_hist_returns.update_layout(title='Histogram of Daily Returns', xaxis_title='Returns', yaxis_title='Frequency')
    fig_hist_returns.show()

    print(f"5th Percentile: {np.percentile(simulated_daily_returns, 5)}")
    print(f"95th Percentile: {np.percentile(simulated_daily_returns, 95)}")
    print(f"Amount required to cover minimum losses for one day: ${pvalue * -np.percentile(simulated_daily_returns, 5)}")

# Example usage
tickers = ['AAPL', 'MSFT', 'GOOGL']
portfolio_size = 100000
start_date = dt.datetime.now() - dt.timedelta(days=365*5)
end_date = dt.datetime.now()

portfolio_analytics(tickers, portfolio_size, start_date, end_date)