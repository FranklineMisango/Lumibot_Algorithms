import streamlit as st
from streamlit_ttyd import terminal
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.title("Frankline & Co. HFT Trading Bot Progress Monitoring - Test Run I")
st.write("Simulating Q2 Portfolio from Warren Buffet's Berkshire Hathaway")
st.image("image/Warren-Buffett-Stock-Holdings.png", use_column_width=True)


try:
    # Start main.py and capture its output
    process = subprocess.Popen(['python', 'main.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process:
        st.success("main.py started successfully")
        logger.info("main.py started successfully")
except Exception as e:
    st.error(f"Failed to start main.py: {e}")
    logger.error(f"Failed to start main.py: {e}")

# Display the output of main.py in Streamlit
st.write("Output on Test Day run from our HFT bot:")
try:
    for line in iter(process.stdout.readline, ''):
        st.text(line.strip())
except Exception as e:
    st.error(f"Error reading output from main.py: {e}")
    logger.error(f"Error reading output from main.py: {e}")

try:
    # start the ttyd server and display the terminal on streamlit
    ttydprocess, port = terminal(cmd="top")
    st.text(f"ttyd server is running on port : {port}")
    logger.info(f"ttyd server is running on port : {port}")

    # kill the ttyd server after a minute
    time.sleep(60)
    ttydprocess.kill()
    logger.info("ttyd server killed after 60 seconds")
except Exception as e:
    st.error(f"Failed to start or stop ttyd server: {e}")
    logger.error(f"Failed to start or stop ttyd server: {e}")

# Ensure the process is terminated
try:
    process.terminate()
    process.wait()
    logger.info("main.py process terminated")
except Exception as e:
    st.error(f"Failed to terminate main.py: {e}")
    logger.error(f"Failed to terminate main.py: {e}")