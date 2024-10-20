 if pred_option_portfolio_strategies == "Financial Signal Analysis":
                ticker = st.text_input("Please enter the ticker needed for investigation")
                if ticker:
                    message = (f"Ticker captured : {ticker}")
                    st.success(message)
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
                    # Constants for analysis
                    index = 'SPY'  # S&P500 as the index for comparison
                    num_of_years = years  # Number of years for historical data
                    start = start_date

                    # Download historical stock prices
                    stock_data = yf.download(ticker, start=start)['Adj Close']
                    # Plotting stock prices and their distribution
                    fig1 = go.Figure()
                    fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data.values, mode='lines', name=f'{ticker.upper()} Price'))
                    fig1.update_layout(title=f'{ticker.upper()} Price', xaxis_title='Date', yaxis_title='Price')
                    st.plotly_chart(fig1)

                    fig2 = go.Figure()
                    fig2.add_trace(go.Histogram(x=stock_data, name=f'{ticker.upper()} Price Distribution'))
                    fig2.update_layout(title=f'{ticker.upper()} Price Distribution', xaxis_title='Price', yaxis_title='Frequency')
                    st.plotly_chart(fig2)

                    # Calculating and plotting stock returns
                    stock_returns = stock_data.apply(np.log).diff(1)
                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=stock_returns.index, y=stock_returns.values, mode='lines', name=f'{ticker.upper()} Returns'))
                    fig3.update_layout(title=f'{ticker.upper()} Returns', xaxis_title='Date', yaxis_title='Returns')
                    st.plotly_chart(fig3)

                    fig4 = go.Figure()
                    fig4.add_trace(go.Histogram(x=stock_returns, name=f'{ticker.upper()} Returns Distribution'))
                    fig4.update_layout(title=f'{ticker.upper()} Returns Distribution', xaxis_title='Returns', yaxis_title='Frequency')
                    st.plotly_chart(fig4)

                    # Rolling statistics for stock returns
                    rolling_window = 22
                    rolling_mean = stock_returns.rolling(rolling_window).mean()
                    rolling_std = stock_returns.rolling(rolling_window).std()
                    rolling_skew = stock_returns.rolling(rolling_window).skew()
                    rolling_kurtosis = stock_returns.rolling(rolling_window).kurt()

                    # Combining rolling statistics into a DataFrame
                    signals = pd.concat([rolling_mean, rolling_std, rolling_skew, rolling_kurtosis], axis=1)
                    signals.columns = ['Mean', 'Std Dev', 'Skewness', 'Kurtosis']

                    fig5 = go.Figure()
                    for col in signals.columns:
                        fig5.add_trace(go.Scatter(x=signals.index, y=signals[col], mode='lines', name=col))
                    fig5.update_layout(title='Rolling Statistics for Stock Returns', xaxis_title='Date', yaxis_title='Value')
                    st.plotly_chart(fig5)

                    # Volatility analysis for S&P500
                    index_data = yf.download(index, start=start)['Adj Close']
                    index_returns = index_data.apply(np.log).diff(1)
                    index_volatility = index_returns.rolling(rolling_window).std()

                    # Drop NaN values from index_volatility
                    index_volatility.dropna(inplace=True)

                    # Gaussian Mixture Model on S&P500 volatility
                    gmm_labels = GaussianMixture(2).fit_predict(index_volatility.values.reshape(-1, 1))
                    index_data = index_data.reindex(index_volatility.index)

                    # Plotting volatility regimes
                    fig6 = go.Figure()
                    fig6.add_trace(go.Scatter(x=index_data[gmm_labels == 0].index,
                                            y=index_data[gmm_labels == 0].values,
                                            mode='markers',
                                            marker=dict(color='blue'),
                                            name='Regime 1'))
                    fig6.add_trace(go.Scatter(x=index_data[gmm_labels == 1].index,
                                            y=index_data[gmm_labels == 1].values,
                                            mode='markers',
                                            marker=dict(color='red'),
                                            name='Regime 2'))
                    fig6.update_layout(title=f'{index} Volatility Regimes (Gaussian Mixture)',
                                    xaxis_title='Date',
                                    yaxis_title='Price',
                                    showlegend=True)
                    st.plotly_chart(fig6)