"""Alert system for trade notifications via email and Telegram."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dotenv import load_dotenv
import requests

load_dotenv()

logger = logging.getLogger(__name__)


class AlertSystem:
    """Send alerts via email and Telegram."""

    def __init__(self):
        """Initialize alert system."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.alert_email = os.getenv("ALERT_EMAIL")

        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        self.email_enabled = self.smtp_user and self.smtp_password and self.alert_email
        self.telegram_enabled = self.telegram_bot_token and self.telegram_chat_id

        if self.email_enabled:
            logger.info("Email alerts enabled")
        else:
            logger.warning("Email alerts disabled - check SMTP configuration")

        if self.telegram_enabled:
            logger.info("Telegram alerts enabled")
        else:
            logger.warning("Telegram alerts disabled - check Telegram configuration")

    def send_alert(self, alert_type: str, subject: str, message: str,
                   critical: bool = False) -> bool:
        """
        Send alert via all enabled channels.

        Args:
            alert_type: Type of alert (ENTRY, EXIT, WIN, LOSS, ERROR, ALERT)
            subject: Alert subject
            message: Alert message
            critical: Whether this is a critical alert

        Returns:
            True if sent successfully
        """
        try:
            emoji_map = {
                "ENTRY": "📈",
                "EXIT": "📉",
                "WIN": "✅",
                "LOSS": "❌",
                "ERROR": "🔴",
                "ALERT": "⚠️"
            }

            emoji = emoji_map.get(alert_type, "📢")

            success = True

            if self.email_enabled:
                if not self._send_email(alert_type, subject, message, emoji):
                    success = False

            if self.telegram_enabled:
                if not self._send_telegram(alert_type, subject, message, emoji):
                    success = False

            return success

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def _send_email(self, alert_type: str, subject: str, message: str,
                    emoji: str) -> bool:
        """
        Send alert via email.

        Args:
            alert_type: Type of alert
            subject: Subject
            message: Message body
            emoji: Emoji prefix

        Returns:
            True if successful
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"{emoji} {subject}"

            body = f"""
Trading Bot Alert

Type: {alert_type}
Subject: {subject}

Message:
{message}

---
Grindstone Apex Trading Bot
"""

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _send_telegram(self, alert_type: str, subject: str, message: str,
                       emoji: str) -> bool:
        """
        Send alert via Telegram.

        Args:
            alert_type: Type of alert
            subject: Subject
            message: Message body
            emoji: Emoji prefix

        Returns:
            True if successful
        """
        try:
            text = f"{emoji} *{subject}*\n\n{message}"

            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"

            payload = {
                "chat_id": self.telegram_chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info(f"Telegram alert sent: {subject}")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def send_startup_alert(self) -> None:
        """Send startup notification."""
        self.send_alert(
            "ALERT",
            "Live Trading Service Started",
            "The trading bot is now live and monitoring elite strategies for entry signals."
        )

    def send_shutdown_alert(self) -> None:
        """Send shutdown notification."""
        self.send_alert(
            "ALERT",
            "Live Trading Service Stopped",
            "The trading bot has been stopped.",
            critical=True
        )

    def send_daily_summary(self, summary: dict) -> None:
        """
        Send daily performance summary.

        Args:
            summary: Summary dict with stats
        """
        message = f"""
Daily Trading Summary

Trades Today: {summary.get('trades_today', 0)}
Winning Trades: {summary.get('winning_trades', 0)}
Losing Trades: {summary.get('losing_trades', 0)}
Win Rate: {summary.get('win_rate', 0)*100:.1f}%

Total P&L: ${summary.get('total_pnl', 0):.2f}
Best Trade: ${summary.get('best_trade', 0):.2f}
Worst Trade: ${summary.get('worst_trade', 0):.2f}

Account Balance: ${summary.get('account_balance', 0):.2f}
Active Strategies: {summary.get('active_strategies', 0)}
"""

        self.send_alert(
            "ALERT",
            "Daily Trading Summary",
            message
        )
