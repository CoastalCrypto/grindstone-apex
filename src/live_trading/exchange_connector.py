"""Exchange integration for live trading via CCXT."""
import logging
import os
import ccxt
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ExchangeConnector:
    """Connect to exchange and execute live trades."""

    def __init__(self, exchange_type: str = None, sandbox: bool = True):
        """
        Initialize exchange connection.

        Args:
            exchange_type: Exchange name (coinbase, binance, kraken, etc.)
            sandbox: Use sandbox/paper trading (default True)
        """
        self.exchange_type = exchange_type or settings.exchange_type
        self.sandbox = sandbox

        try:
            # Get exchange class
            exchange_class = getattr(ccxt, self.exchange_type)

            api_key = settings.exchange_api_key if sandbox else settings.live_api_key
            secret = settings.exchange_secret if sandbox else settings.live_api_secret
            password = settings.exchange_password if sandbox else settings.live_api_password

            # Initialize with API keys
            self.exchange = exchange_class({
                "apiKey": api_key,
                "secret": secret,
                "password": password,
                "sandbox": sandbox,
                "enableRateLimit": True,
                "timeout": 30000,
            })

            logger.info(f"Connected to {self.exchange_type} ({'sandbox' if sandbox else 'live'})")

        except AttributeError:
            logger.error(f"Exchange {self.exchange_type} not found in CCXT")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize {self.exchange_type}: {e}")
            raise

    def get_balance(self, currency: str = "USDT") -> Dict:
        """
        Get account balance.

        Args:
            currency: Currency to check (default USDT)

        Returns:
            Balance dict with free/used/total
        """
        try:
            balance = self.exchange.fetch_balance()

            if currency not in balance:
                return {"free": 0, "used": 0, "total": 0}

            return {
                "free": balance[currency]["free"],
                "used": balance[currency]["used"],
                "total": balance[currency]["total"],
            }

        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {"error": str(e)}

    def get_ticker(self, pair: str) -> Dict:
        """
        Get current ticker information.

        Args:
            pair: Trading pair (e.g., BTC/USDT)

        Returns:
            Ticker info with bid/ask/last price
        """
        try:
            ticker = self.exchange.fetch_ticker(pair)

            return {
                "pair": pair,
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "last": ticker["last"],
                "timestamp": ticker["timestamp"],
            }

        except Exception as e:
            logger.error(f"Error fetching ticker {pair}: {e}")
            return {"error": str(e)}

    def place_limit_order(
        self,
        pair: str,
        side: str,
        amount: float,
        price: float,
        order_id: str = None
    ) -> Dict:
        """
        Place a limit order.

        Args:
            pair: Trading pair (BTC/USDT)
            side: 'buy' or 'sell'
            amount: Amount to trade
            price: Price per unit
            order_id: Optional custom order ID

        Returns:
            Order confirmation
        """
        try:
            logger.info(f"Placing {side} order: {amount} {pair} @ {price}")

            order = self.exchange.create_limit_order(
                symbol=pair,
                side=side,
                amount=amount,
                price=price,
                params={"clientOrderId": order_id} if order_id else {}
            )

            logger.info(f"✓ Order placed: {order['id']}")

            return {
                "order_id": order["id"],
                "pair": pair,
                "side": side,
                "amount": amount,
                "price": price,
                "status": order.get("status", "pending"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": str(e)}

    def place_market_order(
        self,
        pair: str,
        side: str,
        amount: float
    ) -> Dict:
        """
        Place a market order (execute immediately at market price).

        Args:
            pair: Trading pair
            side: 'buy' or 'sell'
            amount: Amount to trade

        Returns:
            Order confirmation
        """
        try:
            logger.info(f"Placing {side} market order: {amount} {pair}")

            order = self.exchange.create_market_order(
                symbol=pair,
                side=side,
                amount=amount
            )

            logger.info(f"✓ Market order filled: {order['id']}")

            return {
                "order_id": order["id"],
                "pair": pair,
                "side": side,
                "amount": amount,
                "status": order.get("status", "closed"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return {"error": str(e)}

    def create_stop_loss_order(
        self,
        pair: str,
        amount: float,
        stop_price: float
    ) -> Dict:
        """
        Create a stop-loss order.

        Args:
            pair: Trading pair
            amount: Amount to sell
            stop_price: Price at which to trigger

        Returns:
            Order confirmation
        """
        try:
            logger.info(f"Creating stop-loss: {amount} {pair} @ {stop_price}")

            order = self.exchange.create_order(
                symbol=pair,
                type="stop_loss",
                side="sell",
                amount=amount,
                stopPrice=stop_price,
                params={"stopPrice": stop_price}
            )

            return {
                "order_id": order["id"],
                "type": "stop_loss",
                "pair": pair,
                "amount": amount,
                "stop_price": stop_price,
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Error creating stop-loss: {e}")
            return {"error": str(e)}

    def cancel_order(self, order_id: str, pair: str) -> Dict:
        """
        Cancel an open order.

        Args:
            order_id: Order ID to cancel
            pair: Trading pair

        Returns:
            Cancellation confirmation
        """
        try:
            logger.info(f"Cancelling order {order_id}")

            result = self.exchange.cancel_order(order_id, pair)

            logger.info(f"✓ Order cancelled: {order_id}")

            return {
                "order_id": order_id,
                "status": "cancelled",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"error": str(e)}

    def get_order_status(self, order_id: str, pair: str) -> Dict:
        """
        Get status of an order.

        Args:
            order_id: Order ID
            pair: Trading pair

        Returns:
            Order status info
        """
        try:
            order = self.exchange.fetch_order(order_id, pair)

            return {
                "order_id": order_id,
                "status": order["status"],
                "filled": order.get("filled", 0),
                "remaining": order.get("remaining", 0),
                "average_price": order.get("average", 0),
                "timestamp": order.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
            return {"error": str(e)}

    def get_open_orders(self, pair: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.

        Args:
            pair: Optional filter by pair

        Returns:
            List of open orders
        """
        try:
            orders = self.exchange.fetch_open_orders(pair)

            return [
                {
                    "order_id": o["id"],
                    "pair": o["symbol"],
                    "side": o["side"],
                    "amount": o["amount"],
                    "price": o["price"],
                    "status": o["status"],
                    "timestamp": o["timestamp"],
                }
                for o in orders
            ]

        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    def get_closed_trades(self, pair: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get closed trades/orders.

        Args:
            pair: Optional filter by pair
            limit: Max results

        Returns:
            List of closed trades
        """
        try:
            orders = self.exchange.fetch_closed_orders(pair, limit=limit)

            return [
                {
                    "order_id": o["id"],
                    "pair": o["symbol"],
                    "side": o["side"],
                    "amount": o["amount"],
                    "price": o["price"],
                    "average": o.get("average", 0),
                    "filled": o.get("filled", 0),
                    "status": o["status"],
                    "timestamp": o["timestamp"],
                }
                for o in orders
            ]

        except Exception as e:
            logger.error(f"Error fetching closed trades: {e}")
            return []

    def get_trading_pair_info(self, pair: str) -> Dict:
        """
        Get trading pair information (min order, fees, etc.).

        Args:
            pair: Trading pair

        Returns:
            Pair limits and info
        """
        try:
            markets = self.exchange.fetch_markets()

            for market in markets:
                if market["symbol"] == pair:
                    return {
                        "pair": pair,
                        "min_order_amount": market["limits"]["amount"]["min"],
                        "max_order_amount": market["limits"]["amount"]["max"],
                        "min_order_value": market["limits"]["cost"]["min"],
                        "max_order_value": market["limits"]["cost"]["max"],
                        "maker_fee": market["maker"],
                        "taker_fee": market["taker"],
                    }

            return {"error": f"Pair {pair} not found"}

        except Exception as e:
            logger.error(f"Error fetching pair info: {e}")
            return {"error": str(e)}

    def calculate_order_cost(self, amount: float, price: float) -> Dict:
        """
        Calculate order cost including fees.

        Args:
            amount: Order amount
            price: Price per unit

        Returns:
            Cost breakdown
        """
        total_cost = amount * price
        taker_fee = total_cost * settings.trading_fees
        total_with_fees = total_cost + taker_fee

        return {
            "amount": amount,
            "price": price,
            "subtotal": total_cost,
            "fees": taker_fee,
            "total": total_with_fees,
            "fee_percentage": (taker_fee / total_cost * 100) if total_cost > 0 else 0,
        }


def get_exchange_connector(sandbox: bool = True) -> ExchangeConnector:
    """
    Get or create exchange connector.

    Args:
        sandbox: Use sandbox mode (default True)

    Returns:
        ExchangeConnector instance
    """
    return ExchangeConnector(
        exchange_type=settings.exchange_type,
        sandbox=sandbox
    )
