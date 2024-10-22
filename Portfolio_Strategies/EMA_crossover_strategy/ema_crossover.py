import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from datetime import datetime as dt

def main(tickers, portfolio, start_date, end_date):

    # Define the analysis period
    num_of_years = years
    start =  start_date
    end = end_date

    # Define tickers for analysis

    # Fetch stock data using Yahoo Finance
    df = yf.download(tickers, start, end)['Close']

    # Calculate moving averages
    short_rolling = df.rolling(window=20).mean()
    long_rolling = df.rolling(window=100).mean()
    ema_short = df.ewm(span=20, adjust=False).mean()

    # Determine trading position based on EMA
    trade_positions_raw = df - ema_short
    trade_positions = trade_positions_raw.apply(np.sign) / 3  # Equal weighting
    trade_positions_final = trade_positions.shift(1)  # Shift to simulate next-day trading

    # Calculate asset and portfolio returns
    asset_log_returns = np.log(df).diff()
    portfolio_log_returns = trade_positions_final * asset_log_returns
    cumulative_portfolio_log_returns = portfolio_log_returns.cumsum()
    cumulative_portfolio_relative_returns = np.exp(cumulative_portfolio_log_returns) - 1

    # Plot cumulative returns
    cumulative_fig = go.Figure()
    for ticker in asset_log_returns:
        cumulative_fig.add_trace(go.Scatter(x=cumulative_portfolio_relative_returns.index,
                                            y=100 * cumulative_portfolio_relative_returns[ticker],
                                            mode='lines',
                                            name=ticker))

    cumulative_fig.update_layout(title='Cumulative Log Returns (%)',
                                xaxis_title='Date',
                                yaxis_title='Cumulative Log Returns (%)',
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    cumulative_fig.show()

    # Comparing exact and approximate cumulative returns
    cumulative_return_exact = cumulative_portfolio_relative_returns.sum(axis=1)
    cumulative_log_return = cumulative_portfolio_log_returns.sum(axis=1)
    cumulative_return_approx = np.exp(cumulative_log_return) - 1

    # Plot exact vs approximate returns
    approx_fig = go.Figure()
    approx_fig.add_trace(go.Scatter(x=cumulative_return_exact.index,
                                    y=100 * cumulative_return_exact,
                                    mode='lines',
                                    name='Exact'))
    approx_fig.add_trace(go.Scatter(x=cumulative_return_approx.index,
                                    y=100 * cumulative_return_approx,
                                    mode='lines',
                                    name='Approx'))

    approx_fig.update_layout(title='EMA Cross over strategy : Total Cumulative Relative Returns (%)',
                            xaxis_title='Date',
                            yaxis_title='EMA Cros over strategy : Total Cumulative Relative Returns (%)',
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
   
    approx_fig.show()

    # Function to print portfolio statistics
    def print_portfolio_statistics(portfolio_returns, num_of_years):
        total_return = portfolio_returns[-1]
        avg_yearly_return = (1 + total_return) ** (1 / num_of_years) - 1
        print(f'Total Portfolio Return: {total_return * 100:.2f}%')
        print(f'Average Yearly Return: {avg_yearly_return * 100:.2f}%')

    # Printing statistics for EMA crossover strategy
    print_portfolio_statistics(cumulative_return_exact, num_of_years)
 



if __name__ == "__main__":
    prompt = int(input("What do you want to do : \n1. Backtest a strategy \n2. Run the strategy Live : "))
    if prompt == 1:
        print("You have selected to backtest a strategy")
        tickers = []
        int_ticker = int(input("How many tickers do you want to investigate? ( > 2) : "))
        for i in range(int_ticker):
            ticker = input(f"Enter ticker {i} to investigate : ")
            tickers.append(ticker)
        print(f"The tickers captured are : {tickers}")
        portfolio = input("Enter the portfolio size in USD That you want to start with : ")
        print(f"The portfolio size captured is : {portfolio}")

        start_date = dt.strptime(input("Enter the start date for the analysis (YYYY-MM-DD) : "), "%Y-%m-%d")
        end_date = dt.strptime(input("Enter the end date for the analysis (YYYY-MM-DD) : "), "%Y-%m-%d")
        print(f"The start date captured is : {start_date}")
        print(f"The end date captured is : {end_date}")
        years = end_date.year - start_date.year
        print(f"The number of years captured is : {years}")
        main(tickers, portfolio, start_date, end_date)
    if prompt == 2: 
        print("Still in development")
        pass
