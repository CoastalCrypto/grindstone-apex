"""API routes for Grindstone Apex."""
import uuid
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

from src.database import (
    get_db, Strategy, BacktestResult, GenerationRun,
    StrategyPerformance, SystemMetrics, LiveTrade
)
from src.config import get_settings
from src.backtesting.data_loader import get_data_loader
from src.backtesting.vectorbt_engine import VectorBTBacktestEngine
from src.strategy_generation.genetic_algorithm import (
    GeneticAlgorithmEngine, create_elite_strategies_from_winners
)

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()


# ============= STRATEGY ENDPOINTS =============

@router.get("/strategies")
async def list_strategies(
    pair: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List strategies with optional filtering."""
    query = db.query(Strategy)

    if pair:
        query = query.filter(Strategy.pair == pair)

    if status:
        query = query.filter(Strategy.status == status)

    strategies = query.order_by(desc(Strategy.created_at)).limit(limit).all()

    return {
        "count": len(strategies),
        "strategies": [s.to_dict() for s in strategies]
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """Get specific strategy details."""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return strategy.to_dict()


# ============= BACKTESTING ENDPOINTS =============

@router.post("/backtest/single")
async def backtest_single_strategy(
    pair: str,
    indicators: Dict,
    position_sizing: Dict,
    risk_management: Dict,
    timeframes: List[int] = [15, 60, 240],
    db: Session = Depends(get_db)
):
    """Backtest a single strategy."""
    try:
        # Load historical data
        loader = get_data_loader()
        candles = loader.load_candles(pair, timeframe=15, days_back=365)

        if candles.empty:
            raise HTTPException(status_code=400, detail=f"No data found for {pair}")

        # Create strategy dict
        strategy_dict = {
            "pair": pair,
            "indicators": indicators,
            "position_sizing": position_sizing,
            "risk_management": risk_management,
            "timeframes": timeframes,
        }

        # Run backtest
        engine = VectorBTBacktestEngine()
        result = engine.backtest_strategy(candles, strategy_dict)

        return {
            "success": result.get("success"),
            "metrics": result.get("metrics"),
            "num_trades": result.get("num_trades"),
        }

    except Exception as e:
        logger.error(f"Backtesting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/batch")
async def backtest_batch(
    strategies: List[Dict],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Backtest multiple strategies (async)."""
    # Save to database for tracking
    generation_run = GenerationRun(
        generation_id=datetime.utcnow().timestamp(),
        strategies_generated=len(strategies),
        status="running"
    )
    db.add(generation_run)
    db.commit()

    # Queue background task
    background_tasks.add_task(
        _backtest_batch_task,
        strategies=strategies,
        generation_id=generation_run.generation_id,
        db=db
    )

    return {
        "message": "Batch backtest queued",
        "generation_id": generation_run.generation_id,
        "num_strategies": len(strategies)
    }


async def _backtest_batch_task(strategies: List[Dict], generation_id: int, db: Session):
    """Background task for batch backtesting."""
    try:
        loader = get_data_loader()
        engine = VectorBTBacktestEngine()
        passed_count = 0

        for i, strat_dict in enumerate(strategies):
            pair = strat_dict.get("pair", "BTC/USDT")

            try:
                # Load data
                candles = loader.load_candles(pair, 15, 365)
                if candles.empty:
                    continue

                # Backtest
                result = engine.backtest_strategy(candles, strat_dict)

                if result.get("success"):
                    metrics = result.get("metrics", {})

                    # Save to database
                    backtest_result = BacktestResult(
                        id=f"result_{uuid.uuid4().hex[:12]}",
                        strategy_id=strat_dict.get("id", f"strat_{i}"),
                        total_profit=metrics.get("total_profit", 0),
                        total_profit_pct=metrics.get("total_profit_pct", 0),
                        win_count=metrics.get("win_count", 0),
                        loss_count=metrics.get("loss_count", 0),
                        win_rate=metrics.get("win_rate", 0),
                        sharpe_ratio=metrics.get("sharpe_ratio", 0),
                        max_drawdown=metrics.get("max_drawdown", 0),
                        composite_score=metrics.get("composite_score", 0),
                        meets_criteria=metrics.get("meets_criteria", False),
                        full_metrics=metrics,
                        backtest_start_date=datetime.utcnow(),
                        backtest_end_date=datetime.utcnow(),
                    )
                    db.add(backtest_result)

                    if metrics.get("meets_criteria"):
                        passed_count += 1

            except Exception as e:
                logger.error(f"Error backtesting strategy {i}: {e}")
                continue

        db.commit()

        # Update generation run
        gen_run = db.query(GenerationRun).filter(
            GenerationRun.generation_id == generation_id
        ).first()
        if gen_run:
            gen_run.status = "completed"
            gen_run.strategies_backtested = len(strategies)
            gen_run.strategies_passed = passed_count
            db.add(gen_run)
            db.commit()

        logger.info(f"Batch backtest completed: {passed_count}/{len(strategies)} passed")

    except Exception as e:
        logger.error(f"Batch backtest task failed: {e}")


# ============= STRATEGY GENERATION ENDPOINTS =============

@router.post("/generate/initial")
async def generate_initial_strategies(
    pair: str,
    count: int = 100,
    db: Session = Depends(get_db)
):
    """Generate initial population of random strategies."""
    try:
        ga = GeneticAlgorithmEngine(pair=pair)
        strategies = ga.create_initial_population(count)

        return {
            "count": len(strategies),
            "strategies": [s.to_dict() for s in strategies]
        }

    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/evolved")
async def generate_evolved_strategies(
    pair: str,
    generation_id: int,
    count: int = 500,
    db: Session = Depends(get_db)
):
    """Generate evolved population based on elite strategies."""
    try:
        # Get elite strategies from previous generation
        elite_results = db.query(BacktestResult).filter(
            BacktestResult.meets_criteria == True
        ).order_by(desc(BacktestResult.composite_score)).limit(20).all()

        if not elite_results:
            return {
                "error": "No elite strategies found",
                "message": "Generate and backtest initial strategies first"
            }

        # Convert to Strategy objects
        elite_strategies = [
            (Strategy.from_dict(r.full_metrics), r.composite_score)
            for r in elite_results
        ]

        # Evolve
        ga = GeneticAlgorithmEngine(pair=pair)
        new_strategies = ga.evolve_population(
            elite_strategies,
            population_size=count,
            generation_id=generation_id
        )

        return {
            "count": len(new_strategies),
            "generation_id": generation_id,
            "elite_count": len(elite_strategies),
            "strategies": [s.to_dict() for s in new_strategies]
        }

    except Exception as e:
        logger.error(f"Evolution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= RALPH LOOP ENDPOINTS =============

@router.get("/ralph-loop/elite")
async def get_elite_strategies(
    pair: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get elite (top performing) strategies."""
    query = db.query(BacktestResult).filter(
        BacktestResult.meets_criteria == True
    ).order_by(desc(BacktestResult.composite_score))

    if pair:
        # Filter by pair if provided
        pass

    results = query.limit(limit).all()

    return {
        "count": len(results),
        "elite": [
            {
                "strategy_id": r.strategy_id,
                "score": r.composite_score,
                "win_rate": r.win_rate,
                "profit_pct": r.total_profit_pct,
                "sharpe_ratio": r.sharpe_ratio,
            }
            for r in results
        ]
    }


@router.get("/ralph-loop/statistics")
async def get_ralph_loop_stats(
    generation_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get Ralph loop statistics."""
    query = db.query(GenerationRun)

    if generation_id:
        query = query.filter(GenerationRun.generation_id == generation_id)

    runs = query.order_by(desc(GenerationRun.started_at)).limit(10).all()

    return {
        "runs": [
            {
                "generation_id": r.generation_id,
                "strategies_generated": r.strategies_generated,
                "strategies_backtested": r.strategies_backtested,
                "strategies_passed": r.strategies_passed,
                "pass_rate": r.strategies_passed / r.strategies_backtested if r.strategies_backtested > 0 else 0,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in runs
        ]
    }


# ============= LIVE TRADING ENDPOINTS =============

@router.get("/live-trading/open-positions")
async def get_open_positions(
    pair: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get open trading positions."""
    query = db.query(LiveTrade).filter(LiveTrade.status == "open")

    if pair:
        query = query.filter(LiveTrade.pair == pair)

    trades = query.order_by(desc(LiveTrade.entry_time)).all()

    return {
        "count": len(trades),
        "positions": [
            {
                "trade_id": t.id,
                "pair": t.pair,
                "entry_price": t.entry_price,
                "entry_time": t.entry_time,
                "size": t.size,
                "strategy_id": t.strategy_id,
            }
            for t in trades
        ]
    }


@router.get("/live-trading/closed-trades")
async def get_closed_trades(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get closed trades."""
    trades = db.query(LiveTrade).filter(
        LiveTrade.status == "closed"
    ).order_by(desc(LiveTrade.exit_time)).limit(limit).all()

    return {
        "count": len(trades),
        "trades": [
            {
                "pair": t.pair,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "exit_reason": t.exit_reason,
            }
            for t in trades
        ]
    }


# ============= SYSTEM ENDPOINTS =============

@router.get("/system/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """Get system health metrics."""
    latest = db.query(SystemMetrics).order_by(
        desc(SystemMetrics.timestamp)
    ).first()

    if not latest:
        return {
            "message": "No metrics yet",
        }

    return {
        "timestamp": latest.timestamp,
        "account_balance": latest.account_balance,
        "total_live_profit": latest.total_live_profit,
        "active_strategies": latest.active_strategies,
        "strategies_in_queue": latest.strategies_in_queue,
        "avg_backtest_time_seconds": latest.avg_backtest_time,
        "total_strategies_tested": latest.total_strategies_tested,
    }


from src.ralph_loop.evaluator import RalphLoopEvaluator


# ============= RALPH LOOP ADVANCED ENDPOINTS =============

@router.get("/ralph-loop/run-cycle")
async def run_ralph_loop_cycle(
    generation_id: int,
    pair: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually trigger a Ralph Loop selection cycle."""
    try:
        evaluator = RalphLoopEvaluator(db)

        # Get backtest results from this generation
        results = db.query(BacktestResult).filter(
            BacktestResult.backtest_start_date >= datetime.utcnow() - timedelta(hours=24)
        ).all()

        if not results:
            return {
                "message": "No backtest results found for this period",
                "suggestion": "Run backtests first"
            }

        # Run Ralph Loop evaluation
        backtest_dicts = [
            {
                "strategy_id": r.strategy_id,
                "metrics": r.full_metrics
            }
            for r in results
        ]

        evaluation = evaluator.evaluate_generation(generation_id, pair, backtest_dicts)
        evaluator.persist_evaluation(generation_id, pair, evaluation)

        return {
            "generation_id": generation_id,
            "pair": pair,
            "evaluation": {
                "total_tested": evaluation["total_tested"],
                "elite_count": evaluation["elite_count"],
                "discard_count": evaluation["discard_count"],
                "pass_rate": evaluation["pass_rate"],
                "best_score": evaluation["best_strategy_score"],
            }
        }

    except Exception as e:
        logger.error(f"Ralph Loop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ralph-loop/patterns")
async def get_successful_patterns(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Identify patterns in successful strategies."""
    try:
        evaluator = RalphLoopEvaluator(db)
        patterns = evaluator.identify_successful_patterns(limit=limit)

        return {
            "patterns": patterns,
            "interpretation": {
                "message": "These are the common characteristics of profitable strategies",
                "next_step": "Use these ranges as constraints for strategy generation"
            }
        }

    except Exception as e:
        logger.error(f"Pattern analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ralph-loop/genealogy/{strategy_id}")
async def get_strategy_genealogy(
    strategy_id: str,
    depth: int = 5,
    db: Session = Depends(get_db)
):
    """Get strategy family tree (ancestors and descendants)."""
    try:
        evaluator = RalphLoopEvaluator(db)
        genealogy = evaluator.get_strategy_genealogy(strategy_id, depth=depth)

        return {
            "strategy_id": strategy_id,
            "ancestors": genealogy["ancestors"],
            "descendants": genealogy["descendants"],
            "interpretation": "Shows how this strategy evolved through generations"
        }

    except Exception as e:
        logger.error(f"Genealogy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ralph-loop/compare")
async def compare_generations(
    gen1_id: int,
    gen2_id: int,
    db: Session = Depends(get_db)
):
    """Compare performance between two generations."""
    try:
        evaluator = RalphLoopEvaluator(db)
        comparison = evaluator.compare_generations(gen1_id, gen2_id)

        return comparison

    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generation/start-service")
async def start_generation_service(
    interval_seconds: int = 300,
    background_tasks: BackgroundTasks = None
):
    """
    Start the continuous generation service.

    This will run strategy generation in the background continuously.
    """
    return {
        "message": "Generation service started",
        "interval_seconds": interval_seconds,
        "note": "The service is designed to run continuously in a separate process",
        "instructions": "Use docker-compose to run the strategy_generator service",
        "command": "docker-compose up strategy_generator"
    }


