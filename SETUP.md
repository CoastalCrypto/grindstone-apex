# Grindstone Apex: Setup Guide

## Prerequisites

- Python 3.11+ installed
- Git installed
- Docker & Docker Compose installed (optional)
- Internet connection for downloading data

## Local Setup (Development)

### 1. Clone Repository

```bash
git clone https://github.com/CoastalCrypto/grindstone-apex.git
cd grindstone-apex
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database (keep PostgreSQL defaults for Docker)
DATABASE_URL=postgresql://trader:grindstone_pass_123@localhost:5432/grindstone_apex

# Redis (keep default for Docker)
REDIS_URL=redis://localhost:6379/0

# Your exchange API keys (get from Coinbase, Binance, etc.)
EXCHANGE_TYPE=coinbase
EXCHANGE_API_KEY=your_api_key_here
EXCHANGE_SECRET=your_secret_here
EXCHANGE_SANDBOX=true

# Strategy settings (keep defaults for first run)
TARGET_WIN_RATE=0.40
TARGET_PROFIT_PCT=0.20

# Initial account size (start small for testing)
INITIAL_ACCOUNT_BALANCE=10000.0

# Don't enable live trading until you're confident
LIVE_TRADING_ENABLED=false
```

### 5. Start Infrastructure Services

Open a terminal and start PostgreSQL:

```bash
docker run --name grindstone-postgres \
  -e POSTGRES_DB=grindstone_apex \
  -e POSTGRES_USER=trader \
  -e POSTGRES_PASSWORD=grindstone_pass_123 \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15
```

Open another terminal and start Redis:

```bash
docker run --name grindstone-redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7
```

### 6. Start FastAPI Application

```bash
uvicorn main:app --reload --port 8001
```

The API should now be running at `http://localhost:8001`

### 7. Verify Installation

```bash
# Check health
curl http://localhost:8001/health

# Check API docs
open http://localhost:8001/docs
```

---

## Docker Setup (Production/Recommended)

### 1. Clone Repository

```bash
git clone https://github.com/CoastalCrypto/grindstone-apex.git
cd grindstone-apex
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

### 3. Start All Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- Redis cache
- FastAPI backend (port 8001)
- Strategy generator service
- Backtester service
- Live trader service

### 4. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f strategy_generator
```

### 5. Stop Services

```bash
docker-compose down
```

---

## First Run: Test Your Setup

### 1. List Available Strategies

```bash
curl http://localhost:8001/api/v1/strategies
```

Expected response: Empty list (no strategies yet)

### 2. Generate Initial Population

```bash
curl -X POST http://localhost:8001/api/v1/generate/initial \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTC/USDT",
    "count": 10
  }'
```

You should get back 10 random strategies.

### 3. Backtest a Single Strategy

```bash
curl -X POST http://localhost:8001/api/v1/backtest/single \
  -H "Content-Type: application/json" \
  -d '{
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
      "breakeven_on_profit": true,
      "max_drawdown_limit": 0.30
    },
    "timeframes": [15, 60, 240]
  }'
```

This will backtest against 1 year of BTC/USDT data and return metrics.

### 4. Check System Health

```bash
curl http://localhost:8001/api/v1/system/metrics
```

---

## Troubleshooting

### Issue: "Connection refused" on PostgreSQL

**Cause**: PostgreSQL not running

**Solution**:
```bash
# Check if container is running
docker ps | grep postgres

# Restart if needed
docker restart grindstone-postgres
```

### Issue: "No data found for BTC/USDT"

**Cause**: yfinance data fetch failed (rate limit or network)

**Solution**:
- Try different pair (e.g., ETH/USDT)
- Wait 60 seconds and retry
- Check internet connection

### Issue: "OSError: [Errno 98] Address already in use"

**Cause**: Port 8001 already in use

**Solution**:
```bash
# Start on different port
uvicorn main:app --port 8002
```

### Issue: Database tables not created

**Solution**:
```python
# Run in Python shell
from src.database import init_db
init_db()
```

---

## Next Steps

1. **Learn the API**: Visit `http://localhost:8001/docs` for interactive API docs
2. **Generate Strategies**: Create initial population (100-500 strategies)
3. **Backtest**: Test strategies against 1 year of historical data
4. **Monitor**: Check elite strategies with `/api/v1/ralph-loop/elite`
5. **Configure Live Trading**: Set up exchange API keys and enable carefully
6. **Monitor Results**: Use system metrics and live trade endpoints

---

## Performance Tips

### Speed Up Backtesting
- Use VectorBT (already default)
- Increase workers: `WORKERS=8` in .env
- Use 15-minute candles instead of smaller timeframes

### Generate Better Strategies
- Start with 100 random strategies
- Backtest all of them
- Keep top 20% as elite
- Mutate elite to create next generation
- Repeat until you have consistent winners

### Reduce False Positives
- Increase `TARGET_WIN_RATE` to 0.50
- Increase `TARGET_SHARPE_RATIO` to 1.5
- Add more filters in strategy generation

---

## Production Deployment

For production use:

1. **Use strong passwords** for PostgreSQL and Redis
2. **Enable HTTPS** for API
3. **Set `ENV=production`** in .env
4. **Disable `EXCHANGE_SANDBOX`** when ready for real trading
5. **Set up monitoring** (prometheus, grafana)
6. **Set up alerts** (email, Telegram)
7. **Use small position sizes** initially
8. **Monitor closely** for first 2 weeks

---

## Getting Help

- **API Docs**: `http://localhost:8001/docs`
- **Logs**: Check docker-compose logs or console output
- **Issues**: GitHub Issues
- **Telegram**: @grindstone_apex

---

**You're ready to go! Start generating and testing strategies.** 🚀
