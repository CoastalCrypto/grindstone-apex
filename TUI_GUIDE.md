# Terminal User Interface (TUI) Guide

## 🖥️ Overview

Grindstone Apex now includes a **professional Terminal User Interface (TUI)** built with Textual and Rich. Monitor and control your trading bot directly from the terminal with beautiful dashboards, real-time updates, and interactive controls.

## ⚡ Quick Start

### 1. Install TUI Dependencies
```bash
pip install textual click rich --break-system-packages
```

### 2. Launch the Dashboard
```bash
# From the repo root
python cli.py tui

# Or directly
python src/tui/app.py
```

### 3. Navigate
- **D** - Dashboard
- **M** - Monitoring
- **S** - Settings
- **Q** - Quit

## 📊 Dashboard Features

### System Status Panel
Real-time overview of your trading bot:
- **Total Strategies** - All strategies in database
- **Deployed** - Strategies active for live trading
- **Open Positions** - Current live trades
- **24h Trades** - Trades closed in last 24 hours
- **24h P&L** - Profit/loss from recent trading
- **Win Rate** - Percentage of winning trades
- **Timestamp** - Current system time

### Positions Monitor
Live monitoring of all open positions:
- **Pair** - Trading pair (BTC/USDT, etc.)
- **Size** - Position size
- **Entry** - Entry price
- **Current** - Current market price
- **P&L** - Unrealized profit/loss (color-coded)
- **Stop** - Stop loss level
- **Target** - Take profit level

Color coding:
- 🟢 **Green** - Profitable positions
- 🔴 **Red** - Losing positions

### Top Strategies Panel
Shows best-performing deployed strategies:
- **Strategy ID** - Unique strategy identifier
- **Pair** - Trading pair it operates on
- **Live P&L** - Total profit/loss from live trading
- **Status** - Active or inactive

## 📈 Monitoring Screen

### Ralph Loop Status
Continuous strategy generation progress:
- **Generation** - Current generation number
- **Generated** - Total strategies created
- **Passed** - Strategies passing profitability checks
- **Pass Rate** - Percentage of successful strategies
- **Status** - Current state (running, complete, etc.)
- **Created** - When this generation started

### Real-Time Alerts Log
Stream of important events:
- Entry signals and executions
- Exit confirmations
- Error messages
- Strategy retirements
- System events

Color-coded alerts:
- 🟢 **Green** - SUCCESS
- 🔴 **Red** - ERROR
- 🟡 **Yellow** - WARNING
- 🔵 **Cyan** - INFO

## ⚙️ Settings Screen

Configure your trading bot:
- **Exchange API** - Configure trading exchange credentials
- **Position Sizing** - Risk per trade settings
- **Risk Management** - Stop loss and take profit rules
- **Database Settings** - Database connection and backup
- **Alert Settings** - Email, Telegram, Slack notifications

## 🎮 CLI Commands

### TUI Dashboard
```bash
python cli.py tui
```
Launch the interactive terminal dashboard.

### Strategy Generation
```bash
python cli.py generate --interval 300 --pairs BTC/USDT,ETH/USDT
```
Start continuous Ralph Loop generation:
- `--interval` - Generation frequency in seconds (default: 300)
- `--pairs` - Trading pairs to generate strategies for

### Live Trading
```bash
python cli.py trade --interval 60
```
Start live trading service:
- `--interval` - Signal check frequency in seconds (default: 60)

### MiroFish Analysis
```bash
python cli.py mirofish --pair BTC/USDT --num-strategies 50 --optimize --stress-test
```
Run MiroFish multi-agent analysis:
- `--pair` - Trading pair
- `--num-strategies` - Number of strategies to generate
- `--optimize` - Enable swarm intelligence optimization
- `--stress-test` - Run stress test on best strategy

### Service Monitoring
```bash
python cli.py monitor --service both
```
Monitor running services:
- `--service` - Choose: `generation`, `trading`, or `both`
- Updates every 5 seconds

### Database Initialization
```bash
python cli.py init
```
Initialize/migrate database schema.

### Version Info
```bash
python cli.py version
```
Show version and feature list.

### Advanced Examples
```bash
python cli.py help-advanced
```
Display advanced usage examples.

## 🚀 Multi-Terminal Setup

**Recommended production setup using multiple terminal windows:**

**Terminal 1 - Strategy Generation:**
```bash
python cli.py generate --interval 300 --pairs BTC/USDT,ETH/USDT
```
Runs continuously, generating and testing 500 strategies every 5 minutes.

**Terminal 2 - Live Trading:**
```bash
python cli.py trade --interval 60
```
Monitors elite strategies, executes trades every 60 seconds.

**Terminal 3 - TUI Dashboard:**
```bash
python cli.py tui
```
Monitor both services in real-time with beautiful interface.

**Terminal 4 (Optional) - Service Monitor:**
```bash
python cli.py monitor --service both
```
Additional monitoring view showing API endpoints.

## 📡 Docker Integration

### Using Docker Compose (All-in-One)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Launch TUI inside container
docker exec -it grindstone_apex python cli.py tui
```

### Using Docker CLI
```bash
# Build image
docker build -t grindstone-apex .

# Run with TUI
docker run -it grindstone-apex python cli.py tui

# Run with generation
docker run -d grindstone-apex python cli.py generate

# Run with trading
docker run -d grindstone-apex python cli.py trade
```

## 🎯 Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **D** | Show Dashboard |
| **M** | Show Monitoring |
| **S** | Show Settings |
| **Q** | Quit Application |
| **↑/↓** | Scroll up/down |
| **PageUp/PageDown** | Scroll by page |
| **Home/End** | Jump to top/bottom |
| **Tab** | Next field/button |
| **Shift+Tab** | Previous field/button |
| **Enter** | Activate button |

## 📊 Dashboard Widgets

### Real-Time Updates
- Dashboard refreshes every 1-2 seconds
- Updates from live database
- Shows current market prices (where available)

### Color Scheme
```
Positive metrics:   Green (#00FF00)
Negative metrics:   Red (#FF0000)
Neutral info:       Cyan (#00FFFF)
Warnings:           Yellow (#FFFF00)
Labels:             White (#FFFFFF)
```

### Performance Indicators

**Win Rate:**
- 🟢 >60% - Excellent
- 🟡 40-60% - Good
- 🔴 <40% - Needs attention

**P&L:**
- 🟢 Positive - Green
- 🔴 Negative - Red

**Status:**
- 🟢 ACTIVE - Green (strategy trading)
- 🔴 INACTIVE - Red (strategy paused)

## 🔧 Customization

### Custom Themes
Modify colors in `src/tui/app.py`:
```python
# Textual CSS for styling
CSS = """
Screen {
    background: $surface;
    color: $text;
}

#status {
    border: solid $accent;
    background: $panel;
}
"""
```

### Custom Widgets
Add new panels to dashboard:
```python
class CustomWidget(Static):
    def render(self) -> str:
        # Custom widget logic
        return "Your custom content"
```

### Adding New Screens
```python
class CustomScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield CustomWidget()
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Custom Screen"
```

## 📝 Configuration

### TUI Settings in `.env`
```bash
# Terminal UI
TUI_UPDATE_INTERVAL=1
TUI_REFRESH_RATE=2
TUI_COLOR_THEME=default

# Display
TUI_SHOW_GRID=true
TUI_SHOW_BORDERS=true
TUI_MAX_ROWS=50
```

## 🐛 Troubleshooting

### TUI Won't Start
```bash
# Check dependencies
pip list | grep textual

# Reinstall
pip install textual click rich --break-system-packages --force-reinstall

# Try directly
python src/tui/app.py
```

### Display Issues
```bash
# Ensure terminal supports Unicode
export LANG=en_US.UTF-8

# Increase terminal size
# Most issues resolve with larger terminal window

# Try different terminal
# Works best with: iTerm2, Terminal.app, Windows Terminal, Alacritty
```

### Performance Issues
```bash
# Reduce update frequency in config
TUI_UPDATE_INTERVAL=2  # Update every 2 seconds instead of 1

# Limit positions displayed
# TUI shows top 20 positions only to maintain performance
```

### Connection Issues
```bash
# Ensure API is running
curl http://localhost:8001/health

# Check database connection
python cli.py init

# View API logs
docker-compose logs api
```

## 📈 Advanced Monitoring

### Using tmux for Multiple Views
```bash
# Create new tmux session
tmux new-session -d -s trading

# Split into multiple panes
tmux split-window -h -t trading:0 -c ~/grindstone_apex
tmux split-window -v -t trading:0 -c ~/grindstone_apex

# Start services in each pane
tmux send-keys -t trading:0.0 'python cli.py generate' Enter
tmux send-keys -t trading:0.1 'python cli.py trade' Enter
tmux send-keys -t trading:0.2 'python cli.py tui' Enter

# Attach to view all
tmux attach-session -t trading
```

### Using screen Alternative
```bash
# Create screen session
screen -S grindstone

# Start generation in first window
python cli.py generate

# New window (Ctrl+A, C)
# Start trading
python cli.py trade

# New window
# Start TUI
python cli.py tui

# Cycle between windows: Ctrl+A, N (next) / Ctrl+A, P (prev)
```

## 🎓 Best Practices

1. **Monitor Regularly** - Check dashboard at least hourly during trading hours
2. **Watch Alerts** - Pay attention to the alerts log for important events
3. **Review P&L** - Daily review of positions and performance
4. **Backup Settings** - Export configuration regularly
5. **Scale Gradually** - Increase position size only as confidence grows
6. **Stay Updated** - Keep bot software and dependencies current

## 📞 Support & Help

```bash
# Show version info
python cli.py version

# Show advanced examples
python cli.py help-advanced

# Check logs
tail -f logs/grindstone_apex.log

# Database status
python -c "from src.database import SessionLocal; print(SessionLocal().query(Strategy).count())"
```

## 🚀 Next Steps

1. **Start Services** - Use multi-terminal setup above
2. **Open Dashboard** - Launch TUI in one terminal
3. **Monitor Activity** - Watch strategies generate and trade
4. **Review Performance** - Check P&L and win rate
5. **Optimize Parameters** - Adjust settings based on results
6. **Scale Up** - Increase position size gradually

---

**The TUI Dashboard is your command center for Grindstone Apex!** 🎯
