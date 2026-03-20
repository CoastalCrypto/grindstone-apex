"""Ralph Loop: Strategy selection and filtering."""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from src.database import BacktestResult, Strategy, StrategyPerformance, GenerationRun
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RalphLoopEvaluator:
    """Evaluate, select, and breed strategies based on performance."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.elite_threshold = settings.elite_threshold  # Top 20%
        self.mutation_rate = settings.mutation_rate

    def evaluate_generation(
        self,
        generation_id: int,
        pair: str,
        backtest_results: List[Dict]
    ) -> Dict:
        """
        Evaluate all strategies in a generation.

        Args:
            generation_id: Generation ID
            pair: Trading pair
            backtest_results: List of backtest result dicts

        Returns:
            Dictionary with elite, discard, and second-chance strategies
        """
        logger.info(f"Evaluating generation {generation_id} ({len(backtest_results)} strategies)")

        if not backtest_results:
            logger.warning("No backtest results to evaluate")
            return {
                "generation_id": generation_id,
                "total_tested": 0,
                "elite_count": 0,
                "discard_count": 0,
                "passed_count": 0,
                "elite": [],
                "discard": [],
            }

        # Score all strategies
        scored = []
        for result in backtest_results:
            metrics = result.get("metrics", {})
            score = metrics.get("composite_score", 0)
            meets_criteria = metrics.get("meets_criteria", False)

            scored.append({
                "strategy_id": result.get("strategy_id"),
                "score": score,
                "meets_criteria": meets_criteria,
                "metrics": metrics,
            })

        # Sort by score
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Ralph Loop: Select top X%
        elite_count = max(1, int(len(scored) * self.elite_threshold))
        elite_strategies = scored[:elite_count]
        discard_strategies = scored[elite_count:]

        # Count how many passed criteria
        passed_count = sum(1 for s in scored if s["meets_criteria"])

        logger.info(f"Ralph Loop results:")
        logger.info(f"  Total strategies: {len(scored)}")
        logger.info(f"  Elite (top {self.elite_threshold*100:.0f}%): {len(elite_strategies)}")
        logger.info(f"  Discarded: {len(discard_strategies)}")
        logger.info(f"  Passed criteria: {passed_count}")
        logger.info(f"  Top score: {elite_strategies[0]['score']:.1f}/100" if elite_strategies else "  No elite")

        return {
            "generation_id": generation_id,
            "total_tested": len(scored),
            "elite_count": len(elite_strategies),
            "discard_count": len(discard_strategies),
            "passed_count": passed_count,
            "pass_rate": passed_count / len(scored) if scored else 0,
            "elite": elite_strategies,
            "discard": discard_strategies,
            "best_strategy_score": elite_strategies[0]["score"] if elite_strategies else 0,
            "worst_strategy_score": discard_strategies[-1]["score"] if discard_strategies else 0,
        }

    def persist_evaluation(
        self,
        generation_id: int,
        pair: str,
        evaluation_result: Dict
    ) -> None:
        """
        Save evaluation results to database.

        Args:
            generation_id: Generation ID
            pair: Trading pair
            evaluation_result: Evaluation result dict
        """
        try:
            # Update generation run
            gen_run = self.db.query(GenerationRun).filter(
                GenerationRun.generation_id == generation_id
            ).first()

            if gen_run:
                gen_run.strategies_passed = evaluation_result.get("passed_count", 0)
                gen_run.strategies_backtested = evaluation_result.get("total_tested", 0)
                self.db.add(gen_run)

            # Mark elite strategies as such
            for elite_strat in evaluation_result.get("elite", []):
                strategy_id = elite_strat["strategy_id"]
                perf = self.db.query(StrategyPerformance).filter(
                    StrategyPerformance.strategy_id == strategy_id
                ).first()

                if perf:
                    perf.deployed = False  # Will be deployed later
                    self.db.add(perf)

            self.db.commit()
            logger.info("Evaluation results persisted to database")

        except Exception as e:
            logger.error(f"Error persisting evaluation: {e}")
            self.db.rollback()

    def get_elite_strategies(
        self,
        pair: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get elite strategies from database.

        Args:
            pair: Optional pair filter
            limit: Max strategies to return

        Returns:
            List of elite strategy dicts
        """
        query = self.db.query(BacktestResult).filter(
            BacktestResult.meets_criteria == True
        ).order_by(desc(BacktestResult.composite_score))

        if pair:
            query = query.filter(BacktestResult.strategy_id.like(f"%{pair}%"))

        results = query.limit(limit).all()

        return [
            {
                "strategy_id": r.strategy_id,
                "score": r.composite_score,
                "win_rate": r.win_rate,
                "profit_pct": r.total_profit_pct,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
                "num_trades": r.win_count + r.loss_count,
                "profit_factor": r.profit_factor,
            }
            for r in results
        ]

    def get_generation_statistics(
        self,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get statistics for recent generations.

        Args:
            limit: Number of generations to return

        Returns:
            List of generation stats
        """
        runs = self.db.query(GenerationRun).order_by(
            desc(GenerationRun.started_at)
        ).limit(limit).all()

        return [
            {
                "generation_id": r.generation_id,
                "strategies_generated": r.strategies_generated,
                "strategies_backtested": r.strategies_backtested,
                "strategies_passed": r.strategies_passed,
                "pass_rate": r.strategies_passed / r.strategies_backtested if r.strategies_backtested > 0 else 0,
                "improvement": (r.strategies_passed / r.strategies_backtested * 100) if r.strategies_backtested > 0 else 0,
                "top_score": r.top_strategy_score,
                "status": r.status,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "duration_seconds": (r.completed_at - r.started_at).total_seconds() if r.completed_at else None,
            }
            for r in runs
        ]

    def get_strategy_genealogy(
        self,
        strategy_id: str,
        depth: int = 5
    ) -> Dict:
        """
        Get genealogy (parent/child relationships) of a strategy.

        Args:
            strategy_id: Strategy ID to trace
            depth: How many generations to trace back

        Returns:
            Genealogy tree
        """
        genealogy = {
            "strategy_id": strategy_id,
            "ancestors": [],
            "descendants": [],
        }

        try:
            # Get the strategy
            strategy = self.db.query(Strategy).filter(
                Strategy.id == strategy_id
            ).first()

            if not strategy:
                return genealogy

            # Trace ancestors (parents)
            current = strategy
            for _ in range(depth):
                if current.parent_id:
                    parent = self.db.query(Strategy).filter(
                        Strategy.id == current.parent_id
                    ).first()

                    if parent:
                        genealogy["ancestors"].append({
                            "id": parent.id,
                            "generation": parent.generation_id,
                            "source": parent.metadata.get("source", "unknown") if hasattr(parent, "metadata") else "unknown",
                        })
                        current = parent
                    else:
                        break
                else:
                    break

            # Trace descendants (children)
            children = self.db.query(Strategy).filter(
                Strategy.parent_id == strategy_id
            ).all()

            for child in children:
                genealogy["descendants"].append({
                    "id": child.id,
                    "generation": child.generation_id,
                    "source": child.metadata.get("source", "unknown") if hasattr(child, "metadata") else "unknown",
                })

            return genealogy

        except Exception as e:
            logger.error(f"Error getting genealogy: {e}")
            return genealogy

    def identify_successful_patterns(
        self,
        limit: int = 50
    ) -> Dict:
        """
        Analyze elite strategies to identify successful parameter patterns.

        Args:
            limit: Number of elite strategies to analyze

        Returns:
            Dictionary with identified patterns
        """
        elite = self.db.query(BacktestResult).filter(
            BacktestResult.meets_criteria == True
        ).order_by(desc(BacktestResult.composite_score)).limit(limit).all()

        if not elite:
            return {"message": "No elite strategies to analyze"}

        patterns = {
            "sma_fast_range": {"min": float('inf'), "max": 0, "avg": 0},
            "sma_slow_range": {"min": float('inf'), "max": 0, "avg": 0},
            "rsi_buy_range": {"min": float('inf'), "max": 0, "avg": 0},
            "rsi_sell_range": {"min": float('inf'), "max": 0, "avg": 0},
            "position_size_range": {"min": float('inf'), "max": 0, "avg": 0},
            "atr_multiplier_range": {"min": float('inf'), "max": 0, "avg": 0},
            "avg_win_rate": 0,
            "avg_sharpe": 0,
            "avg_profit_pct": 0,
        }

        for result in elite:
            metrics = result.full_metrics if hasattr(result, "full_metrics") else {}

            # Extract patterns (simplified - would need full schema)
            patterns["avg_win_rate"] += result.win_rate
            patterns["avg_sharpe"] += result.sharpe_ratio
            patterns["avg_profit_pct"] += result.total_profit_pct

        # Calculate averages
        if elite:
            patterns["avg_win_rate"] /= len(elite)
            patterns["avg_sharpe"] /= len(elite)
            patterns["avg_profit_pct"] /= len(elite)

        patterns["total_elite_analyzed"] = len(elite)

        logger.info(f"Identified patterns from {len(elite)} elite strategies:")
        logger.info(f"  Average win rate: {patterns['avg_win_rate']*100:.1f}%")
        logger.info(f"  Average Sharpe: {patterns['avg_sharpe']:.2f}")
        logger.info(f"  Average profit: {patterns['avg_profit_pct']:.2f}%")

        return patterns

    def compare_generations(
        self,
        gen1_id: int,
        gen2_id: int
    ) -> Dict:
        """
        Compare performance between two generations.

        Args:
            gen1_id: First generation ID
            gen2_id: Second generation ID

        Returns:
            Comparison stats
        """
        gen1 = self.db.query(GenerationRun).filter(
            GenerationRun.generation_id == gen1_id
        ).first()

        gen2 = self.db.query(GenerationRun).filter(
            GenerationRun.generation_id == gen2_id
        ).first()

        if not gen1 or not gen2:
            return {"error": "Generation not found"}

        return {
            "generation_1": {
                "id": gen1_id,
                "pass_rate": gen1.strategies_passed / gen1.strategies_backtested if gen1.strategies_backtested > 0 else 0,
                "top_score": gen1.top_strategy_score,
            },
            "generation_2": {
                "id": gen2_id,
                "pass_rate": gen2.strategies_passed / gen2.strategies_backtested if gen2.strategies_backtested > 0 else 0,
                "top_score": gen2.top_strategy_score,
            },
            "improvement": {
                "pass_rate_change": (gen2.strategies_passed / gen2.strategies_backtested if gen2.strategies_backtested > 0 else 0) - (gen1.strategies_passed / gen1.strategies_backtested if gen1.strategies_backtested > 0 else 0),
                "top_score_change": (gen2.top_strategy_score or 0) - (gen1.top_strategy_score or 0),
            }
        }
