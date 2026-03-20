"""Genetic Algorithm for strategy generation and evolution."""
import random
import uuid
from typing import List, Dict, Tuple, Optional
import logging
import numpy as np
from copy import deepcopy

logger = logging.getLogger(__name__)


class Strategy:
    """Represents a trading strategy with parameters."""

    def __init__(
        self,
        pair: str,
        timeframes: List[int],
        indicators: Dict,
        position_sizing: Dict,
        risk_management: Dict,
        source: str = "ga",
        parent_id: Optional[str] = None,
        generation_id: int = 0
    ):
        """Initialize strategy."""
        self.id = f"strat_{uuid.uuid4().hex[:12]}"
        self.pair = pair
        self.timeframes = timeframes
        self.indicators = indicators
        self.position_sizing = position_sizing
        self.risk_management = risk_management
        self.source = source
        self.parent_id = parent_id
        self.generation_id = generation_id
        self.fitness_score = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pair": self.pair,
            "timeframes": self.timeframes,
            "indicators": self.indicators,
            "position_sizing": self.position_sizing,
            "risk_management": self.risk_management,
            "metadata": {
                "source": self.source,
                "parent_id": self.parent_id,
                "generation_id": self.generation_id,
            }
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create strategy from dictionary."""
        metadata = data.get("metadata", {})
        return cls(
            pair=data["pair"],
            timeframes=data["timeframes"],
            indicators=data["indicators"],
            position_sizing=data["position_sizing"],
            risk_management=data["risk_management"],
            source=metadata.get("source", "ga"),
            parent_id=metadata.get("parent_id"),
            generation_id=metadata.get("generation_id", 0),
        )


class GeneticAlgorithmEngine:
    """Generate and evolve strategies using genetic algorithms."""

    def __init__(self, pair: str = "BTC/USDT", mutation_rate: float = 0.15):
        """
        Initialize GA engine.

        Args:
            pair: Trading pair
            mutation_rate: Probability of mutation per parameter (0-1)
        """
        self.pair = pair
        self.mutation_rate = mutation_rate
        self.elite_strategies = []
        self.generation_id = 0

    def create_initial_population(self, population_size: int = 100) -> List[Strategy]:
        """
        Create initial random population of strategies.

        Args:
            population_size: Number of strategies to generate

        Returns:
            List of Strategy objects
        """
        population = []

        for _ in range(population_size):
            strategy = self._generate_random_strategy()
            population.append(strategy)

        logger.info(f"Created initial population of {len(population)} strategies")
        return population

    def evolve_population(
        self,
        elite_strategies: List[Tuple[Strategy, float]],
        population_size: int = 500,
        generation_id: int = 0
    ) -> List[Strategy]:
        """
        Evolve population by mutating and crossing over elite strategies.

        Args:
            elite_strategies: List of (Strategy, fitness_score) tuples
            population_size: Target population size
            generation_id: Current generation ID

        Returns:
            New population of strategies
        """
        if not elite_strategies:
            logger.warning("No elite strategies provided, generating random population")
            return self.create_initial_population(population_size)

        self.elite_strategies = elite_strategies
        self.generation_id = generation_id

        new_population = []

        # Preserve elite strategies (elitism)
        for elite_strat, _ in elite_strategies[:max(1, population_size // 10)]:
            new_population.append(deepcopy(elite_strat))

        # Generate new strategies through mutation and crossover
        while len(new_population) < population_size:
            # Select parents
            parent1, _ = random.choice(elite_strategies)
            parent2, _ = random.choice(elite_strategies) if len(elite_strategies) > 1 else (parent1, 0)

            # Mutation or Crossover
            if random.random() < 0.6:  # 60% mutation, 40% crossover
                child = self.mutate(parent1, generation_id)
            else:
                child = self.crossover(parent1, parent2, generation_id)

            new_population.append(child)

        logger.info(f"Generated evolved population of {len(new_population)} strategies (generation {generation_id})")
        return new_population

    def mutate(self, strategy: Strategy, generation_id: int) -> Strategy:
        """
        Create mutated version of a strategy.

        Args:
            strategy: Parent strategy
            generation_id: Current generation ID

        Returns:
            New mutated strategy
        """
        mutated = deepcopy(strategy)
        mutated.id = f"strat_{uuid.uuid4().hex[:12]}"
        mutated.parent_id = strategy.id
        mutated.generation_id = generation_id
        mutated.source = "ga_mutation"

        # Mutate each indicator parameter with probability
        for param in mutated.indicators:
            if random.random() < self.mutation_rate:
                mutated.indicators[param] = self._perturb_parameter(
                    param,
                    mutated.indicators[param]
                )

        # Mutate position sizing
        if random.random() < self.mutation_rate:
            mutated.position_sizing["size_amount"] = max(
                0.1,
                min(1.0, mutated.position_sizing["size_amount"] * random.uniform(0.8, 1.2))
            )

        # Mutate risk management
        if random.random() < self.mutation_rate:
            mutated.risk_management["stop_loss_atr"] = max(
                3.0,
                min(5.0, mutated.risk_management["stop_loss_atr"] * random.uniform(0.9, 1.1))
            )

        return mutated

    def crossover(
        self,
        parent1: Strategy,
        parent2: Strategy,
        generation_id: int
    ) -> Strategy:
        """
        Create child strategy by combining two parents.

        Args:
            parent1: First parent strategy
            parent2: Second parent strategy
            generation_id: Current generation ID

        Returns:
            Child strategy
        """
        child = Strategy(
            pair=parent1.pair,
            timeframes=random.choice([parent1.timeframes, parent2.timeframes]),
            indicators={},
            position_sizing={},
            risk_management={},
            source="ga_crossover",
            generation_id=generation_id
        )

        # Take random parameters from each parent
        for key in parent1.indicators:
            child.indicators[key] = random.choice([
                parent1.indicators.get(key),
                parent2.indicators.get(key)
            ])

        for key in parent1.position_sizing:
            child.position_sizing[key] = random.choice([
                parent1.position_sizing.get(key),
                parent2.position_sizing.get(key)
            ])

        for key in parent1.risk_management:
            child.risk_management[key] = random.choice([
                parent1.risk_management.get(key),
                parent2.risk_management.get(key)
            ])

        return child

    def _generate_random_strategy(self) -> Strategy:
        """Generate random strategy with valid parameters."""
        return Strategy(
            pair=self.pair,
            timeframes=[15, 60, 240],
            indicators={
                "sma_fast": random.randint(10, 50),
                "sma_slow": random.randint(100, 250),
                "rsi_threshold_buy": random.randint(20, 40),
                "rsi_threshold_sell": random.randint(60, 80),
                "bollinger_period": random.randint(15, 25),
            },
            position_sizing={
                "size_type": "percent_of_balance",
                "size_amount": random.uniform(0.1, 1.0),
            },
            risk_management={
                "stop_loss_atr": random.uniform(3.0, 5.0),
                "take_profit_percent": random.uniform(0.15, 0.30),
                "breakeven_on_profit": True,
                "max_drawdown_limit": 0.30,
            },
            source="ga"
        )

    def _perturb_parameter(self, param_name: str, current_value: float) -> float:
        """
        Perturb a parameter with bounds checking.

        Args:
            param_name: Name of parameter
            current_value: Current parameter value

        Returns:
            Perturbed value
        """
        # Define bounds for each parameter
        bounds = {
            "sma_fast": (5, 100),
            "sma_slow": (50, 500),
            "rsi_threshold_buy": (10, 50),
            "rsi_threshold_sell": (50, 90),
            "bollinger_period": (10, 50),
            "stop_loss_atr": (2.0, 6.0),
            "take_profit_percent": (0.10, 0.50),
            "size_amount": (0.1, 1.0),
        }

        if param_name not in bounds:
            # Default perturbation: ±20%
            return current_value * random.uniform(0.8, 1.2)

        min_val, max_val = bounds[param_name]

        # Perturbation: ±10-20%
        perturbation = random.uniform(0.9, 1.1)
        new_value = current_value * perturbation

        # Enforce bounds
        return max(min_val, min(max_val, new_value))


def create_elite_strategies_from_winners(
    winning_backtest_results: List[Dict],
    pairs: List[str] = None
) -> List[Tuple[Strategy, float]]:
    """
    Convert winning backtest results to elite strategies for breeding.

    Args:
        winning_backtest_results: List of backtest result dicts
        pairs: Optional list of pairs to filter

    Returns:
        List of (Strategy, score) tuples
    """
    elite = []

    for result in winning_backtest_results:
        # Only include strategies that meet criteria
        if not result.get("metrics", {}).get("meets_criteria", False):
            continue

        # Create strategy from result
        strategy = Strategy(
            pair=result.get("pair", "BTC/USDT"),
            timeframes=result.get("timeframes", [15, 60, 240]),
            indicators=result.get("indicators", {}),
            position_sizing=result.get("position_sizing", {}),
            risk_management=result.get("risk_management", {}),
        )

        score = result.get("metrics", {}).get("composite_score", 0)
        elite.append((strategy, score))

    logger.info(f"Created {len(elite)} elite strategies from winning backtests")
    return elite
