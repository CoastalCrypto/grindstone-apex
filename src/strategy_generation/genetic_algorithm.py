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
            "strategy_type": self.indicators.get("strategy_type", "sma_crossover"),
            "direction": self.indicators.get("direction", "long"),
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
        # Skip non-numeric params like strategy_type and direction
        NON_MUTABLE = {"strategy_type", "direction", "combo_indicators"}
        for param in mutated.indicators:
            if param in NON_MUTABLE:
                continue
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

        # Pick one parent's strategy_type/direction as a coherent unit
        type_parent = random.choice([parent1, parent2])
        child.indicators["strategy_type"] = type_parent.indicators.get("strategy_type", "sma_crossover")
        child.indicators["direction"] = type_parent.indicators.get("direction", "long")

        # Crossover numeric parameters from both parents
        NON_MUTABLE = {"strategy_type", "direction", "combo_indicators"}
        for key in parent1.indicators:
            if key in NON_MUTABLE:
                continue
            p1_val = parent1.indicators.get(key)
            p2_val = parent2.indicators.get(key)
            if p2_val is not None:
                child.indicators[key] = random.choice([p1_val, p2_val])
            else:
                child.indicators[key] = p1_val

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

    # All available strategy types
    STRATEGY_TYPES = [
        'sma_crossover', 'ema_crossover', 'breakout', 'volume_breakout',
        'rsi_reversal', 'bollinger_bounce', 'macd', 'orb', 'liquidity_sweep',
        'fib_retracement', 'stochastic', 'adx_trend', 'ichimoku',
        'ad_line', 'aroon', 'combo'
    ]

    def _generate_random_strategy(self) -> Strategy:
        """Generate random strategy from multiple indicator types, long or short."""
        strategy_type = random.choice(self.STRATEGY_TYPES)
        direction = random.choice(['long', 'short'])
        indicators = self._random_indicators_for_type(strategy_type)

        return Strategy(
            pair=self.pair,
            timeframes=[15, 60, 240],
            indicators=indicators,
            position_sizing={
                "size_type": "percent_of_balance",
                "size_amount": random.uniform(0.1, 0.4),
            },
            risk_management={
                "stop_loss_atr": random.uniform(1.0, 3.5),
                "take_profit_percent": random.uniform(0.005, 0.08),  # 0.5% - 8%
                "breakeven_on_profit": random.choice([True, False]),
                "max_drawdown_limit": 0.30,
            },
            source="ga",
        )

    def _random_indicators_for_type(self, strategy_type: str) -> dict:
        """Generate random indicator parameters for a given strategy type."""
        direction = random.choice(['long', 'short'])
        base = {"strategy_type": strategy_type, "direction": direction}

        if strategy_type == 'sma_crossover':
            fast = random.randint(5, 50)
            slow = random.randint(fast + 15, fast + 150)
            base.update({"sma_fast": fast, "sma_slow": slow})

        elif strategy_type == 'ema_crossover':
            fast = random.randint(5, 30)
            slow = random.randint(fast + 10, fast + 80)
            base.update({"ema_fast": fast, "ema_slow": slow})

        elif strategy_type == 'breakout':
            base.update({"breakout_period": random.randint(10, 96)})

        elif strategy_type == 'volume_breakout':
            base.update({
                "volume_period": random.randint(10, 50),
                "volume_multiplier": random.uniform(1.5, 4.0),
                "price_period": random.randint(5, 20),
            })

        elif strategy_type == 'rsi_reversal':
            buy = random.randint(20, 40)
            sell = random.randint(60, 85)
            base.update({
                "rsi_period": random.randint(7, 21),
                "rsi_threshold_buy": buy,
                "rsi_threshold_sell": sell,
            })

        elif strategy_type == 'bollinger_bounce':
            base.update({
                "bollinger_period": random.randint(15, 40),
                "bollinger_std": random.uniform(1.5, 3.0),
            })

        elif strategy_type == 'macd':
            fast = random.randint(8, 16)
            slow = random.randint(20, 35)
            sig = random.randint(5, 12)
            base.update({"macd_fast": fast, "macd_slow": slow, "macd_signal": sig})

        elif strategy_type == 'orb':
            base.update({"orb_bars": random.randint(2, 8)})

        elif strategy_type == 'liquidity_sweep':
            base.update({
                "sweep_lookback": random.randint(10, 50),
                "reclaim_bars": random.randint(1, 5),
            })

        elif strategy_type == 'fib_retracement':
            base.update({
                "fib_lookback": random.randint(20, 100),
                "fib_level": random.choice([0.236, 0.382, 0.5, 0.618, 0.786]),
                "fib_tolerance": random.uniform(0.002, 0.015),
                "trend_period": random.randint(20, 60),
            })

        elif strategy_type == 'stochastic':
            base.update({
                "stoch_k_period": random.randint(5, 21),
                "stoch_d_period": random.randint(3, 9),
                "stoch_oversold": random.randint(15, 30),
                "stoch_overbought": random.randint(70, 85),
            })

        elif strategy_type == 'adx_trend':
            base.update({
                "adx_period": random.randint(10, 28),
                "adx_threshold": random.uniform(20.0, 35.0),
                "di_period": random.randint(10, 28),
            })

        elif strategy_type == 'ichimoku':
            base.update({
                "tenkan_period": random.randint(7, 12),
                "kijun_period": random.randint(20, 30),
                "senkou_b_period": random.randint(44, 60),
                "displacement": random.randint(22, 30),
            })

        elif strategy_type == 'ad_line':
            base.update({
                "ad_ema_fast": random.randint(3, 12),
                "ad_ema_slow": random.randint(15, 40),
            })

        elif strategy_type == 'aroon':
            base.update({
                "aroon_period": random.randint(14, 50),
                "aroon_threshold": random.uniform(60.0, 85.0),
            })

        elif strategy_type == 'combo':
            # Combo: pick 2-3 indicators from a pool and require ALL to agree
            pool = ['rsi', 'macd', 'bollinger', 'stochastic', 'adx', 'ema', 'volume']
            n_indicators = random.randint(2, 3)
            chosen = random.sample(pool, n_indicators)
            base["combo_indicators"] = ",".join(chosen)
            # Always include params for each chosen indicator
            if 'rsi' in chosen:
                base["rsi_period"] = random.randint(7, 21)
                base["rsi_threshold_buy"] = random.randint(25, 40)
                base["rsi_threshold_sell"] = random.randint(60, 80)
            if 'macd' in chosen:
                fast = random.randint(8, 16)
                slow = random.randint(20, 35)
                base["macd_fast"] = fast
                base["macd_slow"] = slow
                base["macd_signal"] = random.randint(5, 12)
            if 'bollinger' in chosen:
                base["bollinger_period"] = random.randint(15, 35)
                base["bollinger_std"] = random.uniform(1.5, 2.8)
            if 'stochastic' in chosen:
                base["stoch_k_period"] = random.randint(5, 21)
                base["stoch_d_period"] = random.randint(3, 9)
                base["stoch_oversold"] = random.randint(15, 30)
                base["stoch_overbought"] = random.randint(70, 85)
            if 'adx' in chosen:
                base["adx_period"] = random.randint(10, 28)
                base["adx_threshold"] = random.uniform(20.0, 35.0)
                base["di_period"] = random.randint(10, 28)
            if 'ema' in chosen:
                fast = random.randint(5, 20)
                base["ema_fast"] = fast
                base["ema_slow"] = random.randint(fast + 10, fast + 60)
            if 'volume' in chosen:
                base["volume_period"] = random.randint(10, 40)
                base["volume_multiplier"] = random.uniform(1.3, 3.0)

        # Optional RSI filter for non-RSI strategies
        if strategy_type not in ['rsi_reversal'] and random.random() < 0.3:
            base["rsi_filter"] = random.randint(65, 80)

        return base

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
            "sma_fast": (3, 80),
            "sma_slow": (30, 300),
            "rsi_threshold_buy": (20, 50),
            "rsi_threshold_sell": (50, 85),
            "bollinger_period": (10, 40),
            "stop_loss_atr": (1.0, 5.0),
            "take_profit_percent": (0.01, 0.20),
            "size_amount": (0.05, 0.5),
            "fib_lookback": (15, 120),
            "fib_level": (0.15, 0.88),
            "fib_tolerance": (0.001, 0.025),
            "trend_period": (15, 80),
            "stoch_k_period": (3, 30),
            "stoch_d_period": (2, 14),
            "stoch_oversold": (10, 35),
            "stoch_overbought": (65, 90),
            "adx_period": (7, 40),
            "adx_threshold": (15.0, 45.0),
            "di_period": (7, 40),
            "tenkan_period": (5, 15),
            "kijun_period": (15, 40),
            "senkou_b_period": (35, 70),
            "displacement": (18, 35),
            "ad_ema_fast": (2, 15),
            "ad_ema_slow": (10, 50),
            "aroon_period": (10, 60),
            "aroon_threshold": (50.0, 95.0),
        }

        # Safety: skip non-numeric values entirely
        if not isinstance(current_value, (int, float)):
            return current_value

        if param_name not in bounds:
            # Default perturbation: ±20%
            new_value = current_value * random.uniform(0.8, 1.2)
            # Preserve int type for period/window params
            if isinstance(current_value, int):
                return max(1, int(round(new_value)))
            return new_value

        min_val, max_val = bounds[param_name]

        # Perturbation: ±10-20%
        perturbation = random.uniform(0.9, 1.1)
        new_value = current_value * perturbation

        # Enforce bounds
        new_value = max(min_val, min(max_val, new_value))

        # Preserve int type for period/window params
        if isinstance(current_value, int):
            return max(1, int(round(new_value)))
        return new_value


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
