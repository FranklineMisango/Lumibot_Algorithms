import seaborn as sns
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime as dt
from factor_analyzer import FactorAnalyzer, calculate_bartlett_sphericity, calculate_kmo
def main(start_date, end_date, tickers):
    # Setting plot aesthetics
    sns.set(style='darkgrid', context='talk', palette='Dark2')   

    # List of stock symbols for factor analysis
    symbols = tickers

    # Fetching adjusted close prices for the specified symbols
    df = pd.DataFrame({symbol: yf.download(symbol, start_date, end_date)['Adj Close']
                    for symbol in symbols})

    # Initializing FactorAnalyzer and fitting it to our data
    fa = FactorAnalyzer(rotation=None, n_factors=df.shape[1])
    fa.fit(df.dropna())

    # Extracting communalities, eigenvalues, and factor loadings
    communalities = fa.get_communalities()
    eigenvalues, _ = fa.get_eigenvalues()
    loadings = fa.loadings_

    # Plotting the Scree plot to assess the number of factors
    scree_fig = go.Figure()
    scree_fig.add_trace(go.Scatter(x=list(range(1, df.shape[1] + 1)),
                                y=eigenvalues,
                                mode='markers+lines',
                                name='Eigenvalues',
                                marker=dict(color='blue')))
    scree_fig.update_layout(title='Scree Plot for Factor Analysis of the tickers input', 
                            xaxis_title='Number of Factors',
                            yaxis_title='Eigenvalue',
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    scree_fig.show()

    # Bartlett's test of sphericity
    chi_square_value, p_value = calculate_bartlett_sphericity(df.dropna())
    print('Bartlett sphericity test:\nChi-square value:', chi_square_value, '\nP-value:', p_value)

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
        portfolio = float(input("Enter the portfolio size in USD That you want to start with : "))
        print(f"The portfolio size captured is : {portfolio}")

        start_date = dt.strptime(input("Enter the start date for the analysis (YYYY-MM-DD) : "), "%Y-%m-%d")
        end_date = dt.strptime(input("Enter the end date for the analysis (YYYY-MM-DD) : "), "%Y-%m-%d")
        print(f"The start date captured is : {start_date}")
        print(f"The end date captured is : {end_date}")
        years = end_date.year - start_date.year
        print(f"The number of years captured is : {years}")
        main(start_date, end_date, tickers)  # Corrected argument order
    elif prompt == 2: 
        print("Still in development")
        pass
    else:
        print("Invalid option selected")