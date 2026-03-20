"""Quick start example for Grindstone Apex."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtesting.data_loader import HistoricalDataLoader
from src.backtesting.vectorbt_engine import VectorBTBacktestEngine
from src.strategy_generation.genetic_algorithm import GeneticAlgorithmEngine
import json


def example_1_load_data():
    """Example 1: Load historical data."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Load Historical Data")
    print("="*60)

    loader = HistoricalDataLoader(source="yfinance")

    print("Loading 1 year of BTC/USDT 15-minute candles...")
    candles = loader.load_candles(pair="BTC/USDT", timeframe=15, days_back=365)

    print(f"✓ Loaded {len(candles)} candles")
    print(f"  Date range: {candles['timestamp'].min()} to {candles['timestamp'].max()}")
    print(f"  Price range: ${candles['close'].min():.2f} to ${candles['close'].max():.2f}")


def example_2_backtest_single_strategy():
    """Example 2: Backtest a single strategy."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Backtest Single Strategy")
    print("="*60)

    # Load data
    loader = HistoricalDataLoader(source="yfinance")
    candles = loader.load_candles(pair="BTC/USDT", timeframe=15, days_back=365)

    # Define strategy
    strategy = {
        "pair": "BTC/USDT",
        "indicators": {
            "sma_fast": 20,
            "sma_slow": 200,
            "rsi_threshold_buy": 30,
            "rsi_threshold_sell": 70,
            "bollinger_period": 20
        },
        "position_sizing": {
            "size_type": "percent_of_balance",
            "size_amount": 0.5
        },
        "risk_management": {
            "stop_loss_atr": 3.5,
            "take_profit_percent": 0.20,
            "breakeven_on_profit": True,
            "max_drawdown_limit": 0.30
        }
    }

    # Backtest
    print("Backtesting strategy...")
    engine = VectorBTBacktestEngine(initial_balance=10000.0)
    result = engine.backtest_strategy(candles, strategy, strategy_id="example_001")

    # Print results
    metrics = result.get("metrics", {})
    print(f"✓ Backtest complete: {result['num_trades']} trades")
    print(f"  Total P&L: ${metrics.get('total_profit', 0):.2f} ({metrics.get('total_profit_pct', 0):.2f}%)")
    print(f"  Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
    print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {metrics.get('max_drawdown', 0)*100:.1f}%")
    print(f"  Score: {metrics.get('composite_score', 0):.1f}/100")
    print(f"  Meets Criteria: {metrics.get('meets_criteria', False)}")


def example_3_generate_strategies():
    """Example 3: Generate random strategies."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Generate Random Strategies")
    print("="*60)

    ga = GeneticAlgorithmEngine(pair="BTC/USDT")

    print("Generating 20 random strategies...")
    strategies = ga.create_initial_population(population_size=20)

    print(f"✓ Generated {len(strategies)} strategies")

    # Print first 3 strategies
    print("\nFirst 3 strategies:")
    for i, strat in enumerate(strategies[:3]):
        print(f"\nStrategy {i+1} ({strat.id}):")
        print(f"  SMA Fast: {strat.indicators.get('sma_fast', 0)}")
        print(f"  SMA Slow: {strat.indicators.get('sma_slow', 0)}")
        print(f"  Position Size: {strat.position_sizing.get('size_amount', 0)*100:.0f}%")
        print(f"  ATR Stop: {strat.risk_management.get('stop_loss_atr', 0):.1f}x")


def example_4_backtest_multiple():
    """Example 4: Backtest multiple strategies and find best."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Backtest Multiple Strategies")
    print("="*60)

    # Generate strategies
    ga = GeneticAlgorithmEngine(pair="BTC/USDT")
    strategies = ga.create_initial_population(population_size=10)

    # Load data
    loader = HistoricalDataLoader(source="yfinance")
    candles = loader.load_candles(pair="BTC/USDT", timeframe=15, days_back=365)

    # Backtest all
    print(f"Backtesting {len(strategies)} strategies...")
    engine = VectorBTBacktestEngine(initial_balance=10000.0)

    results = []
    for i, strategy in enumerate(strategies):
        result = engine.backtest_strategy(candles, strategy.to_dict(), strategy_id=strategy.id)
        metrics = result.get("metrics", {})
        score = metrics.get("composite_score", 0)
        results.append({
            "strategy": strategy,
            "score": score,
            "trades": result.get("num_trades", 0),
            "win_rate": metrics.get("win_rate", 0),
            "profit_pct": metrics.get("total_profit_pct", 0)
        })

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Print top 3
    print(f"\nTop 3 strategies:")
    for i, result in enumerate(results[:3]):
        print(f"\n#{i+1}: {result['strategy'].id}")
        print(f"  Score: {result['score']:.1f}/100")
        print(f"  Trades: {result['trades']}")
        print(f"  Win Rate: {result['win_rate']*100:.1f}%")
        print(f"  Profit: {result['profit_pct']:.2f}%")


def example_5_genetic_evolution():
    """Example 5: Evolve strategies using genetic algorithm."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Evolve Strategies")
    print("="*60)

    # Generate and backtest initial strategies
    ga = GeneticAlgorithmEngine(pair="BTC/USDT")
    strategies = ga.create_initial_population(population_size=10)

    loader = HistoricalDataLoader(source="yfinance")
    candles = loader.load_candles(pair="BTC/USDT", timeframe=15, days_back=365)

    print(f"Generation 0: Generated {len(strategies)} random strategies")
    engine = VectorBTBacktestEngine(initial_balance=10000.0)

    # Backtest and score
    scored_strategies = []
    for strategy in strategies:
        result = engine.backtest_strategy(candles, strategy.to_dict())
        score = result.get("metrics", {}).get("composite_score", 0)
        scored_strategies.append((strategy, score))

    # Get top performers
    scored_strategies.sort(key=lambda x: x[1], reverse=True)
    top_performers = scored_strategies[:5]

    print(f"  Top 5 average score: {sum(s[1] for s in top_performers)/5:.1f}/100")

    # Evolve
    print(f"\nGeneration 1: Evolving from top performers...")
    new_generation = ga.evolve_population(
        elite_strategies=top_performers,
        population_size=20,
        generation_id=1
    )

    print(f"  Generated {len(new_generation)} evolved strategies")

    # Backtest new generation
    print(f"  Backtesting evolved strategies...")
    new_scored = []
    for strategy in new_generation:
        result = engine.backtest_strategy(candles, strategy.to_dict())
        score = result.get("metrics", {}).get("composite_score", 0)
        new_scored.append((strategy, score))

    new_scored.sort(key=lambda x: x[1], reverse=True)
    print(f"  New generation average score: {sum(s[1] for s in new_scored)/len(new_scored):.1f}/100")
    print(f"  Best in new generation: {new_scored[0][1]:.1f}/100")
    print(f"  Improvement: {new_scored[0][1] - top_performers[0][1]:+.1f}")


def main():
    """Run all examples."""
    print("\n" + "🚀 "*20)
    print("Grindstone Apex - Quick Start Examples")
    print("🚀 "*20)

    try:
        # Run examples
        example_1_load_data()
        example_2_backtest_single_strategy()
        example_3_generate_strategies()
        example_4_backtest_multiple()
        example_5_genetic_evolution()

        print("\n" + "="*60)
        print("✓ All examples completed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Read the documentation: README.md")
        print("2. Start the API: uvicorn main:app --reload")
        print("3. Visit API docs: http://localhost:8001/docs")
        print("4. Configure your exchange API keys in .env")
        print("5. Run generation and backtesting via API")
        print("\nHappy trading! 🚀")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
