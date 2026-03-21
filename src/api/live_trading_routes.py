"""Live trading API routes - Phase 4 endpoints."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_

from src.database import SessionLocal, LiveTrade, StrategyPerformance, Strategy
from src.live_trading.exchange_connector import ExchangeConnector
from src.live_trading.position_manager import PositionManager
from src.live_trading.performance_monitor import PerformanceMonitor
from src.config import get_settings

router = APIRouter(prefix="/api/v1/live-trading", tags=["Live Trading"])
db = SessionLocal()
settings = get_settings()


@router.get("/positions/open")
async def get_open_positions(strategy_id: Optional[str] = None):
    """
    Get open/active trading positions.

    Query params:
    - strategy_id: Filter by strategy (optional)

    Returns:
    {
        "count": 2,
        "positions": [
            {
                "id": "trade_123",
                "strategy_id": "strat_abc",
                "pair": "BTC/USDT",
                "entry_price": 42000,
                "current_price": 42500,
                "size": 0.05,
                "unrealized_pnl": 25,
                "unrealized_pnl_pct": 0.12,
                "stop_loss": 41000,
                "take_profit": 43000,
                "entry_time": "2026-03-19T10:30:00Z",
                "duration_seconds": 3600
            }
        ]
    }
    """
    try:
        query = db.query(LiveTrade).filter(LiveTrade.status == "open")

        if strategy_id:
            query = query.filter(LiveTrade.strategy_id == strategy_id)

        positions = query.all()

        # Add current price and unrealized P&L
        connector = ExchangeConnector(
            exchange_type=settings.live_exchange,
            sandbox=settings.sandbox_mode
        )

        positions_data = []
        for pos in positions:
            try:
                ticker = connector.get_ticker(pos.pair)
                current_price = ticker["last"]

                unrealized_pnl = (current_price - pos.entry_price) * pos.size
                unrealized_pnl_pct = unrealized_pnl / (pos.entry_price * pos.size)

                duration = (datetime.utcnow() - pos.entry_time).total_seconds()

                positions_data.append({
                    "id": pos.id,
                    "strategy_id": pos.strategy_id,
                    "pair": pos.pair,
                    "entry_price": float(pos.entry_price),
                    "current_price": float(current_price),
                    "size": float(pos.size),
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_pct": float(unrealized_pnl_pct),
                    "stop_loss": float(pos.stop_loss),
                    "take_profit": float(pos.take_profit),
                    "entry_time": pos.entry_time.isoformat(),
                    "duration_seconds": int(duration)
                })
            except Exception as e:
                # Skip if can't get current price
                continue

        return {
            "count": len(positions_data),
            "positions": positions_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/closed")
async def get_closed_positions(
    strategy_id: Optional[str] = None,
    hours_back: int = 24,
    limit: int = 100
):
    """
    Get closed/exited trading positions.

    Query params:
    - strategy_id: Filter by strategy (optional)
    - hours_back: Look back period in hours (default 24)
    - limit: Max results (default 100)

    Returns:
    {
        "count": 5,
        "positions": [
            {
                "id": "trade_123",
                "pair": "BTC/USDT",
                "entry_price": 42000,
                "exit_price": 42500,
                "size": 0.05,
                "pnl": 25,
                "pnl_pct": 0.12,
                "duration_seconds": 3600,
                "exit_reason": "take_profit",
                "entry_time": "2026-03-19T10:30:00Z",
                "exit_time": "2026-03-19T11:30:00Z"
            }
        ]
    }
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        query = db.query(LiveTrade).filter(
            and_(
                LiveTrade.status == "closed",
                LiveTrade.exit_time >= cutoff_time
            )
        )

        if strategy_id:
            query = query.filter(LiveTrade.strategy_id == strategy_id)

        positions = query.order_by(LiveTrade.exit_time.desc()).limit(limit).all()

        positions_data = []
        for pos in positions:
            duration = (pos.exit_time - pos.entry_time).total_seconds()

            positions_data.append({
                "id": pos.id,
                "pair": pos.pair,
                "entry_price": float(pos.entry_price),
                "exit_price": float(pos.exit_price or 0),
                "size": float(pos.size),
                "pnl": float(pos.pnl or 0),
                "pnl_pct": float((pos.pnl / (pos.entry_price * pos.size)) if pos.pnl else 0),
                "duration_seconds": int(duration),
                "exit_reason": pos.exit_reason,
                "entry_time": pos.entry_time.isoformat(),
                "exit_time": pos.exit_time.isoformat() if pos.exit_time else None
            })

        return {
            "count": len(positions_data),
            "positions": positions_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{strategy_id}")
async def get_strategy_live_performance(
    strategy_id: str,
    hours_back: int = 24
):
    """
    Get live performance metrics for a strategy.

    Path params:
    - strategy_id: Strategy ID

    Query params:
    - hours_back: Look back period in hours (default 24)

    Returns:
    {
        "strategy_id": "strat_abc",
        "period_hours": 24,
        "total_trades": 5,
        "winning_trades": 3,
        "losing_trades": 2,
        "win_rate": 0.60,
        "total_pnl": 125.50,
        "avg_win": 50.25,
        "avg_loss": -25.00,
        "profit_factor": 2.01,
        "best_trade": 75.00,
        "worst_trade": -30.00
    }
    """
    try:
        monitor = PerformanceMonitor(db)
        metrics = monitor.get_live_metrics(strategy_id, hours_back)

        return metrics

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{strategy_id}/backtest-comparison")
async def compare_backtest_vs_live(strategy_id: str):
    """
    Compare live performance vs backtest expectations (drift analysis).

    Path params:
    - strategy_id: Strategy ID

    Returns:
    {
        "strategy_id": "strat_abc",
        "backtest": {
            "win_rate": 0.55,
            "profit_pct": 25.5,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.15
        },
        "live": {
            "win_rate": 0.60,
            "total_pnl": 125.50,
            "total_trades": 5
        },
        "drift": {
            "win_rate_drift": 0.05,
            "profit_drift": 50.50,
            "acceptable_threshold": 0.15,
            "win_rate_acceptable": true,
            "profit_acceptable": true
        },
        "status": "acceptable"
    }
    """
    try:
        monitor = PerformanceMonitor(db)
        comparison = monitor.compare_with_backtest(strategy_id)

        return comparison

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/{strategy_id}")
async def get_strategy_health(strategy_id: str):
    """
    Get strategy health score (0-100).

    Path params:
    - strategy_id: Strategy ID

    Returns:
    {
        "strategy_id": "strat_abc",
        "health_score": 78.5,
        "status": "healthy",
        "win_rate": 0.60,
        "profit_factor": 2.01,
        "total_trades": 50,
        "total_live_profit": 2500.00,
        "deployed": true
    }
    """
    try:
        monitor = PerformanceMonitor(db)
        health = monitor.get_strategy_health(strategy_id)

        return health

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy/{strategy_id}")
async def deploy_strategy_to_live(strategy_id: str):
    """
    Deploy a strategy to live trading.

    Path params:
    - strategy_id: Strategy ID to deploy

    Returns:
    {
        "strategy_id": "strat_abc",
        "status": "deployed",
        "message": "Strategy deployed for live trading",
        "deployment_time": "2026-03-19T10:30:00Z"
    }
    """
    try:
        # Get strategy
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id
        ).first()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Get or create performance record
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strategy_id
        ).first()

        if not perf:
            perf = StrategyPerformance(
                strategy_id=strategy_id,
                deployed=True,
                live_active=True
            )
        else:
            perf.deployed = True
            perf.live_active = True

        db.add(perf)
        db.commit()

        return {
            "strategy_id": strategy_id,
            "status": "deployed",
            "message": "Strategy deployed for live trading",
            "deployment_time": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retire/{strategy_id}")
async def retire_strategy(strategy_id: str):
    """
    Retire a strategy from live trading.

    Path params:
    - strategy_id: Strategy ID to retire

    Returns:
    {
        "strategy_id": "strat_abc",
        "status": "retired",
        "message": "Strategy retired from live trading",
        "retirement_time": "2026-03-19T10:30:00Z"
    }
    """
    try:
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strategy_id
        ).first()

        if not perf:
            raise HTTPException(status_code=404, detail="Strategy not found")

        perf.deployed = False
        perf.live_active = False

        db.add(perf)
        db.commit()

        return {
            "strategy_id": strategy_id,
            "status": "retired",
            "message": "Strategy retired from live trading",
            "retirement_time": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_live_trading_summary():
    """
    Get overall live trading summary.

    Returns:
    {
        "active_strategies": 5,
        "total_open_positions": 3,
        "total_live_profit": 2500.00,
        "win_rate": 0.58,
        "best_performer": {
            "strategy_id": "strat_abc",
            "pnl": 750.00,
            "win_rate": 0.75
        },
        "worst_performer": {
            "strategy_id": "strat_xyz",
            "pnl": -200.00,
            "win_rate": 0.30
        }
    }
    """
    try:
        # Get active strategies
        active_strategies = db.query(StrategyPerformance).filter(
            StrategyPerformance.deployed == True,
            StrategyPerformance.live_active == True
        ).count()

        # Get open positions
        open_positions = db.query(LiveTrade).filter(
            LiveTrade.status == "open"
        ).count()

        # Get performance stats
        closed_trades = db.query(LiveTrade).filter(
            LiveTrade.status == "closed",
            LiveTrade.exit_time >= datetime.utcnow() - timedelta(days=7)
        ).all()

        total_pnl = sum(t.pnl or 0 for t in closed_trades)
        winners = [t for t in closed_trades if t.pnl and t.pnl > 0]
        win_rate = len(winners) / len(closed_trades) if closed_trades else 0

        # Get best/worst performers
        perfs = db.query(StrategyPerformance).filter(
            StrategyPerformance.deployed == True
        ).all()

        best = max(perfs, key=lambda x: x.live_total_profit or 0, default=None)
        worst = min(perfs, key=lambda x: x.live_total_profit or 0, default=None)

        return {
            "active_strategies": active_strategies,
            "total_open_positions": open_positions,
            "total_live_profit": float(total_pnl),
            "win_rate": float(win_rate),
            "best_performer": {
                "strategy_id": best.strategy_id,
                "pnl": float(best.live_total_profit or 0)
            } if best else None,
            "worst_performer": {
                "strategy_id": worst.strategy_id,
                "pnl": float(worst.live_total_profit or 0)
            } if worst else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
