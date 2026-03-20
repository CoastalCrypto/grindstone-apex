"""Scenario stress testing - test strategies under various market conditions."""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MarketScenario(Enum):
    """Types of market scenarios."""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    FLASH_CRASH = "flash_crash"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    TREND_REVERSAL = "trend_reversal"
    MOMENTUM_SQUEEZE = "momentum_squeeze"


class ScenarioGenerator:
    """Generates synthetic market scenarios."""

    @staticmethod
    def generate_bull_market(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate bull market scenario."""
        returns = np.random.normal(0.001, 0.005, num_candles)  # Positive drift
        prices = base_price * np.cumprod(1 + returns)
        return prices

    @staticmethod
    def generate_bear_market(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate bear market scenario."""
        returns = np.random.normal(-0.001, 0.005, num_candles)  # Negative drift
        prices = base_price * np.cumprod(1 + returns)
        return prices

    @staticmethod
    def generate_sideways_market(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate sideways/range-bound market."""
        prices = base_price + np.cumsum(np.random.normal(0, 1, num_candles))
        # Keep prices in range
        prices = np.clip(prices, base_price * 0.95, base_price * 1.05)
        return prices

    @staticmethod
    def generate_high_volatility(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate high volatility scenario."""
        returns = np.random.normal(0, 0.02, num_candles)  # High std dev
        prices = base_price * np.cumprod(1 + returns)
        return prices

    @staticmethod
    def generate_flash_crash(num_candles: int = 100, base_price: float = 100,
                            crash_position: int = 50, crash_magnitude: float = -0.20) -> np.ndarray:
        """Generate flash crash scenario."""
        prices = np.linspace(base_price, base_price * 1.10, crash_position)

        # Crash
        crash_end = crash_position + 5
        crash_prices = base_price * (1 + crash_magnitude * np.linspace(0, 1, crash_end - crash_position))
        prices = np.concatenate([prices, crash_prices])

        # Recovery
        if len(prices) < num_candles:
            recovery = np.linspace(
                crash_prices[-1],
                base_price * 1.05,
                num_candles - len(prices)
            )
            prices = np.concatenate([prices, recovery])

        return prices[:num_candles]

    @staticmethod
    def generate_liquidity_crisis(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate liquidity crisis - wide bid-ask spread, price gaps."""
        prices = []
        current_price = base_price

        for i in range(num_candles):
            # Large random jumps (gaps) simulating liquidity crisis
            if np.random.random() > 0.8:
                jump = np.random.normal(0, current_price * 0.05)
            else:
                jump = np.random.normal(0, current_price * 0.002)

            current_price = max(1, current_price + jump)
            prices.append(current_price)

        return np.array(prices)

    @staticmethod
    def generate_trend_reversal(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate trend reversal scenario."""
        # First half uptrend
        first_half = np.random.normal(0.001, 0.003, num_candles // 2)
        uptrend = base_price * np.cumprod(1 + first_half)

        # Second half downtrend
        second_half = np.random.normal(-0.001, 0.003, num_candles - num_candles // 2)
        downtrend = uptrend[-1] * np.cumprod(1 + second_half)

        return np.concatenate([uptrend, downtrend])

    @staticmethod
    def generate_momentum_squeeze(num_candles: int = 100, base_price: float = 100) -> np.ndarray:
        """Generate momentum squeeze - low volatility then breakout."""
        # Low volatility phase
        squeeze_length = num_candles // 2
        squeeze = base_price + np.cumsum(np.random.normal(0, 0.1, squeeze_length))
        squeeze = np.clip(squeeze, base_price * 0.98, base_price * 1.02)

        # Breakout phase
        breakout_length = num_candles - squeeze_length
        breakout = squeeze[-1] * np.cumprod(1 + np.random.normal(0.002, 0.01, breakout_length))

        return np.concatenate([squeeze, breakout])


class ScenarioStressTester:
    """Tests strategies under multiple market scenarios."""

    def __init__(self):
        """Initialize stress tester."""
        self.generator = ScenarioGenerator()
        self.scenarios = {
            MarketScenario.BULL_MARKET: self.generator.generate_bull_market,
            MarketScenario.BEAR_MARKET: self.generator.generate_bear_market,
            MarketScenario.SIDEWAYS_MARKET: self.generator.generate_sideways_market,
            MarketScenario.HIGH_VOLATILITY: self.generator.generate_high_volatility,
            MarketScenario.FLASH_CRASH: self.generator.generate_flash_crash,
            MarketScenario.LIQUIDITY_CRISIS: self.generator.generate_liquidity_crisis,
            MarketScenario.TREND_REVERSAL: self.generator.generate_trend_reversal,
            MarketScenario.MOMENTUM_SQUEEZE: self.generator.generate_momentum_squeeze,
        }

    def stress_test_strategy(self, strategy_params: Dict, backtest_func) -> Dict:
        """
        Stress test strategy across all scenarios.

        Args:
            strategy_params: Strategy parameters
            backtest_func: Backtesting function that takes (prices, params) and returns metrics

        Returns:
            Stress test results
        """
        logger.info(f"Stress testing strategy across {len(self.scenarios)} scenarios")

        results = {
            "strategy_params": strategy_params,
            "scenario_results": {},
            "summary": {}
        }

        scenario_metrics = []

        for scenario_name, generator_func in self.scenarios.items():
            logger.info(f"Testing scenario: {scenario_name.value}")

            # Generate scenario
            prices = generator_func(num_candles=252)  # 1 year

            # Backtest
            try:
                metrics = backtest_func(prices, strategy_params)

                results["scenario_results"][scenario_name.value] = {
                    "prices": prices.tolist(),
                    "metrics": metrics
                }

                scenario_metrics.append(metrics)

            except Exception as e:
                logger.error(f"Error in scenario {scenario_name.value}: {e}")
                results["scenario_results"][scenario_name.value] = {"error": str(e)}

        # Calculate summary statistics
        if scenario_metrics:
            results["summary"] = self._calculate_summary(scenario_metrics)

        return results

    def _calculate_summary(self, metrics_list: List[Dict]) -> Dict:
        """Calculate summary statistics across scenarios."""
        win_rates = [m.get("win_rate", 0) for m in metrics_list if "win_rate" in m]
        profit_factors = [m.get("profit_factor", 1) for m in metrics_list if "profit_factor" in m]
        sharpes = [m.get("sharpe_ratio", 0) for m in metrics_list if "sharpe_ratio" in m]
        drawdowns = [m.get("max_drawdown", 0) for m in metrics_list if "max_drawdown" in m]

        return {
            "avg_win_rate": float(np.mean(win_rates)) if win_rates else 0,
            "min_win_rate": float(np.min(win_rates)) if win_rates else 0,
            "max_win_rate": float(np.max(win_rates)) if win_rates else 0,
            "win_rate_std": float(np.std(win_rates)) if win_rates else 0,

            "avg_profit_factor": float(np.mean(profit_factors)) if profit_factors else 1,
            "min_profit_factor": float(np.min(profit_factors)) if profit_factors else 1,
            "max_profit_factor": float(np.max(profit_factors)) if profit_factors else 1,

            "avg_sharpe": float(np.mean(sharpes)) if sharpes else 0,
            "min_sharpe": float(np.min(sharpes)) if sharpes else 0,

            "worst_drawdown": float(np.min(drawdowns)) if drawdowns else 0,
            "avg_drawdown": float(np.mean(drawdowns)) if drawdowns else 0,

            "robustness_score": self._calculate_robustness_score(win_rates, profit_factors, sharpes)
        }

    def _calculate_robustness_score(self, win_rates: List[float],
                                    profit_factors: List[float],
                                    sharpes: List[float]) -> float:
        """
        Calculate robustness score (0-100).

        Measures consistency across scenarios.
        """
        if not win_rates or not profit_factors:
            return 0

        # Penalize inconsistency
        wr_consistency = 1 - (np.std(win_rates) / (np.mean(win_rates) + 0.01))
        pf_consistency = 1 - (np.std(profit_factors) / (np.mean(profit_factors) + 0.01))

        # Win rate contribution
        avg_wr = np.mean(win_rates)
        wr_score = max(0, min(1, avg_wr)) * 50

        # Profit factor contribution
        avg_pf = np.mean(profit_factors)
        pf_score = max(0, min(1, (avg_pf - 1) / 2)) * 30

        # Consistency contribution
        consistency_score = max(0, min(1, (wr_consistency + pf_consistency) / 2)) * 20

        return float(wr_score + pf_score + consistency_score)

    def get_worst_case_scenario(self, results: Dict) -> Tuple[str, Dict]:
        """Get the worst performing scenario."""
        worst_scenario = None
        worst_metrics = None
        worst_win_rate = 1.0

        for scenario_name, result in results["scenario_results"].items():
            if "metrics" in result:
                wr = result["metrics"].get("win_rate", 1.0)
                if wr < worst_win_rate:
                    worst_win_rate = wr
                    worst_scenario = scenario_name
                    worst_metrics = result["metrics"]

        return worst_scenario or "unknown", worst_metrics or {}

    def get_best_case_scenario(self, results: Dict) -> Tuple[str, Dict]:
        """Get the best performing scenario."""
        best_scenario = None
        best_metrics = None
        best_win_rate = 0.0

        for scenario_name, result in results["scenario_results"].items():
            if "metrics" in result:
                wr = result["metrics"].get("win_rate", 0.0)
                if wr > best_win_rate:
                    best_win_rate = wr
                    best_scenario = scenario_name
                    best_metrics = result["metrics"]

        return best_scenario or "unknown", best_metrics or {}
