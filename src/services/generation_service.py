"""Background service for continuous strategy generation and evolution."""
import logging
import time
import asyncio
from typing import List
import os
from dotenv import load_dotenv

from src.database import SessionLocal, Strategy, BacktestResult, GenerationRun
from src.config import get_settings
from src.backtesting.data_loader import get_data_loader
from src.backtesting.vectorbt_engine import VectorBTBacktestEngine
from src.strategy_generation.genetic_algorithm import (
    GeneticAlgorithmEngine, create_elite_strategies_from_winners
)
from src.ralph_loop.evaluator import RalphLoopEvaluator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class StrategyGenerationService:
    """Continuous background service for strategy generation and evolution."""

    def __init__(self):
        """Initialize service."""
        self.db = SessionLocal()
        self.settings = settings
        self.loader = get_data_loader()
        self.backtest_engine = VectorBTBacktestEngine()
        self.evaluator = RalphLoopEvaluator(self.db)

    def run_continuous(self, interval_seconds: int = 300):
        """
        Run continuous generation loop.

        Args:
            interval_seconds: Time between generation cycles (default 5 min)
        """
        generation_id = 0

        logger.info("="*60)
        logger.info("Starting Continuous Strategy Generation Service")
        logger.info(f"Generation interval: {interval_seconds}s")
        logger.info(f"Pairs to trade: {self.settings.pairs_list}")
        logger.info("="*60)

        while True:
            try:
                generation_id += 1
                logger.info(f"\n🔄 Generation {generation_id} starting...")

                # Run generation cycle
                self.run_generation_cycle(generation_id)

                # Wait for next cycle
                logger.info(f"⏳ Waiting {interval_seconds}s until next generation...")
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("🛑 Generation service stopped by user")
                break

            except Exception as e:
                logger.error(f"❌ Error in generation cycle: {e}", exc_info=True)
                logger.info(f"⏳ Waiting {interval_seconds}s before retry...")
                time.sleep(interval_seconds)

    def run_generation_cycle(self, generation_id: int) -> None:
        """
        Run one complete generation cycle.

        Args:
            generation_id: Current generation ID
        """
        start_time = time.time()

        # Create generation run record
        gen_run = GenerationRun(
            generation_id=generation_id,
            status="running"
        )
        self.db.add(gen_run)
        self.db.commit()

        try:
            total_strategies = 0
            total_passed = 0

            for pair in self.settings.pairs_list:
                logger.info(f"\n📊 Processing pair: {pair}")

                # Get elite strategies from previous generation
                elite = self.evaluator.get_elite_strategies(limit=20)

                # Generate strategies
                if not elite or generation_id == 1:
                    # First generation: random population
                    logger.info(f"  Generating {self.settings.strategies_per_generation} random strategies...")
                    ga = GeneticAlgorithmEngine(pair=pair)
                    strategies = ga.create_initial_population(
                        self.settings.strategies_per_generation
                    )
                else:
                    # Subsequent generations: evolve from elite
                    logger.info(f"  Evolving from {len(elite)} elite strategies...")
                    elite_tuples = [(None, s["score"]) for s in elite]  # Simplified
                    ga = GeneticAlgorithmEngine(pair=pair)
                    strategies = ga.evolve_population(
                        elite_tuples,
                        self.settings.strategies_per_generation,
                        generation_id
                    )

                # Backtest all strategies
                logger.info(f"  Backtesting {len(strategies)} strategies...")
                backtest_results = []
                passed_count = 0

                for i, strategy in enumerate(strategies):
                    try:
                        # Load data
                        candles = self.loader.load_candles(pair, 15, 365)
                        if candles.empty:
                            logger.warning(f"    No data for {pair}")
                            continue

                        # Backtest
                        result = self.backtest_engine.backtest_strategy(
                            candles,
                            strategy.to_dict(),
                            strategy_id=strategy.id
                        )

                        if result.get("success"):
                            backtest_results.append(result)
                            metrics = result.get("metrics", {})

                            if metrics.get("meets_criteria"):
                                passed_count += 1

                            # Show progress every 50
                            if (i + 1) % 50 == 0:
                                logger.info(f"    Tested {i+1}/{len(strategies)}")

                    except Exception as e:
                        logger.error(f"    Error backtesting strategy {i}: {e}")

                # Evaluate using Ralph Loop
                logger.info(f"  Evaluating {len(backtest_results)} backtest results...")
                evaluation = self.evaluator.evaluate_generation(
                    generation_id,
                    pair,
                    backtest_results
                )

                logger.info(f"  ✓ Ralph Loop Results for {pair}:")
                logger.info(f"    - Tested: {evaluation['total_tested']}")
                logger.info(f"    - Passed criteria: {evaluation['passed_count']} ({evaluation['pass_rate']*100:.1f}%)")
                logger.info(f"    - Elite (top 20%): {evaluation['elite_count']}")
                logger.info(f"    - Best score: {evaluation['best_strategy_score']:.1f}/100")

                total_strategies += evaluation['total_tested']
                total_passed += evaluation['passed_count']

                # Persist results
                self.evaluator.persist_evaluation(generation_id, pair, evaluation)

                # Save elite strategies to DB
                for elite_strat in evaluation['elite'][:5]:  # Save top 5
                    try:
                        strat_id = elite_strat['strategy_id']
                        logger.info(f"    Saving elite strategy: {strat_id}")
                        # Strategy already saved from backtesting
                    except Exception as e:
                        logger.error(f"    Error saving elite strategy: {e}")

            # Update generation run
            duration = time.time() - start_time
            gen_run = self.db.query(GenerationRun).filter(
                GenerationRun.generation_id == generation_id
            ).first()

            if gen_run:
                gen_run.status = "completed"
                gen_run.strategies_generated = total_strategies
                gen_run.strategies_backtested = total_strategies
                gen_run.strategies_passed = total_passed
                gen_run.completed_at = time.time()
                self.db.add(gen_run)
                self.db.commit()

            logger.info(f"\n✅ Generation {generation_id} complete!")
            logger.info(f"  Total strategies: {total_strategies}")
            logger.info(f"  Total passed: {total_passed} ({total_passed/total_strategies*100:.1f}%)")
            logger.info(f"  Duration: {duration:.0f}s")

        except Exception as e:
            logger.error(f"Error in generation cycle: {e}")
            gen_run.status = "failed"
            gen_run.error_message = str(e)
            self.db.add(gen_run)
            self.db.commit()

    def get_status(self) -> dict:
        """Get current service status."""
        latest_gen = self.db.query(GenerationRun).order_by(
            GenerationRun.generation_id.desc()
        ).first()

        if not latest_gen:
            return {"status": "idle", "message": "No generations yet"}

        return {
            "status": latest_gen.status,
            "current_generation": latest_gen.generation_id,
            "strategies_generated": latest_gen.strategies_generated,
            "strategies_passed": latest_gen.strategies_passed,
            "pass_rate": latest_gen.strategies_passed / latest_gen.strategies_generated if latest_gen.strategies_generated > 0 else 0,
        }


def main():
    """Entry point for generation service."""
    service = StrategyGenerationService()

    # Run with 5-minute intervals
    try:
        service.run_continuous(interval_seconds=300)
    except KeyboardInterrupt:
        logger.info("Service stopped")
    finally:
        service.db.close()


if __name__ == "__main__":
    main()
