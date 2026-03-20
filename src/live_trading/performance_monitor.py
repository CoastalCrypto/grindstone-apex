"""Monitor live trading performance vs backtest expectations."""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database import LiveTrade, BacktestResult, StrategyPerformance
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PerformanceMonitor:
    """Monitor and analyze live trading performance."""

    def __init__(self, db: Session):
        """
        Initialize performance monitor.

        Args:
            db: Database session
        """
        self.db = db

    def get_live_metrics(self, strategy_id: str, hours_back: int = 24) -> Dict:
        """
        Get live trading metrics for a strategy.

        Args:
            strategy_id: Strategy ID
            hours_back: Look back period in hours (default 24)

        Returns:
            Live metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        trades = self.db.query(LiveTrade).filter(
            and_(
                LiveTrade.strategy_id == strategy_id,
                LiveTrade.status == "closed",
                LiveTrade.exit_time >= cutoff_time
            )
        ).all()

        if not trades:
            return {
                "strategy_id": strategy_id,
                "total_trades": 0,
                "message": "No closed trades in period"
            }

        # Calculate metrics
        total_trades = len(trades)
        winners = [t for t in trades if t.pnl and t.pnl > 0]
        losers = [t for t in trades if t.pnl and t.pnl < 0]

        total_pnl = sum(t.pnl for t in trades if t.pnl)
        win_rate = len(winners) / total_trades if total_trades > 0 else 0

        gross_profit = sum(t.pnl for t in winners if t.pnl)
        gross_loss = abs(sum(t.pnl for t in losers if t.pnl))

        return {
            "strategy_id": strategy_id,
            "period_hours": hours_back,
            "total_trades": total_trades,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": gross_profit / len(winners) if winners else 0,
            "avg_loss": gross_loss / len(losers) if losers else 0,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0,
            "best_trade": max([t.pnl for t in trades if t.pnl], default=0),
            "worst_trade": min([t.pnl for t in trades if t.pnl], default=0),
        }

    def compare_with_backtest(self, strategy_id: str) -> Dict:
        """
        Compare live performance with backtest expectations.

        Args:
            strategy_id: Strategy ID

        Returns:
            Comparison with drift analysis
        """
        # Get backtest metrics
        backtest = self.db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strategy_id
        ).first()

        if not backtest:
            return {"error": "No backtest results found"}

        # Get live metrics (last 7 days)
        live = self.get_live_metrics(strategy_id, hours_back=168)

        if live.get("total_trades", 0) == 0:
            return {"message": "No live trades yet for comparison"}

        # Calculate drift
        backtest_win_rate = backtest.win_rate
        live_win_rate = live.get("win_rate", 0)
        win_rate_drift = abs(live_win_rate - backtest_win_rate)

        backtest_profit_pct = backtest.total_profit_pct
        live_profit_pct = live.get("total_pnl", 0)  # In dollars, not percentage
        profit_drift = abs(live_profit_pct - backtest_profit_pct)

        drift_threshold = settings.performance_drift_threshold

        return {
            "strategy_id": strategy_id,
            "backtest": {
                "win_rate": backtest_win_rate,
                "profit_pct": backtest_profit_pct,
                "sharpe_ratio": backtest.sharpe_ratio,
                "max_drawdown": backtest.max_drawdown,
            },
            "live": {
                "win_rate": live_win_rate,
                "total_pnl": live.get("total_pnl", 0),
                "total_trades": live.get("total_trades", 0),
                "best_trade": live.get("best_trade", 0),
                "worst_trade": live.get("worst_trade", 0),
            },
            "drift": {
                "win_rate_drift": win_rate_drift,
                "profit_drift": profit_drift,
                "acceptable_threshold": drift_threshold,
                "win_rate_acceptable": win_rate_drift <= drift_threshold,
                "profit_acceptable": profit_drift <= drift_threshold,
            },
            "status": "acceptable" if (win_rate_drift <= drift_threshold and profit_drift <= drift_threshold) else "needs_review",
        }

    def flag_underperforming_strategy(self, strategy_id: str) -> Dict:
        """
        Check if a strategy is underperforming and should be retired.

        Args:
            strategy_id: Strategy ID

        Returns:
            Assessment with recommendation
        """
        live = self.get_live_metrics(strategy_id, hours_back=72)  # 3 days

        if live.get("total_trades", 0) < 5:
            return {
                "strategy_id": strategy_id,
                "status": "insufficient_data",
                "recommendation": "Need at least 5 trades to assess",
                "trades_so_far": live.get("total_trades", 0)
            }

        win_rate = live.get("win_rate", 0)
        total_pnl = live.get("total_pnl", 0)

        # Criteria for underperformance
        is_losing_money = total_pnl < 0
        win_rate_below_threshold = win_rate < 0.30  # Below 30%

        if is_losing_money and win_rate_below_threshold:
            return {
                "strategy_id": strategy_id,
                "status": "underperforming",
                "recommendation": "RETIRE - losing money and low win rate",
                "metrics": {
                    "total_pnl": total_pnl,
                    "win_rate": win_rate,
                    "total_trades": live.get("total_trades", 0),
                },
                "action": "retire"
            }

        elif is_losing_money:
            return {
                "strategy_id": strategy_id,
                "status": "caution",
                "recommendation": "MONITOR - losing money but has acceptable win rate",
                "metrics": {
                    "total_pnl": total_pnl,
                    "win_rate": win_rate,
                },
                "action": "monitor"
            }

        else:
            return {
                "strategy_id": strategy_id,
                "status": "performing",
                "recommendation": "KEEP - profitable",
                "metrics": {
                    "total_pnl": total_pnl,
                    "win_rate": win_rate,
                },
                "action": "continue"
            }

    def get_strategy_health(self, strategy_id: str) -> Dict:
        """
        Get overall health score for a strategy.

        Args:
            strategy_id: Strategy ID

        Returns:
            Health score (0-100) and assessment
        """
        # Get performance
        performance = self.db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strategy_id
        ).first()

        if not performance:
            return {"error": "Strategy not found"}

        # Get recent live trades
        recent_trades = self.db.query(LiveTrade).filter(
            and_(
                LiveTrade.strategy_id == strategy_id,
                LiveTrade.status == "closed"
            )
        ).order_by(LiveTrade.exit_time.desc()).limit(50).all()

        if not recent_trades:
            # No live trades yet, use backtest
            backtest = self.db.query(BacktestResult).filter(
                BacktestResult.strategy_id == strategy_id
            ).first()

            if backtest:
                return {
                    "strategy_id": strategy_id,
                    "health_score": backtest.composite_score,
                    "status": "not_deployed",
                    "message": "No live trades yet - using backtest score",
                }

            return {"error": "No data available"}

        # Calculate health based on live performance
        win_rate = sum(1 for t in recent_trades if t.pnl > 0) / len(recent_trades)
        profit_factor = sum(t.pnl for t in recent_trades if t.pnl > 0) / abs(sum(t.pnl for t in recent_trades if t.pnl < 0) or 1)

        # Health score (0-100)
        health = 0
        health += win_rate * 40  # 40 points for win rate
        health += min(profit_factor / 2 * 40, 40)  # 40 points for profitability
        health += 20 if performance.deployed else 0  # 20 points for being deployed

        return {
            "strategy_id": strategy_id,
            "health_score": min(health, 100),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": len(recent_trades),
            "status": "healthy" if health > 60 else "needs_attention" if health > 30 else "poor",
            "total_live_profit": performance.live_total_profit,
            "deployed": performance.deployed,
        }

    def generate_performance_report(self, strategy_id: str) -> str:
        """
        Generate a text report of strategy performance.

        Args:
            strategy_id: Strategy ID

        Returns:
            Performance report as formatted string
        """
        health = self.get_strategy_health(strategy_id)
        comparison = self.compare_with_backtest(strategy_id)
        assessment = self.flag_underperforming_strategy(strategy_id)

        report = f"""
═════════════════════════════════════════════════════════════
STRATEGY PERFORMANCE REPORT: {strategy_id}
═════════════════════════════════════════════════════════════

HEALTH SCORE: {health.get('health_score', 'N/A'):.1f}/100
Status: {health.get('status', 'Unknown')}

LIVE PERFORMANCE:
  - Win Rate: {health.get('win_rate', 0)*100:.1f}%
  - Profit Factor: {health.get('profit_factor', 0):.2f}x
  - Total Trades: {health.get('total_trades', 0)}
  - Total Profit: ${health.get('total_live_profit', 0):.2f}
  - Deployed: {'Yes' if health.get('deployed') else 'No'}

BACKTEST vs LIVE DRIFT:
  - Status: {comparison.get('drift', {}).get('status', 'Unknown')}
  - Win Rate Drift: {comparison.get('drift', {}).get('win_rate_drift', 0)*100:.2f}%
  - Acceptable: {'✓ Yes' if comparison.get('drift', {}).get('win_rate_acceptable') else '✗ No'}

ASSESSMENT:
  - Status: {assessment.get('status')}
  - Recommendation: {assessment.get('recommendation')}
  - Action: {assessment.get('action').upper()}

═════════════════════════════════════════════════════════════
"""
        return report
