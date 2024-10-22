if pred_option_portfolio_strategies == "Support Resistance Finder":
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
                    def fetch_stock_data(ticker, start_date, end_date):
                        df = yf.download(ticker, start=start_date, end=end_date)
                        df["Date"] = df.index
                        return df.reset_index(drop=True)

                    # Function to identify support and resistance levels
                    def identify_levels(df):
                        levels = []
                        for i in range(2, df.shape[0] - 2):
                            if is_support(df, i):
                                levels.append((i, df["Low"][i], "Support"))
                            elif is_resistance(df, i):
                                levels.append((i, df["High"][i], "Resistance"))
                        return levels

                    # Define support and resistance checks
                    def is_support(df, i):
                        return df["Low"][i] < min(df["Low"][i - 1], df["Low"][i + 1])

                    def is_resistance(df, i):
                        return df["High"][i] > max(df["High"][i - 1], df["High"][i + 1])

                    # Function to plot support and resistance levels
                    def plot_support_resistance(df, levels):
                        fig, ax = plt.subplots()
                        candlestick_ohlc(ax, zip(mpl_dates.date2num(df['Date']), df['Open'], df['High'], df['Low'], df['Close']), width=0.6, colorup='green', colordown='red', alpha=0.8)
                        ax.xaxis.set_major_formatter(mpl_dates.DateFormatter('%d-%m-%Y'))

                        for level in levels:
                            plt.hlines(level[1], xmin=df["Date"][level[0]], xmax=max(df["Date"]), colors="blue")
                        plt.title(f"Support and Resistance for {ticker.upper()}")
                        plt.xlabel("Date")
                        plt.ylabel("Price")
                        st.pyplot(fig)

                    # Main
                    st.title("Support and Resistance Levels Visualization")

                    ticker = st.text_input("Enter a ticker:")
                    num_of_years = st.slider("Number of years:", min_value=0.1, max_value=10.0, value=0.2, step=0.1)

                    start_date = pd.Timestamp.now() - pd.Timedelta(days=int(365.25 * num_of_years))
                    end_date = pd.Timestamp.now()

                    df = fetch_stock_data(ticker, start_date, end_date)
                    levels = identify_levels(df)
                    plot_support_resistance(df, levels)