import streamlit as st
import requests
import pandas as pd
import math
from secrets_1 import IEX_CLOUD_API_TOKEN

def main():
    st.title("Live Equal Weight Benchmark Optimizer")
    st.warning("This project is intended for users with a basic understanding of Algorithmic Trading")
    st.image('/home/misango/code/Xpay_AlgoTrader/images/s&p.png')
    st.markdown("**Enter stock tickers and select a benchmark:**")

    if 'tickers' not in st.session_state:
        st.session_state.tickers = []

    if 'benchmark' not in st.session_state:
        st.session_state.benchmarks = []
    
    # Create a form for the ticker input
    with st.form(key='ticker_form'):
        col1, col2 = st.columns([2, 1])
        with col1:
            ticker_input = st.text_input("Enter a stock ticker:", key='ticker_input')
        with col2:
            add_ticker_button = st.form_submit_button(label="Add +")
            remove_ticker_button = st.form_submit_button(label="Remove -")
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
            benchmark = st.selectbox("Select One benchmark (More will be added soon):", ["SPY", "DJIA", "HSI", "UKX", "SX5E", "SHCOMP", "N225", "STI", "NSEASI", "DFMGI", "ADXGI", "TASI"])
        with col2:
            add_benchmark_button = st.form_submit_button("Add +")
            remove_benchmark_button = st.form_submit_button("Remove -")

    # Add or remove the selected benchmark from the list when the user clicks the corresponding button
    if add_benchmark_button:
        st.session_state.benchmarks.append(benchmark)
    if remove_benchmark_button and benchmark in st.session_state.tickers:
        st.session_state.benchmarks.remove(benchmark)
    
    st.write(st.session_state.benchmarks)


    portfolio_size = st.number_input("Enter the value of your portfolio in ($):")
    try:
        val = float(portfolio_size)
    except ValueError:
        print("That's not a number! \n Try again:")
        portfolio_size = input("Enter the value of your portfolio in ($):")
    
    if st.button("Optimize"):
        # Blueprints for Showcasing the Final Data Frames

        my_columns = ['Ticker', 'Price', 'Market Capitalization', 'Number Of Shares to Buy']
        final_dataframe = pd.DataFrame(columns=my_columns)

        symbol_groups = list(chunks(st.session_state.tickers, len(st.session_state.tickers)))
        symbol_strings = []
        for i in range(0, len(symbol_groups)):
            symbol_strings.append(','.join(symbol_groups[i]))
        final_dataframe = pd.DataFrame(columns=my_columns)
        if benchmark == 'SPY' :
            for symbol_string in symbol_strings:
                batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch/?types=quote&symbols={symbol_string}&token={IEX_CLOUD_API_TOKEN}'
                data = requests.get(batch_api_call_url).json()
                for symbol in symbol_string.split(','):
                    final_dataframe = final_dataframe.append(
                        pd.Series([symbol,
                                data[symbol]['quote']['latestPrice'],
                                data[symbol]['quote']['marketCap'],
                                data[symbol]['quote']['latestTime']
                                ],
                                index=my_columns),
                            ignore_index=True)
        position_size = float(portfolio_size) / len(final_dataframe.index)
        for i in range(0, len(final_dataframe['Ticker'])):
            final_dataframe.loc[i, 'Number Of Shares to Buy'] = math.floor(position_size / final_dataframe['Price'][i])          
        st.write(final_dataframe)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if __name__ == "__main__":
    main()
