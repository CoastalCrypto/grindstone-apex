# Grindstone Apex: AI-Driven Self-Improving Trading Bot

> **An advanced cryptocurrency trading system that autonomously generates, tests, backtests, and deploys profitable trading strategies using genetic algorithms, transformer neural networks, multi-agent simulation, and swarm intelligence optimization.**

Welcome to Grindstone Apex! This comprehensive guide will help you set up, configure, and run the complete trading system from scratch.

---

## 📚 Table of Contents

1. [System Overview](#system-overview)
2. [Quick Start (5 Minutes)](#quick-start-5-minutes)
3. [Prerequisites & Installation](#prerequisites--installation)
4. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
5. [Configuration](#configuration)
6. [Running the System](#running-the-system)
7. [CLI Commands](#cli-commands)
8. [Terminal UI Dashboard](#terminal-ui-dashboard)
9. [API Documentation](#api-documentation)
10. [Docker Deployment](#docker-deployment)
11. [System Architecture](#system-architecture)
12. [Workflow & Concepts](#workflow--concepts)
13. [Performance Monitoring](#performance-monitoring)
14. [Troubleshooting](#troubleshooting)
15. [Advanced Features](#advanced-features)
16. [Support & Contributing](#support--contributing)

---

## System Overview

### What is Grindstone Apex?

Grindstone Apex is a **self-improving trading bot** that:
- **Generates** thousands of trading strategies automatically
- **Backtests** strategies in minutes using vectorized processing
- **Selects** winners using the "Ralph Loop" (keep top 20%, discard bottom 80%)
- **Deploys** elite strategies to live trading on multiple exchanges
- **Monitors** performance and adapts to market changes
- **Improves** continuously through genetic algorithms and AI

### Key Features

✨ **Intelligent Strategy Generation**
- Random strategy creation with 50+ parameter combinations
- Genetic algorithm mutations (±10-20% variance)
- Transformer neural networks for parameter prediction
- Multi-agent market simulation (7 agent types)
- Swarm intelligence optimization (PSO + ACO)

⚡ **Ultra-Fast Backtesting**
- VectorBT-based vectorized processing (100+ strategies/minute)
- 1 year of historical data processing in seconds
- Multi-timeframe support (15m, 1h, 4h)
- Real fee modeling and slippage

🎯 **Ralph Loop - Continuous Evolution**
- Automatically selects top 20% performing strategies
- Discards bottom 80% to prevent resource waste
- Gives losers second chances through mutation
- Tracks genealogy and evolution patterns
- Keeps strategies profitable over time

💰 **Live Trading Engine**
- Multi-exchange support (Binance, Coinbase, Kraken, Blofin, etc.)
- Real-time position management
- ATR-based stop losses with breakeven protection
- Position sizing based on account risk
- Automated entry/exit signal execution

📊 **Real-Time Monitoring**
- Terminal UI dashboard with live metrics
- System status, open positions, strategy performance
- Alert logs (entry signals, errors, warnings)
- Web API with 40+ endpoints
- Drift detection between backtest and live

🔬 **Advanced AI & Analysis**
- Market regime detection (6 regimes)
- Scenario stress testing (8 market conditions)
- Regime transition prediction
- LLM council voting for final decisions
- MiroFish multi-agent market simulation

---

## Quick Start (5 Minutes)

### Fastest Setup (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/CoastalCrypto/grindstone-apex.git
cd grindstone-apex

# 2. Create configuration
cp .env.example .env

# 3. Start everything
docker-compose up -d

# 4. Verify it's running
curl http://localhost:8001/health
```

✅ That's it! Your system is running at `http://localhost:8001`

### API Examples

```bash
# View health
curl http://localhost:8001/health

# Launch TUI dashboard
docker-compose exec api python cli.py tui

# Start strategy generation
docker-compose exec api python cli.py generate --interval 300

# Start live trading
docker-compose exec api python cli.py trade --interval 60

# Run MiroFish analysis
docker-compose exec api python cli.py mirofish --pair BTC/USDT --optimize --stress-test

# View API docs
# Open browser to: http://localhost:8001/docs
```

---

## Prerequisites & Installation

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2)
- **Python**: 3.11 or higher
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 5GB for data and models
- **Internet**: Required for exchange APIs and data

### Dependencies

Install system prerequisites based on your OS:

**macOS:**
```bash
brew install postgresql redis python@3.11
```

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib redis-server python3.11 python3.11-venv
```

**Windows:**
- Download PostgreSQL from https://www.postgresql.org/download/windows/
- Download Redis from https://github.com/microsoftarchive/redis/releases
- Python from https://www.python.org/downloads/

### Python Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate    # macOS/Linux
# or
venv\Scripts\activate       # Windows

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt --break-system-packages
```

---

## Step-by-Step Setup Guide

### Step 1: Environment Configuration

```bash
# Copy example config
cp .env.example .env

# Edit the file with your settings
nano .env  # or use your preferred editor
```

Edit these critical values:

```bash
# Database
DATABASE_URL=postgresql://trader:password@localhost:5432/grindstone_apex

# Redis
REDIS_URL=redis://localhost:6379/0

# Exchange (multiple exchanges supported)
LIVE_EXCHANGE=binance          # or coinbase, kraken, blofin, etc.
LIVE_API_KEY=your_api_key
LIVE_API_SECRET=your_secret
SANDBOX_MODE=true              # Use sandbox for testing first!

# Trading Settings
PAIRS_TO_TRADE=BTC/USDT,ETH/USDT
TARGET_WEEKLY_PROFIT_USDT=5000
MIN_ACCOUNT_BALANCE_USDT=1000

# Strategy Parameters
STRATEGIES_PER_GENERATION=500   # Generate 500 strategies per cycle
ELITE_THRESHOLD=0.20            # Keep top 20%
MUTATION_RATE=0.15              # Mutate by ±15%

# Risk Management
STOP_LOSS_ATR_MULTIPLIER=3.5    # 3.5x ATR stops
TAKE_PROFIT_PERCENT=0.20        # 20% profit targets
MAX_POSITIONS=5                 # Max concurrent positions
POSITION_SIZE_PERCENT=0.5       # Risk 0.5% per trade

# Notifications (optional)
ALERT_EMAIL=your_email@gmail.com
ALERT_TELEGRAM_BOT_TOKEN=your_token
ALERT_TELEGRAM_CHAT_ID=your_chat_id
```

### Step 2: Database Setup

```bash
# Start PostgreSQL (if using Docker)
docker run --name postgres \
  -e POSTGRES_DB=grindstone_apex \
  -e POSTGRES_USER=trader \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15

# Wait 10 seconds for database to start
sleep 10

# Initialize database schema
python cli.py init
```

You should see: `✓ Database initialized`

### Step 3: Cache Setup

```bash
# Start Redis (if using Docker)
docker run --name redis \
  -p 6379:6379 \
  -d redis:7

# Verify connection
redis-cli ping  # Should return PONG
```

### Step 4: Verify Installation

```bash
# Test all components are working
python cli.py version

# Expected output:
# Grindstone Apex v1.0.0
# AI-Driven Self-Improving Trading Bot
#
# Phases Included:
#   ✓ Phase 1: VectorBT Backtesting
#   ✓ Phase 2: Genetic Algorithm
#   ✓ Phase 3: Ralph Loop
#   ✓ Phase 4: Live Trading
#   ✓ Phase 5: Advanced AI
#   ✓ MiroFish: Multi-Agent Simulation
```

---

## Configuration

### Strategy Generation Parameters

These control how strategies are created:

```bash
# Number of strategies to generate per cycle
STRATEGIES_PER_GENERATION=500

# Percentage to keep as elite (top performers)
ELITE_THRESHOLD=0.20           # Keep top 20%

# How much to mutate strategies
MUTATION_RATE=0.15             # ±15% variance

# How far back to backtest
BACKTEST_YEAR_RANGE=365        # 1 year of data

# Minimum quality threshold
MIN_STRATEGY_SCORE=50           # Out of 100
```

### Risk Management Parameters

These protect your capital:

```bash
# Stop loss size relative to ATR
STOP_LOSS_ATR_MULTIPLIER=3.5   # 3.5x Average True Range

# Profit target percentage
TAKE_PROFIT_PERCENT=0.20        # Close at +20% profit

# How many positions can be open
MAX_POSITIONS=5

# Size per trade as % of account
POSITION_SIZE_PERCENT=0.5       # Risk 0.5% per trade

# Maximum allowed drawdown
MAX_DRAWDOWN_PERCENT=30
```

### Performance Criteria

These define what makes a "winning" strategy:

```bash
# Minimum win rate
TARGET_WIN_RATE=0.40            # 40% of trades should win

# Minimum profit requirement
TARGET_PROFIT_PCT=0.20          # 20% total profit

# Sharpe ratio threshold
MIN_SHARPE_RATIO=1.0

# Profit factor (gross profit / gross loss)
MIN_PROFIT_FACTOR=2.0
```

### Advanced Settings

```bash
# Market timeframes to analyze
TIMEFRAMES=15m,1h,4h

# Number of elite strategies to deploy live
LIVE_STRATEGIES_COUNT=3

# Drift detection threshold
PERFORMANCE_DRIFT_THRESHOLD=0.15  # Flag if backtest/live differ by 15%

# How often to check for trading signals (seconds)
SIGNAL_CHECK_INTERVAL=60

# How often to generate new strategies (seconds)
GENERATION_INTERVAL=300         # Every 5 minutes

# Database cleanup (days)
ARCHIVE_AFTER_DAYS=30           # Archive old trades after 30 days
```

---

## Running the System

### Recommended Multi-Terminal Setup

For production use, run each component in a separate terminal:

**Terminal 1 - Strategy Generation:**
```bash
python cli.py generate --interval 300 --pairs BTC/USDT,ETH/USDT
```
This continuously generates 500 strategies every 5 minutes.

**Terminal 2 - Live Trading:**
```bash
python cli.py trade --interval 60
```
This executes trades from elite strategies every 60 seconds.

**Terminal 3 - TUI Dashboard:**
```bash
python cli.py tui
```
This shows real-time monitoring with beautiful interface.

**Terminal 4 (Optional) - API Server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```
Provides REST API for programmatic access.

### Single Terminal (Development Only)

```bash
# Start everything with Docker Compose
docker-compose up -d

# View logs from all services
docker-compose logs -f

# To stop
docker-compose down
```

---

## CLI Commands

### Core Commands

#### Generate Strategies
```bash
# Basic generation (default settings)
python cli.py generate

# Specify interval and trading pairs
python cli.py generate --interval 300 --pairs BTC/USDT,ETH/USDT,SOL/USDT

# Custom parameters
python cli.py generate \
  --interval 600 \
  --pairs BTC/USDT \
  --num-strategies 1000
```

#### Start Live Trading
```bash
# Run with default 60-second signal check
python cli.py trade

# Check signals every 30 seconds
python cli.py trade --interval 30

# Check every 2 minutes
python cli.py trade --interval 120
```

#### Launch TUI Dashboard
```bash
# Start the terminal user interface
python cli.py tui

# Controls:
#   D - Show Dashboard
#   M - Show Monitoring
#   S - Show Settings
#   Q - Quit
```

#### MiroFish Multi-Agent Analysis
```bash
# Basic analysis
python cli.py mirofish --pair BTC/USDT

# With optimization
python cli.py mirofish \
  --pair BTC/USDT \
  --num-strategies 100 \
  --optimize

# Full analysis with stress testing
python cli.py mirofish \
  --pair BTC/USDT \
  --num-strategies 200 \
  --optimize \
  --stress-test
```

### Utility Commands

#### Initialize Database
```bash
python cli.py init
# Initializes or migrates database schema
```

#### Monitor Services
```bash
# Monitor all services
python cli.py monitor --service both

# Monitor only generation
python cli.py monitor --service generation

# Monitor only trading
python cli.py monitor --service trading
```

#### Show Version
```bash
python cli.py version
# Displays version and available features
```

#### Show Advanced Help
```bash
python cli.py help-advanced
# Displays advanced usage examples
```

---

## Terminal UI Dashboard

The TUI provides real-time monitoring of your trading bot.

### Dashboard Screen (Press D)

Shows key metrics:
- **Total Strategies**: All strategies in database
- **Deployed**: Strategies actively trading
- **Open Positions**: Current live trades
- **24h Trades**: Trades closed in last 24 hours
- **24h P&L**: Profit/loss from recent trades
- **Win Rate**: Percentage of winning trades

Also displays:
- **Open Positions** table with entry price, current price, P&L
- **Top Strategies** showing best performers and their live P&L

### Monitoring Screen (Press M)

Tracks generation progress and events:
- **Ralph Loop Status**: Generation count, pass rate
- **Real-Time Alerts Log**: Color-coded events (green=success, red=error, yellow=warning)
- Entry/exit signals, errors, strategy retirements

### Settings Screen (Press S)

Configure system parameters:
- Exchange API credentials
- Position sizing rules
- Risk management settings
- Database connections
- Alert notification preferences

### Keyboard Controls

| Key | Action |
|-----|--------|
| **D** | Show Dashboard |
| **M** | Show Monitoring |
| **S** | Show Settings |
| **Q** | Quit Application |
| **↑/↓** | Scroll up/down |
| **PageUp/PageDown** | Scroll by page |
| **Home/End** | Jump to top/bottom |
| **Tab** | Next field |
| **Shift+Tab** | Previous field |
| **Enter** | Activate button |

---

## API Documentation

The system includes a REST API with 40+ endpoints accessible at `http://localhost:8001/docs`

### Key Endpoints

#### Health & Status
```bash
# System health
curl http://localhost:8001/health

# Get system metrics
curl http://localhost:8001/api/v1/system/metrics

# Get trading summary
curl http://localhost:8001/api/v1/live-trading/summary
```

#### Strategy Management
```bash
# List all strategies
curl http://localhost:8001/api/v1/strategies

# Get elite strategies
curl http://localhost:8001/api/v1/ralph-loop/elite?limit=20

# Get strategy by ID
curl http://localhost:8001/api/v1/strategies/{strategy_id}
```

#### Backtesting
```bash
# Backtest a single strategy
curl -X POST http://localhost:8001/api/v1/backtest/single \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTC/USDT",
    "indicators": {
      "sma_fast": 20,
      "sma_slow": 200,
      "rsi_threshold_buy": 30,
      "rsi_threshold_sell": 70
    }
  }'

# Backtest multiple strategies
curl -X POST http://localhost:8001/api/v1/backtest/batch \
  -H "Content-Type: application/json" \
  -d '{"count": 100, "pair": "BTC/USDT"}'
```

#### Live Trading
```bash
# Get open positions
curl http://localhost:8001/api/v1/live-trading/positions/open

# Get closed positions
curl http://localhost:8001/api/v1/live-trading/positions/closed

# Deploy strategy
curl -X POST http://localhost:8001/api/v1/live-trading/deploy \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "strat_123"}'

# Retire strategy
curl -X POST http://localhost:8001/api/v1/live-trading/retire \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "strat_123"}'
```

#### Generation & Evolution
```bash
# Generate initial strategies
curl -X POST http://localhost:8001/api/v1/generate/initial \
  -H "Content-Type: application/json" \
  -d '{"pair": "BTC/USDT", "count": 100}'

# Get generation statistics
curl http://localhost:8001/api/v1/ralph-loop/statistics

# Get strategy genealogy
curl http://localhost:8001/api/v1/ralph-loop/genealogy/{strategy_id}

# Get evolution patterns
curl http://localhost:8001/api/v1/ralph-loop/patterns
```

#### Advanced Analysis
```bash
# Train transformer on elite strategies
curl -X POST http://localhost:8001/api/v1/phase5/transformer/train

# Predict parameters
curl -X POST http://localhost:8001/api/v1/phase5/transformer/predict \
  -H "Content-Type: application/json" \
  -d '{"context": "bull_market"}'

# Market regime detection
curl -X POST http://localhost:8001/api/v1/phase5/market-regime/detect \
  -H "Content-Type: application/json" \
  -d '{"pair": "BTC/USDT"}'

# Council voting consensus
curl -X POST http://localhost:8001/api/v1/phase5/council/vote \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "strat_123", "market_context": "volatile"}'
```

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f postgres
docker-compose logs -f redis

# Stop all services
docker-compose down

# Remove all data (clean slate)
docker-compose down -v
```

### Manual Docker Usage

```bash
# Build custom image
docker build -t grindstone-apex:latest .

# Run API server
docker run -it \
  -p 8001:8001 \
  -e DATABASE_URL=postgresql://trader:pass@host/grindstone_apex \
  grindstone-apex:latest \
  uvicorn main:app --host 0.0.0.0

# Run strategy generation
docker run -d \
  -e DATABASE_URL=postgresql://trader:pass@host/grindstone_apex \
  grindstone-apex:latest \
  python cli.py generate

# Run live trading
docker run -d \
  -e DATABASE_URL=postgresql://trader:pass@host/grindstone_apex \
  -e LIVE_EXCHANGE=binance \
  -e LIVE_API_KEY=$API_KEY \
  -e LIVE_API_SECRET=$API_SECRET \
  grindstone-apex:latest \
  python cli.py trade
```

### Docker Compose Services

The `docker-compose.yml` includes:

- **postgres**: Database (port 5432)
- **redis**: Cache (port 6379)
- **api**: FastAPI server (port 8001)
- **strategy-generator**: Background generation
- **live-trader**: Background trading
- (Optional) nginx: Reverse proxy

---

## System Architecture

### High-Level Overview

```
User Interface
    ├── TUI Dashboard (Terminal)
    ├── REST API (Web)
    └── CLI Tools

Core Modules
    ├── Strategy Generation
    │   ├── Random generation
    │   ├── Genetic mutations
    │   ├── Transformer predictor
    │   └── MiroFish validation
    │
    ├── Backtesting
    │   ├── Data loader (yfinance/CCXT)
    │   ├── VectorBT engine
    │   └── Metrics calculator
    │
    ├── Ralph Loop
    │   ├── Strategy scorer
    │   ├── Elite selector
    │   └── Genealogy tracker
    │
    └── Live Trading
        ├── Exchange connector (CCXT)
        ├── Position manager
        ├── Signal executor
        └── Performance monitor

Data Storage
    ├── PostgreSQL (persistent data)
    ├── Redis (cache)
    └── File storage (models)

External Services
    ├── Multiple exchanges (Binance, Coinbase, etc.)
    ├── Market data (yfinance)
    └── Notifications (Email, Telegram)
```

### Database Schema

**Strategy Table**
- ID, parameters, creation timestamp
- Parent ID (genealogy tracking)
- Backtest score, generation number

**BacktestResult Table**
- Strategy ID, pair, timeframe
- Win rate, profit factor, Sharpe ratio
- Entry/exit rules, position sizes

**LiveTrade Table**
- Strategy ID, pair, entry/exit price
- Position size, P&L, status
- Timestamps

**StrategyPerformance Table**
- Live performance metrics
- Deployment status, health score
- Comparison with backtest

**GenerationRun Table**
- Generation number, timestamp
- Strategies generated/passed
- Pass rate statistics

### Data Flow

```
1. Generate → Random/mutated strategies
2. Backtest → Test on historical data
3. Score → Calculate metrics
4. Rank → Sort by performance
5. Select → Keep top 20% (elite)
6. Deploy → Send elite to live trading
7. Monitor → Track real performance
8. Adapt → Mutate for next generation
9. Loop → Repeat infinitely
```

---

## Workflow & Concepts

### Phase 1: Strategy Generation

Strategies are created with random parameters:

```python
Strategy Example:
  - Fast MA: 20 (buy when price > fast MA)
  - Slow MA: 200 (confirm with slow MA)
  - RSI Buy: 35 (only buy on RSI < 35)
  - RSI Sell: 65 (sell on RSI > 65)
  - Stop Loss: 3.5x ATR
  - Take Profit: +20%
```

**Generation Methods:**
1. **Random**: Create completely random parameters
2. **Mutation**: Take elite strategy, change by ±10-20%
3. **Crossover**: Mix parameters from two elite strategies
4. **Transformer**: Use AI to predict good parameters

### Phase 2: Backtesting

Each strategy is tested on 1 year of historical data:

```
For each strategy:
  1. Load 1-year price data (1h/4h/15m)
  2. Simulate trades with exact conditions
  3. Track entry price, exit price, P&L
  4. Calculate metrics (win rate, profit factor, Sharpe)
  5. Record all trades
```

**Speed**: 100+ strategies/minute (vs. 1/minute traditional)

### Phase 3: Ralph Loop

Named after Karpathy's approach - continuous evolution:

```
Each cycle (every 5 minutes):
  1. Score all 500 new strategies
  2. Keep top 100 (20%)
  3. Discard bottom 400 (80%)
  4. Mutate the top 100 to create 400 new strategies
  5. Add back to pool, repeat
```

**Result**: Elite strategies improve over time as the pool evolves

### Phase 4: Live Deployment

Top strategies trade with real capital:

```
For each deployed strategy:
  1. Check for entry signals every 60 seconds
  2. Execute entry order if conditions met
  3. Monitor position with stop loss / take profit
  4. Close position on exit signal or stops
  5. Track performance vs backtest
  6. Flag if performance drifts >15%
  7. Retire underperformers
```

### Phase 5: Advanced AI

Optimize and validate strategies:

```
Transformer Network:
  - Trained on elite strategies
  - Predicts optimal parameters for market conditions
  - Adapts to bull/bear/sideways markets

Market Regime Detection:
  - Identifies 6 market regimes
  - Recommends strategy types per regime
  - Flags pause conditions

Stress Testing:
  - Tests strategies in 8 scenarios
  - Flash crashes, high volatility, liquidity crises
  - Calculates robustness score

LLM Council:
  - Risk Analyst voter
  - Momentum Expert voter
  - Value Analyzer voter
  - Correlation Expert voter
  - Final voting consensus
```

### MiroFish Integration

Multi-agent market simulation:

```
7 Agent Types Simulate Markets:
  1. Trend Followers (follow price momentum)
  2. Mean Reversion (buy low, sell high)
  3. Momentum Chasers (ride trends)
  4. Arbitrageurs (exploit price differences)
  5. Market Makers (provide liquidity)
  6. Noise Traders (random trading)
  7. Institutional Players (large orders)

Validation:
  - Tests strategy against realistic agent behavior
  - Particle Swarm Optimization for parameter tuning
  - Ant Colony Optimization for learning
  - Scenario stress testing

Result:
  - Only strategies validated in multi-agent sim get deployed
  - Higher confidence in real trading
```

---

## Performance Monitoring

### Key Metrics to Track

**Backtesting Metrics:**
- Win Rate: % of profitable trades (target ≥ 40%)
- Profit Factor: Gross profit / Gross loss (target ≥ 2.0)
- Sharpe Ratio: Risk-adjusted returns (target ≥ 1.0)
- Max Drawdown: Worst peak-to-trough (target ≤ 30%)

**Live Trading Metrics:**
- P&L: Total profit/loss in USDT
- Win Rate: % of winning trades
- Profit Factor: Real trading effectiveness
- Health Score: Overall strategy performance (0-100)

**Generation Metrics:**
- Generation Pass Rate: % of strategies meeting criteria
- Elite Count: Number of elite strategies
- Generation Speed: Strategies per minute
- Mutation Effectiveness: Quality improvement

### Monitoring Dashboard

Access live metrics:

```bash
# In TUI, press D for Dashboard to see:
- System Status Panel
- Open Positions Monitor
- Top Strategies Performance

# In TUI, press M for Monitoring:
- Ralph Loop Generation Progress
- Real-Time Alerts Log
- Strategy Evolution Tracking
```

### Via API

```bash
# Get comprehensive metrics
curl http://localhost:8001/api/v1/system/metrics

# Response includes:
{
  "active_strategies": 5,
  "total_open_positions": 3,
  "total_live_profit": 1250.50,
  "win_rate": 0.45,
  "generation_pass_rate": 0.22,
  "avg_strategy_score": 67.5
}
```

---

## Troubleshooting

### Common Issues & Solutions

#### Database Connection Failed
```
Error: could not translate host name "postgres" to address
```
**Solutions:**
1. Ensure PostgreSQL is running: `docker ps | grep postgres`
2. Check DATABASE_URL in .env is correct
3. Verify database credentials
4. Restart PostgreSQL: `docker restart postgres`

#### No Data Available
```
Error: No data found for BTC/USDT on yfinance
```
**Solutions:**
1. Check internet connection
2. yfinance may be rate-limited; wait and retry
3. Try different pair (ETH/USDT, SOL/USDT)
4. Use CCXT data source instead if available

#### Redis Connection Refused
```
Error: Connection refused on port 6379
```
**Solutions:**
1. Start Redis: `docker run -d --name redis -p 6379:6379 redis:7`
2. Verify Redis is running: `redis-cli ping` (should return PONG)
3. Check REDIS_URL in .env

#### TUI Won't Start
```
Error: Textual not found or display issues
```
**Solutions:**
```bash
# Reinstall dependencies
pip install textual click rich --break-system-packages --force-reinstall

# Try directly
python src/tui/app.py

# Ensure Unicode support
export LANG=en_US.UTF-8

# Use larger terminal window
```

#### API Server Won't Start
```
Error: Address already in use (port 8001)
```
**Solutions:**
```bash
# Find what's using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8002
```

#### Out of Memory During Backtesting
```
Error: MemoryError during backtesting
```
**Solutions:**
1. Reduce STRATEGIES_PER_GENERATION (e.g., from 500 to 250)
2. Use fewer timeframes
3. Reduce backtesting period from 365 to 180 days
4. Increase server RAM or add swap space

#### API Endpoints Not Responding
```
Error: Connection timeout on http://localhost:8001/api/v1/...
```
**Solutions:**
1. Check API is running: `curl http://localhost:8001/health`
2. View logs: `docker-compose logs api`
3. Restart API: `docker-compose restart api`
4. Check network connectivity

---

## Advanced Features

### Custom Strategy Templates

Create strategies with specific indicators:

```bash
# SMA Crossover Strategy
{
  "name": "SMA Crossover",
  "indicators": {
    "fast_sma": 20,
    "slow_sma": 200,
    "rsi_period": 14
  }
}

# Bollinger Bands Strategy
{
  "name": "Bollinger Bands",
  "indicators": {
    "bb_period": 20,
    "bb_std_dev": 2,
    "rsi_threshold": 30
  }
}

# Multi-Indicator Strategy
{
  "name": "Combo",
  "indicators": {
    "sma_fast": 12,
    "sma_slow": 26,
    "rsi_buy": 30,
    "rsi_sell": 70,
    "bb_period": 20,
    "macd_fast": 12,
    "macd_slow": 26
  }
}
```

### Multi-Exchange Trading

Trade across multiple exchanges simultaneously:

```bash
# In .env
LIVE_EXCHANGE=binance
# Also supports: coinbase, kraken, blofin, huobi, okx, bybit, etc.

# Run multiple traders
docker-compose exec api python cli.py trade --exchange binance
docker-compose exec api python cli.py trade --exchange coinbase
docker-compose exec api python cli.py trade --exchange kraken
```

### Backtesting Configuration

Adjust backtesting parameters:

```bash
# Different time periods
BACKTEST_YEAR_RANGE=180        # 6 months
BACKTEST_YEAR_RANGE=90         # 3 months

# Different pairs
BACKTEST_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT

# Different timeframes
BACKTEST_TIMEFRAMES=15m,1h,4h,1d
```

### Performance Optimization

Speed up the system:

```bash
# Reduce generation frequency (trades less often)
GENERATION_INTERVAL=600        # Generate every 10 minutes instead of 5

# Reduce strategy count per generation
STRATEGIES_PER_GENERATION=250   # Generate 250 instead of 500

# Use smaller backtest period
BACKTEST_YEAR_RANGE=180         # 6 months instead of 1 year

# Cache more aggressively
REDIS_CACHE_TTL=3600           # 1 hour cache
```

### Custom Alerts

Set up notifications:

```bash
# Email alerts (Gmail)
ALERT_EMAIL=your_email@gmail.com
ALERT_SMTP_SERVER=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_PASSWORD=your_app_password

# Telegram alerts
ALERT_TELEGRAM_BOT_TOKEN=your_bot_token
ALERT_TELEGRAM_CHAT_ID=your_chat_id

# Alert types
ALERT_ON_ENTRY=true             # Alert on trade entry
ALERT_ON_EXIT=true              # Alert on trade exit
ALERT_ON_WIN=true               # Alert on winning trade
ALERT_ON_LOSS=true              # Alert on losing trade
ALERT_ON_ERROR=true             # Alert on errors
```

---

## Support & Contributing

### Getting Help

1. **Documentation**: Read the full guides in `/docs` folder
   - PHASE_3_RALPH_LOOP.md
   - PHASE_4_LIVE_TRADING.md
   - PHASE_5_ADVANCED_AI.md
   - MIROFISH_INTEGRATION.md
   - TUI_GUIDE.md

2. **API Documentation**: http://localhost:8001/docs (Swagger UI)

3. **Logs**: Check logs for detailed error information
   ```bash
   # Docker logs
   docker-compose logs api

   # Local logs
   tail -f logs/grindstone_apex.log
   ```

4. **GitHub Issues**: Report bugs and request features

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Make changes and test thoroughly
4. Commit with clear messages
5. Push to branch and create Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8

# Run tests
pytest tests/

# Format code
black src/

# Lint
flake8 src/

# Run in debug mode
LOG_LEVEL=DEBUG python cli.py generate
```

---

## Performance Targets

### Daily Goals

- **Strategies Generated**: 5,000+ (500 × ~10 cycles)
- **Pass Rate**: 20%+ (1,000 elite strategies)
- **Backtest Speed**: 100+ strategies/minute
- **Live P&L**: $5-10 per day (scaling up)

### Weekly Goals

- **Strategies Deployed**: 5-10 elite strategies
- **Weekly P&L**: $5,000-10,000 (target)
- **Win Rate**: 40%+ across all trades
- **Profit Factor**: 2.0+ (gross profit / loss)

### Monthly Goals

- **Strategy Evolution**: Continuous improvement visible
- **Monthly P&L**: $20,000-40,000 (target)
- **Deployed Strategies**: 10-20 active strategies
- **Live Win Rate**: Maintain 40%+

---

## Configuration Examples

### Conservative (Low Risk)

```bash
POSITION_SIZE_PERCENT=0.1       # Risk 0.1% per trade
MAX_POSITIONS=1                 # One trade at a time
STOP_LOSS_ATR_MULTIPLIER=5      # Wider stops
TAKE_PROFIT_PERCENT=0.10        # Lower targets
TARGET_WIN_RATE=0.50            # Higher quality
MIN_STRATEGY_SCORE=70
```

### Aggressive (High Risk)

```bash
POSITION_SIZE_PERCENT=1.0       # Risk 1% per trade
MAX_POSITIONS=10                # Many concurrent trades
STOP_LOSS_ATR_MULTIPLIER=2      # Tight stops
TAKE_PROFIT_PERCENT=0.50        # High targets
TARGET_WIN_RATE=0.35            # Accept lower quality
MIN_STRATEGY_SCORE=40
```

### Balanced (Recommended)

```bash
POSITION_SIZE_PERCENT=0.5       # Risk 0.5% per trade
MAX_POSITIONS=5                 # Several trades
STOP_LOSS_ATR_MULTIPLIER=3.5    # Standard stops
TAKE_PROFIT_PERCENT=0.20        # Realistic targets
TARGET_WIN_RATE=0.40            # Reasonable quality
MIN_STRATEGY_SCORE=60
```

---

## Next Steps

1. **Complete Setup**: Follow the step-by-step guide above
2. **Paper Trade**: Run with `SANDBOX_MODE=true` first
3. **Monitor Dashboard**: Use TUI to watch the bot work
4. **Start Small**: Begin with 0.01 BTC or small USDT amount
5. **Scale Gradually**: Increase position size as confidence grows
6. **Review Regularly**: Check P&L and strategy performance daily
7. **Optimize**: Adjust parameters based on results

---

## FAQ

**Q: How long does strategy generation take?**
A: ~1-2 seconds per strategy, so 500 strategies = 500-1000 seconds (~10-17 minutes)

**Q: Can I trade multiple pairs?**
A: Yes! Set `PAIRS_TO_TRADE=BTC/USDT,ETH/USDT,SOL/USDT` in .env

**Q: What's the minimum starting capital?**
A: Recommended $1,000-5,000 to properly test. Start with paper trading first.

**Q: How often do strategies update?**
A: New generation every 5 minutes (configurable). Live trading checks every 60 seconds.

**Q: Can I use multiple exchanges?**
A: Yes, through CCXT. Supports 100+ exchanges (Binance, Coinbase, Kraken, etc.)

**Q: What's the best time to start?**
A: 24/5 crypto markets - anytime works. Avoid major economic announcements.

**Q: How do I monitor performance?**
A: Use the TUI dashboard, API endpoints, or connect to databases directly.

---

## ⚠️ Risk Disclaimer

**IMPORTANT: This is experimental software for research purposes.**

- 🚨 Cryptocurrency trading involves significant risk
- 💰 You can lose your entire investment
- 📉 Past performance does not guarantee future results
- 🧪 This system is experimental - use small amounts first
- 📋 Always paper trade before live trading
- 🔒 Keep API keys secure and use IP whitelisting
- 📞 Monitor your account regularly
- 🛑 Set strict stop losses and position sizing
- 🎓 Understand trading before risking capital

**Start with 1-5% of your capital in paper trading mode (`SANDBOX_MODE=true`) for at least 1-2 weeks before going live with real capital.**

---

## Support

For issues, questions, or suggestions:

- 📖 Read the comprehensive guides in the `/docs` folder
- 🐛 Report bugs on GitHub Issues
- 💬 Join discussions on GitHub Discussions
- 📧 Contact support@grindstoneapex.com
- 🚀 Follow updates on [@grindstone_apex](https://twitter.com/grindstone_apex)

---

**Built with ❤️ for the trading community**

*Grindstone Apex - Where strategies evolve. Where profits grow. Where trading meets AI.*

🚀 **Happy trading!**
