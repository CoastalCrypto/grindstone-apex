"""Main TUI application for Grindstone Apex."""
import logging
from datetime import datetime
from typing import Dict, Optional

from textual.app import ComposeResult, SystemCommand
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Static, Label, RichLog, DataTable,
    TabbedContent, TabPane
)
from textual.reactive import reactive
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich import box

from src.database import SessionLocal, Strategy, LiveTrade, StrategyPerformance
from src.config import get_settings

logger = logging.getLogger(__name__)


class SystemStatus(Static):
    """Display system status panel."""

    def __init__(self):
        """Initialize status panel."""
        super().__init__()
        self.db = SessionLocal()
        self.update_interval = 1.0  # Update every second

    def render(self) -> str:
        """Render status panel."""
        try:
            # Get counts
            total_strategies = self.db.query(Strategy).count()
            deployed_strategies = self.db.query(StrategyPerformance).filter(
                StrategyPerformance.deployed == True
            ).count()
            open_positions = self.db.query(LiveTrade).filter(
                LiveTrade.status == "open"
            ).count()

            # Calculate metrics
            from datetime import timedelta
            recent_trades = self.db.query(LiveTrade).filter(
                LiveTrade.status == "closed",
                LiveTrade.exit_time >= datetime.utcnow() - timedelta(hours=24)
            ).all()

            total_pnl = sum(t.pnl or 0 for t in recent_trades)
            wins = len([t for t in recent_trades if t.pnl and t.pnl > 0])

            status_table = Table(box=box.ROUNDED, title="System Status",
                               title_style="bold cyan")
            status_table.add_column("Metric", style="cyan")
            status_table.add_column("Value", style="green")

            status_table.add_row("Total Strategies", str(total_strategies))
            status_table.add_row("Deployed", str(deployed_strategies))
            status_table.add_row("Open Positions", str(open_positions))
            status_table.add_row("24h Trades", str(len(recent_trades)))
            status_table.add_row("24h P&L", f"${total_pnl:+.2f}")
            status_table.add_row("Win Rate (24h)", f"{wins/len(recent_trades)*100:.1f}%" if recent_trades else "N/A")
            status_table.add_row("Timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

            return str(status_table)

        except Exception as e:
            return f"[red]Error: {str(e)}[/red]"


class PositionsMonitor(Static):
    """Monitor open positions."""

    def __init__(self):
        """Initialize positions monitor."""
        super().__init__()
        self.db = SessionLocal()

    def render(self) -> str:
        """Render positions."""
        try:
            positions = self.db.query(LiveTrade).filter(
                LiveTrade.status == "open"
            ).all()

            if not positions:
                return "[yellow]No open positions[/yellow]"

            table = Table(box=box.ROUNDED, title="Open Positions",
                         title_style="bold cyan")
            table.add_column("Pair", style="cyan")
            table.add_column("Size", style="green")
            table.add_column("Entry", style="yellow")
            table.add_column("Current", style="magenta")
            table.add_column("P&L", style="red")
            table.add_column("Stop", style="blue")
            table.add_column("Target", style="green")

            for pos in positions[:20]:  # Show top 20
                try:
                    from src.live_trading.exchange_connector import ExchangeConnector
                    from src.config import get_settings

                    settings = get_settings()
                    connector = ExchangeConnector(
                        exchange=settings.live_exchange,
                        api_key=settings.live_api_key,
                        api_secret=settings.live_api_secret,
                        sandbox=settings.sandbox_mode
                    )

                    ticker = connector.get_ticker(pos.pair)
                    current_price = ticker["last"]
                    unrealized_pnl = (current_price - pos.entry_price) * pos.size

                    pnl_color = "green" if unrealized_pnl > 0 else "red"

                    table.add_row(
                        pos.pair,
                        f"{pos.size:.4f}",
                        f"${pos.entry_price:.2f}",
                        f"${current_price:.2f}",
                        f"[{pnl_color}]${unrealized_pnl:+.2f}[/{pnl_color}]",
                        f"${pos.stop_loss:.2f}",
                        f"${pos.take_profit:.2f}"
                    )
                except:
                    continue

            return str(table)

        except Exception as e:
            return f"[red]Error: {str(e)}[/red]"


class StrategyPerformance(Static):
    """Show top performing strategies."""

    def __init__(self):
        """Initialize performance view."""
        super().__init__()
        self.db = SessionLocal()

    def render(self) -> str:
        """Render performance."""
        try:
            strategies = self.db.query(StrategyPerformance).order_by(
                StrategyPerformance.live_total_profit.desc()
            ).limit(10).all()

            if not strategies:
                return "[yellow]No deployed strategies[/yellow]"

            table = Table(box=box.ROUNDED, title="Top Strategies",
                         title_style="bold cyan")
            table.add_column("Strategy ID", style="cyan")
            table.add_column("Pair", style="yellow")
            table.add_column("Live P&L", style="green")
            table.add_column("Status", style="magenta")

            for strat in strategies:
                status_color = "green" if strat.live_active else "red"
                status = f"[{status_color}]{'ACTIVE' if strat.live_active else 'INACTIVE'}[/{status_color}]"

                table.add_row(
                    strat.strategy_id[:12] + "...",
                    strat.strategy_id,  # Would get from strategy table
                    f"${strat.live_total_profit or 0:+.2f}",
                    status
                )

            return str(table)

        except Exception as e:
            return f"[red]Error: {str(e)}[/red]"


class DashboardScreen(Screen):
    """Main dashboard screen."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #status {
        height: 12;
        border: solid $accent;
    }

    #positions {
        height: 15;
        border: solid $accent;
    }

    #performance {
        height: 12;
        border: solid $accent;
    }

    Button {
        margin: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield SystemStatus(id="status")
        yield PositionsMonitor(id="positions")
        yield StrategyPerformance(id="performance")
        yield Footer()

    def on_mount(self) -> None:
        """Mount the screen."""
        self.title = "Grindstone Apex - Trading Dashboard"
        self.sub_title = "Multi-Agent AI Trading Bot"


class GenerationMonitor(Static):
    """Monitor Ralph Loop generation progress."""

    def __init__(self):
        """Initialize generation monitor."""
        super().__init__()
        self.db = SessionLocal()

    def render(self) -> str:
        """Render generation progress."""
        try:
            from src.database import GenerationRun
            from sqlalchemy import desc

            recent_gen = self.db.query(GenerationRun).order_by(
                desc(GenerationRun.generation_id)
            ).first()

            if not recent_gen:
                return "[yellow]No generation data available[/yellow]"

            table = Table(box=box.ROUNDED, title="Ralph Loop Status",
                         title_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            pass_rate = (recent_gen.strategies_passed / recent_gen.strategies_generated * 100) \
                       if recent_gen.strategies_generated > 0 else 0

            table.add_row("Generation", str(recent_gen.generation_id))
            table.add_row("Generated", str(recent_gen.strategies_generated))
            table.add_row("Passed", str(recent_gen.strategies_passed))
            table.add_row("Pass Rate", f"{pass_rate:.1f}%")
            table.add_row("Status", recent_gen.status or "Unknown")
            table.add_row("Created", recent_gen.created_at.strftime("%Y-%m-%d %H:%M:%S") if recent_gen.created_at else "N/A")

            return str(table)

        except Exception as e:
            return f"[red]Error: {str(e)}[/red]"


class AlertsLog(RichLog):
    """Real-time alerts log."""

    def __init__(self):
        """Initialize alerts log."""
        super().__init__(markup=True)
        self.max_lines = 100

    def add_alert(self, message: str, level: str = "INFO") -> None:
        """Add alert to log."""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")

        colors = {
            "ERROR": "red",
            "WARNING": "yellow",
            "SUCCESS": "green",
            "INFO": "cyan"
        }

        color = colors.get(level, "white")
        formatted = f"[{color}][{timestamp}] {level}:[/{color}] {message}"
        self.write(Text.from_markup(formatted))


class MonitoringScreen(Screen):
    """Monitoring and alerts screen."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #generation {
        height: 12;
        border: solid $accent;
    }

    #alerts {
        border: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield GenerationMonitor(id="generation")
        yield AlertsLog(id="alerts")
        yield Footer()

    def on_mount(self) -> None:
        """Mount the screen."""
        self.title = "Grindstone Apex - Monitoring"
        self.alerts = self.query_one("#alerts", AlertsLog)
        self.alerts.add_alert("Monitoring system initialized", "INFO")


class SettingsScreen(Screen):
    """Settings and configuration screen."""

    CSS = """
    Screen {
        layout: vertical;
        align: center middle;
    }

    Container {
        width: 60;
        height: auto;
        border: solid $accent;
    }

    Label {
        margin: 1 2;
    }

    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container():
            yield Label("[bold cyan]Grindstone Apex Settings[/bold cyan]")
            yield Label("")
            yield Label("Exchange Settings")
            yield Button("Configure Exchange API", id="exchange-btn")
            yield Label("")
            yield Label("Strategy Settings")
            yield Button("Position Sizing", id="sizing-btn")
            yield Button("Risk Management", id="risk-btn")
            yield Label("")
            yield Label("System Settings")
            yield Button("Database Settings", id="db-btn")
            yield Button("Alert Settings", id="alerts-btn")
            yield Label("")
            yield Button("[bold red]Exit[/bold red]", id="exit-btn")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "exit-btn":
            self.app.exit()


class GrindstoneApp:
    """Main Grindstone Apex TUI application."""

    def __init__(self):
        """Initialize the app."""
        from textual.app import App

        class GroundstoneTextApp(App):
            """Textual app for Grindstone Apex."""

            BINDINGS = [
                ("d", "show_dashboard", "Dashboard"),
                ("m", "show_monitoring", "Monitor"),
                ("s", "show_settings", "Settings"),
                ("q", "quit", "Quit"),
            ]

            def on_mount(self) -> None:
                """Mount the app."""
                self.install_screen(DashboardScreen(), name="dashboard")
                self.install_screen(MonitoringScreen(), name="monitoring")
                self.install_screen(SettingsScreen(), name="settings")
                self.show_screen("dashboard")

            def action_show_dashboard(self) -> None:
                """Show dashboard."""
                self.show_screen("dashboard")

            def action_show_monitoring(self) -> None:
                """Show monitoring."""
                self.show_screen("monitoring")

            def action_show_settings(self) -> None:
                """Show settings."""
                self.show_screen("settings")

        self.app = GroundstoneTextApp()

    def run(self) -> None:
        """Run the TUI application."""
        try:
            self.app.run()
        except Exception as e:
            logger.error(f"Error running TUI: {e}")
            print(f"[red]Error: {e}[/red]")


def main() -> None:
    """Entry point for TUI."""
    app = GrindstoneApp()
    app.run()


if __name__ == "__main__":
    main()
