"""Fast backtesting engine using VectorBT."""
import pandas as pd
import numpy as np
import vectorbt as vbt
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings

from .metrics import Trade, BacktestMetrics, calculate_atr

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class VectorBTBacktestEngine:
    """High-speed backtesting using VectorBT library."""

    def __init__(self, initial_balance: float = 10000.0, fees: float = 0.001):
        """
        Initialize backtest engine.

        Args:
            initial_balance: Starting account balance
            fees: Trading fees as decimal (0.001 = 0.1%)
        """
        self.initial_balance = initial_balance
        self.fees = fees
        self.metrics_calculator = BacktestMetrics(initial_balance)

    def backtest_strategy(
        self,
        candles: pd.DataFrame,
        strategy_params: dict,
        strategy_id: str = None
    ) -> Dict:
        """
        Backtest a strategy against historical data.

        Args:
            candles: DataFrame with OHLCV data
            strategy_params: Strategy parameters dict
            strategy_id: Optional strategy identifier

        Returns:
            Dictionary with backtest results
        """
        try:
            # Generate signals
            buy_signals, sell_signals = self._generate_signals(candles, strategy_params)

            if buy_signals.sum() == 0:
                logger.warning(f"No buy signals generated for {strategy_id}")
                return self._empty_result()

            # Execute trades
            trades = self._execute_trades(
                candles,
                buy_signals,
                sell_signals,
                strategy_params
            )

            if not trades:
                logger.warning(f"No trades executed for {strategy_id}")
                return self._empty_result()

            # Calculate metrics
            metrics = self.metrics_calculator.calculate(trades, strategy_params)

            result = {
                "strategy_id": strategy_id,
                "num_trades": len(trades),
                "metrics": metrics,
                "trades": trades,
                "timestamp": datetime.utcnow(),
                "success": True,
            }

            return result

        except Exception as e:
            logger.error(f"Error backtesting strategy {strategy_id}: {e}")
            result = self._empty_result()
            result["error"] = str(e)
            return result

    def _generate_signals(
        self,
        candles: pd.DataFrame,
        strategy_params: dict
    ) -> Tuple[pd.Series, pd.Series]:
        """Generate buy/sell signals based on indicators."""
        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        volume = candles['volume'].values

        # Initialize signals
        buy_signal = np.zeros(len(close), dtype=bool)
        sell_signal = np.zeros(len(close), dtype=bool)

        # Get indicator parameters
        indicators = strategy_params.get('indicators', {})

        # SMA Crossover Strategy (primary)
        if 'sma_fast' in indicators and 'sma_slow' in indicators:
            sma_fast = self._calculate_sma(close, indicators['sma_fast'])
            sma_slow = self._calculate_sma(close, indicators['sma_slow'])

            # Buy signal: fast crosses above slow
            buy_signal = (sma_fast > sma_slow) & (
                np.roll(sma_fast, 1) <= np.roll(sma_slow, 1)
            )

            # Sell signal: fast crosses below slow
            sell_signal = (sma_fast < sma_slow) & (
                np.roll(sma_fast, 1) >= np.roll(sma_slow, 1)
            )

        # RSI Filter (only trade if RSI in range)
        if 'rsi_threshold_buy' in indicators and 'rsi_threshold_sell' in indicators:
            rsi = self._calculate_rsi(close, period=14)
            rsi_buy = indicators['rsi_threshold_buy']
            rsi_sell = indicators['rsi_threshold_sell']

            # Only buy if RSI is oversold
            buy_signal = buy_signal & (rsi < rsi_buy)

            # Sell signal if RSI is overbought
            sell_signal = sell_signal | (rsi > rsi_sell)

        # Bollinger Bands for volatility (optional)
        if 'bollinger_period' in indicators:
            bb_period = indicators['bollinger_period']
            bb_upper, bb_lower, bb_mid = self._calculate_bollinger_bands(close, bb_period)

            # Only buy if price is near lower band
            buy_signal = buy_signal & (close < bb_mid)

        # Ensure no consecutive buys/sells
        buy_signal = self._remove_consecutive(buy_signal)
        sell_signal = self._remove_consecutive(sell_signal)

        return pd.Series(buy_signal), pd.Series(sell_signal)

    def _execute_trades(
        self,
        candles: pd.DataFrame,
        buy_signals: pd.Series,
        sell_signals: pd.Series,
        strategy_params: dict
    ) -> List[Trade]:
        """Execute trades based on signals with position management."""
        trades = []
        position_active = False
        entry_price = None
        entry_time = None
        entry_index = None

        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        timestamps = candles['timestamp'].values

        risk_params = strategy_params.get('risk_management', {})
        atr_mult = risk_params.get('stop_loss_atr', 3.5)
        tp_percent = risk_params.get('take_profit_percent', 0.20)

        # Calculate ATR for stops
        df_with_atr = candles.copy()
        df_with_atr['atr'] = calculate_atr(
            df_with_atr['high'],
            df_with_atr['low'],
            df_with_atr['close'],
            period=14
        )
        atr_values = df_with_atr['atr'].values

        # Position sizing
        pos_size_type = strategy_params.get('position_sizing', {}).get('size_type', 'percent_of_balance')
        pos_size_amount = strategy_params.get('position_sizing', {}).get('size_amount', 0.5)

        if pos_size_type == 'percent_of_balance':
            position_value = self.initial_balance * pos_size_amount
        else:
            position_value = self.initial_balance * 0.5  # Default

        for i in range(len(candles)):
            current_price = close[i]
            current_time = timestamps[i]
            current_atr = atr_values[i] if not np.isnan(atr_values[i]) else 0

            # Entry logic
            if not position_active and buy_signals.iloc[i]:
                position_active = True
                entry_price = current_price
                entry_time = current_time
                entry_index = i

            # Exit logic
            elif position_active and entry_index is not None:
                # Calculate stop loss and take profit
                stop_loss = entry_price - (current_atr * atr_mult)
                take_profit = entry_price * (1 + tp_percent)

                # Check exit conditions
                exit_price = None
                exit_time = current_time
                exit_reason = None

                # Take profit hit
                if current_price >= take_profit:
                    exit_price = take_profit
                    exit_reason = "tp"

                # Stop loss hit
                elif current_price <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "sl"

                # Sell signal
                elif sell_signals.iloc[i]:
                    exit_price = current_price
                    exit_reason = "signal"

                # Execute exit
                if exit_price is not None:
                    # Calculate position size
                    size = position_value / entry_price

                    # Calculate P&L
                    fees = size * entry_price * self.fees + size * exit_price * self.fees
                    pnl = (exit_price - entry_price) * size - fees

                    # Create trade object
                    trade = Trade(
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size=size,
                        entry_time=pd.Timestamp(entry_time),
                        exit_time=pd.Timestamp(exit_time),
                        fees=fees
                    )

                    trades.append(trade)
                    position_active = False
                    entry_price = None
                    entry_time = None
                    entry_index = None

        # Close any open position at end of backtest
        if position_active and entry_price is not None:
            exit_price = close[-1]
            size = position_value / entry_price
            fees = size * entry_price * self.fees + size * exit_price * self.fees

            trade = Trade(
                entry_price=entry_price,
                exit_price=exit_price,
                size=size,
                entry_time=pd.Timestamp(entry_time),
                exit_time=pd.Timestamp(timestamps[-1]),
                fees=fees
            )
            trades.append(trade)

        return trades

    # Indicator Calculations
    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Simple Moving Average."""
        return pd.Series(prices).rolling(window=period).mean().values

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index."""
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.values

    def _calculate_bollinger_bands(
        self,
        prices: np.ndarray,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands."""
        sma = self._calculate_sma(prices, period)
        std = pd.Series(prices).rolling(window=period).std().values

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return upper, lower, sma

    def _remove_consecutive(self, signals: np.ndarray) -> np.ndarray:
        """Remove consecutive signals."""
        signals = signals.copy()
        for i in range(1, len(signals)):
            if signals[i] and signals[i - 1]:
                signals[i] = False
        return signals

    def _empty_result(self) -> Dict:
        """Return empty result dict."""
        return {
            "strategy_id": None,
            "num_trades": 0,
            "metrics": self.metrics_calculator._empty_metrics(),
            "trades": [],
            "timestamp": datetime.utcnow(),
            "success": False,
        }


def backtest_strategy(strategy: dict, candles: pd.DataFrame, **kwargs) -> Dict:
    """Convenience function for backtesting."""
    engine = VectorBTBacktestEngine(**kwargs)
    return engine.backtest_strategy(candles, strategy)
