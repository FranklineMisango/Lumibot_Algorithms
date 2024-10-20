if pred_option_portfolio_strategies == "Stock Spread Plotter":
                portfolio = st.number_input("Enter the portfolio size in USD")
                if portfolio:
                    st.write(f"The portfolio size in USD Captured is : {portfolio}")

                min_date = datetime(1980, 1, 1)
                # Date input widget with custom minimum date
                col1, col2 = st.columns([2, 2])
                with col1:
                    start_date = st.date_input("Start date:", min_value=min_date)
                with col2:
                    end_date = st.date_input("End Date:")
                years = end_date.year - start_date.year
                st.success(f"Years captured: {years}")
                # Initialize the stocks list in session state if it doesn't exist
                if 'stocks' not in st.session_state:
                    st.session_state.stocks = []

                # Function to add stock
                def addStock():
                    tsk = st.text_input('Enter your tickers', key='ticker_input', placeholder='Enter a ticker')
                    if tsk:
                        st.session_state.stocks.append(tsk)
                        st.success(f"Ticker {tsk} added.")
                        st.experimental_rerun()  # Refresh the app to show the updated list

                # Display the add stock button and call the function if clicked
                if st.button('Add Ticker'):
                    addStock()

                # Display the list of stocks
                st.write("Current list of tickers:")
                st.write(st.session_state.stocks)
                threshold = st.slider("Threshold", min_value=0.1, max_value=5.0, value=0.5)
                stop_loss = st.slider("Stop Loss", min_value=0.1, max_value=5.0, value=1.0)
                if st.button("Check"):
                    # Function to fetch stock data
                    def fetch_stock_data(tickers, start_date, end_date):
                        data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']
                        data.index = pd.to_datetime(data.index)
                        return data

                    def plot_stock_spread(df, ticker1, ticker2, threshold=0.5, stop_loss=1):
                        spread = df[ticker1] - df[ticker2]
                        mean_spread = spread.mean()
                        sell_threshold = mean_spread + threshold
                        buy_threshold = mean_spread - threshold
                        sell_stop = mean_spread + stop_loss
                        buy_stop = mean_spread - stop_loss

                        fig = go.Figure()

                        # Add the individual stock prices
                        fig.add_trace(go.Scatter(x=df.index, y=df[ticker1], mode='lines', name=ticker1))
                        fig.add_trace(go.Scatter(x=df.index, y=df[ticker2], mode='lines', name=ticker2))

                        # Add the spread
                        fig.add_trace(go.Scatter(x=df.index, y=spread, mode='lines', name='Spread', line=dict(color='#85929E')))

                        # Add threshold and stop lines
                        fig.add_hline(y=sell_threshold, line=dict(color='blue', dash='dash'), name='Sell Threshold')
                        fig.add_hline(y=buy_threshold, line=dict(color='red', dash='dash'), name='Buy Threshold')
                        fig.add_hline(y=sell_stop, line=dict(color='green', dash='dash'), name='Sell Stop')
                        fig.add_hline(y=buy_stop, line=dict(color='yellow', dash='dash'), name='Buy Stop')

                        # Update layout for better presentation
                        fig.update_layout(
                            title=f'Stock Spread between {ticker1} and {ticker2}',
                            xaxis_title='Date',
                            yaxis_title='Price',
                            legend_title='Legend',
                            template='plotly_white'
                        )

                        st.plotly_chart(fig)
                    # Main
                    if len(st.session_state.stocks) >= 2:
                        df = fetch_stock_data(st.session_state.stocks, start_date, end_date)
                        for i in range(len(st.session_state.stocks) - 1):
                            plot_stock_spread(df, st.session_state.stocks[i], st.session_state.stocks[i + 1], threshold, stop_loss)
                    else:
                        st.error("Please enter at least two tickers for the analysis.")
