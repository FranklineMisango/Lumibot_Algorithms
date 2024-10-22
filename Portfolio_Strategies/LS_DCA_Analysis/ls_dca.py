
            if pred_option_portfolio_strategies == "LS DCA Analysis":
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
                    def fetch_stock_data(symbol, start, end):
                        return yf.download(symbol, start, end)

                    # Lump Sum Investment Function
                    def lump_sum_investment(df, invest_date, principal):
                        invest_price = df.loc[invest_date]['Adj Close']
                        current_price = df['Adj Close'][-1]
                        return principal * ((current_price / invest_price) - 1)

                    # Dollar-Cost Averaging Function
                    def dca_investment(df, invest_date, periods, freq, principal):
                        dca_dates = pd.date_range(invest_date, periods=periods, freq=freq)
                        dca_dates = dca_dates[dca_dates < df.index[-1]]
                        cut_off_count = 12 - len(dca_dates)
                        cut_off_value = cut_off_count * (principal / periods)
                        dca_value = cut_off_value
                        for date in dca_dates:
                            trading_date = df.index[df.index.searchsorted(date)]
                            dca_value += lump_sum_investment(df, trading_date, principal / periods)
                        return dca_value

                    # User Input
                    symbol = ticker
                    years = years
                    principal = portfolio

                    # Set dates for data retrieval
                    start_date = start_date
                    end_date = end_date

                    # Fetch Data
                    stock_data = fetch_stock_data(symbol, start_date, end_date)

                    # Analysis for Lump Sum and DCA
                    lump_sum_values = [lump_sum_investment(stock_data, date, principal) for date in stock_data.index]
                    dca_values = [dca_investment(stock_data, date, 12, '30D', principal) for date in stock_data.index]
                
                    fig1 = go.Figure()
                    fig1.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Adj Close'], mode='lines', name=f'{symbol} Price'))
                    fig1.update_layout(title=f'{symbol} Stock Price', yaxis_title='Price', yaxis_tickprefix='$', yaxis_tickformat=',.0f')

                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=stock_data.index, y=lump_sum_values, mode='lines', name='Lump Sum Investment'))
                    fig2.add_trace(go.Scatter(x=stock_data.index, y=dca_values, mode='lines', name='DCA Investment'))
                    fig2.update_layout(title='Lump Sum vs. DCA Investment Value', yaxis_title='Investment Value', yaxis_tickprefix='$', yaxis_tickformat=',.0f')

                    fig3 = go.Figure()
                    fig3.add_trace(go.Scatter(x=stock_data.index, y=np.array(lump_sum_values) - np.array(dca_values), mode='lines', name='Difference in Investment Values'))
                    fig3.update_layout(title='Difference Between Lump Sum and DCA', yaxis_title='Difference', yaxis_tickprefix='$', yaxis_tickformat=',.0f')

                    # Display plots in Streamlit
                    st.plotly_chart(fig1)
                    st.plotly_chart(fig2)
                    st.plotly_chart(fig3)
