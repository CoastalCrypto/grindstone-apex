"""Manage open trading positions."""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from src.database import LiveTrade
from src.live_trading.exchange_connector import ExchangeConnector

logger = logging.getLogger(__name__)


class PositionManager:
    """Track and manage open trading positions."""

    def __init__(self, connector: ExchangeConnector, db: Session):
        """
        Initialize position manager.

        Args:
            connector: ExchangeConnector instance
            db: Database session
        """
        self.connector = connector
        self.db = db

    def open_position(
        self,
        strategy_id: str,
        pair: str,
        entry_price: float,
        size: float,
        stop_loss: float,
        take_profit: float,
        leverage: float = 1.0
    ) -> Dict:
        """
        Open a new trading position.

        Args:
            strategy_id: Strategy opening the trade
            pair: Trading pair
            entry_price: Entry price
            size: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            leverage: Leverage multiplier (default 1.0)

        Returns:
            Position confirmation
        """
        try:
            logger.info(f"Opening position: {pair} {size} @ {entry_price}")

            # Adjust size for leverage
            leveraged_size = size * leverage

            # Place entry order (market order for immediate execution)
            entry_order = self.connector.place_market_order(
                pair=pair,
                side="buy",
                amount=leveraged_size
            )

            if "error" in entry_order:
                logger.error(f"Failed to place entry order: {entry_order['error']}")
                return entry_order

            # Place stop-loss
            sl_order = self.connector.create_stop_loss_order(
                pair=pair,
                amount=leveraged_size,
                stop_price=stop_loss
            )

            # Place take-profit (limit order)
            tp_order = self.connector.place_limit_order(
                pair=pair,
                side="sell",
                amount=leveraged_size,
                price=take_profit
            )

            # Record in database
            trade = LiveTrade(
                id=f"trade_{entry_order['order_id']}",
                strategy_id=strategy_id,
                pair=pair,
                entry_price=entry_price,
                size=leveraged_size,
                entry_value=entry_price * leveraged_size,
                entry_time=datetime.utcnow(),
                entry_order_id=entry_order.get("order_id"),
                status="open"
            )

            self.db.add(trade)
            self.db.commit()

            logger.info(f"✓ Position opened: {trade.id}")

            return {
                "position_id": trade.id,
                "strategy_id": strategy_id,
                "pair": pair,
                "size": leveraged_size,
                "entry_price": entry_price,
                "entry_value": entry_price * leveraged_size,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "open",
                "entry_order_id": entry_order.get("order_id"),
                "sl_order_id": sl_order.get("order_id"),
                "tp_order_id": tp_order.get("order_id"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return {"error": str(e)}

    def close_position(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = "manual"
    ) -> Dict:
        """
        Close a trading position.

        Args:
            trade_id: Trade ID to close
            exit_price: Exit price
            exit_reason: Why the trade closed (tp, sl, manual)

        Returns:
            Close confirmation
        """
        try:
            trade = self.db.query(LiveTrade).filter(LiveTrade.id == trade_id).first()

            if not trade or trade.status == "closed":
                return {"error": "Trade not found or already closed"}

            logger.info(f"Closing position: {trade_id} @ {exit_price}")

            # Calculate P&L
            pnl = (exit_price - trade.entry_price) * trade.size
            pnl_pct = (pnl / trade.entry_value) * 100

            # Record exit
            exit_order = self.connector.place_market_order(
                pair=trade.pair,
                side="sell",
                amount=trade.size
            )

            # Update database
            trade.exit_price = exit_price
            trade.exit_time = datetime.utcnow()
            trade.pnl = pnl
            trade.pnl_percent = pnl_pct
            trade.status = "closed"
            trade.exit_reason = exit_reason
            trade.exit_order_id = exit_order.get("order_id")

            self.db.add(trade)
            self.db.commit()

            logger.info(f"✓ Position closed: PnL = {pnl:.2f} ({pnl_pct:.2f}%)")

            return {
                "trade_id": trade_id,
                "pair": trade.pair,
                "entry_price": trade.entry_price,
                "exit_price": exit_price,
                "size": trade.size,
                "pnl": pnl,
                "pnl_percent": pnl_pct,
                "exit_reason": exit_reason,
                "status": "closed",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {"error": str(e)}

    def get_open_positions(self, strategy_id: Optional[str] = None) -> List[Dict]:
        """
        Get all open positions.

        Args:
            strategy_id: Optional filter by strategy

        Returns:
            List of open positions
        """
        query = self.db.query(LiveTrade).filter(LiveTrade.status == "open")

        if strategy_id:
            query = query.filter(LiveTrade.strategy_id == strategy_id)

        trades = query.all()

        return [
            {
                "trade_id": t.id,
                "strategy_id": t.strategy_id,
                "pair": t.pair,
                "entry_price": t.entry_price,
                "size": t.size,
                "entry_value": t.entry_value,
                "entry_time": t.entry_time.isoformat(),
                "status": "open",
            }
            for t in trades
        ]

    def get_position_status(self, trade_id: str, current_price: Optional[float] = None) -> Dict:
        """
        Get current status of a position.

        Args:
            trade_id: Trade ID
            current_price: Current market price (for unrealized P&L)

        Returns:
            Position status
        """
        trade = self.db.query(LiveTrade).filter(LiveTrade.id == trade_id).first()

        if not trade:
            return {"error": "Trade not found"}

        status = {
            "trade_id": trade_id,
            "strategy_id": trade.strategy_id,
            "pair": trade.pair,
            "entry_price": trade.entry_price,
            "size": trade.size,
            "status": trade.status,
            "entry_time": trade.entry_time.isoformat(),
        }

        if trade.status == "open" and current_price:
            # Calculate unrealized P&L
            unrealized_pnl = (current_price - trade.entry_price) * trade.size
            unrealized_pnl_pct = (unrealized_pnl / trade.entry_value) * 100

            status.update({
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percent": unrealized_pnl_pct,
            })

        elif trade.status == "closed":
            status.update({
                "exit_price": trade.exit_price,
                "realized_pnl": trade.pnl,
                "realized_pnl_percent": trade.pnl_percent,
                "exit_time": trade.exit_time.isoformat(),
                "exit_reason": trade.exit_reason,
            })

        return status

    def update_breakeven_stop(
        self,
        trade_id: str,
        current_price: float,
        breakeven_buffer: float = 0.0
    ) -> Dict:
        """
        Move stop-loss to breakeven when profitable.

        Args:
            trade_id: Trade ID
            current_price: Current market price
            breakeven_buffer: Buffer above entry (default 0 = exact breakeven)

        Returns:
            Update confirmation
        """
        trade = self.db.query(LiveTrade).filter(LiveTrade.id == trade_id).first()

        if not trade or trade.status == "closed":
            return {"error": "Trade not found or already closed"}

        # Check if profitable
        current_pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100

        if current_pnl_pct > 1.0:  # At least 1% profit
            new_stop = trade.entry_price + breakeven_buffer

            logger.info(f"Moving stop-loss to breakeven: {new_stop}")

            # In real implementation, would update the actual stop-loss order on exchange
            # For now, just log the action

            return {
                "trade_id": trade_id,
                "action": "breakeven_stop",
                "new_stop_price": new_stop,
                "current_price": current_price,
                "current_pnl_pct": current_pnl_pct,
                "status": "updated",
            }

        return {
            "trade_id": trade_id,
            "status": "not_profitable_yet",
            "current_pnl_pct": current_pnl_pct,
            "threshold": 1.0,
        }

    def get_position_summary(self, strategy_id: Optional[str] = None) -> Dict:
        """
        Get summary of all positions.

        Args:
            strategy_id: Optional filter by strategy

        Returns:
            Summary statistics
        """
        query = self.db.query(LiveTrade)

        if strategy_id:
            query = query.filter(LiveTrade.strategy_id == strategy_id)

        trades = query.all()

        open_trades = [t for t in trades if t.status == "open"]
        closed_trades = [t for t in trades if t.status == "closed"]

        # Calculate stats
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        total_trades = len(closed_trades)
        winning_trades = sum(1 for t in closed_trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in closed_trades if t.pnl and t.pnl < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        return {
            "open_positions": len(open_trades),
            "closed_trades": len(closed_trades),
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0,
        }
