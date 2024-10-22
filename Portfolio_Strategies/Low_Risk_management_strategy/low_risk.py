if pred_option_portfolio_strategies == "Risk Management":
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
                                
                    # Define the start and end dates for data retrieval
                    start = dt.datetime(2019, 1, 1)
                    now = dt.datetime.now()

                    # Define the moving averages and exponential moving averages to be used
                    smaUsed = [50, 200]
                    emaUsed = [21]

                    # User inputs for stock ticker and position
                    stock = st.text_input("Enter a ticker: ")
                    position = st.selectbox("Buy or Short?", ["Buy", "Short"]).lower()
                    AvgGain = st.number_input("Enter Your Average Gain (%)", value=0.0, step=0.1)
                    AvgLoss = st.number_input("Enter Your Average Loss (%)", value=0.0, step=0.1)

                    # Fetch historical data from Yahoo Finance
                    df = yf.download(stock, start=start, end=now)

                    # Calculate the maximum stop value and target returns based on user's position
                    if position == "buy":
                        close = df["Adj Close"][-1]
                        maxStop = close * (1 - AvgLoss / 100)
                        targets = [round(close * (1 + (i * AvgGain / 100)), 2) for i in range(1, 4)]
                    elif position == "short":
                        close = df["Adj Close"][-1]
                        maxStop = close * (1 + AvgLoss / 100)
                        targets = [round(close * (1 - (i * AvgGain / 100)), 2) for i in range(1, 4)]

                    # Calculate SMA and EMA for the stock
                    for x in smaUsed:
                        df[f"SMA_{x}"] = df["Adj Close"].rolling(window=x).mean()
                    for x in emaUsed:
                        df[f"EMA_{x}"] = df["Adj Close"].ewm(span=x, adjust=False).mean()

                    # Fetching the latest values of SMA, EMA, and 5 day low
                    sma_values = {f"SMA_{x}": round(df[f"SMA_{x}"][-1], 2) for x in smaUsed}
                    ema_values = {f"EMA_{x}": round(df[f"EMA_{x}"][-1], 2) for x in emaUsed}
                    low5 = round(min(df["Low"].tail(5)), 2)

                    # Calculate the performance metrics and checks
                    performance_checks = {}
                    for key, value in {**sma_values, **ema_values, "Low_5": low5}.items():
                        pf = round(((close / value) - 1) * 100, 2)
                        check = value > maxStop if position == "buy" else value < maxStop
                        performance_checks[key] = {"Performance": pf, "Check": check}

                    # Displaying the results
                    st.write(f"Current Stock: {stock} | Price: {round(close, 2)}")
                    st.write(" | ".join([f"{key}: {value}" for key, value in {**sma_values, **ema_values, 'Low_5': low5}.items()]))
                    st.write("-------------------------------------------------")
                    st.write(f"Max Stop: {round(maxStop, 2)}")
                    st.write(f"Price Targets: 1R: {targets[0]} | 2R: {targets[1]} | 3R: {targets[2]}")
                    for key, value in performance_checks.items():
                        st.write(f"From {key} {value['Performance']}% - {'Within' if value['Check'] else 'Outside'} Max Stop")


            if pred_option_portfolio_strategies == "RSI Trendline Strategy":
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
                    # Define the date range for data retrieval
                    num_of_years = 10
                    start = datetime.datetime.now() - datetime.timedelta(days=365.25 * num_of_years)
                    end = datetime.datetime.now()

                    # Load stock symbols
                    @st.cache
                    def load_tickers():
                        stocklist = ti.tickers_sp500()
                        return [stock.replace(".", "-") for stock in stocklist]  # Adjusting ticker format for Yahoo Finance

                    stocklist = load_tickers()

                    # Initialize the DataFrame for exporting results
                    exportList = pd.DataFrame(columns=['Stock', "RSI", "200 Day MA"])

                    # Process a limited number of stocks for demonstration
                    for stock in stocklist[:5]:
                        time.sleep(1.5)  # To avoid hitting API rate limits
                        st.write(f"\npulling {stock}")

                        # Fetch stock data
                        df = yf.download(stock, start=start, end=end)

                        try:
                            # Calculate indicators: 200-day MA, RSI
                            df["SMA_200"] = df.iloc[:, 4].rolling(window=200).mean()
                            df["rsi"] = ta.RSI(df["Close"])
                            currentClose, moving_average_200, RSI = df["Adj Close"][-1], df["SMA_200"][-1], df["rsi"].tail(14).mean()
                            two_day_rsi_avg = (df.rsi[-1] + df.rsi[-2]) / 2

                            # Define entry criteria
                            if currentClose > moving_average_200 and two_day_rsi_avg < 33:
                                exportList = exportList.append({'Stock': stock, "RSI": RSI, "200 Day MA": moving_average_200}, ignore_index=True)
                                st.write(f"{stock} made the requirements")

                        except Exception as e:
                            st.write(e)  # Handling exceptions

                    # Displaying the exported list
                    st.write(exportList)