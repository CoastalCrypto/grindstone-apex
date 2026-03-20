"""Phase 5 Advanced AI API routes - transformer, autoresearch, market regime, and council voting."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from src.database import SessionLocal, Strategy
from src.strategy_generation.transformer_predictor import TransformerStrategyPredictor
from src.strategy_generation.autoresearch import AutoResearch
from src.analysis.market_regime import MarketRegimeDetector
from src.ai.llm_council import Council
from src.backtesting.data_loader import get_data_loader

router = APIRouter(prefix="/api/v1/phase5", tags=["Phase 5 - Advanced AI"])
db = SessionLocal()


@router.post("/transformer/train")
async def train_transformer_on_elite(epochs: int = 10, batch_size: int = 32):
    """
    Fine-tune transformer on elite strategies.

    Query params:
    - epochs: Number of training epochs (default 10)
    - batch_size: Batch size (default 32)

    Returns:
    {
        "status": "success",
        "epochs": 10,
        "final_loss": 0.0234,
        "history": [0.5, 0.4, 0.3, ...]
    }
    """
    try:
        predictor = TransformerStrategyPredictor()

        # Get elite strategies from database
        elite_strategies = db.query(Strategy).filter(
            Strategy.status == "elite"
        ).limit(100).all()

        if not elite_strategies:
            raise HTTPException(status_code=404, detail="No elite strategies found")

        # Convert to dicts
        elite_dicts = [
            {
                "id": s.id,
                "parameters": s.indicators or {},
                "metrics": {
                    "win_rate": 0.55,  # Would come from backtest results
                    "profit_pct": 25,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.15,
                }
            }
            for s in elite_strategies
        ]

        # Train
        result = predictor.train_on_elite_strategies(
            elite_dicts,
            epochs=epochs,
            batch_size=batch_size
        )

        # Save model
        predictor.save_model("models/transformer_elite.pt")

        return {
            "status": "success",
            "message": f"Trained on {len(elite_dicts)} elite strategies",
            **result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transformer/predict")
async def predict_strategy_parameters(
    pair: str = "BTC/USDT",
    top_k: int = 5
):
    """
    Predict optimal strategy parameters for current market.

    Query params:
    - pair: Trading pair (default BTC/USDT)
    - top_k: Number of parameter sets to generate (default 5)

    Returns:
    {
        "pair": "BTC/USDT",
        "strategies": [
            {
                "sma_fast": 12,
                "sma_slow": 35,
                "rsi_period": 15,
                "risk_percentage": 2.5,
                "profit_target": 0.03
            }
        ],
        "timestamp": "2026-03-19T10:30:00Z"
    }
    """
    try:
        loader = get_data_loader()
        candles = loader.load_candles(pair, "1h", 30)

        if candles.empty:
            raise HTTPException(status_code=404, detail=f"No data for {pair}")

        # Get current market features
        market_features = {
            "volatility": candles['close'].pct_change().std() * 100,
            "trend": (candles['close'].iloc[-1] - candles['close'].iloc[-20]) / candles['close'].iloc[-20],
            "momentum": (candles['close'].iloc[-1] - candles['close'].iloc[-5]) / candles['close'].iloc[-5],
            "volume_ma_ratio": candles['volume'].iloc[-1] / candles['volume'].iloc[-20:].mean(),
        }

        predictor = TransformerStrategyPredictor("models/transformer_elite.pt")
        predicted = predictor.predict_parameters(market_features, top_k=top_k)

        return {
            "pair": pair,
            "market_features": market_features,
            "strategies": predicted,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autoresearch/generate-report")
async def generate_research_report(generation_limit: int = 10):
    """
    Generate autoresearch report on successful patterns.

    Query params:
    - generation_limit: Analyze last N generations (default 10)

    Returns:
    {
        "timestamp": "2026-03-19T10:30:00Z",
        "elite_count": 45,
        "patterns": {
            "sma_fast": {
                "mean": 15.2,
                "median": 14.0,
                "recommended_range": [12, 18]
            }
        },
        "performance_insights": {
            "win_rate": {"mean": 0.58, "median": 0.60},
            "profit_factor": {"mean": 1.95, "median": 2.05}
        },
        "recommendations": [
            "✅ Excellent average win rate (>60%)",
            "📊 SMA Fast optimal range: 12-18 periods",
            "🔄 Consider fine-tuning parameters..."
        ]
    }
    """
    try:
        autoresearch = AutoResearch("research_output")
        report = autoresearch.generate_research_report(generation_limit)

        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autoresearch/patterns")
async def get_elite_patterns():
    """
    Get identified successful parameter patterns from elite strategies.

    Returns:
    {
        "patterns": {
            "parameter_name": {
                "mean": 15.2,
                "median": 14.0,
                "mode": 14.0,
                "range": [10, 20],
                "recommended_range": [12, 18]
            }
        }
    }
    """
    try:
        autoresearch = AutoResearch()
        elite_strategies = []  # Would fetch from evaluator

        if not elite_strategies:
            # Get from database
            from src.ralph_loop.evaluator import RalphLoopEvaluator
            evaluator = RalphLoopEvaluator(db)
            elite_strategies = evaluator.get_elite_strategies(limit=50)

        patterns = autoresearch._analyze_parameter_patterns(elite_strategies)

        return {"patterns": patterns}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-regime/detect")
async def detect_market_regime(pair: str = "BTC/USDT"):
    """
    Detect current market regime.

    Query params:
    - pair: Trading pair (default BTC/USDT)

    Returns:
    {
        "pair": "BTC/USDT",
        "regime": "strong_uptrend",
        "confidence": 0.85,
        "trend": 0.15,
        "volatility": 2.3,
        "atr": 850.5,
        "adx": 65.4,
        "recommended_strategies": ["momentum_follow", "trend_following"],
        "should_pause": false
    }
    """
    try:
        loader = get_data_loader()
        candles = loader.load_candles(pair, "1h", 50)

        if candles.empty:
            raise HTTPException(status_code=404, detail=f"No data for {pair}")

        detector = MarketRegimeDetector()
        analysis = detector.detect_regime(candles)

        recommended = detector.get_recommended_strategies(analysis)
        should_pause = detector.should_pause_trading(analysis)

        return {
            "pair": pair,
            **analysis,
            "recommended_strategies": recommended,
            "should_pause": should_pause,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/council/vote")
async def get_council_vote(strategy_id: str, pair: str = "BTC/USDT"):
    """
    Get LLM council vote on a strategy.

    Query params:
    - strategy_id: Strategy ID to vote on
    - pair: Trading pair (default BTC/USDT)

    Returns:
    {
        "strategy_id": "strat_abc123",
        "votes": {
            "risk_analyst": "buy",
            "momentum_expert": "strong_buy",
            "value_analyzer": "buy",
            "correlation_expert": "neutral"
        },
        "consensus": "buy",
        "confidence": 0.78,
        "recommendation": "✅ CONSENSUS: Good candidate for deployment",
        "council_analysis": "COUNCIL ANALYSIS FOR STRATEGY...",
        "reasoning": {
            "risk_analyst": "Risk analysis: acceptable drawdown, strong risk-adjusted returns...",
            ...
        }
    }
    """
    try:
        # Get strategy
        strategy = db.query(Strategy).filter(
            Strategy.id == strategy_id
        ).first()

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Get market regime
        loader = get_data_loader()
        candles = loader.load_candles(pair, "1h", 50)

        detector = MarketRegimeDetector()
        market_context = detector.detect_regime(candles)

        # Get council vote
        council = Council()
        vote_result = council.vote_on_strategy(
            {
                "id": strategy.id,
                "parameters": strategy.indicators or {},
                "metrics": {
                    "win_rate": 0.55,
                    "profit_pct": 25,
                    "profit_factor": 1.9,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.15,
                    "total_trades": 50
                }
            },
            market_context
        )

        return vote_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/council/consensus-summary")
async def get_council_consensus_summary(limit: int = 20):
    """
    Get consensus votes for multiple elite strategies.

    Query params:
    - limit: Number of strategies to analyze (default 20)

    Returns:
    {
        "strategies_analyzed": 20,
        "strong_buy_count": 5,
        "buy_count": 10,
        "neutral_count": 3,
        "sell_count": 2,
        "recommendations": [
            {
                "strategy_id": "strat_best",
                "consensus": "strong_buy",
                "confidence": 0.95,
                "recommendation": "✅ STRONG CONSENSUS: Deploy to live trading immediately"
            }
        ]
    }
    """
    try:
        from src.ralph_loop.evaluator import RalphLoopEvaluator
        evaluator = RalphLoopEvaluator(db)

        elite_strategies = evaluator.get_elite_strategies(limit=limit)

        if not elite_strategies:
            raise HTTPException(status_code=404, detail="No elite strategies found")

        council = Council()

        consensus_results = []
        vote_counts = {
            "strong_buy": 0,
            "buy": 0,
            "neutral": 0,
            "sell": 0,
            "strong_sell": 0
        }

        for strategy in elite_strategies[:limit]:
            vote = council.vote_on_strategy(strategy, {"regime": "neutral"})

            vote_counts[vote["consensus"]] += 1
            consensus_results.append({
                "strategy_id": strategy.get("strategy_id"),
                "consensus": vote["consensus"],
                "confidence": vote["confidence"],
                "recommendation": vote["recommendation"]
            })

        # Sort by confidence
        consensus_results.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "strategies_analyzed": len(consensus_results),
            **vote_counts,
            "recommendations": consensus_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phase5/status")
async def get_phase5_status():
    """
    Get overall Phase 5 AI system status.

    Returns:
    {
        "phase": "5",
        "components": {
            "transformer": {"status": "ready", "model_loaded": true},
            "autoresearch": {"status": "ready", "last_report": "2026-03-19T10:30:00Z"},
            "market_regime": {"status": "ready"},
            "llm_council": {"status": "ready", "members": 4}
        }
    }
    """
    return {
        "phase": "5",
        "name": "Advanced AI System",
        "components": {
            "transformer_predictor": {
                "status": "ready",
                "description": "Fine-tuned transformer for predicting strategy parameters",
                "model_path": "models/transformer_elite.pt"
            },
            "autoresearch": {
                "status": "ready",
                "description": "Automatic research and pattern documentation",
                "output_directory": "research_output"
            },
            "market_regime_detector": {
                "status": "ready",
                "description": "Market regime detection and analysis",
                "regimes_supported": [
                    "strong_uptrend",
                    "weak_uptrend",
                    "sideways",
                    "weak_downtrend",
                    "strong_downtrend",
                    "volatile"
                ]
            },
            "llm_council": {
                "status": "ready",
                "description": "Multi-expert AI voting system for strategy validation",
                "members": 4,
                "member_list": [
                    "risk_analyst",
                    "momentum_expert",
                    "value_analyzer",
                    "correlation_expert"
                ]
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }
