"""Enhanced strategy generator using MiroFish-powered multi-agent simulation."""
import logging
from typing import Dict, List, Optional
import numpy as np

from src.simulation.agent_market_simulator import AgentMarketSimulator
from src.simulation.scenario_tester import ScenarioStressTester, MarketScenario
from src.optimization.swarm_optimizer import HybridSwarmOptimizer, ParticleSwarmOptimizer
from src.analysis.regime_predictor import RegimePredictionModel
from src.mirofish.mirofish_client import MiroFishClient, LocalMiroFishSimulator
from src.backtesting.vectorbt_engine import VectorBTBacktestEngine
from src.backtesting.data_loader import get_data_loader

logger = logging.getLogger(__name__)


class MiroFishEnhancedStrategyGenerator:
    """
    Enhanced strategy generator using MiroFish multi-agent simulation.

    Combines:
    - Agent-based market simulation
    - Swarm intelligence optimization
    - Scenario stress testing
    - Regime-aware generation
    - Live MiroFish API integration
    """

    def __init__(self, use_mirofish_api: bool = True):
        """
        Initialize enhanced generator.

        Args:
            use_mirofish_api: Use live MiroFish API if available
        """
        self.mirofish = MiroFishClient() if use_mirofish_api else LocalMiroFishSimulator()
        self.agent_simulator = AgentMarketSimulator(num_agents=100)
        self.stress_tester = ScenarioStressTester()
        self.regime_predictor = RegimePredictionModel()
        self.backtester = VectorBTBacktestEngine()
        self.loader = get_data_loader()

        logger.info("MiroFish Enhanced Strategy Generator initialized")

    def generate_with_agent_validation(self, param_template: Dict,
                                       pair: str = "BTC/USDT",
                                       num_strategies: int = 50) -> List[Dict]:
        """
        Generate strategies validated against agent-based simulation.

        Args:
            param_template: Template strategy parameters
            pair: Trading pair
            num_strategies: Number of strategies to generate

        Returns:
            List of validated strategies
        """
        logger.info(f"Generating {num_strategies} strategies with agent-based validation")

        strategies = []

        # Load market data
        candles = self.loader.load_candles(pair, "1h", 100)
        if candles.empty:
            logger.error(f"No data for {pair}")
            return []

        prices = candles["close"].values

        # Run agent-based simulation
        sim_result = self.agent_simulator.simulate(prices, num_steps=100)

        simulated_prices = sim_result["simulated_prices"]
        agent_stats = sim_result["agent_returns"]

        logger.info(f"Simulated market generated {len(agent_stats)} agent performance profiles")

        # Generate strategies based on agent behavior patterns
        for i in range(num_strategies):
            # Create variation of template
            strategy = self._mutate_strategy(param_template)

            # Backtest on simulated prices
            try:
                metrics = self.backtester.backtest_strategy(simulated_prices, strategy)

                # Check if meets criteria
                if metrics.get("composite_score", 0) > 60:
                    strategy["metrics"] = metrics
                    strategy["simulation_validated"] = True
                    strategies.append(strategy)

            except Exception as e:
                logger.debug(f"Strategy {i} failed simulation: {e}")

        logger.info(f"Generated {len(strategies)} agent-validated strategies")
        return strategies

    def optimize_with_swarm(self, strategy_template: Dict,
                           pair: str = "BTC/USDT",
                           optimization_type: str = "hybrid") -> Dict:
        """
        Optimize strategy parameters using swarm intelligence.

        Args:
            strategy_template: Template strategy
            pair: Trading pair
            optimization_type: "pso", "aco", or "hybrid"

        Returns:
            Optimized strategy
        """
        logger.info(f"Optimizing strategy with {optimization_type} swarm optimizer")

        # Define parameter bounds
        param_bounds = {
            "sma_fast": (5, 50),
            "sma_slow": (10, 100),
            "rsi_period": (10, 30),
            "risk_percentage": (0.5, 5),
            "profit_target": (0.01, 0.10),
        }

        # Load data for fitness evaluation
        candles = self.loader.load_candles(pair, "1h", 100)
        if candles.empty:
            logger.error(f"No data for {pair}")
            return strategy_template

        prices = candles["close"].values

        # Define fitness function
        def fitness_func(params: Dict) -> float:
            try:
                metrics = self.backtester.backtest_strategy(prices, params)
                return metrics.get("composite_score", 0)
            except:
                return 0

        # Select optimizer
        if optimization_type == "pso":
            optimizer = ParticleSwarmOptimizer(param_bounds, population_size=30)
            result = optimizer.optimize(fitness_func)
        elif optimization_type == "aco":
            from src.optimization.swarm_optimizer import AntColonyOptimizer
            optimizer = AntColonyOptimizer(param_bounds, num_ants=50)
            result = optimizer.optimize(fitness_func)
        else:  # hybrid
            optimizer = HybridSwarmOptimizer(param_bounds)
            result = optimizer.optimize(fitness_func, iterations=50)

        optimized_strategy = result["best_params"]
        optimized_strategy["fitness"] = result["best_fitness"]
        optimized_strategy["optimization_method"] = optimization_type

        logger.info(f"Optimization complete. Best fitness: {result['best_fitness']:.4f}")

        return optimized_strategy

    def stress_test_strategy(self, strategy: Dict,
                            pair: str = "BTC/USDT") -> Dict:
        """
        Stress test strategy across multiple market scenarios.

        Args:
            strategy: Strategy to test
            pair: Trading pair

        Returns:
            Stress test results
        """
        logger.info("Starting scenario-based stress testing")

        # Load data
        candles = self.loader.load_candles(pair, "1h", 100)
        if candles.empty:
            logger.error(f"No data for {pair}")
            return {"error": "No data"}

        prices = candles["close"].values

        # Backtest function
        def backtest_func(scenario_prices, strategy_params):
            try:
                return self.backtester.backtest_strategy(scenario_prices, strategy_params)
            except:
                return {}

        # Run stress tests
        stress_results = self.stress_tester.stress_test_strategy(strategy, backtest_func)

        # Get robustness assessment
        worst_scenario, worst_metrics = self.stress_tester.get_worst_case_scenario(stress_results)
        best_scenario, best_metrics = self.stress_tester.get_best_case_scenario(stress_results)

        stress_results["worst_scenario"] = worst_scenario
        stress_results["best_scenario"] = best_scenario

        return stress_results

    def predict_regime_and_adapt(self, current_regime: str,
                                pair: str = "BTC/USDT") -> Dict:
        """
        Predict market regime transitions and adapt strategy.

        Args:
            current_regime: Current market regime
            pair: Trading pair

        Returns:
            Adapted strategy recommendations
        """
        logger.info(f"Predicting regime transitions from {current_regime}")

        # Load data
        candles = self.loader.load_candles(pair, "1h", 100)
        if candles.empty:
            logger.error(f"No data for {pair}")
            return {"error": "No data"}

        # Get forecast
        forecast = self.regime_predictor.get_regime_forecast(
            current_regime,
            {
                "close": candles["close"].values,
                "high": candles["high"].values,
                "low": candles["low"].values,
                "volume": candles["volume"].values
            },
            periods=5
        )

        logger.info(f"Regime forecast: {[f['next_regime_probs'] for f in forecast]}")

        return {
            "current_regime": current_regime,
            "forecast": forecast,
            "recommendation": self._get_regime_recommendation(forecast)
        }

    def run_mirofish_analysis(self, strategy: Dict,
                             market_data: Dict) -> Dict:
        """
        Run comprehensive MiroFish analysis on strategy.

        Args:
            strategy: Strategy to analyze
            market_data: Current market data

        Returns:
            MiroFish analysis results
        """
        logger.info("Running MiroFish multi-agent analysis")

        # Scenario analysis
        scenario_result = self.mirofish.analyze_strategy_scenario(
            strategy,
            market_scenario="bull_market"
        )

        # Market prediction
        market_prediction = self.mirofish.analyze_market_prediction(
            market_data,
            prediction_horizon="1_month"
        )

        return {
            "scenario_analysis": scenario_result,
            "market_prediction": market_prediction,
            "combined_analysis": self._combine_analyses(scenario_result, market_prediction)
        }

    def _mutate_strategy(self, template: Dict) -> Dict:
        """Mutate template strategy with random perturbations."""
        mutated = template.copy()

        for key, value in mutated.items():
            if isinstance(value, (int, float)) and key not in ["generation_id"]:
                # Mutate with ±10% variance
                variance = np.random.uniform(-0.1, 0.1)
                mutated[key] = max(1, value * (1 + variance))

        return mutated

    def _get_regime_recommendation(self, forecast: List[Dict]) -> str:
        """Get strategy recommendation based on regime forecast."""
        if not forecast:
            return "Hold current strategy"

        # Look at next regime probability
        next_probs = forecast[0].get("next_regime_probs", {})

        if not next_probs:
            return "Hold current strategy"

        most_likely = max(next_probs.items(), key=lambda x: x[1])

        if most_likely[0] in ["strong_uptrend", "weak_uptrend"]:
            return "✅ Trend-following strategies recommended"
        elif most_likely[0] in ["strong_downtrend", "weak_downtrend"]:
            return "⚠️ Consider short strategies or reduce exposure"
        elif most_likely[0] == "sideways":
            return "📊 Mean-reversion strategies recommended"
        elif most_likely[0] == "volatile":
            return "🔄 Options/hedging strategies recommended"
        else:
            return "Hold current strategy"

    def _combine_analyses(self, scenario_result: Dict,
                         market_prediction: Dict) -> Dict:
        """Combine different analyses for holistic recommendation."""
        return {
            "scenario_confidence": scenario_result.get("analysis", {}).get("robustness_score", 0),
            "market_prediction_confidence": market_prediction.get("prediction_report", {}).get("confidence", 0),
            "combined_signal": "Proceed with caution" if all([
                scenario_result.get("analysis", {}).get("robustness_score", 0) > 60,
                market_prediction.get("prediction_report", {}).get("confidence", 0) > 0.7
            ]) else "Analyze further"
        }
