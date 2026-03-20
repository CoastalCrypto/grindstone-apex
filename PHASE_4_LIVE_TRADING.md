# Phase 4: Live Trading - Real-Time Strategy Deployment

## 🎯 Overview

Phase 4 transforms elite strategies from backtesting into **live trading production**. It manages:

1. **Real Exchange Integration** - CCXT connector to Blofin, Coinbase, Binance, Kraken
2. **Position Lifecycle** - Entry execution, stop/profit management, exit
3. **Risk Management** - ATR stops, breakeven protection, position sizing
4. **Performance Monitoring** - Live vs backtest drift detection, strategy health scoring
5. **Alert System** - Email and Telegram notifications for all events

## ✅ What's Been Built

### Core Components

**ExchangeConnector** (`src/live_trading/exchange_connector.py`)
- Multi-exchange abstraction (CCXT)
- Account balance checking
- Real-time price feeds
- Order placement (limit/market/stop-loss)
- Order management and cancellation
- Sandbox mode support for testing
- Comprehensive error handling

**PositionManager** (`src/live_trading/position_manager.py`)
- Position opening with entry order execution
- Stop-loss and take-profit orders
- Real-time position monitoring
- Breakeven stop updates
- Position closing with P&L tracking
- Position status with unrealized profit/loss
- Position history and statistics

**PerformanceMonitor** (`src/live_trading/performance_monitor.py`)
- Live metrics calculation (win rate, profit factor, best/worst trades)
- Backtest vs live drift detection (default 15% threshold)
- Strategy health scoring (0-100 scale)
- Underperformance detection and auto-retirement
- Performance report generation

**LiveTradingService** (`src/services/live_trader_service.py`)
- Continuous monitoring loop (configurable interval, default 60s)
- Active strategy tracking from database
- Signal generation from current candles
- Entry order execution with position sizing
- Exit management (stop/profit/signal)
- Real-time position monitoring
- Strategy health checks
- System metrics tracking
- Graceful error handling and recovery

**AlertSystem** (`src/alerts/alert_system.py`)
- Email alerts (SMTP)
- Telegram notifications
- Alert types: ENTRY, EXIT, WIN, LOSS, ERROR, ALERT
- Formatted messages with emojis
- Startup/shutdown notifications
- Daily summary generation

### API Endpoints (Phase 4)

**GET /api/v1/live-trading/positions/open**
- Get active trading positions with current unrealized P&L

**GET /api/v1/live-trading/positions/closed**
- Get historical closed positions with filtering

**GET /api/v1/live-trading/performance/{strategy_id}**
- Live performance metrics (trades, win rate, P&L)

**GET /api/v1/live-trading/performance/{strategy_id}/backtest-comparison**
- Drift analysis comparing backtest vs live

**GET /api/v1/live-trading/health/{strategy_id}**
- Strategy health score (0-100) with status

**POST /api/v1/live-trading/deploy/{strategy_id}**
- Deploy strategy to live trading

**POST /api/v1/live-trading/retire/{strategy_id}**
- Retire strategy from live trading

**GET /api/v1/live-trading/summary**
- Overall live trading summary (active strategies, profit, win rate)

## 🚀 How to Use

### Setup Configuration

Update `.env` with exchange credentials:

```bash
# Live trading settings
LIVE_EXCHANGE=blofin
LIVE_API_KEY=your_api_key
LIVE_API_SECRET=your_api_secret
SANDBOX_MODE=true  # Start in sandbox for testing

# Alert settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=your_email@gmail.com

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### Step 1: Deploy Elite Strategy

```bash
# Deploy strategy to live trading
curl -X POST http://localhost:8001/api/v1/live-trading/deploy/strat_elite_123
```

### Step 2: Start Live Trading Service

**Option A: Docker**
```bash
docker-compose up -d live_trader

# Check logs
docker-compose logs -f live_trader
```

**Option B: Python**
```python
from src.services.live_trader_service import LiveTradingService

service = LiveTradingService()
service.run_continuous(check_interval=60)  # Check every 60 seconds
```

### Step 3: Monitor Live Trading

```bash
# Check open positions
curl http://localhost:8001/api/v1/live-trading/positions/open

# Get performance
curl http://localhost:8001/api/v1/live-trading/performance/strat_elite_123

# Check drift vs backtest
curl http://localhost:8001/api/v1/live-trading/performance/strat_elite_123/backtest-comparison

# Get strategy health
curl http://localhost:8001/api/v1/live-trading/health/strat_elite_123

# Summary
curl http://localhost:8001/api/v1/live-trading/summary
```

## 📊 Monitoring & Alerts

### Alert Types

- **📈 ENTRY**: New position opened
  - Includes size, entry price, stop loss, target

- **📉 EXIT**: Position closed
  - Shows exit price, P&L, duration

- **✅ WIN**: Profitable exit
  - P&L and win percentage

- **❌ LOSS**: Loss exit
  - Loss amount and percentage

- **🔴 ERROR**: System errors
  - Error details and recovery action

- **⚠️ ALERT**: Strategic alerts
  - Strategy health changes, retirement, summaries

### Real-Time Notifications

Receive alerts on multiple channels:
1. **Email** - Full formatted alerts
2. **Telegram** - Quick mobile notifications

### Daily Summary

Automatic daily summary includes:
- Number of trades
- Win/loss breakdown
- Total P&L
- Best/worst trades
- Account balance update

## 🔍 Performance Monitoring

### Health Score (0-100)

**Components:**
- Win Rate: 40 points (higher is better)
- Profit Factor: 40 points (ratio of wins to losses)
- Deployment Status: 20 points (extra for active trading)

**Status Levels:**
- 🟢 **Healthy** (>60): Strategy performing well
- 🟡 **Needs Attention** (30-60): Monitor closely
- 🔴 **Poor** (<30): Consider retirement

### Drift Detection

Compares live performance vs backtest expectations:

```
Backtest: 55% win rate, 25% profit
Live:     50% win rate, 20% profit
Drift:    5% win rate, 5% profit
Threshold: 15% (default)
Status:   ✓ ACCEPTABLE
```

If drift exceeds threshold:
- Strategy marked for review
- Alert sent to user
- May trigger auto-retirement if conditions met

### Auto-Retirement Criteria

Strategy automatically retired if:
- **AND**: Losing money + Win rate < 30%
- **OR**: Multiple consecutive losing positions without recovery
- **OR**: Health score drops below 20

## 💰 Position Sizing

Three modes available:

### Fixed Amount
```python
{
    "sizing_mode": "fixed_amount",
    "fixed_amount": 100  # $100 per trade
}
```

### Risk Percentage
```python
{
    "sizing_mode": "risk_percentage",
    "risk_percentage": 2  # 2% of account risk
}
```

### ATR-Based
```python
{
    "sizing_mode": "atr_based",
    "atr_multiplier": 2  # Stop loss = entry - 2*ATR
}
```

## 🛡️ Risk Management

### Stop Loss
- **ATR-Based**: `entry_price - (ATR * multiplier)`
- **Percentage**: `entry_price * (1 - risk_pct)`
- **Fixed**: Fixed dollar amount

### Take Profit
- **Percentage**: `entry_price * (1 + profit_target)`
- **Ratio**: `entry_price * (1 + 2 * stop_distance)`
- **Fixed**: Fixed price level

### Breakeven Protection
- Triggered when profit reaches 1% of position
- Move stop loss to entry price - 1% buffer
- Locks in near-breakeven trades
- Removes risk on trending positions

### Maximum Concurrent Positions
```python
{
    "max_concurrent": 1,  # One open position at a time
    "max_daily_loss": -500,  # Stop trading if lose $500/day
    "max_consecutive_losses": 3  # Pause after 3 losses
}
```

## 📈 Example Trading Session

```
10:00 AM - Service starts
├─ Load active strategies (5 deployed)
├─ Connect to Blofin exchange
└─ Begin 60-second monitoring cycle

10:01 AM - Signal detected on BTC/USDT
├─ 📈 Entry signal (SMA crossover)
├─ Account balance: $10,000
├─ Position size: 0.05 BTC (2% risk)
├─ Entry price: $42,000
├─ Stop loss: $41,000 (1 ATR)
├─ Target: $43,000 (2% profit)
└─ 📬 Email alert sent

10:35 AM - Position in profit
├─ Current price: $42,500
├─ Unrealized P&L: +$25
├─ Update breakeven stop

11:00 AM - Take profit hit
├─ Exit price: $43,000
├─ Exit reason: take_profit
├─ Realized P&L: +$50
├─ Trade duration: 59 minutes
└─ ✅ Win alert sent

End of Day - Daily Summary
├─ 5 total trades
├─ 3 wins, 2 losses
├─ 60% win rate
├─ +$125 total profit
└─ 📊 Summary email sent
```

## 🔧 Configuration

In `.env`:

```bash
# Live trading interval (seconds between signal checks)
LIVE_TRADING_INTERVAL=60

# Position sizing defaults
DEFAULT_POSITION_SIZING_MODE=risk_percentage
DEFAULT_RISK_PERCENTAGE=2

# Risk management defaults
DEFAULT_ATR_MULTIPLIER=3
DEFAULT_PROFIT_TARGET=0.02
DEFAULT_MAX_CONSECUTIVE_LOSSES=5

# Drift monitoring
PERFORMANCE_DRIFT_THRESHOLD=0.15

# Alerts
ALERT_EMAIL_ENABLED=true
ALERT_TELEGRAM_ENABLED=true

# Sandbox for testing
SANDBOX_MODE=true
```

## ⚠️ Best Practices

1. **Start in Sandbox**: Always test with `SANDBOX_MODE=true` first
2. **Monitor Closely**: Check alerts frequently during first week
3. **Position Sizing**: Be conservative initially (1-2% risk per trade)
4. **Gradual Scale**: Increase size as you gain confidence
5. **Daily Reviews**: Check performance reports daily
6. **Drift Monitoring**: Watch for backtest vs live divergence
7. **Time Zones**: Ensure server time is synchronized (UTC)
8. **Network**: Maintain stable internet connection
9. **Backup**: Keep API keys secure and backed up
10. **Emergency Stop**: Have manual exit plan if needed

## 🚨 Troubleshooting

### No Trades Executing

**Check:**
1. Strategy deployed? `curl http://localhost:8001/api/v1/live-trading/deploy/{id}`
2. Service running? `docker-compose logs live_trader`
3. Exchange connection? Check API credentials in .env
4. Signals generating? Check candle data loading

### Positions Not Closing

**Check:**
1. Take profit price correct?
2. Stop loss in right direction?
3. Exchange connectivity?
4. Order placement permissions in API key?

### Alerts Not Sending

**Check:**
1. SMTP configured correctly?
2. Gmail: Need app password (not account password)
3. Telegram: Valid bot token and chat ID?
4. Network can reach SMTP/Telegram servers?

### High Slippage

**Solutions:**
1. Use limit orders instead of market
2. Reduce position size
3. Check market volatility (use market regime detector)
4. Avoid trading during low liquidity times

## 📝 Next Steps

1. Configure exchange credentials in `.env`
2. Test in sandbox mode first
3. Deploy elite strategies to live
4. Monitor initial trading closely
5. Use performance monitoring to improve
6. Proceed to Phase 5 for advanced AI features

---

**Phase 4 Live Trading is complete and ready for production deployment!** 🚀
