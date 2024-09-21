# Lumibots Trading Algorithm HFT 

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Contributions](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)

## 📖 Introduction

This project is implementation of high-frequency trading (HFT) bots that use various strategies, user predefined,  to identify and execute trades on various stock tickers. The bot reads historical minute data, executes the strategy, and places buy or sell orders based on programmed conditions.

## 🏆 Current Achievements 

- **Positive ROI for Buy/Hold** : Our Buy_hold strategy is currently being tested with Warren' buffets portfolio and is making around 2,000 per day which marked the first positive P & L since inception 

- **Long/short executes 100,000 trades in a historic run** : Our Long/short strategy recently did 100k + Trades in a single Day run and we helped us validate its shell-life per trade. We thank AWS powerful EC2 Servers as always

## 🚀 Features

- **Some Strategy : Long Hold strategy**: Runs the HFT and determines which stocks to short/hold throghout the day after user provides them
- **Automated Trading**: Automatically places buy and sell orders based on the strategy. Turns on at 0930 Hrs NY Time and Sleeps at 03:45 hrs NY Time. 
- **Email Alerts**: Sends email notifications for trade executions.
- **Order Logging**: Logs all executed orders to a CSV / Graph file for record-keeping.

## 🔄 Updates and Project Goals

I am currently reprogramming all strategies within the [`Backtesting Algorithms`] folder to be real-time HFT algorithms with trading bot capabalities. The user can also backtest with them . This will allow for a more modular and flexible approach to trading strategies. Users can now choose to run any algorithm manually that is labelled 'strategy' if they prefer, without relying solely on the ROC strategy. This enhancement aims to provide greater flexibility and customization for different trading needs.

## 🛠️ Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/trading-algorithm-bot.git
    cd trading-algorithm-bot
    ```

2. **Create a virtual environment and activate it**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install the required dependencies**:
    ```
    bash
    pip install -r requirements.txt
    
    ```

4. **Set up environment variables**:
    ```bash
    export EMAIL_ADDRESS="your_email@example.com"
    export EMAIL_PASSWORD="your_email_password"
    export ALPACA_API_KEY = "your_apca_api_key_id"
    export ALPACA_API_SECRET_KEY =  "your_apca_secret_key"
    ```

## 📈 Usage

1. **Prepare your tick data**:
    - Ensure the program is downloading files for each ticker in the `tick_data` directory. Each file should follow the structure:
      ```csv
      Datetime,Open,High,Low,Close,Adj Close,Volume
      2024-09-05 10:32,54.209999084472656,54.209999084472656,54.18000030517578,54.209999084472656,54.209999084472656,0
    - You can also run `python run Alpacafetchmain.py` and fetch data from alpaca real-time(requires subscription) but can be used for historical data
      ```

2. **Run the algorithm (You can tweak and add more strategies inside algorithms/defined Technical Indicators)**:
    ```bash
    python main.py
    ```

## 📧 Email Alerts

The bot sends email alerts for each trade execution. Ensure you have set the `EMAIL_ADDRESS` and `EMAIL_PASSWORD` environment variables correctly.

## 📊 Order Logging

All executed orders are logged in the `Orders.csv` file with details such as time, ticker, type, price, quantity, total, and account balance.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📞 Contact

For any inquiries, please contact [franklinemisango4@gmail.com](mailto:your_email@example.com).

---

*Happy Trading!*