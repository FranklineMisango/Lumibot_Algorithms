# Lumibots Trading Algorithm HFT 

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Contributions](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)

## 📖 Introduction

This project is a high-frequency trading (HFT) bot that uses a Rate of Change (ROC) strategy to identify and execute trades on various stock tickers. The bot reads historical stock data, calculates the ROC, and places buy or sell orders based on predefined conditions.

## 🚀 Features

- **Dynamic ROC Calculation**: Calculates the ROC based on the `Close` price and dynamically determined timeframe.
- **Automated Trading**: Automatically places buy and sell orders based on the calculated ROC.
- **Email Alerts**: Sends email notifications for trade executions.
- **Order Logging**: Logs all executed orders to a CSV file for record-keeping.

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
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables**:
    ```bash
    export EMAIL_ADDRESS="your_email@example.com"
    export EMAIL_PASSWORD="your_email_password"
    ```

## 📈 Usage

1. **Prepare your tick data**:
    - Ensure you have CSV files for each ticker in the `tick_data` directory. Each file should follow the structure:
      ```csv
      Datetime,Open,High,Low,Close,Adj Close,Volume
      2024-09-05 10:32,54.209999084472656,54.209999084472656,54.18000030517578,54.209999084472656,54.209999084472656,0
      ```

2. **Run the algorithm**:
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