"""Calculate backtesting metrics and scoring."""
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class Trade:
    """Represents a single trade."""

    def __init__(
        self,
        entry_price: float,
        exit_price: float,
        size: float,
        entry_time: pd.Timestamp,
        exit_time: pd.Timestamp,
        fees: float = 0.0
    ):
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.size = size
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.fees = fees

    @property
    def pnl(self) -> float:
        """Profit/loss in USDT."""
        return (self.exit_price - self.entry_price) * self.size - self.fees

    @property
    def pnl_pct(self) -> float:
        """Profit/loss as percentage."""
        return (self.pnl / (self.entry_price * self.size)) * 100

    @property
    def duration(self) -> float:
        """Trade duration in hours."""
        return (self.exit_time - self.entry_time).total_seconds() / 3600

    def is_winner(self) -> bool:
        """Whether this trade was profitable."""
        return self.pnl > 0


class BacktestMetrics:
    """Calculate comprehensive backtesting metrics."""

    def __init__(self, initial_balance: float = 10000.0):
        """
        Initialize metrics calculator.

        Args:
            initial_balance: Starting account balance
        """
        self.initial_balance = initial_balance

    def calculate(self, trades: List[Trade], strategy_params: dict = None) -> Dict:
        """
        Calculate all metrics for a list of trades.

        Args:
            trades: List of Trade objects
            strategy_params: Optional strategy parameters for reference

        Returns:
            Dictionary of calculated metrics
        """
        if not trades:
            return self._empty_metrics()

        # Basic metrics
        total_trades = len(trades)
        winners = [t for t in trades if t.is_winner()]
        losers = [t for t in trades if not t.is_winner()]

        win_count = len(winners)
        loss_count = len(losers)
        win_rate = win_count / total_trades if total_trades > 0 else 0

        # Profit metrics
        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = (total_pnl / self.initial_balance) * 100

        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))

        avg_win = (gross_profit / win_count) if win_count > 0 else 0
        avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0

        # Risk metrics
        equity_curve = self._calculate_equity_curve(trades)
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        sharpe_ratio = self._calculate_sharpe(equity_curve)
        sortino_ratio = self._calculate_sortino(equity_curve)

        # Consistency metrics
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        recovery_factor = (total_pnl / max_drawdown) if max_drawdown > 0 else float('inf')

        # Trade quality
        trade_durations = [t.duration for t in trades]
        avg_trade_duration = np.mean(trade_durations) if trade_durations else 0
        best_trade = max([t.pnl for t in trades]) if trades else 0
        worst_trade = min([t.pnl for t in trades]) if trades else 0

        # Fee impact
        total_fees = sum(t.fees for t in trades)
        fee_impact_pct = (total_fees / gross_profit * 100) if gross_profit > 0 else 0

        # Prepare metrics dict
        metrics = {
            # Profitability
            "total_profit": total_pnl,
            "total_profit_pct": total_pnl_pct,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,

            # Win/Loss
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,

            # Risk-Adjusted
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,

            # Consistency
            "profit_factor": profit_factor if profit_factor != float('inf') else 0,
            "recovery_factor": recovery_factor if recovery_factor != float('inf') else 0,

            # Trade Quality
            "avg_trade_duration": avg_trade_duration,
            "best_trade": best_trade,
            "worst_trade": worst_trade,

            # Fees
            "total_fees": total_fees,
            "fee_impact_pct": fee_impact_pct,

            # Extra
            "expectancy": self._calculate_expectancy(avg_win, avg_loss, win_rate),
        }

        # Calculate composite score
        metrics["composite_score"] = self.score_strategy(metrics)

        # Check if meets profitability criteria
        metrics["meets_criteria"] = self.check_profitability_criteria(metrics)

        return metrics

    def score_strategy(self, metrics: Dict) -> float:
        """
        Calculate composite score (0-100) for a strategy.

        Weights (tuned for real crypto markets):
        - 25% Win rate (50%+ = full marks)
        - 25% Risk-adjusted returns (Sharpe 1.5+ = full marks)
        - 20% Consistency (Profit factor 1.5+ = full marks)
        - 20% Net profit percentage (10%+ = full marks)
        - 10% Trade count bonus (more trades = more confidence)
        """
        try:
            # Win rate: 50%+ gets full 25 points
            win_rate_score = min(metrics['win_rate'] * 100 / 50.0 * 25, 25)

            # Sharpe: 1.5+ gets full 25 points (realistic for crypto)
            sharpe = max(metrics['sharpe_ratio'], 0)
            sharpe_score = min((sharpe / 1.5) * 25, 25)

            # Profit factor: 1.5+ gets full 20 points
            pf = max(metrics['profit_factor'], 0)
            consistency_score = min((pf / 1.5) * 20, 20)

            # Net profit: 10%+ gets full 20 points
            profit_pct = max(metrics['total_profit_pct'], 0)
            profit_score = min((profit_pct / 10.0) * 20, 20)

            # Trade count: 10+ trades gets full 10 points (penalize lucky 1-trade wonders)
            trade_count = metrics.get('total_trades', 0)
            trade_score = min((trade_count / 10.0) * 10, 10)

            total_score = win_rate_score + sharpe_score + consistency_score + profit_score + trade_score
            return min(total_score, 100)
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return 0

    def check_profitability_criteria(self, metrics: Dict) -> bool:
        """
        Check if strategy meets minimum profitability criteria.

        Criteria (tuned for real crypto markets):
        - Win rate >= 35% (trend-following can be profitable at lower win rates)
        - Sharpe ratio > 0.5 (realistic for crypto with high volatility)
        - Total profit > 0 (net positive after fees)
        - Max drawdown < 40% (crypto is volatile, allow wider drawdowns)
        - At least 3 trades (avoid lucky single-trade strategies)
        """
        criteria = {
            "min_win_rate": metrics['win_rate'] >= 0.35,
            "min_sharpe": metrics['sharpe_ratio'] > 0.5,
            "min_profit": metrics['total_profit'] > 0,
            "max_drawdown": metrics['max_drawdown'] < 0.40,
            "min_trades": metrics['total_trades'] >= 3,
        }

        # Log which criteria failed
        for criterion, passed in criteria.items():
            if not passed:
                logger.debug(f"Failed criterion: {criterion}")

        return all(criteria.values())

    def _calculate_equity_curve(self, trades: List[Trade]) -> np.ndarray:
        """Calculate equity curve over time."""
        equity = [self.initial_balance]
        for trade in trades:
            equity.append(equity[-1] + trade.pnl)
        return np.array(equity)

    def _calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """Calculate maximum drawdown as percentage."""
        if len(equity_curve) < 2:
            return 0.0

        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        return abs(np.min(drawdown))

    def _calculate_sharpe(self, equity_curve: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe ratio.

        For backtesting: uses per-trade returns annualized by estimated trades/year.
        Crypto markets trade 365 days/year.
        """
        if len(equity_curve) < 3:
            return 0.0

        returns = np.diff(equity_curve) / equity_curve[:-1]

        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0

        # Estimate annualization factor from number of trades
        # More trades = higher confidence in the ratio
        n_trades = len(returns)
        trades_per_year = max(n_trades, 12)  # Assume at least 12 trades/year baseline

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * trades_per_year
        annual_std = std_return * np.sqrt(trades_per_year)

        sharpe = (annual_return - risk_free_rate) / annual_std if annual_std > 0 else 0

        # Cap at reasonable values to avoid inf from low-trade strategies
        return max(min(sharpe, 10.0), -10.0)

    def _calculate_sortino(self, equity_curve: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sortino ratio (uses only downside volatility).
        """
        if len(equity_curve) < 3:
            return 0.0

        returns = np.diff(equity_curve) / equity_curve[:-1]

        if len(returns) == 0:
            return 0.0

        # Downside returns only
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return 5.0  # Good but not infinite

        n_trades = len(returns)
        trades_per_year = max(n_trades, 12)

        annual_return = np.mean(returns) * trades_per_year
        downside_std = np.std(downside_returns) * np.sqrt(trades_per_year)

        sortino = (annual_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        return max(min(sortino, 10.0), -10.0)

    def _calculate_expectancy(self, avg_win: float, avg_loss: float, win_rate: float) -> float:
        """
        Calculate expectancy (average profit per trade).

        Formula: (Win Rate * Avg Win) - ((1 - Win Rate) * Avg Loss)
        """
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    def _empty_metrics(self) -> Dict:
        """Return metrics dict with zeros for no trades."""
        return {
            "total_profit": 0,
            "total_profit_pct": 0,
            "gross_profit": 0,
            "gross_loss": 0,
            "total_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "max_drawdown": 0,
            "profit_factor": 0,
            "recovery_factor": 0,
            "avg_trade_duration": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "total_fees": 0,
            "fee_impact_pct": 0,
            "expectancy": 0,
            "composite_score": 0,
            "meets_criteria": False,
        }


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Period for ATR calculation (default 14)

    Returns:
        ATR series
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()

    return atr
