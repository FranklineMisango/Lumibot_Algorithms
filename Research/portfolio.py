import quantstats as qs
import streamlit as st
import plotly.express as px
import yfinance as yf
import pandas as pd

def portfolio():
    st.header("Portfolio Analysis")

    st.sidebar.subheader("Enter Portfolio Details")
    index_input = st.sidebar.text_input("Enter Index and Weights (e.g., 'TSLA: 1.3, AGG: -0.3'):")
    period_input = st.sidebar.selectbox("Select Period", ["1y", "3y", "5y"])

    if st.sidebar.button("Analyze Portfolio"):
        index_data = {}
        for item in index_input.split(','):
            symbol, weight = item.strip().split(':')
            index_data[symbol.strip()] = float(weight.strip())

        # Create an empty DataFrame to store portfolio balance
        index = qs.utils.make_index(index_data, period=period_input)
        index.index = index.index.tz_localize(None)

        portfolio_balance_df = pd.DataFrame(index=index.index)
        portfolio_balance_df['portfolio_balance'] = 10000  # Assuming 10000 as the initial balance

        for symbol, weight in index_data.items():
            stock_data = yf.download(symbol, period=period_input)
            stock_returns = stock_data['Adj Close'].pct_change().fillna(0)
            portfolio_balance_df['portfolio_balance'] *= (1 + weight * stock_returns + weight)

        st.subheader("Portfolio Earnings")
        st.plotly_chart(px.line(portfolio_balance_df, x=portfolio_balance_df.index, y='portfolio_balance', title='Portfolio Balance', labels={'portfolio_balance': 'Balance'}))

        st.subheader("Monthly Heatmap")
        st.plotly_chart(px.imshow(portfolio_balance_df['portfolio_balance'].pct_change().dropna().unstack().unstack().reset_index(), x='level_0', y='level_1', z=0), use_container_width=True)

if __name__ == "__main__":
    portfolio()
