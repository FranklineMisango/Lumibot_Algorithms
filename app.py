import streamlit as st
import time

st.title("Trading Bot Progress Monitor")

log_file = 'progress.log'

# Function to read the log file
def read_log():
    with open(log_file, 'r') as f:
        return f.read()

# Display the log file content
log_content = read_log()
log_lines = log_content.split('\n')

# Display the log lines in Streamlit
log_display = st.empty()
log_display.text_area("Log Output", value="\n".join(log_lines), height=400)

# Update the log display every 5 seconds
while True:
    time.sleep(5)
    log_content = read_log()
    log_lines = log_content.split('\n')
    log_display.text_area("Log Output", value="\n".join(log_lines), height=400)