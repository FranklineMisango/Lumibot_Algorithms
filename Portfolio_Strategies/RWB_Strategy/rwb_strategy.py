if pred_option_portfolio_strategies == "RWB Strategy":
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
                    emas_used = [3, 5, 8, 10, 12, 15, 30, 35, 40, 45, 50, 60]

                    def get_stock_data(ticker, num_of_years):
                        start_date = dt.date.today() - dt.timedelta(days=365.25 * num_of_years)
                        end_date = dt.datetime.now()
                        df = yf.download(ticker, start_date, end_date).dropna()
                        for ema in emas_used:
                            df[f"Ema_{ema}"] = df.iloc[:, 4].ewm(span=ema, adjust=False).mean()
                        return df.iloc[60:]

                    def rwb_strategy(df):
                        pos, num, percent_change = 0, 0, []
                        for i in df.index:
                            cmin = min(df[f"Ema_{ema}"][i] for ema in emas_used[:6])
                            cmax = max(df[f"Ema_{ema}"][i] for ema in emas_used[6:])
                            close = df["Adj Close"][i]
                            if cmin > cmax and pos == 0:
                                bp, pos = close, 1
                                st.write(f"Buying now at {bp}")
                            elif cmin < cmax and pos == 1:
                                pos, sp = 0, close
                                st.write(f"Selling now at {sp}")
                                percent_change.append((sp / bp - 1) * 100)
                            if num == df["Adj Close"].count() - 1 and pos == 1:
                                pos, sp = 0, close
                                st.write(f"Selling now at {sp}")
                                percent_change.append((sp / bp - 1) * 100)
                            num += 1
                        return percent_change

                    st.title("RWB Strategy Visualization")

                    stock = st.text_input("Enter a ticker:", "AAPL")
                    num_of_years = st.number_input("Enter number of years:", min_value=1, max_value=10, step=1, value=5)

                    df = get_stock_data(stock, num_of_years)
                    percent_change = rwb_strategy(df)

                    gains = sum(i for i in percent_change if i > 0)
                    losses = sum(i for i in percent_change if i < 0)
                    total_trades = len(percent_change)
                    total_return = round((np.prod([1 + i/100 for i in percent_change]) - 1) * 100, 2)

                    st.write(f"Results for {stock.upper()} going back to {num_of_years} years:")
                    st.write(f"Number of Trades: {total_trades}")
                    st.write(f"Total return: {total_return}%")

                    fig = go.Figure()
                    for ema in emas_used:
                        fig.add_trace(go.Scatter(x=df.index, y=df[f"Ema_{ema}"], mode='lines', name=f"Ema_{ema}"))
                    fig.add_trace(go.Scatter(x=df.index, y=df["Adj Close"], mode='lines', name="Adj Close", line=dict(color='green')))
                    fig.update_layout(title=f"RWB Strategy for {stock.upper()}", xaxis_title="Date", yaxis_title="Price", template='plotly_dark')
                    st.plotly_chart(fig)

