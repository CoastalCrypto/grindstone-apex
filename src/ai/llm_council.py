"""LLM Council voting system - multiple AI perspectives for strategy validation."""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Vote types."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class Council:
    """Represents a council of expert AIs voting on strategies."""

    def __init__(self):
        """Initialize council."""
        self.members = {
            "risk_analyst": RiskAnalystVoter(),
            "momentum_expert": MomentumExpertVoter(),
            "value_analyzer": ValueAnalyzerVoter(),
            "correlation_expert": CorrelationExpertVoter(),
        }

    def vote_on_strategy(self, strategy: Dict, market_context: Dict) -> Dict:
        """
        Get council votes on a strategy.

        Args:
            strategy: Strategy dict with parameters and backtest metrics
            market_context: Current market regime and conditions

        Returns:
            Vote summary and recommendations
        """
        logger.info(f"Council voting on strategy {strategy.get('id', 'unknown')}")

        votes = {}
        reasoning = {}

        # Get individual votes
        for member_name, member in self.members.items():
            try:
                vote, reason = member.vote(strategy, market_context)
                votes[member_name] = vote.value
                reasoning[member_name] = reason

            except Exception as e:
                logger.error(f"Error getting vote from {member_name}: {e}")
                votes[member_name] = VoteType.NEUTRAL.value
                reasoning[member_name] = str(e)

        # Calculate consensus
        consensus = self._calculate_consensus(votes)

        return {
            "strategy_id": strategy.get("id"),
            "votes": votes,
            "consensus": consensus["vote"],
            "confidence": consensus["confidence"],
            "recommendation": self._get_recommendation(consensus),
            "reasoning": reasoning,
            "council_analysis": self._generate_analysis(votes, reasoning, strategy)
        }

    def _calculate_consensus(self, votes: Dict[str, str]) -> Dict:
        """Calculate consensus from votes."""
        vote_mapping = {
            VoteType.STRONG_BUY.value: 2,
            VoteType.BUY.value: 1,
            VoteType.NEUTRAL.value: 0,
            VoteType.SELL.value: -1,
            VoteType.STRONG_SELL.value: -2,
        }

        scores = [vote_mapping.get(v, 0) for v in votes.values()]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Determine consensus
        if avg_score > 1:
            consensus_vote = VoteType.STRONG_BUY.value
        elif avg_score > 0.3:
            consensus_vote = VoteType.BUY.value
        elif avg_score < -1:
            consensus_vote = VoteType.STRONG_SELL.value
        elif avg_score < -0.3:
            consensus_vote = VoteType.SELL.value
        else:
            consensus_vote = VoteType.NEUTRAL.value

        # Confidence is based on agreement
        max_score = max(scores)
        min_score = min(scores)
        disagreement = abs(max_score - min_score)
        confidence = 1.0 - (disagreement / 4.0)  # Normalize to 0-1

        return {
            "vote": consensus_vote,
            "avg_score": avg_score,
            "confidence": max(0, confidence)
        }

    def _get_recommendation(self, consensus: Dict) -> str:
        """Generate recommendation based on consensus."""
        vote = consensus["vote"]
        confidence = consensus["confidence"]

        if vote == VoteType.STRONG_BUY.value:
            return "✅ STRONG CONSENSUS: Deploy to live trading immediately"
        elif vote == VoteType.BUY.value:
            if confidence > 0.7:
                return "✅ CONSENSUS: Good candidate for deployment"
            else:
                return "⚠️ MIXED OPINION: Deploy with caution, monitor closely"
        elif vote == VoteType.SELL.value:
            return "❌ MIXED REJECTION: Reconsider or improve parameters"
        elif vote == VoteType.STRONG_SELL.value:
            return "🔴 STRONG CONSENSUS: Retire or redesign strategy"
        else:
            return "⏸️ NEUTRAL: Needs more data or market regime change"

    def _generate_analysis(self, votes: Dict, reasoning: Dict,
                          strategy: Dict) -> str:
        """Generate detailed council analysis."""
        analysis = f"""
COUNCIL ANALYSIS FOR STRATEGY {strategy.get('id', 'Unknown')}

Votes Cast:
"""
        for member, vote in votes.items():
            analysis += f"  - {member.upper()}: {vote}\n"
            if member in reasoning:
                analysis += f"    Reason: {reasoning[member]}\n"

        metrics = strategy.get("metrics", {})
        analysis += f"""
Strategy Metrics:
  - Win Rate: {metrics.get('win_rate', 0)*100:.1f}%
  - Profit Factor: {metrics.get('profit_factor', 0):.2f}
  - Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
  - Max Drawdown: {metrics.get('max_drawdown', 0)*100:.1f}%
"""

        return analysis


class RiskAnalystVoter:
    """Analyzes risk metrics."""

    def vote(self, strategy: Dict, market_context: Dict) -> Tuple[VoteType, str]:
        """
        Vote based on risk analysis.

        Returns:
            Tuple of (vote, reasoning)
        """
        metrics = strategy.get("metrics", {})

        max_drawdown = metrics.get("max_drawdown", 1.0)
        sharpe = metrics.get("sharpe_ratio", 0)

        reasons = []

        # Check max drawdown
        if max_drawdown > 0.40:
            reasons.append("high drawdown")
        elif max_drawdown < 0.15:
            reasons.append("acceptable drawdown")

        # Check Sharpe ratio
        if sharpe > 1.5:
            reasons.append("strong risk-adjusted returns")
        elif sharpe < 0.5:
            reasons.append("poor risk-adjusted returns")

        # Determine vote
        risk_score = -max_drawdown * 2 + sharpe * 0.5

        if risk_score > 1.5:
            vote = VoteType.STRONG_BUY
        elif risk_score > 0:
            vote = VoteType.BUY
        elif risk_score > -1:
            vote = VoteType.NEUTRAL
        elif risk_score > -2:
            vote = VoteType.SELL
        else:
            vote = VoteType.STRONG_SELL

        reasoning = f"Risk analysis: {', '.join(reasons)}. Score: {risk_score:.2f}"

        return vote, reasoning


class MomentumExpertVoter:
    """Analyzes momentum and trend potential."""

    def vote(self, strategy: Dict, market_context: Dict) -> Tuple[VoteType, str]:
        """Vote based on momentum analysis."""
        metrics = strategy.get("metrics", {})
        params = strategy.get("parameters", {})

        win_rate = metrics.get("win_rate", 0)
        profit_pct = metrics.get("profit_pct", 0)
        total_trades = metrics.get("total_trades", 0)

        reasons = []

        # Check win rate
        if win_rate > 0.60:
            reasons.append("strong win rate")
        elif win_rate < 0.35:
            reasons.append("weak win rate")

        # Check profit potential
        if profit_pct > 20:
            reasons.append("excellent profit potential")
        elif profit_pct < 5:
            reasons.append("limited profit potential")

        # Check sample size
        if total_trades < 10:
            reasons.append("limited sample size - risky")

        # Momentum score
        momentum_score = win_rate * 2 + (profit_pct / 100) - (1 if total_trades < 10 else 0)

        if momentum_score > 1:
            vote = VoteType.STRONG_BUY
        elif momentum_score > 0.5:
            vote = VoteType.BUY
        elif momentum_score > -0.5:
            vote = VoteType.NEUTRAL
        else:
            vote = VoteType.SELL

        reasoning = f"Momentum analysis: {', '.join(reasons)}. Score: {momentum_score:.2f}"

        return vote, reasoning


class ValueAnalyzerVoter:
    """Analyzes value and consistency."""

    def vote(self, strategy: Dict, market_context: Dict) -> Tuple[VoteType, str]:
        """Vote based on value analysis."""
        metrics = strategy.get("metrics", {})

        profit_factor = metrics.get("profit_factor", 1.0)
        sharpe = metrics.get("sharpe_ratio", 0)
        consistency = self._calculate_consistency(metrics)

        reasons = []

        # Check profit factor
        if profit_factor > 2.0:
            reasons.append("excellent profit factor")
        elif profit_factor > 1.5:
            reasons.append("good profit factor")
        elif profit_factor < 1.1:
            reasons.append("weak profit factor")

        # Check consistency
        if consistency > 0.8:
            reasons.append("highly consistent")
        elif consistency < 0.5:
            reasons.append("inconsistent performance")

        # Value score
        value_score = (profit_factor - 1) * 2 + consistency - sharpe * 0.3

        if value_score > 2:
            vote = VoteType.STRONG_BUY
        elif value_score > 1:
            vote = VoteType.BUY
        elif value_score > -0.5:
            vote = VoteType.NEUTRAL
        else:
            vote = VoteType.SELL

        reasoning = f"Value analysis: {', '.join(reasons)}. Score: {value_score:.2f}"

        return vote, reasoning

    def _calculate_consistency(self, metrics: Dict) -> float:
        """Calculate consistency metric."""
        win_rate = metrics.get("win_rate", 0.5)
        max_dd = metrics.get("max_drawdown", 1.0)

        # Consistency = high win rate + low drawdown
        consistency = (win_rate * 0.6) + ((1 - max_dd) * 0.4)

        return max(0, min(1, consistency))


class CorrelationExpertVoter:
    """Analyzes correlation to market regime."""

    def vote(self, strategy: Dict, market_context: Dict) -> Tuple[VoteType, str]:
        """Vote based on market regime fit."""
        regime = market_context.get("regime", "sideways")
        params = strategy.get("parameters", {})

        # Strategy parameter characteristics
        sma_fast = params.get("sma_fast", 10)
        sma_slow = params.get("sma_slow", 30)

        reasons = []

        # Regime compatibility
        regime_compatibility = self._get_regime_compatibility(regime, params)

        if regime_compatibility > 0.8:
            reasons.append(f"excellent fit for {regime} market")
            vote = VoteType.STRONG_BUY
        elif regime_compatibility > 0.6:
            reasons.append(f"good fit for {regime} market")
            vote = VoteType.BUY
        elif regime_compatibility > 0.4:
            reasons.append(f"moderate fit for {regime} market")
            vote = VoteType.NEUTRAL
        else:
            reasons.append(f"poor fit for {regime} market")
            vote = VoteType.SELL

        reasoning = f"Correlation analysis: {', '.join(reasons)}. Compatibility: {regime_compatibility:.2f}"

        return vote, reasoning

    def _get_regime_compatibility(self, regime: str, params: Dict) -> float:
        """Calculate regime compatibility score."""
        # Different regimes prefer different parameters
        compatibility_map = {
            "strong_uptrend": 0.9 if params.get("sma_fast", 10) < 20 else 0.6,
            "weak_uptrend": 0.8 if params.get("sma_slow", 30) > 40 else 0.5,
            "sideways": 0.8 if 10 < params.get("sma_fast", 10) < 20 else 0.6,
            "weak_downtrend": 0.7,
            "strong_downtrend": 0.6 if params.get("sma_fast", 10) < 25 else 0.5,
            "volatile": 0.5,
        }

        return compatibility_map.get(regime, 0.5)
