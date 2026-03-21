import logging
import os
from dotenv import load_dotenv

# Force loading .env vars into os.environ before imports grab them
load_dotenv()

from src.live_trading.exchange_connector import ExchangeConnector
from src.alerts.alert_system import AlertSystem
from src.config import get_settings

def run_tests():
    settings = get_settings()
    print("="*50)
    print(f"Testing Blofin API (Sandbox: {settings.sandbox_mode})...")
    try:
        connector = ExchangeConnector(
            exchange_type=settings.live_exchange,
            sandbox=settings.sandbox_mode
        )
        balance = connector.get_balance("USDT")
        print(f"SUCCESS! USDT Balance: {balance}")
    except Exception as e:
        print(f"ERROR connecting to exchange: {e}")

    print("-" * 50)
    print("Testing Telegram Bot...")
    try:
        alerts = AlertSystem()
        alerts.send_alert(
            "INFO", 
            "Integration Test Successful", 
            "Paper trading exchange API and Telegram bot connections are both working properly!"
        )
        print("SUCCESS! Test message sent to your Telegram chat.")
    except Exception as e:
        print(f"ERROR sending Telegram message: {e}")
    print("="*50)

if __name__ == "__main__":
    run_tests()
