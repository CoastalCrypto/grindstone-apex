"""Live trading execution service - real-time strategy deployment and monitoring."""
import logging
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

from src.database import (
    SessionLocal, Strategy, LiveTrade, StrategyPerformance,
    SystemMetrics
)
from src.config import get_settings
from src.backtesting.data_loader import get_data_loader
from src.live_trading.exchange_connector import ExchangeConnector
from src.live_trading.position_manager import PositionManager
from src.live_trading.performance_monitor import PerformanceMonitor
from src.alerts.alert_system import AlertSystem

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class LiveTradingService:
    """Background service for live strategy execution and monitoring."""

    def __init__(self):
        """Initialize live trading service."""
        self.db = SessionLocal()
        self.settings = settings
        self.loader = get_data_loader()
        self.connector = ExchangeConnector(
            exchange_type=settings.live_exchange,
            sandbox=settings.sandbox_mode
        )
        # PositionManager expects (connector, db) — db was previously passed first by mistake
        self.position_manager = PositionManager(self.connector, self.db)
        self.performance_monitor = PerformanceMonitor(self.db)
        self.alert_system = AlertSystem()

        self.active_strategies: Dict[str, Dict] = {}
        self.running = False

    def run_continuous(self, check_interval: int = 60):
        """
        Run continuous live trading monitoring loop.

        Args:
            check_interval: Seconds between signal checks (default 60)
        """
        logger.info("="*60)
        logger.info("Starting Live Trading Service")
        logger.info(f"Exchange: {settings.live_exchange}")
        logger.info(f"Sandbox mode: {settings.sandbox_mode}")
        logger.info(f"Check interval: {check_interval}s")
        logger.info("="*60)

        self.running = True

        while self.running:
            try:
                # Refresh active strategies
                self._refresh_active_strategies()

                # Monitor each strategy
                for strategy_id, strategy_data in self.active_strategies.items():
                    try:
                        self._monitor_strategy(strategy_id, strategy_data)
                    except Exception as e:
                        logger.error(f"Error monitoring strategy {strategy_id}: {e}")
                        self.alert_system.send_alert(
                            "ERROR",
                            f"Strategy {strategy_id} monitoring failed",
                            f"Error: {str(e)}"
                        )

                # Update system metrics
                self._update_system_metrics()

                # Check for underperforming strategies
                self._check_strategy_health()

                # Wait for next check
                logger.debug(f"Waiting {check_interval}s for next cycle...")
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Live trading service stopped by user")
                self.running = False
                break

            except Exception as e:
                logger.error(f"Error in live trading loop: {e}", exc_info=True)
                self.alert_system.send_alert(
                    "ERROR",
                    "Live trading service error",
                    f"Error: {str(e)}\n\nService will retry in {check_interval}s"
                )
                time.sleep(check_interval)

    def _refresh_active_strategies(self) -> None:
        """Load/refresh deployed strategies from database."""
        try:
            strategies = self.db.query(StrategyPerformance).filter(
                StrategyPerformance.deployed == True,
                StrategyPerformance.live_active == True
            ).all()

            for perf in strategies:
                strategy = self.db.query(Strategy).filter(
                    Strategy.id == perf.strategy_id
                ).first()

                if strategy:
                    self.active_strategies[strategy.id] = {
                        "strategy": strategy,
                        "performance": perf,
                        "last_signal_time": None,
                        "last_check": datetime.utcnow()
                    }

            logger.info(f"Active strategies loaded: {len(self.active_strategies)}")

        except Exception as e:
            logger.error(f"Error refreshing strategies: {e}")

    def _monitor_strategy(self, strategy_id: str, strategy_data: Dict) -> None:
        """
        Monitor a single strategy for entry signals.

        Args:
            strategy_id: Strategy ID
            strategy_data: Strategy metadata
        """
        strategy = strategy_data["strategy"]
        pair = strategy.pair

        # Timeframes stored as JSON list of ints [15, 60, 240] or strings
        # Always normalize to integers for the loader
        raw_timeframes = strategy.timeframes or [15]
        if isinstance(raw_timeframes, str):
            import json as _json
            try:
                raw_timeframes = _json.loads(raw_timeframes)
            except Exception:
                raw_timeframes = [15]
        timeframes = [int(tf) for tf in raw_timeframes if str(tf).isdigit() or isinstance(tf, int)]
        if not timeframes:
            timeframes = [15]

        try:
            # Load current candles — keyed by int timeframe
            candles_data = {}
            for tf in timeframes:
                candles = self.loader.load_candles(pair, tf, 365)
                if not hasattr(candles, 'empty') or candles.empty:
                    logger.warning(f"No data for {pair} {tf}m")
                    return
                candles_data[tf] = candles

            # Generate signals from current data
            signal = self._generate_signal(strategy, candles_data)

            if signal:
                logger.info(f"🎯 SIGNAL: {strategy_id} on {pair}")
                logger.info(f"   Signal type: {signal['type']}")
                logger.info(f"   Confidence: {signal.get('confidence', 0)*100:.1f}%")

                # Check existing positions
                open_positions = self.position_manager.get_open_positions(strategy_id)

                if signal["type"] == "buy":
                    if len(open_positions) < strategy.position_sizing.get("max_concurrent", 1):
                        self._execute_entry(strategy_id, strategy, pair, signal)
                    else:
                        logger.info(f"Max concurrent positions reached for {strategy_id}")

                elif signal["type"] == "sell" and open_positions:
                    # Close positions
                    for position in open_positions:
                        self._execute_exit(position["id"], signal.get("exit_price"))

                # Update last signal time
                strategy_data["last_signal_time"] = datetime.utcnow()

            # Monitor existing positions
            for position in self.position_manager.get_open_positions(strategy_id):
                self._monitor_position(position, strategy, candles_data)

        except Exception as e:
            logger.error(f"Error monitoring strategy {strategy_id}: {e}")

    def _generate_signal(self, strategy: Strategy, candles_data: Dict) -> Optional[Dict]:
        """
        Generate trading signal from candles using the full strategy-type dispatch.

        Runs the VectorBT signal logic on recent candle data and checks if
        the last few bars produced an entry signal.

        Args:
            strategy: Strategy object
            candles_data: Dict of timeframe -> candles (keyed by int, e.g. 15)

        Returns:
            Signal dict with keys {type, price, confidence, timestamp} or None
        """
        try:
            from src.backtesting.vectorbt_engine import VectorBTBacktestEngine

            # candles_data is keyed by int (15, 60, 240)
            candles = candles_data.get(15) or candles_data.get("15m")
            if candles is None or not hasattr(candles, 'empty') or candles.empty:
                logger.warning("No 15m candles available for signal generation")
                return None

            # Need enough history for indicators to warm up
            if len(candles) < 100:
                logger.warning(f"Not enough candle history: {len(candles)} bars")
                return None

            # Build strategy_params dict from the Strategy object
            indicators = strategy.indicators or {}
            if isinstance(indicators, str):
                import json as _json
                try:
                    indicators = _json.loads(indicators)
                    # Handle double-encoded JSON
                    if isinstance(indicators, str):
                        indicators = _json.loads(indicators)
                except Exception:
                    indicators = {}

            strategy_params = {
                "strategy_type": strategy.strategy_type or "sma_crossover",
                "direction": strategy.direction or "long",
                "indicators": indicators,
            }

            # Run signal generation on the full candle history
            engine = VectorBTBacktestEngine()
            buy_signals, sell_signals = engine._generate_signals(candles, strategy_params)

            direction = strategy.direction or "long"
            latest_price = float(candles["close"].iloc[-1])

            # Check last 3 bars for a fresh signal (avoid acting on old ones)
            look_back = 3
            recent_buy = buy_signals.iloc[-look_back:].any()
            recent_sell = sell_signals.iloc[-look_back:].any()

            if direction == "long":
                if recent_buy:
                    logger.info(f"  → BUY signal for {strategy.strategy_type} (long)")
                    return {
                        "type": "buy",
                        "price": latest_price,
                        "confidence": 0.75,
                        "timestamp": datetime.utcnow()
                    }
                if recent_sell:
                    logger.info(f"  → SELL/EXIT signal for {strategy.strategy_type} (long)")
                    return {
                        "type": "sell",
                        "price": latest_price,
                        "confidence": 0.75,
                        "timestamp": datetime.utcnow()
                    }

            elif direction == "short":
                # For shorts: sell_signal = entry, buy_signal = exit
                if recent_sell:
                    logger.info(f"  → SHORT entry signal for {strategy.strategy_type}")
                    return {
                        "type": "buy",   # mapped to "buy" so caller opens a position
                        "price": latest_price,
                        "confidence": 0.75,
                        "direction": "short",
                        "timestamp": datetime.utcnow()
                    }
                if recent_buy:
                    logger.info(f"  → SHORT exit signal for {strategy.strategy_type}")
                    return {
                        "type": "sell",
                        "price": latest_price,
                        "confidence": 0.75,
                        "timestamp": datetime.utcnow()
                    }

            return None

        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return None

    def _execute_entry(self, strategy_id: str, strategy: Strategy,
                       pair: str, signal: Dict) -> None:
        """
        Execute entry order.

        Args:
            strategy_id: Strategy ID
            strategy: Strategy object
            pair: Trading pair
            signal: Signal dict
        """
        try:
            entry_price = signal["price"]

            # Calculate position size
            account_balance = self.connector.get_balance("USDT")["free"]
            position_sizing = strategy.position_sizing or {}

            if position_sizing.get("sizing_mode") == "fixed_amount":
                risk_amount = position_sizing.get("fixed_amount", 100)
            else:
                risk_amount = account_balance * position_sizing.get("risk_percentage", 0.02)

            position_size = risk_amount / entry_price

            # Calculate stop loss (ATR-based)
            risk_mgmt = strategy.risk_management or {}
            atr_multiplier = risk_mgmt.get("atr_multiplier", 3)

            # Simple ATR calculation (use int timeframe, not string)
            candles = self.loader.load_candles(pair, 15, 365)
            if not candles.empty:
                atr = self._calculate_atr(candles, periods=14)
                stop_loss = entry_price - (atr * atr_multiplier)
            else:
                stop_loss = entry_price * 0.95

            take_profit = entry_price * (1 + risk_mgmt.get("profit_target", 0.02))

            logger.info(f"📈 Opening position: {pair}")
            logger.info(f"   Size: {position_size:.4f}")
            logger.info(f"   Entry: ${entry_price:.2f}")
            logger.info(f"   Stop: ${stop_loss:.2f}")
            logger.info(f"   Target: ${take_profit:.2f}")

            # Open position
            trade = self.position_manager.open_position(
                strategy_id=strategy_id,
                pair=pair,
                entry_price=entry_price,
                size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=position_sizing.get("leverage", 1)
            )

            if trade:
                self.alert_system.send_alert(
                    "ENTRY",
                    f"{pair} Long Entry",
                    f"Strategy: {strategy_id}\n"
                    f"Size: {position_size:.4f}\n"
                    f"Entry: ${entry_price:.2f}\n"
                    f"Stop: ${stop_loss:.2f}\n"
                    f"Target: ${take_profit:.2f}"
                )

        except Exception as e:
            logger.error(f"Error executing entry: {e}")
            self.alert_system.send_alert(
                "ERROR",
                "Entry execution failed",
                f"Strategy {strategy_id} entry failed: {str(e)}"
            )

    def _execute_exit(self, trade_id: str, exit_price: Optional[float] = None) -> None:
        """
        Execute exit order.

        Args:
            trade_id: Trade ID
            exit_price: Optional manual exit price
        """
        try:
            trade = self.db.query(LiveTrade).filter(
                LiveTrade.id == trade_id
            ).first()

            if not trade:
                logger.warning(f"Trade {trade_id} not found")
                return

            # Get current price if not provided
            if exit_price is None:
                ticker = self.connector.get_ticker(trade.pair)
                exit_price = ticker["last"]

            pnl = (exit_price - trade.entry_price) * trade.size - trade.fees_paid
            pnl_pct = (pnl / (trade.entry_price * trade.size)) * 100

            logger.info(f"📉 Closing position: {trade.pair}")
            logger.info(f"   Exit: ${exit_price:.2f}")
            logger.info(f"   P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")

            # Close position
            closed_trade = self.position_manager.close_position(
                trade_id=trade_id,
                exit_price=exit_price,
                exit_reason="signal"
            )

            if closed_trade:
                alert_type = "WIN" if pnl > 0 else "LOSS"
                self.alert_system.send_alert(
                    alert_type,
                    f"{trade.pair} Exit",
                    f"Exit Price: ${exit_price:.2f}\n"
                    f"P&L: ${pnl:.2f} ({pnl_pct:.2f}%)\n"
                    f"Duration: {(datetime.utcnow() - trade.entry_time).seconds}s"
                )

        except Exception as e:
            logger.error(f"Error executing exit: {e}")

    def _monitor_position(self, position: Dict, strategy: Strategy,
                         candles_data: Dict) -> None:
        """
        Monitor open position for stop/profit targets.

        Args:
            position: Position dict
            strategy: Strategy object
            candles_data: Candles by timeframe
        """
        try:
            _c = candles_data.get(15) or candles_data.get("15m")
            if _c is None or not hasattr(_c, 'empty') or _c.empty:
                return
            current_price = _c.iloc[-1]["close"]
            trade = self.db.query(LiveTrade).filter(
                LiveTrade.id == position["id"]
            ).first()

            if not trade:
                return

            # Check stop loss
            if current_price <= trade.stop_loss:
                logger.warning(f"🛑 Stop loss hit: {strategy.pair}")
                self._execute_exit(trade.id, trade.stop_loss)
                return

            # Check take profit
            if current_price >= trade.take_profit:
                logger.info(f"✅ Take profit hit: {strategy.pair}")
                self._execute_exit(trade.id, trade.take_profit)
                return

            # Update breakeven stop if profitable
            pnl = (current_price - trade.entry_price) * trade.size
            if pnl > 0 and pnl > (trade.entry_price * trade.size * 0.01):  # 1% profit
                self.position_manager.update_breakeven_stop(
                    trade_id=trade.id,
                    current_price=current_price,
                    breakeven_buffer=0.01  # 1% buffer
                )

        except Exception as e:
            logger.error(f"Error monitoring position: {e}")

    def _check_strategy_health(self) -> None:
        """Check for underperforming strategies and alert."""
        try:
            for strategy_id in self.active_strategies:
                health = self.performance_monitor.get_strategy_health(strategy_id)

                if health.get("status") == "poor":
                    logger.warning(f"⚠️  Strategy {strategy_id} health is poor")

                    assessment = self.performance_monitor.flag_underperforming_strategy(
                        strategy_id
                    )

                    if assessment.get("action") == "retire":
                        logger.critical(f"🔴 Retiring strategy {strategy_id}")

                        # Disable strategy
                        perf = self.db.query(StrategyPerformance).filter(
                            StrategyPerformance.strategy_id == strategy_id
                        ).first()

                        if perf:
                            perf.live_active = False
                            self.db.add(perf)
                            self.db.commit()

                            self.alert_system.send_alert(
                                "ALERT",
                                f"Strategy {strategy_id} retired",
                                f"Status: {assessment['status']}\n"
                                f"Recommendation: {assessment['recommendation']}"
                            )

        except Exception as e:
            logger.error(f"Error checking strategy health: {e}")

    def _update_system_metrics(self) -> None:
        """Update system metrics."""
        try:
            account = self.connector.get_balance("USDT")
            open_positions = self.db.query(LiveTrade).filter(
                LiveTrade.status == "open"
            ).count()

            metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                account_balance=account["total"],
                account_free=account["free"],
                account_used=account["used"],
                active_strategies=len(self.active_strategies),
                open_positions=open_positions
            )

            self.db.add(metrics)
            self.db.commit()

        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def _calculate_atr(self, candles, periods: int = 14) -> float:
        """Calculate Average True Range."""
        try:
            import pandas as pd
            high_low = candles['high'] - candles['low']
            high_close = (candles['high'] - candles['close'].shift()).abs()
            low_close = (candles['low'] - candles['close'].shift()).abs()

            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(periods).mean().iloc[-1]

            return float(atr) if not pd.isna(atr) else 0.0

        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0

    def stop(self) -> None:
        """Stop the service."""
        logger.info("Stopping live trading service...")
        self.running = False
        self.db.close()


def main():
    """Entry point for live trading service."""
    service = LiveTradingService()

    try:
        # Run with 60-second check interval
        service.run_continuous(check_interval=60)
    except KeyboardInterrupt:
        logger.info("Service stopped")
    finally:
        service.stop()


if __name__ == "__main__":
    main()
