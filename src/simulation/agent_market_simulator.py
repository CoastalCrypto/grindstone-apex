"""Agent-based market simulator - simulates realistic market microstructure with autonomous agents."""
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of market agents."""
    TREND_FOLLOWER = "trend_follower"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM_CHASER = "momentum_chaser"
    ARBITRAGEUR = "arbitrageur"
    NOISE_TRADER = "noise_trader"
    INSTITUTIONAL = "institutional"
    MARKET_MAKER = "market_maker"


@dataclass
class Agent:
    """Represents a trading agent in the market."""
    agent_id: str
    agent_type: AgentType
    capital: float
    position: float = 0  # Current position size
    entry_price: float = 0
    profits: float = 0
    trades_count: int = 0
    win_count: int = 0

    def __post_init__(self):
        """Initialize agent memory."""
        self.memory = {
            "recent_prices": [],
            "recent_returns": [],
            "recent_volumes": [],
            "winning_trades": [],
            "losing_trades": [],
            "sentiment": 0  # -1 to 1
        }


class AgentMarketSimulator:
    """Simulates market with autonomous trading agents."""

    def __init__(self, num_agents: int = 100, agent_distribution: Optional[Dict] = None):
        """
        Initialize simulator.

        Args:
            num_agents: Number of agents to simulate
            agent_distribution: Optional dict specifying agent type distribution
        """
        self.num_agents = num_agents
        self.agents = self._create_agents(num_agents, agent_distribution)
        self.market_price = 100  # Starting price
        self.market_history = []
        self.order_book = {"bids": [], "asks": []}

    def _create_agents(self, num_agents: int,
                      distribution: Optional[Dict]) -> List[Agent]:
        """Create agents with specified distribution."""
        if distribution is None:
            distribution = {
                AgentType.TREND_FOLLOWER: 0.25,
                AgentType.MEAN_REVERSION: 0.20,
                AgentType.MOMENTUM_CHASER: 0.15,
                AgentType.ARBITRAGEUR: 0.15,
                AgentType.MARKET_MAKER: 0.10,
                AgentType.NOISE_TRADER: 0.15,
            }

        agents = []
        agent_id = 0

        for agent_type, proportion in distribution.items():
            count = int(num_agents * proportion)
            for _ in range(count):
                agent = Agent(
                    agent_id=f"agent_{agent_id}",
                    agent_type=agent_type,
                    capital=10000 * (np.random.uniform(0.5, 2.0))
                )
                agents.append(agent)
                agent_id += 1

        return agents

    def simulate(self, base_prices: np.ndarray, num_steps: int = 100) -> Dict:
        """
        Simulate market with agents trading.

        Args:
            base_prices: Base price sequence to perturb
            num_steps: Number of steps to simulate

        Returns:
            Simulation results with agent trades and market stats
        """
        logger.info(f"Starting simulation with {len(self.agents)} agents for {num_steps} steps")

        simulated_prices = []
        simulated_volumes = []
        trades_log = []
        agent_returns = {}

        # Initialize agent memory with base prices
        for agent in self.agents:
            agent.memory["recent_prices"] = base_prices[-20:].tolist()
            agent.memory["recent_returns"] = np.diff(base_prices[-20:]) / base_prices[-21:-1]
            agent.memory["sentiment"] = np.random.uniform(-0.5, 0.5)

        current_price = base_prices[-1]
        volume = 0

        for step in range(num_steps):
            # Each agent generates orders
            orders = []
            for agent in self.agents:
                order = self._generate_agent_order(agent, current_price, step)
                if order:
                    orders.append(order)

            # Match orders and execute trades
            if orders:
                executed_trades, avg_price, execution_volume = self._match_orders(orders)
                trades_log.extend(executed_trades)

                # Update agent positions and P&L
                for trade in executed_trades:
                    agent_idx = int(trade["agent_id"].split("_")[1])
                    if agent_idx < len(self.agents):
                        agent = self.agents[agent_idx]
                        self._update_agent_position(agent, trade)

                # Apply market impact
                price_change = self._calculate_price_change(
                    executed_trades, current_price
                )
                current_price = max(1, current_price + price_change)
                volume = execution_volume

            # Add noise/drift
            noise = np.random.normal(0, current_price * 0.001)
            current_price = max(1, current_price + noise)

            # Update agent memory
            for agent in self.agents:
                agent.memory["recent_prices"].append(current_price)
                agent.memory["recent_prices"] = agent.memory["recent_prices"][-50:]

            simulated_prices.append(current_price)
            simulated_volumes.append(volume)

        # Collect results
        for agent in self.agents:
            agent_returns[agent.agent_id] = {
                "initial_capital": 10000,
                "final_capital": agent.capital + agent.profits,
                "total_return": (agent.profits / (10000 * 0.9)) if 10000 > 0 else 0,
                "trades": agent.trades_count,
                "win_rate": agent.win_count / agent.trades_count if agent.trades_count > 0 else 0,
                "total_pnl": agent.profits
            }

        return {
            "simulated_prices": np.array(simulated_prices),
            "simulated_volumes": np.array(simulated_volumes),
            "trades": trades_log,
            "agent_returns": agent_returns,
            "market_stats": self._calculate_market_stats(
                np.array(simulated_prices),
                np.array(simulated_volumes)
            )
        }

    def _generate_agent_order(self, agent: Agent, current_price: float,
                             step: int) -> Optional[Dict]:
        """
        Generate trading order based on agent type and strategy.

        Args:
            agent: Agent instance
            current_price: Current market price
            step: Current time step

        Returns:
            Order dict or None
        """
        try:
            if agent.agent_type == AgentType.TREND_FOLLOWER:
                return self._trend_follower_order(agent, current_price)
            elif agent.agent_type == AgentType.MEAN_REVERSION:
                return self._mean_reversion_order(agent, current_price)
            elif agent.agent_type == AgentType.MOMENTUM_CHASER:
                return self._momentum_order(agent, current_price)
            elif agent.agent_type == AgentType.ARBITRAGEUR:
                return self._arbitrage_order(agent, current_price)
            elif agent.agent_type == AgentType.MARKET_MAKER:
                return self._market_maker_order(agent, current_price)
            elif agent.agent_type == AgentType.NOISE_TRADER:
                return self._noise_trader_order(agent, current_price)

        except Exception as e:
            logger.error(f"Error generating order for {agent.agent_id}: {e}")

        return None

    def _trend_follower_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Trend follower buys on uptrends, sells on downtrends."""
        if len(agent.memory["recent_prices"]) < 5:
            return None

        recent_prices = agent.memory["recent_prices"][-5:]
        trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

        if trend > 0.01:  # Uptrend
            size = agent.capital * 0.05 / current_price
            return {
                "agent_id": agent.agent_id,
                "side": "buy",
                "price": current_price * 1.001,  # Buy at slight premium
                "size": size,
                "type": "limit"
            }
        elif trend < -0.01:  # Downtrend
            if agent.position > 0:
                return {
                    "agent_id": agent.agent_id,
                    "side": "sell",
                    "price": current_price * 0.999,
                    "size": agent.position,
                    "type": "limit"
                }

        return None

    def _mean_reversion_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Mean reversion buys low, sells high."""
        if len(agent.memory["recent_prices"]) < 20:
            return None

        mean_price = np.mean(agent.memory["recent_prices"][-20:])
        std_dev = np.std(agent.memory["recent_prices"][-20:])

        if current_price < mean_price - std_dev:  # Price too low
            size = agent.capital * 0.05 / current_price
            return {
                "agent_id": agent.agent_id,
                "side": "buy",
                "price": current_price,
                "size": size,
                "type": "market"
            }
        elif current_price > mean_price + std_dev and agent.position > 0:  # Price too high
            return {
                "agent_id": agent.agent_id,
                "side": "sell",
                "price": current_price,
                "size": agent.position,
                "type": "market"
            }

        return None

    def _momentum_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Momentum chaser follows recent price movements."""
        if len(agent.memory["recent_prices"]) < 3:
            return None

        recent_return = (agent.memory["recent_prices"][-1] -
                        agent.memory["recent_prices"][-3]) / agent.memory["recent_prices"][-3]

        if recent_return > 0.005:  # Recent uptick
            size = agent.capital * 0.04 / current_price
            return {
                "agent_id": agent.agent_id,
                "side": "buy",
                "price": current_price * 1.002,
                "size": size,
                "type": "limit"
            }

        return None

    def _arbitrage_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Arbitrageur looks for mispricing."""
        # Simplified: random small trades
        if np.random.random() > 0.7:
            side = "buy" if np.random.random() > 0.5 else "sell"
            return {
                "agent_id": agent.agent_id,
                "side": side,
                "price": current_price,
                "size": agent.capital * 0.02 / current_price,
                "type": "market"
            }

        return None

    def _market_maker_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Market maker provides liquidity."""
        # Market makers place both bids and asks (simplified as one order)
        return {
            "agent_id": agent.agent_id,
            "side": "buy",
            "price": current_price * 0.999,
            "size": agent.capital * 0.03 / current_price,
            "type": "limit"
        }

    def _noise_trader_order(self, agent: Agent, current_price: float) -> Optional[Dict]:
        """Noise trader makes random trades."""
        if np.random.random() > 0.8:
            side = "buy" if np.random.random() > 0.5 else "sell"
            return {
                "agent_id": agent.agent_id,
                "side": side,
                "price": current_price,
                "size": agent.capital * 0.03 / current_price,
                "type": "market"
            }

        return None

    def _match_orders(self, orders: List[Dict]) -> Tuple[List[Dict], float, float]:
        """
        Match buy and sell orders.

        Returns:
            Tuple of (executed_trades, average_price, volume)
        """
        buy_orders = [o for o in orders if o["side"] == "buy"]
        sell_orders = [o for o in orders if o["side"] == "sell"]

        executed_trades = []
        total_volume = 0
        total_value = 0

        # Simple matching: match available buy/sell pairs
        for buy_order in buy_orders:
            for sell_order in sell_orders:
                # Match quantity (simplified)
                match_size = min(buy_order.get("size", 1), sell_order.get("size", 1))

                if match_size > 0:
                    exec_price = (buy_order["price"] + sell_order["price"]) / 2

                    executed_trades.append({
                        "agent_id": buy_order["agent_id"],
                        "side": "buy",
                        "price": exec_price,
                        "size": match_size,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    executed_trades.append({
                        "agent_id": sell_order["agent_id"],
                        "side": "sell",
                        "price": exec_price,
                        "size": match_size,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    total_volume += match_size
                    total_value += exec_price * match_size

        avg_price = total_value / total_volume if total_volume > 0 else 0

        return executed_trades, avg_price, total_volume

    def _update_agent_position(self, agent: Agent, trade: Dict) -> None:
        """Update agent's position after trade execution."""
        price = trade["price"]
        size = trade["size"]

        if trade["side"] == "buy":
            agent.position += size
            agent.entry_price = (agent.entry_price * (agent.position - size) + price * size) / agent.position if agent.position > 0 else price

        elif trade["side"] == "sell":
            if agent.position > 0:
                pnl = (price - agent.entry_price) * min(size, agent.position)
                agent.profits += pnl

                if pnl > 0:
                    agent.win_count += 1

                agent.position = max(0, agent.position - size)

        agent.trades_count += 1

    def _calculate_price_change(self, trades: List[Dict], current_price: float) -> float:
        """Calculate price change from order flow."""
        if not trades:
            return 0

        buy_volume = sum(t["size"] for t in trades if t["side"] == "buy")
        sell_volume = sum(t["size"] for t in trades if t["side"] == "sell")

        net_flow = buy_volume - sell_volume
        price_impact = net_flow * 0.0001 * current_price

        return price_impact

    def _calculate_market_stats(self, prices: np.ndarray,
                               volumes: np.ndarray) -> Dict:
        """Calculate overall market statistics."""
        returns = np.diff(prices) / prices[:-1]

        return {
            "mean_price": float(np.mean(prices)),
            "price_volatility": float(np.std(returns) * 100),
            "total_volume": float(np.sum(volumes)),
            "avg_volume": float(np.mean(volumes)),
            "price_range": float(np.max(prices) - np.min(prices)),
            "sharpe_ratio": float(np.mean(returns) / np.std(returns)) if np.std(returns) > 0 else 0,
            "returns": returns.tolist()
        }
