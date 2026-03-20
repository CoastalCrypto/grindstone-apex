"""Autoresearch system - automatically document successful strategy patterns."""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import statistics

from src.database import SessionLocal, Strategy, BacktestResult, GenerationRun
from src.ralph_loop.evaluator import RalphLoopEvaluator

logger = logging.getLogger(__name__)


class AutoResearch:
    """Automatically analyze and document successful strategy patterns."""

    def __init__(self, output_dir: str = "research_output"):
        """
        Initialize autoresearch system.

        Args:
            output_dir: Directory for research output
        """
        self.db = SessionLocal()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.evaluator = RalphLoopEvaluator(self.db)

    def generate_research_report(self, generation_limit: int = 10) -> Dict:
        """
        Generate comprehensive research report on successful patterns.

        Args:
            generation_limit: Analyze last N generations

        Returns:
            Research report dict
        """
        logger.info(f"Generating research report (last {generation_limit} generations)...")

        try:
            # Get recent elite strategies
            elite_strategies = self.evaluator.get_elite_strategies(limit=100)

            if not elite_strategies:
                logger.warning("No elite strategies found")
                return {"error": "No elite strategies"}

            # Analyze patterns
            patterns = self._analyze_parameter_patterns(elite_strategies)
            performance_insights = self._analyze_performance_insights(elite_strategies)
            evolution_analysis = self._analyze_evolution(generation_limit)

            # Compile report
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "elite_count": len(elite_strategies),
                "patterns": patterns,
                "performance_insights": performance_insights,
                "evolution": evolution_analysis,
                "recommendations": self._generate_recommendations(
                    patterns, performance_insights
                )
            }

            # Save report
            self._save_report(report)

            return report

        except Exception as e:
            logger.error(f"Error generating research report: {e}")
            return {"error": str(e)}

    def _analyze_parameter_patterns(self, elite_strategies: List[Dict]) -> Dict:
        """
        Analyze common parameters in elite strategies.

        Args:
            elite_strategies: List of elite strategy dicts

        Returns:
            Pattern analysis
        """
        logger.info("Analyzing parameter patterns...")

        patterns = {
            "sma_fast": [],
            "sma_slow": [],
            "rsi_period": [],
            "rsi_overbought": [],
            "rsi_oversold": [],
            "bb_period": [],
            "bb_std_dev": [],
            "risk_percentage": [],
            "profit_target": [],
        }

        for strategy in elite_strategies:
            params = strategy.get("parameters", {})

            patterns["sma_fast"].append(params.get("sma_fast", 10))
            patterns["sma_slow"].append(params.get("sma_slow", 30))
            patterns["rsi_period"].append(params.get("rsi_period", 14))
            patterns["rsi_overbought"].append(params.get("rsi_overbought", 70))
            patterns["rsi_oversold"].append(params.get("rsi_oversold", 30))
            patterns["bb_period"].append(params.get("bb_period", 20))
            patterns["bb_std_dev"].append(params.get("bb_std_dev", 2))
            patterns["risk_percentage"].append(params.get("risk_percentage", 2))
            patterns["profit_target"].append(params.get("profit_target", 0.02))

        # Calculate statistics
        analysis = {}
        for param, values in patterns.items():
            if not values:
                continue

            analysis[param] = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
                "mode": self._get_mode(values),
                "recommended_range": [
                    max(min(values) - statistics.stdev(values) if len(values) > 1 else min(values), 0),
                    min(values) + statistics.stdev(values) if len(values) > 1 else max(values)
                ]
            }

        return analysis

    def _analyze_performance_insights(self, elite_strategies: List[Dict]) -> Dict:
        """
        Analyze performance metrics of elite strategies.

        Args:
            elite_strategies: List of elite strategies

        Returns:
            Performance analysis
        """
        logger.info("Analyzing performance insights...")

        win_rates = []
        profit_pcts = []
        sharpe_ratios = []
        profit_factors = []

        for strategy in elite_strategies:
            metrics = strategy.get("metrics", {})

            if metrics.get("win_rate"):
                win_rates.append(metrics["win_rate"])
            if metrics.get("profit_pct"):
                profit_pcts.append(metrics["profit_pct"])
            if metrics.get("sharpe_ratio"):
                sharpe_ratios.append(metrics["sharpe_ratio"])
            if metrics.get("profit_factor"):
                profit_factors.append(metrics["profit_factor"])

        return {
            "win_rate": {
                "mean": statistics.mean(win_rates) if win_rates else 0,
                "median": statistics.median(win_rates) if win_rates else 0,
                "stdev": statistics.stdev(win_rates) if len(win_rates) > 1 else 0,
            },
            "profit_pct": {
                "mean": statistics.mean(profit_pcts) if profit_pcts else 0,
                "median": statistics.median(profit_pcts) if profit_pcts else 0,
                "stdev": statistics.stdev(profit_pcts) if len(profit_pcts) > 1 else 0,
            },
            "sharpe_ratio": {
                "mean": statistics.mean(sharpe_ratios) if sharpe_ratios else 0,
                "median": statistics.median(sharpe_ratios) if sharpe_ratios else 0,
                "stdev": statistics.stdev(sharpe_ratios) if len(sharpe_ratios) > 1 else 0,
            },
            "profit_factor": {
                "mean": statistics.mean(profit_factors) if profit_factors else 0,
                "median": statistics.median(profit_factors) if profit_factors else 0,
                "stdev": statistics.stdev(profit_factors) if len(profit_factors) > 1 else 0,
            }
        }

    def _analyze_evolution(self, generation_limit: int) -> Dict:
        """
        Analyze evolution over generations.

        Args:
            generation_limit: Number of recent generations to analyze

        Returns:
            Evolution analysis
        """
        logger.info("Analyzing evolution...")

        try:
            gen_runs = self.db.query(GenerationRun).order_by(
                GenerationRun.generation_id.desc()
            ).limit(generation_limit).all()

            evolution = {
                "generations_analyzed": len(gen_runs),
                "pass_rate_trend": [],
                "best_score_trend": [],
                "strategy_improvement": []
            }

            for run in reversed(gen_runs):
                if run.strategies_generated > 0:
                    pass_rate = run.strategies_passed / run.strategies_generated
                    evolution["pass_rate_trend"].append({
                        "generation": run.generation_id,
                        "pass_rate": pass_rate
                    })

            # Calculate improvement
            if len(evolution["pass_rate_trend"]) > 1:
                first_rate = evolution["pass_rate_trend"][0]["pass_rate"]
                last_rate = evolution["pass_rate_trend"][-1]["pass_rate"]
                improvement = ((last_rate - first_rate) / first_rate * 100) if first_rate > 0 else 0

                evolution["improvement_percentage"] = improvement
                evolution["improvement_direction"] = "improving" if improvement > 0 else "declining"

            return evolution

        except Exception as e:
            logger.error(f"Error analyzing evolution: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, patterns: Dict, performance: Dict) -> List[str]:
        """
        Generate recommendations based on analysis.

        Args:
            patterns: Parameter patterns
            performance: Performance analysis

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check win rate
        win_rate = performance.get("win_rate", {}).get("mean", 0)
        if win_rate < 0.40:
            recommendations.append(
                "❌ Average win rate is below 40%. Consider stricter entry criteria or increased risk management."
            )
        elif win_rate > 0.60:
            recommendations.append(
                "✅ Excellent average win rate (>60%). Current strategies are performing well."
            )

        # Check profit factor
        pf = performance.get("profit_factor", {}).get("mean", 0)
        if pf > 2.0:
            recommendations.append(
                "✅ Profit factor >2.0 indicates strong risk-reward. Keep current parameter ranges."
            )
        elif pf < 1.2:
            recommendations.append(
                "⚠️ Low profit factor. Increase take-profit targets or tighten stop losses."
            )

        # Check sharpe ratio
        sharpe = performance.get("sharpe_ratio", {}).get("mean", 0)
        if sharpe < 0.8:
            recommendations.append(
                "⚠️ Low Sharpe ratio. Strategy returns are not well-compensated for risk."
            )

        # Parameter recommendations
        if patterns.get("sma_fast"):
            sma_fast_range = patterns["sma_fast"]["recommended_range"]
            recommendations.append(
                f"📊 SMA Fast optimal range: {sma_fast_range[0]:.0f}-{sma_fast_range[1]:.0f} periods"
            )

        if patterns.get("risk_percentage"):
            risk_range = patterns["risk_percentage"]["recommended_range"]
            recommendations.append(
                f"💰 Risk percentage optimal range: {risk_range[0]:.2f}-{risk_range[1]:.2f}%"
            )

        recommendations.append(
            "🔄 Consider fine-tuning parameters within recommended ranges and rerun Ralph Loop."
        )

        return recommendations

    def _save_report(self, report: Dict) -> None:
        """Save report to file."""
        try:
            filename = f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.output_dir / filename

            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"Research report saved to {filepath}")

            # Also save markdown version
            self._save_markdown_report(report)

        except Exception as e:
            logger.error(f"Error saving report: {e}")

    def _save_markdown_report(self, report: Dict) -> None:
        """Save markdown version of report."""
        try:
            filename = f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            filepath = self.output_dir / filename

            md_content = f"""# Grindstone Apex Research Report

Generated: {report['timestamp']}

## Summary

- Elite Strategies Analyzed: {report['elite_count']}
- Status: Successfully analyzed trading patterns

## Parameter Patterns

### SMA Indicators
"""
            patterns = report.get("patterns", {})
            if patterns.get("sma_fast"):
                sma_fast = patterns["sma_fast"]
                md_content += f"""
- **SMA Fast**: Mean={sma_fast['mean']:.1f}, Range: {sma_fast['min']:.0f}-{sma_fast['max']:.0f}
- **Recommended Range**: {sma_fast['recommended_range'][0]:.0f}-{sma_fast['recommended_range'][1]:.0f}
"""

            if patterns.get("sma_slow"):
                sma_slow = patterns["sma_slow"]
                md_content += f"""- **SMA Slow**: Mean={sma_slow['mean']:.1f}, Range: {sma_slow['min']:.0f}-{sma_slow['max']:.0f}
- **Recommended Range**: {sma_slow['recommended_range'][0]:.0f}-{sma_slow['recommended_range'][1]:.0f}
"""

            md_content += f"""
## Performance Insights

### Win Rate
- Mean: {report['performance_insights']['win_rate']['mean']*100:.1f}%
- Median: {report['performance_insights']['win_rate']['median']*100:.1f}%

### Profit Factor
- Mean: {report['performance_insights']['profit_factor']['mean']:.2f}
- Median: {report['performance_insights']['profit_factor']['median']:.2f}

### Sharpe Ratio
- Mean: {report['performance_insights']['sharpe_ratio']['mean']:.2f}
- Median: {report['performance_insights']['sharpe_ratio']['median']:.2f}

## Evolution Analysis

Generations Analyzed: {report['evolution'].get('generations_analyzed', 0)}
"""

            if 'improvement_percentage' in report['evolution']:
                md_content += f"\nImprovement: {report['evolution']['improvement_percentage']:.1f}% ({report['evolution']['improvement_direction']})\n"

            md_content += "\n## Recommendations\n\n"
            for rec in report.get('recommendations', []):
                md_content += f"- {rec}\n"

            md_content += "\n---\n*Generated by Grindstone Apex Autoresearch System*"

            with open(filepath, 'w') as f:
                f.write(md_content)

            logger.info(f"Markdown report saved to {filepath}")

        except Exception as e:
            logger.error(f"Error saving markdown report: {e}")

    def _get_mode(self, values: List) -> Optional[float]:
        """Get mode of values."""
        try:
            return max(set(values), key=values.count)
        except:
            return None
