if pred_option_portfolio_strategies == "Moving Average Strategy":
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
                
                    # Function to download stock data
                    def download_stock_data(ticker, start_date, end_date):
                        return yf.download(ticker, start_date, end_date)

                    # Function to calculate moving averages
                    def calculate_moving_averages(data, windows):
                        for window in windows:
                            data[f'SMA_{window}'] = data['Adj Close'].rolling(window).mean()
                        return data

                    # Main function
                    def main():
                        st.title("Stock Data Analysis with Moving Averages")

                        ticker = st.text_input("Enter a ticker:")
                        if not ticker:
                            st.warning("Please enter a valid ticker.")
                            return

                        num_of_years = 6
                        start_date = dt.datetime.now() - dt.timedelta(int(365.25 * num_of_years))
                        end_date = dt.datetime.now()

                        # Download and process stock data
                        stock_data = download_stock_data(ticker, start_date, end_date)
                        stock_data = calculate_moving_averages(stock_data, [20, 40, 80])

                        # Plotting
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Adj Close'], mode='lines', name='Close Price'))
                        for window in [20, 40, 80]:
                            fig.add_trace(go.Scatter(x=stock_data.index, y=stock_data[f'SMA_{window}'], mode='lines', name=f'{window}-days SMA'))
                        
                        fig.update_layout(title=f'{ticker.upper()} Close Price with Moving Averages',
                                        xaxis_title='Date',
                                        yaxis_title='Close Price')

                        st.plotly_chart(fig)
