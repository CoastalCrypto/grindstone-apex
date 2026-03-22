#!/usr/bin/env python3
"""
Grindstone Apex - Full Backtesting Pipeline Runner
Generates strategies via Genetic Algorithm, backtests them, and applies Ralph Loop selection.
Bypasses Redis (no cache needed) and works with SQLite.
"""
import sys
import os
import json
import time
import uuid
import logging
from datetime import datetime, timedelta

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import numpy as np
import pandas as pd
import ccxt

from src.config import get_settings
from src.database import SessionLocal, init_db, Strategy as DBStrategy, BacktestResult, GenerationRun, StrategyPerformance
from src.backtesting.vectorbt_engine import VectorBTBacktestEngine
from src.backtesting.metrics import calculate_atr
from src.strategy_generation.genetic_algorithm import GeneticAlgorithmEngine, Strategy as GAStrategy

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
NUM_STRATEGIES = 500          # Full generation size
PAIRS = ["BTC/USDT:USDT", "ETH/USDT:USDT", "XAU/USDT:USDT", "XAG/USDT:USDT"]
TIMEFRAME = "15m"             # 15-minute candles
DAYS_BACK = 365               # 12 months of data
ELITE_THRESHOLD = 0.20        # Keep top 20% (Ralph Loop)


def fetch_candles_ccxt(pair: str, timeframe: str = "15m", days_back: int = 180) -> pd.DataFrame:
    """Fetch OHLCV data from Blofin via ccxt, or generate synthetic data if no network."""

    # Try live fetch first
    try:
        logger.info(f"Attempting to fetch {pair} {timeframe} candles from Blofin...")
        exchange = ccxt.blofin({
            "apiKey": settings.exchange_api_key,
            "secret": settings.exchange_secret,
            "password": settings.exchange_password,
            "enableRateLimit": True,
            "timeout": 15000,
        })

        all_candles = []
        end_ts = int(datetime.utcnow().timestamp() * 1000)
        start_ts = int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)
        current_ts = start_ts

        while current_ts < end_ts:
            candles = exchange.fetch_ohlcv(pair, timeframe=timeframe, since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + 1
            time.sleep(0.3)

        if all_candles:
            df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            logger.info(f"Fetched {len(df)} live candles for {pair}")
            return df

    except Exception as e:
        logger.warning(f"Cannot fetch live data ({type(e).__name__}), using synthetic data")

    # Generate realistic synthetic BTC/USDT data
    return generate_synthetic_candles(pair, timeframe, days_back)


def generate_synthetic_candles(pair: str, timeframe: str = "15m", days_back: int = 180) -> pd.DataFrame:
    """
    Generate realistic synthetic OHLCV data modeled on BTC price behavior.
    Uses geometric Brownian motion with mean-reverting volatility.
    """
    logger.info(f"Generating synthetic {pair} {timeframe} data ({days_back} days)...")

    np.random.seed(42)  # Reproducible results

    # Timeframe in minutes
    tf_minutes = int(timeframe.replace('m', '').replace('h', '')) if 'h' not in timeframe else int(timeframe.replace('h', '')) * 60
    candles_per_day = (24 * 60) // tf_minutes
    total_candles = candles_per_day * days_back

    # BTC-like parameters
    initial_price = 65000.0
    annual_drift = 0.15        # 15% annual drift
    annual_vol = 0.65          # 65% annual volatility (typical BTC)

    # Convert to per-candle
    dt = tf_minutes / (365.25 * 24 * 60)
    mu = annual_drift * dt
    sigma = annual_vol * np.sqrt(dt)

    # Generate returns with regime changes (trending/ranging)
    returns = np.random.normal(mu, sigma, total_candles)

    # Add some autocorrelation (momentum)
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i-1]

    # Add regime changes (bull/bear cycles roughly every 30-60 days)
    regime_length = candles_per_day * np.random.randint(30, 60)
    for i in range(0, total_candles, regime_length):
        end = min(i + regime_length, total_candles)
        regime_drift = np.random.choice([-0.0003, 0.0, 0.0003])  # bear, neutral, bull
        returns[i:end] += regime_drift

    # Build price series
    close_prices = initial_price * np.exp(np.cumsum(returns))

    # Generate OHLV from close
    opens = np.roll(close_prices, 1)
    opens[0] = initial_price

    # High/Low with realistic wicks
    wick_size = sigma * close_prices * np.random.uniform(0.5, 2.0, total_candles)
    highs = np.maximum(opens, close_prices) + abs(wick_size)
    lows = np.minimum(opens, close_prices) - abs(wick_size)

    # Volume (higher on big moves, with daily patterns)
    base_volume = 500 + np.random.exponential(200, total_candles)
    move_volume = abs(returns) / sigma * 300
    volume = (base_volume + move_volume) * close_prices / 1000

    # Timestamps
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    timestamps = pd.date_range(start=start_date, periods=total_candles, freq=f'{tf_minutes}min')

    df = pd.DataFrame({
        'timestamp': timestamps[:total_candles],
        'open': opens,
        'high': highs,
        'low': lows,
        'close': close_prices,
        'volume': volume,
    })

    logger.info(f"Generated {len(df)} synthetic candles: "
                f"${df['close'].iloc[0]:.0f} -> ${df['close'].iloc[-1]:.0f} "
                f"(range: ${df['low'].min():.0f} - ${df['high'].max():.0f})")

    return df


def run_backtest_pipeline():
    """Run the full backtesting pipeline."""

    # ──────────────────────────────────────────
    # Step 0: Initialize database
    # ──────────────────────────────────────────
    logger.info("=" * 70)
    logger.info("GRINDSTONE APEX - BACKTESTING PIPELINE")
    logger.info("=" * 70)

    init_db()
    db = SessionLocal()

    # Determine generation ID
    latest = db.query(GenerationRun).order_by(GenerationRun.generation_id.desc()).first()
    generation_id = (latest.generation_id + 1) if latest else 1

    # Create generation run record
    gen_run = GenerationRun(generation_id=generation_id, status="running")
    db.add(gen_run)
    db.commit()

    pipeline_start = time.time()
    total_strategies_tested = 0
    total_passed = 0
    all_results = []

    for pair in PAIRS:
        logger.info(f"\n{'─' * 50}")
        logger.info(f"PAIR: {pair} | Generation: {generation_id}")
        logger.info(f"{'─' * 50}")

        # ──────────────────────────────────────────
        # Step 1: Fetch market data
        # ──────────────────────────────────────────
        candles = fetch_candles_ccxt(pair, TIMEFRAME, DAYS_BACK)
        if candles.empty:
            logger.error(f"Skipping {pair} - no data")
            continue

        logger.info(f"Data: {len(candles)} candles, "
                     f"Price range: ${candles['close'].min():.2f} - ${candles['close'].max():.2f}")

        # ──────────────────────────────────────────
        # Step 2: Generate strategies via Genetic Algorithm
        # ──────────────────────────────────────────
        ga = GeneticAlgorithmEngine(pair=pair, mutation_rate=settings.mutation_rate)

        # Check for elite strategies from previous generations
        elite_from_db = db.query(BacktestResult).filter(
            BacktestResult.meets_criteria == True
        ).order_by(BacktestResult.composite_score.desc()).limit(50).all()

        if elite_from_db and generation_id > 1:
            # EVOLUTION MODE: Breed from previous elite strategies
            logger.info(f"\n🧬 EVOLUTION MODE: Breeding from {len(elite_from_db)} elite ancestors...")

            # Convert DB results back to GA Strategy objects for breeding
            elite_tuples = []
            for r in elite_from_db:
                db_strat = db.query(DBStrategy).filter(DBStrategy.id == r.strategy_id).first()
                if db_strat:
                    try:
                        ga_strat = GAStrategy(
                            pair=pair,
                            timeframes=json.loads(db_strat.timeframes) if isinstance(db_strat.timeframes, str) else db_strat.timeframes,
                            indicators=json.loads(db_strat.indicators) if isinstance(db_strat.indicators, str) else db_strat.indicators,
                            position_sizing=json.loads(db_strat.position_sizing) if isinstance(db_strat.position_sizing, str) else db_strat.position_sizing,
                            risk_management=json.loads(db_strat.risk_management) if isinstance(db_strat.risk_management, str) else db_strat.risk_management,
                            source="elite_ancestor",
                            parent_id=db_strat.id,
                            generation_id=generation_id,
                        )
                        elite_tuples.append((ga_strat, r.composite_score))
                    except Exception as e:
                        logger.warning(f"Could not reconstruct strategy {r.strategy_id}: {e}")

            if elite_tuples:
                strategies = ga.evolve_population(elite_tuples, NUM_STRATEGIES, generation_id)
                logger.info(f"Evolved {len(strategies)} strategies from {len(elite_tuples)} elite parents")
            else:
                logger.info(f"Could not reconstruct elite strategies, generating fresh random population")
                strategies = ga.create_initial_population(NUM_STRATEGIES)
        else:
            # GENESIS MODE: First generation — random population
            logger.info(f"\n🎲 GENESIS MODE: Generating {NUM_STRATEGIES} random strategies...")
            strategies = ga.create_initial_population(NUM_STRATEGIES)

        logger.info(f"Generated {len(strategies)} strategies")

        # ──────────────────────────────────────────
        # Step 3: Backtest all strategies
        # ──────────────────────────────────────────
        logger.info(f"\nBacktesting {len(strategies)} strategies against {len(candles)} candles...")
        engine = VectorBTBacktestEngine(
            initial_balance=settings.initial_account_balance,
            fees=settings.trading_fees
        )

        backtest_results = []
        start_bt = time.time()

        for i, strategy in enumerate(strategies):
            strat_dict = strategy.to_dict()
            result = engine.backtest_strategy(candles, strat_dict, strategy_id=strategy.id)

            if result.get("success"):
                result["pair"] = pair
                result["generation_id"] = generation_id
                result["strategy_params"] = strat_dict
                backtest_results.append(result)

            # Progress
            if (i + 1) % 25 == 0:
                elapsed = time.time() - start_bt
                rate = (i + 1) / elapsed
                logger.info(f"  [{i+1}/{len(strategies)}] {rate:.1f} strategies/sec | "
                           f"{len(backtest_results)} successful")

        bt_time = time.time() - start_bt
        logger.info(f"\nBacktesting complete: {len(backtest_results)}/{len(strategies)} successful in {bt_time:.1f}s "
                     f"({len(backtest_results)/bt_time:.1f} strategies/sec)")

        # ──────────────────────────────────────────
        # Step 4: Ralph Loop - Evaluate & Select
        # ──────────────────────────────────────────
        logger.info(f"\nApplying Ralph Loop (keep top {ELITE_THRESHOLD*100:.0f}%)...")

        # Score and sort
        scored = []
        for result in backtest_results:
            metrics = result.get("metrics", {})
            scored.append({
                "strategy_id": result["strategy_id"],
                "score": metrics.get("composite_score", 0),
                "meets_criteria": metrics.get("meets_criteria", False),
                "metrics": metrics,
                "params": result.get("strategy_params", {}),
                "pair": pair,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        elite_count = max(1, int(len(scored) * ELITE_THRESHOLD))
        elite = scored[:elite_count]
        discarded = scored[elite_count:]
        passed_count = sum(1 for s in scored if s["meets_criteria"])

        logger.info(f"\nRalph Loop Results for {pair}:")
        logger.info(f"  Total tested:    {len(scored)}")
        logger.info(f"  Passed criteria: {passed_count} ({passed_count/len(scored)*100:.1f}%)")
        logger.info(f"  Elite (top 20%): {len(elite)}")
        logger.info(f"  Discarded:       {len(discarded)}")

        if elite:
            logger.info(f"  Best score:      {elite[0]['score']:.1f}/100")
            logger.info(f"  Worst elite:     {elite[-1]['score']:.1f}/100")

        # ──────────────────────────────────────────
        # Step 5: Save results to database
        # ──────────────────────────────────────────
        logger.info(f"\nSaving results to database...")
        saved_count = 0

        for s in scored:
            try:
                metrics = s["metrics"]
                params = s["params"]
                strat_id = s["strategy_id"]
                is_elite = s in elite

                # Save Strategy record
                db_strategy = DBStrategy(
                    id=strat_id,
                    pair=pair,
                    timeframes=json.dumps(params.get("timeframes", [15, 60, 240])),
                    indicators=json.dumps(params.get("indicators", {})),
                    position_sizing=json.dumps(params.get("position_sizing", {})),
                    risk_management=json.dumps(params.get("risk_management", {})),
                    source="genetic_algo",
                    generation_id=generation_id,
                    status="elite" if is_elite else "backtested",
                )
                db.add(db_strategy)

                # Save BacktestResult
                bt_result = BacktestResult(
                    id=f"bt_{uuid.uuid4().hex[:12]}",
                    strategy_id=strat_id,
                    total_profit=metrics.get("total_profit", 0),
                    total_profit_pct=metrics.get("total_profit_pct", 0),
                    win_count=metrics.get("win_count", 0),
                    loss_count=metrics.get("loss_count", 0),
                    win_rate=metrics.get("win_rate", 0),
                    avg_win=metrics.get("avg_win", 0),
                    avg_loss=metrics.get("avg_loss", 0),
                    sharpe_ratio=metrics.get("sharpe_ratio", 0),
                    sortino_ratio=metrics.get("sortino_ratio", 0),
                    max_drawdown=metrics.get("max_drawdown", 0),
                    profit_factor=metrics.get("profit_factor", 0),
                    recovery_factor=metrics.get("recovery_factor", 0),
                    avg_trade_duration=metrics.get("avg_trade_duration", 0),
                    best_trade=metrics.get("best_trade", 0),
                    worst_trade=metrics.get("worst_trade", 0),
                    composite_score=metrics.get("composite_score", 0),
                    meets_criteria=metrics.get("meets_criteria", False),
                    full_metrics=json.dumps(metrics),
                    backtest_start_date=candles['timestamp'].iloc[0],
                    backtest_end_date=candles['timestamp'].iloc[-1],
                )
                db.add(bt_result)
                saved_count += 1

            except Exception as e:
                logger.error(f"Error saving strategy {s['strategy_id']}: {e}")
                db.rollback()
                continue

        db.commit()
        logger.info(f"Saved {saved_count} strategies and backtest results to database")

        total_strategies_tested += len(scored)
        total_passed += passed_count
        all_results.extend(scored)

    # ──────────────────────────────────────────
    # Step 6: Update generation run & final report
    # ──────────────────────────────────────────
    gen_run = db.query(GenerationRun).filter(GenerationRun.generation_id == generation_id).first()
    if gen_run:
        gen_run.status = "completed"
        gen_run.strategies_generated = total_strategies_tested
        gen_run.strategies_backtested = total_strategies_tested
        gen_run.strategies_passed = total_passed
        gen_run.completed_at = datetime.utcnow()

        # Best strategy
        if all_results:
            best = max(all_results, key=lambda x: x["score"])
            gen_run.top_strategy_id = best["strategy_id"]
            gen_run.top_strategy_score = best["score"]

        db.add(gen_run)
        db.commit()

    pipeline_time = time.time() - pipeline_start

    # ──────────────────────────────────────────
    # Final Report
    # ──────────────────────────────────────────
    logger.info("\n" + "=" * 70)
    logger.info("BACKTESTING COMPLETE - GENERATION %d RESULTS", generation_id)
    logger.info("=" * 70)
    logger.info(f"Total strategies tested: {total_strategies_tested}")
    logger.info(f"Total passed criteria:   {total_passed} ({total_passed/total_strategies_tested*100:.1f}%)" if total_strategies_tested > 0 else "")
    logger.info(f"Pipeline duration:       {pipeline_time:.1f}s")
    logger.info(f"Throughput:              {total_strategies_tested/pipeline_time:.1f} strategies/sec" if pipeline_time > 0 else "")

    # Show top 10 elite strategies
    if all_results:
        all_results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"\nTOP 10 ELITE STRATEGIES:")
        logger.info(f"{'Rank':<5} {'ID':<20} {'Score':<8} {'Win%':<8} {'Profit%':<10} {'Sharpe':<8} {'MaxDD':<8} {'Trades':<7} {'Criteria':<8}")
        logger.info("-" * 92)

        for i, s in enumerate(all_results[:10]):
            m = s["metrics"]
            logger.info(
                f"{i+1:<5} {s['strategy_id']:<20} "
                f"{m['composite_score']:<8.1f} "
                f"{m['win_rate']*100:<8.1f} "
                f"{m['total_profit_pct']:<10.2f} "
                f"{m['sharpe_ratio']:<8.2f} "
                f"{m['max_drawdown']*100:<8.1f} "
                f"{m['total_trades']:<7} "
                f"{'PASS' if m['meets_criteria'] else 'FAIL':<8}"
            )

        # Summary of criteria-passing strategies
        passing = [s for s in all_results if s["metrics"]["meets_criteria"]]
        if passing:
            logger.info(f"\n{len(passing)} STRATEGIES PASSED ALL CRITERIA:")
            logger.info(f"  Avg Win Rate:   {np.mean([s['metrics']['win_rate'] for s in passing])*100:.1f}%")
            logger.info(f"  Avg Sharpe:     {np.mean([s['metrics']['sharpe_ratio'] for s in passing]):.2f}")
            logger.info(f"  Avg Profit%:    {np.mean([s['metrics']['total_profit_pct'] for s in passing]):.2f}%")
            logger.info(f"  Avg Max DD:     {np.mean([s['metrics']['max_drawdown'] for s in passing])*100:.1f}%")
        else:
            logger.info("\nNo strategies passed all criteria in this generation.")
            logger.info("This is normal for Gen 1 - the Ralph Loop will evolve better strategies over generations.")

    logger.info(f"\nDatabase: {os.getenv('DATABASE_URL', 'sqlite:///grindstone_apex.db')}")
    logger.info("=" * 70)

    db.close()
    return all_results


if __name__ == "__main__":
    results = run_backtest_pipeline()
