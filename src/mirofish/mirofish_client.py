"""MiroFish API client - integration with MiroFish multi-agent simulation platform."""
import logging
import json
import os
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)


class MiroFishClient:
    """Client for MiroFish multi-agent simulation API."""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize MiroFish client.

        Args:
            api_key: MiroFish API key (or from env MIROFISH_API_KEY)
            api_url: MiroFish API URL (or from env MIROFISH_API_URL)
        """
        self.api_key = api_key or os.getenv("MIROFISH_API_KEY")
        self.api_url = api_url or os.getenv("MIROFISH_API_URL", "https://api.mirofish.io")
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

        logger.info(f"MiroFish client initialized at {self.api_url}")

    def create_simulation(self, seed_data: Dict[str, Any], prediction_query: str,
                        num_agents: int = 1000, simulation_steps: int = 100) -> Dict:
        """
        Create a new simulation environment.

        Args:
            seed_data: Initial data (reports, documents, narratives)
            prediction_query: Natural language prediction request
            num_agents: Number of agents to simulate
            simulation_steps: Number of simulation steps

        Returns:
            Simulation ID and metadata
        """
        payload = {
            "seed_data": seed_data,
            "prediction_query": prediction_query,
            "num_agents": num_agents,
            "simulation_steps": simulation_steps,
            "config": {
                "enable_memory": True,
                "enable_personality": True,
                "enable_dynamics": True
            }
        }

        try:
            response = self.session.post(
                f"{self.api_url}/v1/simulations",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Created simulation: {result.get('simulation_id')}")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating simulation: {e}")
            return {"error": str(e)}

    def run_simulation(self, simulation_id: str) -> Dict:
        """
        Run a simulation.

        Args:
            simulation_id: ID of simulation to run

        Returns:
            Simulation results
        """
        try:
            response = self.session.post(
                f"{self.api_url}/v1/simulations/{simulation_id}/run",
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Simulation {simulation_id} completed")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error running simulation: {e}")
            return {"error": str(e)}

    def get_simulation_results(self, simulation_id: str) -> Dict:
        """Get results from completed simulation."""
        try:
            response = self.session.get(
                f"{self.api_url}/v1/simulations/{simulation_id}/results",
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching results: {e}")
            return {"error": str(e)}

    def inject_scenario_variable(self, simulation_id: str, variable_name: str,
                                value: Any) -> Dict:
        """
        Inject a variable into running simulation for scenario testing.

        Args:
            simulation_id: Simulation ID
            variable_name: Variable name
            value: Variable value

        Returns:
            Response
        """
        payload = {
            "variable_name": variable_name,
            "value": value
        }

        try:
            response = self.session.post(
                f"{self.api_url}/v1/simulations/{simulation_id}/inject",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            logger.info(f"Injected {variable_name}={value} into simulation")

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error injecting variable: {e}")
            return {"error": str(e)}

    def query_agent(self, simulation_id: str, agent_id: str,
                   query: str) -> Dict:
        """
        Query an agent's thoughts/predictions.

        Args:
            simulation_id: Simulation ID
            agent_id: Agent ID
            query: Question for agent

        Returns:
            Agent response
        """
        payload = {"query": query}

        try:
            response = self.session.post(
                f"{self.api_url}/v1/simulations/{simulation_id}/agents/{agent_id}/query",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying agent: {e}")
            return {"error": str(e)}

    def generate_prediction_report(self, simulation_id: str,
                                  report_type: str = "comprehensive") -> Dict:
        """
        Generate prediction report from simulation.

        Args:
            simulation_id: Simulation ID
            report_type: Type of report (comprehensive, executive, detailed)

        Returns:
            Report content
        """
        payload = {"report_type": report_type}

        try:
            response = self.session.post(
                f"{self.api_url}/v1/simulations/{simulation_id}/report",
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            report = response.json()
            logger.info(f"Generated {report_type} report for simulation")

            return report

        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}

    def analyze_market_prediction(self, market_data: Dict,
                                 prediction_horizon: str = "1_month") -> Dict:
        """
        Use MiroFish to predict market movements.

        Args:
            market_data: Current market data (price, volume, indicators)
            prediction_horizon: Prediction horizon (1_week, 1_month, 3_month)

        Returns:
            Market prediction
        """
        seed_data = {
            "current_market_state": market_data,
            "historical_patterns": "Market tends to mean revert after extremes",
            "agent_behaviors": [
                "Trend followers buy on uptrends",
                "Mean reversion traders buy on dips",
                "Momentum traders follow recent movements"
            ]
        }

        prediction_query = f"What will the market do in the next {prediction_horizon}? " \
                          f"Consider current price of {market_data.get('current_price', 'unknown')}, " \
                          f"volatility of {market_data.get('volatility', 'unknown')}, " \
                          f"and current trend of {market_data.get('trend', 'unknown')}."

        logger.info("Starting market prediction simulation with MiroFish")

        # Create simulation
        sim_result = self.create_simulation(seed_data, prediction_query, num_agents=500)

        if "error" in sim_result:
            logger.error(f"Simulation creation failed: {sim_result['error']}")
            return sim_result

        simulation_id = sim_result.get("simulation_id")

        # Run simulation
        run_result = self.run_simulation(simulation_id)

        if "error" in run_result:
            logger.error(f"Simulation run failed: {run_result['error']}")
            return run_result

        # Get results
        results = self.get_simulation_results(simulation_id)

        # Generate report
        if "error" not in results:
            report = self.generate_prediction_report(simulation_id)
            results["prediction_report"] = report

        return results

    def analyze_strategy_scenario(self, strategy_params: Dict,
                                 market_scenario: str = "bull_market") -> Dict:
        """
        Analyze how strategy performs under simulated agent-based scenarios.

        Args:
            strategy_params: Strategy parameters to analyze
            market_scenario: Market scenario name

        Returns:
            Analysis results
        """
        seed_data = {
            "strategy_parameters": strategy_params,
            "market_scenario": market_scenario,
            "agent_types": [
                "trend_followers",
                "mean_reversion_traders",
                "momentum_chasers",
                "market_makers"
            ]
        }

        prediction_query = f"How will this strategy perform in a {market_scenario}? " \
                          f"Strategy: {json.dumps(strategy_params)}"

        logger.info(f"Analyzing strategy in {market_scenario} scenario")

        sim_result = self.create_simulation(seed_data, prediction_query, num_agents=1000)

        if "error" in sim_result:
            return sim_result

        simulation_id = sim_result.get("simulation_id")

        # Run simulation
        run_result = self.run_simulation(simulation_id)

        if "error" in run_result:
            return run_result

        # Get results
        results = self.get_simulation_results(simulation_id)

        return {
            "simulation_id": simulation_id,
            "strategy_params": strategy_params,
            "scenario": market_scenario,
            "analysis": results
        }


class LocalMiroFishSimulator:
    """Local fallback simulator when MiroFish API unavailable."""

    def __init__(self):
        """Initialize local simulator."""
        from src.simulation.agent_market_simulator import AgentMarketSimulator
        self.simulator = AgentMarketSimulator(num_agents=100)

    def simulate_market(self, scenario: str = "neutral") -> Dict:
        """Run local agent-based simulation."""
        from src.backtesting.data_loader import get_data_loader

        loader = get_data_loader()
        base_prices = loader.load_candles("BTC/USDT", "1h", 30)

        if base_prices.empty:
            logger.warning("No price data for simulation")
            return {"error": "No price data"}

        prices = base_prices["close"].values

        result = self.simulator.simulate(prices, num_steps=100)

        return {
            "scenario": scenario,
            "simulated_prices": result["simulated_prices"].tolist(),
            "market_stats": result["market_stats"],
            "agent_returns": result["agent_returns"]
        }

    def analyze_strategy(self, strategy_params: Dict,
                        scenario: str = "neutral") -> Dict:
        """Analyze strategy performance in simulated market."""
        result = self.simulate_market(scenario)

        if "error" in result:
            return result

        # Would backtest strategy against simulated prices
        return {
            "strategy_params": strategy_params,
            "scenario": scenario,
            "simulated_market": result
        }


def get_mirofish_client() -> MiroFishClient:
    """Get MiroFish client (or local simulator if API unavailable)."""
    api_key = os.getenv("MIROFISH_API_KEY")

    if api_key:
        return MiroFishClient()
    else:
        logger.warning("MiroFish API key not configured, using local simulator")
        return LocalMiroFishSimulator()
