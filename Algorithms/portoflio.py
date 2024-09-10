import quantstats as qs
import matplotlib as plt
import streamlit as st


qs.extend_pandas()

index = {"SPY": 1.3, "AGG": -.3}
portfolio = qs.utils.make_index(index, period='1y')
portfolio.index = portfolio.index.tz_localize(None)

# Create the Matplotlib figure and axis
fig, ax = plt.subplots()
portfolio.plot_earnings(start_balance=10000000)  # Use ax=ax to specify the axis

# Display the Matplotlib figure using st.pyplot() or matplotlib??
st.pyplot(fig)