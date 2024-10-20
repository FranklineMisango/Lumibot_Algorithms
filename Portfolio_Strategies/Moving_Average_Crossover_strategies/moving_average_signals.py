            if pred_option_portfolio_strategies == "Moving Average Crossover Signals":
                ticker = st.text_input("Please enter the ticker needed for investigation")
                if ticker:
                    message = (f"Ticker captured : {ticker}")
                    st.success(message)
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
                st.success(f"years captured : {years}")
                if st.button("Check"):
                    # Function to retrieve stock data
                    def get_stock_data(ticker, start_date, end_date):
                        return yf.download(ticker, start_date, end_date)

                    # Function to calculate Simple Moving Averages (SMA)
                    def calculate_sma(data, window):
                        return data['Close'].rolling(window=window).mean()

                    # Function to generate buy and sell signals
                    def generate_signals(data):
                        signal_buy = []
                        signal_sell = []
                        flag = -1

                        for i in range(len(data)):
                            if data['SMA 50'][i] > data['SMA 200'][i] and flag != 1:
                                signal_buy.append(data['Close'][i])
                                signal_sell.append(np.nan)
                                flag = 1
                            elif data['SMA 50'][i] < data['SMA 200'][i] and flag != 0:
                                signal_buy.append(np.nan)
                                signal_sell.append(data['Close'][i])
                                flag = 0
                            else:
                                signal_buy.append(np.nan)
                                signal_sell.append(np.nan)

                        return signal_buy, signal_sell

                    # Main function to run the analysis
                    def main():
                        st.title("Stock Data Analysis with Moving Averages and Signals")

                        ticker = st.text_input("Enter a ticker:")
                        if not ticker:
                            st.warning("Please enter a valid ticker.")
                            return

                        num_of_years = 6
                        start_date = dt.datetime.now() - dt.timedelta(int(365.25 * num_of_years))
                        end_date = dt.datetime.now()

                        # Retrieve and process stock data
                        stock_data = get_stock_data(ticker, start_date, end_date)
                        stock_data['SMA 50'] = calculate_sma(stock_data, 50)
                        stock_data['SMA 200'] = calculate_sma(stock_data, 200)

                        # Generate buy and sell signals
                        buy_signals, sell_signals = generate_signals(stock_data)

                        # Plotting
                        fig = go.Figure()

                        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], mode='lines', name='Close Price'))
                        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA 50'], mode='lines', name='SMA 50'))
                        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA 200'], mode='lines', name='SMA 200'))
                        fig.add_trace(go.Scatter(x=stock_data.index, y=buy_signals, mode='markers', name='Buy Signal', marker=dict(symbol='triangle-up', color='green')))
                        fig.add_trace(go.Scatter(x=stock_data.index, y=sell_signals, mode='markers', name='Sell Signal', marker=dict(symbol='triangle-down', color='red')))

                        fig.update_layout(title=f'{ticker.upper()} Close Price History with Buy & Sell Signals',
                                        xaxis_title='Date',
                                        yaxis_title='Close Price')

                        st.plotly_chart(fig)