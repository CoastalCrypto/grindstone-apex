# Getting Started Checklist

Complete these steps to get Grindstone Apex running.

## ✅ Installation (15 minutes)

- [ ] **Clone repository**
  ```bash
  git clone https://github.com/CoastalCrypto/grindstone-apex.git
  cd grindstone-apex
  ```

- [ ] **Create .env file**
  ```bash
  cp .env.example .env
  ```

- [ ] **Edit .env with your settings**
  - [ ] Set DATABASE_URL (if not using Docker)
  - [ ] Set REDIS_URL (if not using Docker)
  - [ ] Set EXCHANGE_TYPE (coinbase, binance, etc.)
  - [ ] Set EXCHANGE_API_KEY and EXCHANGE_SECRET (optional, for live trading)

- [ ] **Choose deployment method**
  - [ ] **Option A: Docker (Recommended)**
    - [ ] Install Docker & Docker Compose
    - [ ] Run: `docker-compose up -d`
    - [ ] Wait for services to start (~30s)
  - [ ] **Option B: Local Development**
    - [ ] Create venv: `python -m venv venv && source venv/bin/activate`
    - [ ] Install deps: `pip install -r requirements.txt`
    - [ ] Start Postgres: `docker run -p 5432:5432 -e POSTGRES_DB=grindstone_apex -e POSTGRES_USER=trader -e POSTGRES_PASSWORD=password postgres:15`
    - [ ] Start Redis: `docker run -p 6379:6379 redis:7`
    - [ ] Start API: `uvicorn main:app --reload`

## ✅ Verification (5 minutes)

- [ ] **Check API is running**
  ```bash
  curl http://localhost:8001/health
  # Should return: {"status": "healthy", ...}
  ```

- [ ] **Visit API documentation**
  - [ ] Open browser: `http://localhost:8001/docs`
  - [ ] See interactive API docs

- [ ] **Run examples (optional, but recommended)**
  ```bash
  python examples/quick_start.py
  # Should show 5 completed examples
  ```

## ✅ First Test (10 minutes)

- [ ] **Generate strategies**
  ```bash
  curl -X POST http://localhost:8001/api/v1/generate/initial \
    -H "Content-Type: application/json" \
    -d '{"pair": "BTC/USDT", "count": 5}'
  ```

- [ ] **Backtest one strategy**
  ```bash
  curl -X POST http://localhost:8001/api/v1/backtest/single \
    -H "Content-Type: application/json" \
    -d '{
      "pair": "BTC/USDT",
      "indicators": {"sma_fast": 20, "sma_slow": 200, "rsi_threshold_buy": 30, "rsi_threshold_sell": 70, "bollinger_period": 20},
      "position_sizing": {"size_type": "percent_of_balance", "size_amount": 0.5},
      "risk_management": {"stop_loss_atr": 3.5, "take_profit_percent": 0.20, "breakeven_on_profit": true, "max_drawdown_limit": 0.30}
    }'
  ```

- [ ] **Check results**
  - [ ] Should show metrics: profit, win_rate, sharpe, drawdown
  - [ ] Should show composite_score and meets_criteria

## ✅ Configuration (Optional)

- [ ] **Set up exchange API (for live trading)**
  - [ ] [ ] Go to Coinbase/Binance/Kraken account
  - [ ] [ ] Create API key with trade permissions
  - [ ] [ ] Add to .env: EXCHANGE_API_KEY and EXCHANGE_SECRET
  - [ ] [ ] Set EXCHANGE_SANDBOX=true initially
  - [ ] [ ] Test with paper trading first

- [ ] **Configure strategy generation**
  - [ ] Edit .env:
    - [ ] STRATEGIES_PER_GENERATION (default: 500)
    - [ ] ELITE_THRESHOLD (default: 0.20 = top 20%)
    - [ ] MUTATION_RATE (default: 0.15 = 15%)
    - [ ] TARGET_WIN_RATE (default: 0.40 = 40%)

- [ ] **Configure risk management**
  - [ ] Edit .env:
    - [ ] POSITION_SIZE_AMOUNT (default: 0.5 = 50% of account)
    - [ ] STOP_LOSS_ATR_MULTIPLIER (default: 3.5)
    - [ ] TAKE_PROFIT_PERCENT (default: 0.20 = 20%)
    - [ ] MAX_DRAWDOWN_LIMIT (default: 0.30 = 30%)

## ✅ Understanding the System

- [ ] **Read documentation**
  - [ ] Read README.md (5 min) - overview and features
  - [ ] Read SETUP.md (5 min) - detailed installation
  - [ ] Read PROJECT_SUMMARY.md (5 min) - what's been built
  - [ ] View Technical Spec (10 min) - architecture details

- [ ] **Understand the workflow**
  - [ ] Generate strategies (random or evolved)
  - [ ] Backtest against 1 year of history
  - [ ] Ralph Loop: Keep winners (top 20%), discard losers (bottom 80%)
  - [ ] Deploy top performers to live trading
  - [ ] Monitor live performance
  - [ ] Retire when unprofitable, generate new ones

- [ ] **Review code structure**
  - [ ] src/backtesting/ - backtesting engine
  - [ ] src/strategy_generation/ - genetic algorithm
  - [ ] src/api/routes.py - API endpoints
  - [ ] src/database.py - data models

## ✅ Start Using

### Option 1: API (Recommended for continuous operation)

- [ ] **Start continuous generation loop**
  1. Generate 500 random strategies
  2. Backtest all (async via API)
  3. Ralph Loop: keep top 20%
  4. Repeat step 1 with evolved strategies

- [ ] **Via curl/Python/your language:**
  ```bash
  # See README.md API section for examples
  ```

### Option 2: Examples (Good for learning)

- [ ] **Run quick_start.py examples**
  ```bash
  python examples/quick_start.py
  ```

### Option 3: Manual Testing

- [ ] **Use the Swagger UI**
  1. Visit `http://localhost:8001/docs`
  2. Click on endpoints to test
  3. Enter parameters and see results

## ✅ Production Setup (When Ready)

- [ ] **Enable live trading** (ONLY after testing!)
  - [ ] Set LIVE_TRADING_ENABLED=true
  - [ ] Set EXCHANGE_SANDBOX=false
  - [ ] Use SMALL position sizes initially
  - [ ] Monitor CLOSELY for first 2 weeks

- [ ] **Set up monitoring**
  - [ ] Check system metrics regularly: `/api/v1/system/metrics`
  - [ ] Monitor open positions: `/api/v1/live-trading/open-positions`
  - [ ] Review closed trades: `/api/v1/live-trading/closed-trades`
  - [ ] Check elite strategies: `/api/v1/ralph-loop/elite`

- [ ] **Set up alerts**
  - [ ] Telegram alerts (configure in code)
  - [ ] Email alerts (configure in code)
  - [ ] Performance drift detection

- [ ] **Backup strategy**
  - [ ] Regular database backups
  - [ ] Save winning strategies
  - [ ] Log all trades
  - [ ] Document what works

## ✅ Troubleshooting

- [ ] **Can't connect to database**
  - [ ] Check DATABASE_URL in .env
  - [ ] Verify PostgreSQL is running: `docker ps`
  - [ ] Try restarting: `docker-compose restart`

- [ ] **Can't load historical data**
  - [ ] Check internet connection
  - [ ] Try different pair (yfinance may be rate-limited)
  - [ ] Check REDIS_URL

- [ ] **API not responding**
  - [ ] Check if running: `curl http://localhost:8001/health`
  - [ ] Check logs: `docker-compose logs api`
  - [ ] Verify port 8001 is free

- [ ] **Backtest too slow**
  - [ ] Increase WORKERS in .env
  - [ ] Use larger timeframe (60m instead of 15m)
  - [ ] Reduce date range (6 months instead of 1 year)

## ✅ Next: Advanced Topics (Optional)

- [ ] **Fine-tune strategy generation**
  - [ ] Adjust mutation rates
  - [ ] Add custom indicators
  - [ ] Implement strategy constraints

- [ ] **Integrate transformer model**
  - [ ] Fine-tune on your winning strategies
  - [ ] Use ML to predict parameters
  - [ ] See src/strategy_generation/transformer_predictor.py

- [ ] **Implement autoresearch**
  - [ ] Automatically document what works
  - [ ] Generate insights
  - [ ] Learn from winners

- [ ] **Multi-pair strategies**
  - [ ] Test across BTC, ETH, other assets
  - [ ] Find pairs with best strategies
  - [ ] Correlate strategies

## ✅ Success Criteria

You'll know it's working when:

- ✅ API responds to health check
- ✅ Can generate strategies via API
- ✅ Can backtest strategies successfully
- ✅ See meaningful metrics (profit%, win_rate, sharpe)
- ✅ Elite strategies have scores > 60/100
- ✅ Can see generated strategies in database

## 🎯 Final Steps

1. **Complete setup** (all checkboxes above) ✅
2. **Run examples** to understand system
3. **Generate 100 strategies** and backtest
4. **Identify top performers** (Ralph Loop)
5. **Deploy to paper trading** (paper mode on exchange)
6. **Monitor for 1 week** to ensure consistency
7. **Deploy to live trading** (small amounts!) if confident
8. **Monitor continuously** and adapt

---

**Estimated total time: 30-45 minutes for full setup**

You're ready to start! 🚀

Questions? Check:
- README.md for overview
- SETUP.md for installation help
- /docs for API documentation
- examples/quick_start.py for code examples
