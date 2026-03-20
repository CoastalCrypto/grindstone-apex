"""Command-line interface for Grindstone Apex."""
import click
import logging
from typing import Optional

from src.tui.app import GrindstoneApp
from src.services.generation_service import StrategyGenerationService
from src.services.live_trader_service import LiveTradingService
from src.mirofish.enhanced_strategy_generator import MiroFishEnhancedStrategyGenerator
from src.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Grindstone Apex - AI-Driven Self-Improving Trading Bot."""
    pass


@cli.command()
def tui():
    """Launch the Terminal User Interface dashboard."""
    click.echo("🎰 Starting Grindstone Apex TUI...")
    click.echo("Press 'q' to quit, 'd' for dashboard, 'm' for monitoring, 's' for settings")
    click.echo("")

    app = GrindstoneApp()
    app.run()


@cli.command()
@click.option('--interval', default=300, help='Generation interval in seconds (default: 300)')
@click.option('--pairs', default='BTC/USDT,ETH/USDT', help='Trading pairs (comma-separated)')
def generate(interval: int, pairs: str):
    """Start continuous strategy generation (Ralph Loop)."""
    click.echo(f"🔄 Starting strategy generation service...")
    click.echo(f"   Interval: {interval}s")
    click.echo(f"   Pairs: {pairs}")

    init_db()

    service = StrategyGenerationService()
    pairs_list = [p.strip() for p in pairs.split(',')]

    try:
        service.run_continuous(interval_seconds=interval, pairs=pairs_list)
    except KeyboardInterrupt:
        click.echo("\n✋ Generation service stopped")


@cli.command()
@click.option('--interval', default=60, help='Check interval in seconds (default: 60)')
def trade(interval: int):
    """Start live trading service."""
    click.echo(f"📈 Starting live trading service...")
    click.echo(f"   Check interval: {interval}s")
    click.echo("")

    init_db()

    service = LiveTradingService()

    try:
        service.run_continuous(check_interval=interval)
    except KeyboardInterrupt:
        click.echo("\n✋ Trading service stopped")


@cli.command()
@click.option('--pair', default='BTC/USDT', help='Trading pair')
@click.option('--num-strategies', default=50, help='Number of strategies to generate')
@click.option('--optimize', is_flag=True, help='Use swarm optimization')
@click.option('--stress-test', is_flag=True, help='Run stress test')
def mirofish(pair: str, num_strategies: int, optimize: bool, stress_test: bool):
    """Run MiroFish multi-agent analysis."""
    click.echo(f"🧠 Starting MiroFish analysis...")
    click.echo(f"   Pair: {pair}")
    click.echo(f"   Strategies: {num_strategies}")
    click.echo(f"   Optimize: {optimize}")
    click.echo(f"   Stress test: {stress_test}")
    click.echo("")

    init_db()

    gen = MiroFishEnhancedStrategyGenerator()

    # Generate strategies
    click.echo("⏳ Generating agent-validated strategies...")
    strategies = gen.generate_with_agent_validation(
        param_template={
            "sma_fast": 15,
            "sma_slow": 35,
            "rsi_period": 14,
            "risk_percentage": 2
        },
        pair=pair,
        num_strategies=num_strategies
    )
    click.echo(f"✓ Generated {len(strategies)} validated strategies")

    if optimize and strategies:
        click.echo("\n⏳ Optimizing best strategy...")
        optimized = gen.optimize_with_swarm(strategies[0], pair=pair)
        click.echo(f"✓ Optimization complete. Fitness: {optimized.get('fitness', 0):.2f}")

        if stress_test:
            click.echo("\n⏳ Running stress test...")
            stress = gen.stress_test_strategy(optimized, pair=pair)
            robustness = stress.get('summary', {}).get('robustness_score', 0)
            click.echo(f"✓ Stress test complete. Robustness: {robustness:.1f}/100")


@cli.command()
def init():
    """Initialize database."""
    click.echo("📊 Initializing database...")
    init_db()
    click.echo("✓ Database initialized")


@cli.command()
@click.option('--service', type=click.Choice(['generation', 'trading', 'both']), default='both')
def monitor(service: str):
    """Monitor running services."""
    import time
    import requests
    import json

    click.echo(f"📡 Monitoring {service} service(s)...")
    click.echo("")

    while True:
        try:
            # Get system status from API
            response = requests.get("http://localhost:8001/api/v1/live-trading/summary")

            if response.status_code == 200:
                data = response.json()
                click.clear()
                click.echo("🎰 Grindstone Apex - Service Monitor")
                click.echo("=" * 60)
                click.echo(f"Active Strategies: {data.get('active_strategies', 0)}")
                click.echo(f"Open Positions: {data.get('total_open_positions', 0)}")
                click.echo(f"Total P&L: ${data.get('total_live_profit', 0):.2f}")
                click.echo(f"Win Rate: {data.get('win_rate', 0)*100:.1f}%")
                click.echo("")
                click.echo("Press Ctrl+C to stop monitoring")

            time.sleep(5)

        except KeyboardInterrupt:
            click.echo("\n✋ Monitoring stopped")
            break
        except Exception as e:
            click.echo(f"⚠️  Error: {e}")
            time.sleep(5)


@cli.command()
def version():
    """Show version information."""
    click.echo("Grindstone Apex v1.0.0")
    click.echo("AI-Driven Self-Improving Trading Bot")
    click.echo("")
    click.echo("Phases Included:")
    click.echo("  ✓ Phase 1: VectorBT Backtesting")
    click.echo("  ✓ Phase 2: Genetic Algorithm")
    click.echo("  ✓ Phase 3: Ralph Loop")
    click.echo("  ✓ Phase 4: Live Trading")
    click.echo("  ✓ Phase 5: Advanced AI")
    click.echo("  ✓ MiroFish: Multi-Agent Simulation")


@cli.command()
def help_advanced():
    """Show advanced usage examples."""
    click.echo("Advanced Usage Examples")
    click.echo("=" * 60)
    click.echo("")
    click.echo("1. Start everything (generation + trading + TUI):")
    click.echo("   # Terminal 1")
    click.echo("   grindstone generate --interval 300")
    click.echo("")
    click.echo("   # Terminal 2")
    click.echo("   grindstone trade --interval 60")
    click.echo("")
    click.echo("   # Terminal 3")
    click.echo("   grindstone tui")
    click.echo("")
    click.echo("2. Run MiroFish analysis:")
    click.echo("   grindstone mirofish --pair BTC/USDT --optimize --stress-test")
    click.echo("")
    click.echo("3. Monitor services:")
    click.echo("   grindstone monitor --service both")
    click.echo("")
    click.echo("4. Docker Compose (recommended):")
    click.echo("   docker-compose up -d")
    click.echo("   docker-compose logs -f api")


if __name__ == "__main__":
    cli()
