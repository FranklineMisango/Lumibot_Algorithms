import streamlit as st
import requests
import pandas as pd
import math
from statistics import mean
import numpy as np
from scipy import stats
from secrets_1 import IEX_CLOUD_API_TOKEN

def main():
    st.title("Level III : Quantitative Value Investing Strategizer")
    message = "This app allows us to Strategize a Value investing Approach which means investing in the stocks that are cheapest relative to common measures of business value (like earnings or assets)."
    st.success(message)
    st.warning("This project is intended for users with a basic understanding of Algorithmic Trading")
    st.image('/home/misango/code/Xpay_AlgoTrader/images/value.jpg')
    st.markdown("**Enter stock tickers and select a benchmark:**")

    if 'tickers' not in st.session_state:
        st.session_state.tickers = []

    if 'benchmark' not in st.session_state:
        st.session_state.benchmarks = []
    
    # Create a form for the ticker input
    with st.form(key='ticker_form'):
        col1, col2 = st.columns([2, 1])
        with col1:
            ticker_input = st.text_input("Enter a stock ticker or Load from our list:", key='ticker_input')
        with col2:
            add_ticker_button = st.form_submit_button(label="Add +")
            remove_ticker_button = st.form_submit_button(label="Remove -")
        #if st.form_submit_button(message):
            #st.session_state.tickers = tickers['Ticker'].tolist()  # Get values from the 'Ticker' column
            #st.session_state.tickers_string = ','.join(st.session_state.tickers)  # Join tickers into a single string
            #st.session_state.tickers = [st.session_state.tickers_string]  # Convert the single string to a list


        # Check if the ticker is already in the list
        is_duplicate = ticker_input in st.session_state.tickers

        # Add the entered ticker to the list when the user clicks the "+" button
        if add_ticker_button and not is_duplicate:
            st.session_state.tickers.append(ticker_input)

        # Remove the last ticker from the list when the "-" button is clicked
        if remove_ticker_button:
            if st.session_state.tickers:
                st.session_state.tickers.pop()

    st.write(st.session_state.tickers)

    # Create a form for selecting the benchmark
    with st.form(key='benchmark_form'):
        col1, col2 = st.columns([2, 1])
        with col1:
            benchmark = st.selectbox("Select One benchmark (More will be added soon):", ["S&P 500", "DJIA", "HSI", "UKX", "SX5E", "SHCOMP", "N225", "STI", "NSEASI", "DFMGI", "ADXGI", "TASI"])
        with col2:
            add_benchmark_button = st.form_submit_button("Add +")
            remove_benchmark_button = st.form_submit_button("Remove -")

    # Add or remove the selected benchmark from the list when the user clicks the corresponding button
    if add_benchmark_button:
        st.session_state.benchmarks.append(benchmark)
    if remove_benchmark_button and benchmark in st.session_state.benchmarks:
        st.session_state.benchmarks.remove(benchmark)

    st.write(st.session_state.benchmarks)

    #How much Money does the User have for input
    portfolio_size = st.number_input("Enter the value of your portfolio in ($):")
    try:
        val = float(portfolio_size)
    except ValueError:
        print("That's not a number! \n Try again:")
        portfolio_size = input("Enter the value of your portfolio in ($):")
    
    if st.button("Strategize"):
        # Blueprints for Showcasing the Final Data Frames
        symbol_groups = list(chunks(st.session_state.tickers, len(st.session_state.tickers)))
        symbol_strings = []
        for i in range(0, len(symbol_groups)):
            symbol_strings.append(','.join(symbol_groups[i]))

        rv_columns = [
        'Ticker',
        'Price',
        'Number of Shares to Buy', 
        'Price-to-Earnings Ratio',
        'PE Percentile',
        'Price-to-Book Ratio',
        'PB Percentile',
        'Price-to-Sales Ratio',
        'PS Percentile',
        'EV/EBITDA',
        'EV/EBITDA Percentile',
        'EV/GP',
        'EV/GP Percentile',
        'RV Score'
        ]

        rv_dataframe = pd.DataFrame(columns = rv_columns)

        for symbol_string in symbol_strings:
            batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
            data = requests.get(batch_api_call_url).json()
            for symbol in symbol_string.split(','):
                enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
                ebitda = data[symbol]['advanced-stats']['EBITDA']
                gross_profit = data[symbol]['advanced-stats']['grossProfit']
                
                try:
                    ev_to_ebitda = enterprise_value/ebitda
                except TypeError:
                    ev_to_ebitda = np.NaN
                
                try:
                    ev_to_gross_profit = enterprise_value/gross_profit
                except TypeError:
                    ev_to_gross_profit = np.NaN
                    
                rv_dataframe = rv_dataframe.append(
                    pd.Series([
                        symbol,
                        data[symbol]['quote']['latestPrice'],
                        'N/A',
                        data[symbol]['quote']['peRatio'],
                        'N/A',
                        data[symbol]['advanced-stats']['priceToBook'],
                        'N/A',
                        data[symbol]['advanced-stats']['priceToSales'],
                        'N/A',
                        ev_to_ebitda,
                        'N/A',
                        ev_to_gross_profit,
                        'N/A',
                        'N/A'
                ],
                index = rv_columns),
                    ignore_index = True
                )
        #Removing all the Null axes       
        for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio','Price-to-Sales Ratio',  'EV/EBITDA','EV/GP']:
            rv_dataframe[column].fillna(rv_dataframe[column].mean(), inplace = True)
        #rv_dataframe[rv_dataframe.isnull().any(axis=1)]
        metrics = {
            'Price-to-Earnings Ratio': 'PE Percentile',
            'Price-to-Book Ratio':'PB Percentile',
            'Price-to-Sales Ratio': 'PS Percentile',
            'EV/EBITDA':'EV/EBITDA Percentile',
            'EV/GP':'EV/GP Percentile'
}
        for row in rv_dataframe.index:
            for metric in metrics.keys():
                rv_dataframe.loc[row, metrics[metric]] = stats.percentileofscore(rv_dataframe[metric], rv_dataframe.loc[row, metric])/100

        # Print each percentile score to make sure it was calculated properly
        for metric in metrics.values():
            print(rv_dataframe[metric])

        for row in rv_dataframe.index:
            value_percentiles = []
            for metric in metrics.keys():
                value_percentiles.append(rv_dataframe.loc[row, metrics[metric]])
            rv_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)
        position_size = float(portfolio_size) / len(rv_dataframe.index)
        for i in range(0, len(rv_dataframe['Ticker'])):
            rv_dataframe.loc[i, 'Number of Shares to Buy'] = int(math.floor(position_size / rv_dataframe['Price'][i]))


        if rv_dataframe is not None:
            st.write(rv_dataframe)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if __name__ == "__main__":
    main()