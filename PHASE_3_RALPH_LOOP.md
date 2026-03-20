# Phase 3: Ralph Loop Implementation

## 🎯 Overview

The **Ralph Loop** is the continuous selection and evolution mechanism that keeps your trading bot improving automatically. It:

1. **Generates** hundreds of strategies per cycle
2. **Backtests** them against 1 year of historical data
3. **Evaluates** performance using strict criteria
4. **Keeps** top 20% (elite strategies)
5. **Discards** bottom 80% (losing strategies)
6. **Breed** winners to create next generation
7. **Repeats** indefinitely, adapting to market changes

## ✅ What's Been Built

### Components

- **Ralph Loop Evaluator** (`src/ralph_loop/evaluator.py`)
  - Strategy selection logic (top 20%)
  - Performance analysis
  - Genealogy tracking
  - Pattern identification
  - Generation comparison

- **Generation Service** (`src/services/generation_service.py`)
  - Continuous background worker
  - Multi-pair support
  - Automated cycle management
  - Logging and monitoring

- **New API Endpoints** (5 new endpoints)
  - Manual Ralph Loop cycle triggering
  - Pattern analysis
  - Strategy genealogy
  - Generation comparison
  - Service control

## 🚀 How to Use

### Option 1: Automated (Recommended) - Docker

```bash
# In docker-compose.yml, the strategy_generator service runs continuously

# Start all services including continuous generation
docker-compose up -d

# Check logs
docker-compose logs -f strategy_generator

# Monitor metrics
curl http://localhost:8001/api/v1/system/metrics
```

The system will:
1. Generate 500 strategies every 5 minutes (configurable)
2. Backtest all of them
3. Apply Ralph Loop (keep top 20%, discard 80%)
4. Save elite strategies to database
5. Use elite as parents for next generation
6. **Loop forever** as market changes

### Option 2: Manual Control - API

**Step 1: Generate initial strategies**
```bash
curl -X POST http://localhost:8001/api/v1/generate/initial \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTC/USDT",
    "count": 500
  }'
```

**Step 2: Backtest them**
```bash
curl -X POST http://localhost:8001/api/v1/backtest/batch \
  -H "Content-Type: application/json" \
  -d '[{strategy1}, {strategy2}, ...]'
```

**Step 3: Run Ralph Loop**
```bash
curl -X GET 'http://localhost:8001/api/v1/ralph-loop/run-cycle?generation_id=1&pair=BTC/USDT'
```

**Step 4: Get elite strategies**
```bash
curl http://localhost:8001/api/v1/ralph-loop/elite?limit=20
```

**Step 5: Generate evolved strategies for next cycle**
```bash
curl -X POST http://localhost:8001/api/v1/generate/evolved \
  -H "Content-Type: application/json" \
  -d '{
    "pair": "BTC/USDT",
    "generation_id": 2,
    "count": 500
  }'
```

**Repeat steps 2-5 infinitely!**

### Option 3: Python Script

```python
from src.services.generation_service import StrategyGenerationService

service = StrategyGenerationService()

# Run 10 generations
for i in range(10):
    service.run_generation_cycle(i + 1)

# Check status
print(service.get_status())
```

## 📊 Monitoring

### Key Metrics

```bash
# System metrics
curl http://localhost:8001/api/v1/system/metrics

# Elite strategies (top performers)
curl http://localhost:8001/api/v1/ralph-loop/elite?limit=10

# Generation statistics (improvement over time)
curl http://localhost:8001/api/v1/ralph-loop/statistics

# Pattern analysis (what works)
curl http://localhost:8001/api/v1/ralph-loop/patterns
```

### Expected Improvements

**Generation 1:**
- Pass rate: ~20-30% (many random failures)
- Best score: 40-60/100
- Average score: 20-30/100

**Generation 5:**
- Pass rate: ~40-50% (elite breeding working)
- Best score: 70-80/100
- Average score: 40-50/100

**Generation 10+:**
- Pass rate: ~50-70% (consistent winners)
- Best score: 80-95/100
- Average score: 60-70/100

## 🔍 Understanding Ralph Loop

### The Selection Logic

```
Generation 0: 500 random strategies
└─ Backtest all 500
   ├─ 100 pass criteria (20%)
   └─ 400 fail criteria (80%)

Ralph Loop Selection:
├─ TOP 20% (KEEP) → Elite strategies
│  ├─ Best performers
│  ├─ Used as parents for next generation
│  └─ Mutated to explore nearby parameter space
│
└─ BOTTOM 80% (DISCARD) → But give 2nd chances
   ├─ Mutate losers → Try them again
   └─ Cross losers with winners → Maybe hybrid works
```

### Why It Works

1. **Elitism**: Top performers breed more → better genes spread
2. **Diversity**: Mutations prevent convergence to local optimum
3. **Pressure**: Only the strong survive → continuous improvement
4. **Adaptation**: Each generation learns from market changes

## 📈 Example Evolution

```
Strategy Lifecycle:
═══════════════════

Generation 0:
  Strategy A: Score 45/100 ✗ (random)
  Strategy B: Score 52/100 ✓ (lucky random!)

Generation 1 (breed from B):
  Strategy B1: Score 60/100 ✓ (mutation of B)
  Strategy B2: Score 58/100 ✓ (crossover of B)
  Strategy B3: Score 55/100 ✓ (mutation of B)

Generation 2 (breed from B1, B2, B3):
  Strategy B1a: Score 68/100 ✓ (improving!)
  Strategy B1b: Score 72/100 ✓✓ (great!)
  Strategy B2a: Score 70/100 ✓✓

Generation 3+:
  Score continues improving...
  Best ever: Score 85/100 ✓✓✓
```

## 🎛️ Configuration

Edit `.env` to customize Ralph Loop:

```bash
# How many strategies per generation (default 500)
STRATEGIES_PER_GENERATION=500

# Keep top X% as elite (default 20%)
ELITE_THRESHOLD=0.20

# Mutation strength (default 15% per parameter)
MUTATION_RATE=0.15

# Generation interval in seconds (default 300 = 5 min)
# Set in generation_service.py or docker-compose

# Profitability criteria
TARGET_WIN_RATE=0.40          # 40% minimum
TARGET_PROFIT_PCT=0.20        # 20% per trade
TARGET_SHARPE_RATIO=1.0       # Risk-adjusted return
```

## 🔄 Continuous Operation

The service is designed to run **forever**, adapting to market changes:

```
Hour 0:    Generation 1  → Elite identified
Hour 1:    Generation 2  → Breed from Gen 1 elite
Hour 2:    Generation 3  → Breed from Gen 2 elite
...
Hour 24:   Generation 288 → Continuous evolution!
...
Day 30:    Generation 8,640 → Highly adapted strategies
```

Market conditions change constantly → Your strategies must too!

## 🛠️ Troubleshooting

### No strategies passing criteria

**Problem**: Pass rate is 0%

**Solutions**:
1. Lower ELITE_THRESHOLD from 0.20 to 0.30
2. Lower TARGET_WIN_RATE from 0.40 to 0.30
3. Increase STRATEGIES_PER_GENERATION
4. Check historical data is available

### Performance degrading

**Problem**: Scores are declining

**Solutions**:
1. Market regime changed → normal
2. Increase MUTATION_RATE to explore more
3. Run more generations
4. Check for data issues (bad candles)

### Service running slowly

**Problem**: Backtesting takes too long

**Solutions**:
1. Use 60-minute instead of 15-minute candles
2. Reduce backtest period from 365 to 180 days
3. Increase WORKERS in .env
4. Use SSD for database

## 📝 API Reference (Ralph Loop)

### GET /api/v1/ralph-loop/elite
Get elite (top 20%) strategies

**Query params:**
- `pair`: Filter by trading pair (optional)
- `limit`: Max results (default 20)

**Response:**
```json
{
  "count": 5,
  "elite": [
    {
      "strategy_id": "strat_abc123",
      "score": 82.5,
      "win_rate": 0.58,
      "profit_pct": 45.3,
      "sharpe_ratio": 1.85
    },
    ...
  ]
}
```

### GET /api/v1/ralph-loop/statistics
Get generation statistics

**Response:**
```json
{
  "runs": [
    {
      "generation_id": 10,
      "strategies_generated": 500,
      "strategies_backtested": 500,
      "strategies_passed": 275,
      "pass_rate": 0.55,
      "status": "completed"
    },
    ...
  ]
}
```

### GET /api/v1/ralph-loop/patterns
Identify successful parameter patterns

**Response:**
```json
{
  "patterns": {
    "avg_win_rate": 0.58,
    "avg_sharpe": 1.45,
    "avg_profit_pct": 35.2,
    "sma_fast_range": {...},
    "sma_slow_range": {...}
  }
}
```

### GET /api/v1/ralph-loop/genealogy/{strategy_id}
Get strategy family tree

**Response:**
```json
{
  "strategy_id": "strat_abc123",
  "ancestors": [
    {
      "id": "strat_parent_123",
      "generation": 5,
      "source": "ga_mutation"
    }
  ],
  "descendants": [...]
}
```

### GET /api/v1/ralph-loop/compare
Compare two generations

**Query params:**
- `gen1_id`: First generation ID
- `gen2_id`: Second generation ID

**Response:**
```json
{
  "generation_1": {"pass_rate": 0.40, "top_score": 75},
  "generation_2": {"pass_rate": 0.55, "top_score": 85},
  "improvement": {
    "pass_rate_change": 0.15,
    "top_score_change": 10
  }
}
```

## 🎓 Best Practices

1. **Start with many generations** (10+) before going live
2. **Monitor patterns** - they reveal what works
3. **Don't lower criteria too much** - stays profitable
4. **Keep elite strategies** - they're proven
5. **Increase mutation rate** if stuck - explore more
6. **Test new markets** - strategies vary by pair
7. **Monitor live performance** - backtest != reality

## 🚀 Next Steps

1. **Start the service**
   ```bash
   docker-compose up strategy_generator -d
   ```

2. **Monitor progress**
   ```bash
   curl http://localhost:8001/api/v1/ralph-loop/elite
   curl http://localhost:8001/api/v1/ralph-loop/statistics
   ```

3. **After 10+ generations**, review elite strategies
   ```bash
   curl http://localhost:8001/api/v1/ralph-loop/patterns
   ```

4. **Deploy top performers to live trading** (Phase 4)

---

**Ralph Loop is now running! Your bot will continuously improve.** 🤖📈
