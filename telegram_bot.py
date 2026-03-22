#!/usr/bin/env python3
"""
Grindstone Apex - Telegram Bot Controller
Full command interface for backtesting, live trading, and monitoring.

Commands:
  /start          - Welcome message & command list
  /status         - System status (strategies, generations, positions)
  /backtest       - Start a new backtesting generation
  /stop           - Stop running backtest
  /elite          - Show top elite strategies per pair (with IDs)
  /inspect ID     - View full strategy details (params, results, status)
  /deploy ID      - Deploy a specific strategy to live trading
  /golive PAIR    - Auto-deploy best strategy for a pair to live trading
  /stoplive PAIR  - Stop live trading for a pair
  /balance        - Show exchange account balance
  /positions      - Show open positions
  /history N      - Show last N trades (default 10)
  /kill           - Emergency: close all positions and stop all trading
"""
import sys
import os
import json
import logging
import asyncio
import signal
import threading
import time
from datetime import datetime, timedelta

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, filters
)

from src.config import get_settings
from src.database import (
    SessionLocal, init_db, Strategy, BacktestResult, GenerationRun,
    StrategyPerformance, LiveTrade, SystemMetrics
)
from sqlalchemy import desc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
BOT_TOKEN = settings.telegram_bot_token
CHAT_ID = settings.telegram_chat_id
AUTO_DEPLOY_THRESHOLD = 85.0  # Auto-deploy strategies scoring above this
AUTO_DEPLOY_ENABLED = True

# Global state
backtest_process = None
backtest_running = False
live_trading_service = None
live_trading_thread = None


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────
def get_db():
    """Get a fresh database session."""
    return SessionLocal()


def authorized(func):
    """Decorator to restrict commands to the configured chat ID."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if str(update.effective_chat.id) != str(CHAT_ID):
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await func(update, context)
    return wrapper


def format_number(n, decimals=2):
    """Format number with commas."""
    if n is None:
        return "N/A"
    if abs(n) >= 1000:
        return f"{n:,.{decimals}f}"
    return f"{n:.{decimals}f}"


# ──────────────────────────────────────────────
# /start - Welcome
# ──────────────────────────────────────────────
@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with available commands."""
    msg = (
        "🤖 *Grindstone Apex Trading Bot*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 *Monitoring*\n"
        "  /status - System overview\n"
        "  /elite - Top strategies per pair\n"
        "  /inspect ID - View strategy details\n"
        "  /balance - Exchange balance\n"
        "  /positions - Open positions\n"
        "  /history - Recent trades\n\n"
        "🧬 *Backtesting*\n"
        "  /backtest - Start new generation\n"
        "  /stop - Stop current backtest\n\n"
        "🚀 *Live Trading*\n"
        "  /deploy ID - Deploy specific strategy\n"
        "  /golive PAIR - Auto-deploy best for pair\n"
        "  /stoplive PAIR - Stop pair trading\n"
        "  /kill - Emergency stop all\n\n"
        f"⚙️ Auto-deploy: {'ON' if AUTO_DEPLOY_ENABLED else 'OFF'} "
        f"(threshold: {AUTO_DEPLOY_THRESHOLD}/100)"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ──────────────────────────────────────────────
# /status - System Status
# ──────────────────────────────────────────────
@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system status."""
    db = get_db()
    try:
        total_strategies = db.query(Strategy).count()
        total_results = db.query(BacktestResult).count()
        passing = db.query(BacktestResult).filter(BacktestResult.meets_criteria == True).count()
        elite_count = db.query(Strategy).filter(Strategy.status == "elite").count()

        latest_gen = db.query(GenerationRun).order_by(desc(GenerationRun.generation_id)).first()
        gen_info = "None yet"
        if latest_gen:
            tested = latest_gen.strategies_backtested or 0
            passed = latest_gen.strategies_passed or 0
            rate = (passed / tested * 100) if tested > 0 else 0
            top = latest_gen.top_strategy_score or 0
            gen_info = (
                f"Gen {latest_gen.generation_id} | "
                f"{tested} tested | {passed} passed ({rate:.0f}%) | "
                f"Top: {top:.1f}/100 | {latest_gen.status}"
            )

        # Deployed strategies
        deployed = db.query(StrategyPerformance).filter(
            StrategyPerformance.deployed == True,
            StrategyPerformance.live_active == True
        ).count()

        # Open positions
        open_pos = db.query(LiveTrade).filter(LiveTrade.status == "open").count()

        # Recent P&L
        recent_trades = db.query(LiveTrade).filter(
            LiveTrade.status == "closed",
            LiveTrade.exit_time >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        pnl_24h = sum(t.pnl or 0 for t in recent_trades)
        wins_24h = len([t for t in recent_trades if (t.pnl or 0) > 0])

        msg = (
            "📊 *Grindstone Apex Status*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🧬 *Strategies:* {total_strategies}\n"
            f"✅ *Passing criteria:* {passing}\n"
            f"⭐ *Elite pool:* {elite_count}\n"
            f"🚀 *Live deployed:* {deployed}\n"
            f"📈 *Open positions:* {open_pos}\n\n"
            f"📅 *Latest Generation:*\n{gen_info}\n\n"
            f"💰 *24h P&L:* ${pnl_24h:+.2f} "
            f"({wins_24h}/{len(recent_trades)} wins)\n\n"
            f"🔄 *Backtest running:* {'Yes' if backtest_running else 'No'}\n"
            f"⚡ *Live trading:* {'Active' if live_trading_thread and live_trading_thread.is_alive() else 'Stopped'}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        db.close()


# ──────────────────────────────────────────────
# /elite - Top Strategies Per Pair
# ──────────────────────────────────────────────
@authorized
async def cmd_elite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top elite strategies grouped by pair."""
    db = get_db()
    try:
        pairs = ["BTC/USDT:USDT", "ETH/USDT:USDT", "XAU/USDT:USDT", "XAG/USDT:USDT"]
        msg = "⭐ *Elite Strategies*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for pair in pairs:
            # Get top 3 for this pair
            top = db.query(BacktestResult).join(
                Strategy, Strategy.id == BacktestResult.strategy_id
            ).filter(
                Strategy.pair == pair,
                BacktestResult.meets_criteria == True
            ).order_by(desc(BacktestResult.composite_score)).limit(3).all()

            if not top:
                msg += f"\n📉 *{pair}*: No qualifying strategies yet\n"
                continue

            msg += f"\n📈 *{pair}*\n"
            for i, r in enumerate(top):
                deployed = db.query(StrategyPerformance).filter(
                    StrategyPerformance.strategy_id == r.strategy_id,
                    StrategyPerformance.deployed == True
                ).first()
                status = " 🟢 LIVE" if deployed else ""

                # Get strategy type info
                strat = db.query(Strategy).filter(Strategy.id == r.strategy_id).first()
                stype = ""
                if strat and strat.indicators:
                    ind = strat.indicators if isinstance(strat.indicators, dict) else {}
                    stype = f" ({ind.get('strategy_type', '?')} {ind.get('direction', '?')})"

                # Show short ID for reference
                short_id = r.strategy_id[-8:] if r.strategy_id else "?"

                msg += (
                    f"  {i+1}. `{short_id}` Score: {r.composite_score:.1f} | "
                    f"Win: {r.win_rate*100:.0f}% | "
                    f"Profit: {r.total_profit_pct:.1f}%"
                    f"{stype}{status}\n"
                )

        msg += (
            f"\n💡 `/inspect ID` - View strategy details"
            f"\n💡 `/deploy ID` - Deploy a specific strategy"
            f"\n💡 `/golive PAIR` - Auto-deploy best for pair"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        db.close()


# ──────────────────────────────────────────────
# /inspect ID - View Full Strategy Details
# ──────────────────────────────────────────────
@authorized
async def cmd_inspect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full details of a strategy by ID (or partial ID)."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/inspect ID`\n"
            "Use the short ID from /elite (e.g. `/inspect a1b2c3d4`)",
            parse_mode="Markdown"
        )
        return

    search_id = context.args[0].strip()
    db = get_db()
    try:
        # Try exact match first, then partial match on ending
        strat = db.query(Strategy).filter(Strategy.id == search_id).first()
        if not strat:
            strat = db.query(Strategy).filter(Strategy.id.like(f"%{search_id}")).first()
        if not strat:
            await update.message.reply_text(f"❌ No strategy found matching `{search_id}`", parse_mode="Markdown")
            return

        # Get backtest results
        result = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strat.id
        ).order_by(desc(BacktestResult.composite_score)).first()

        # Get deploy status
        perf = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strat.id
        ).first()

        indicators = strat.indicators if isinstance(strat.indicators, dict) else {}
        risk = strat.risk_management if isinstance(strat.risk_management, dict) else {}
        pos = strat.position_sizing if isinstance(strat.position_sizing, dict) else {}

        msg = (
            f"🔍 *Strategy Details*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*ID:* `{strat.id}`\n"
            f"*Pair:* {strat.pair}\n"
            f"*Status:* {strat.status}\n"
            f"*Gen:* {strat.generation_id} | *Source:* {strat.source}\n\n"
        )

        # Strategy type and direction
        stype = indicators.get('strategy_type', 'unknown')
        direction = indicators.get('direction', 'long')
        msg += f"📋 *Type:* {stype} ({direction})\n\n"

        # Key parameters (skip meta fields)
        skip_keys = {'strategy_type', 'direction'}
        param_lines = []
        for k, v in indicators.items():
            if k in skip_keys:
                continue
            if isinstance(v, float):
                param_lines.append(f"  • {k}: {v:.4f}")
            else:
                param_lines.append(f"  • {k}: {v}")

        if param_lines:
            msg += "*Indicators:*\n" + "\n".join(param_lines) + "\n\n"

        # Risk management
        if risk:
            msg += "*Risk:*\n"
            for k, v in risk.items():
                msg += f"  • {k}: {v}\n"
            msg += "\n"

        # Position sizing
        if pos:
            msg += "*Position:*\n"
            for k, v in pos.items():
                msg += f"  • {k}: {v}\n"
            msg += "\n"

        # Backtest results
        if result:
            msg += (
                f"📊 *Backtest Results:*\n"
                f"  Score: *{result.composite_score:.1f}*/100\n"
                f"  Profit: {result.total_profit_pct:.2f}%\n"
                f"  Win Rate: {result.win_rate*100:.1f}%\n"
                f"  Sharpe: {result.sharpe_ratio:.2f}\n"
                f"  Max Drawdown: {result.max_drawdown:.2f}%\n"
                f"  Trades: {result.win_count + result.loss_count} "
                f"({result.win_count}W / {result.loss_count}L)\n"
            )
            if result.profit_factor:
                msg += f"  Profit Factor: {result.profit_factor:.2f}\n"

        # Deploy status
        if perf and perf.deployed:
            msg += (
                f"\n🟢 *LIVE DEPLOYED*\n"
                f"  Live Profit: ${perf.live_total_profit:.2f}\n"
                f"  Live Trades: {perf.live_total_trades}\n"
            )

        msg += f"\n💡 Deploy with: `/deploy {strat.id[-8:]}`"
        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        db.close()


# ──────────────────────────────────────────────
# /deploy ID - Deploy a Specific Strategy to Live
# ──────────────────────────────────────────────
@authorized
async def cmd_deploy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deploy a specific strategy by ID to live trading."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/deploy ID`\n"
            "Use the short ID from /elite or /inspect\n"
            "Example: `/deploy a1b2c3d4`",
            parse_mode="Markdown"
        )
        return

    search_id = context.args[0].strip()
    db = get_db()
    try:
        # Find strategy by exact or partial ID
        strat = db.query(Strategy).filter(Strategy.id == search_id).first()
        if not strat:
            strat = db.query(Strategy).filter(Strategy.id.like(f"%{search_id}")).first()
        if not strat:
            await update.message.reply_text(f"❌ No strategy found matching `{search_id}`", parse_mode="Markdown")
            return

        # Get backtest result
        result = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strat.id
        ).order_by(desc(BacktestResult.composite_score)).first()

        if not result:
            await update.message.reply_text(f"❌ No backtest results for this strategy. Run /backtest first.")
            return

        # Check if already deployed
        existing = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strat.id
        ).first()

        if existing and existing.deployed and existing.live_active:
            await update.message.reply_text(
                f"ℹ️ Strategy `{strat.id[-8:]}` is already live on {strat.pair}\n"
                f"Score: {result.composite_score:.1f} | Win: {result.win_rate*100:.0f}%",
                parse_mode="Markdown"
            )
            return

        # Deploy it
        if existing:
            existing.deployed = True
            existing.live_active = True
            db.add(existing)
        else:
            perf = StrategyPerformance(
                strategy_id=strat.id,
                backtest_total_profit=result.total_profit,
                backtest_win_rate=result.win_rate,
                backtest_sharpe=result.sharpe_ratio,
                deployed=True,
                live_active=True,
            )
            db.add(perf)

        strat.status = "deployed"
        db.add(strat)
        db.commit()

        indicators = strat.indicators if isinstance(strat.indicators, dict) else {}
        stype = indicators.get('strategy_type', 'unknown')
        direction = indicators.get('direction', 'long')

        await update.message.reply_text(
            f"🚀 *Strategy Deployed!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*ID:* `{strat.id[-8:]}`\n"
            f"*Pair:* {strat.pair}\n"
            f"*Type:* {stype} ({direction})\n"
            f"*Score:* {result.composite_score:.1f}/100\n"
            f"*Win Rate:* {result.win_rate*100:.0f}%\n"
            f"*Profit:* {result.total_profit_pct:.1f}%\n\n"
            f"Strategy is now live trading on {strat.pair}.\n"
            f"Use `/stoplive {strat.pair}` to stop.",
            parse_mode="Markdown"
        )

    finally:
        db.close()


# ──────────────────────────────────────────────
# /backtest - Start Backtesting
# ──────────────────────────────────────────────
@authorized
async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new backtesting generation."""
    global backtest_running, backtest_process

    if backtest_running:
        await update.message.reply_text("⚠️ Backtest already running. Use /stop to cancel first.")
        return

    # Parse optional number of generations
    num_gens = 1
    if context.args:
        try:
            num_gens = int(context.args[0])
            num_gens = min(num_gens, 50)  # Cap at 50
        except ValueError:
            pass

    await update.message.reply_text(
        f"🧬 Starting {num_gens} backtesting generation(s)...\n"
        f"This will generate and test strategies across all pairs.\n"
        f"I'll notify you when each generation completes."
    )

    # Run in background thread
    def run_backtest_generations(app, chat_id, num_gens):
        global backtest_running
        backtest_running = True

        try:
            for gen_num in range(num_gens):
                if not backtest_running:
                    asyncio.run_coroutine_threadsafe(
                        app.bot.send_message(chat_id, "🛑 Backtest stopped by user."),
                        app.bot._application._loop if hasattr(app.bot, '_application') else asyncio.get_event_loop()
                    )
                    break

                # Import and run the backtest pipeline
                from run_backtest import run_backtest_pipeline
                results = run_backtest_pipeline()

                # Build result summary
                if results:
                    results.sort(key=lambda x: x["score"], reverse=True)
                    passing = [r for r in results if r["metrics"]["meets_criteria"]]

                    db = get_db()
                    latest_gen = db.query(GenerationRun).order_by(
                        desc(GenerationRun.generation_id)
                    ).first()
                    gen_id = latest_gen.generation_id if latest_gen else "?"
                    db.close()

                    summary = (
                        f"✅ *Generation {gen_id} Complete* ({gen_num+1}/{num_gens})\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 Tested: {len(results)}\n"
                        f"✅ Passed criteria: {len(passing)}\n"
                    )

                    if results:
                        best = results[0]
                        summary += (
                            f"🏆 Best: {best['score']:.1f}/100\n"
                            f"   Win: {best['metrics']['win_rate']*100:.0f}% | "
                            f"Profit: {best['metrics']['total_profit_pct']:.1f}% | "
                            f"Sharpe: {best['metrics']['sharpe_ratio']:.1f}\n"
                        )

                    # Check auto-deploy
                    if AUTO_DEPLOY_ENABLED and passing:
                        auto_deployed = []
                        for strat in passing:
                            if strat["score"] >= AUTO_DEPLOY_THRESHOLD:
                                deployed = _auto_deploy_strategy(strat["strategy_id"])
                                if deployed:
                                    auto_deployed.append(strat)

                        if auto_deployed:
                            summary += (
                                f"\n🚀 *Auto-deployed {len(auto_deployed)} strategies* "
                                f"(score ≥ {AUTO_DEPLOY_THRESHOLD})\n"
                            )
                            for s in auto_deployed[:3]:
                                summary += f"  • {s['strategy_id'][:16]}... ({s['score']:.1f})\n"

                    # Send via requests since we're in a thread
                    import requests
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": summary,
                            "parse_mode": "Markdown"
                        }
                    )
                else:
                    import requests
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": f"⚠️ Generation {gen_num+1} produced no results."
                        }
                    )

        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            import requests
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"❌ Backtest error: {str(e)[:200]}"
                }
            )
        finally:
            backtest_running = False

    thread = threading.Thread(
        target=run_backtest_generations,
        args=(context.application, CHAT_ID, num_gens),
        daemon=True
    )
    thread.start()


# ──────────────────────────────────────────────
# /stop - Stop Backtesting
# ──────────────────────────────────────────────
@authorized
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop running backtest."""
    global backtest_running
    if backtest_running:
        backtest_running = False
        await update.message.reply_text("🛑 Stopping backtest after current generation completes...")
    else:
        await update.message.reply_text("ℹ️ No backtest currently running.")


# ──────────────────────────────────────────────
# /golive PAIR - Deploy Strategy to Live Trading
# ──────────────────────────────────────────────
@authorized
async def cmd_golive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deploy the best strategy for a pair to live trading."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/golive PAIR`\n"
            "Example: `/golive BTC/USDT:USDT`\n\n"
            "Available pairs:\n"
            "• BTC/USDT:USDT\n"
            "• ETH/USDT:USDT\n"
            "• XAU/USDT:USDT\n"
            "• XAG/USDT:USDT",
            parse_mode="Markdown"
        )
        return

    pair = context.args[0].upper()
    # Normalize shorthand
    pair_map = {
        "BTC": "BTC/USDT:USDT", "ETH": "ETH/USDT:USDT",
        "XAU": "XAU/USDT:USDT", "XAG": "XAG/USDT:USDT",
    }
    pair = pair_map.get(pair, pair)

    db = get_db()
    try:
        # Find the best strategy for this pair
        best = db.query(BacktestResult).join(
            Strategy, Strategy.id == BacktestResult.strategy_id
        ).filter(
            Strategy.pair == pair,
            BacktestResult.meets_criteria == True
        ).order_by(desc(BacktestResult.composite_score)).first()

        if not best:
            await update.message.reply_text(
                f"❌ No qualifying strategies found for {pair}.\n"
                f"Run /backtest first to generate strategies."
            )
            return

        strategy = db.query(Strategy).filter(Strategy.id == best.strategy_id).first()
        if not strategy:
            await update.message.reply_text("❌ Strategy not found in database.")
            return

        # Check if already deployed
        existing = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == best.strategy_id
        ).first()

        if existing and existing.deployed and existing.live_active:
            await update.message.reply_text(
                f"ℹ️ Strategy already live for {pair}\n"
                f"Score: {best.composite_score:.1f} | Win: {best.win_rate*100:.0f}%"
            )
            return

        # Deploy
        if existing:
            existing.deployed = True
            existing.live_active = True
            db.add(existing)
        else:
            perf = StrategyPerformance(
                strategy_id=best.strategy_id,
                backtest_total_profit=best.total_profit,
                backtest_win_rate=best.win_rate,
                backtest_sharpe=best.sharpe_ratio,
                deployed=True,
                live_active=True,
            )
            db.add(perf)

        strategy.status = "deployed"
        db.add(strategy)
        db.commit()

        # Start live trading service if not running
        _ensure_live_trading_running()

        await update.message.reply_text(
            f"🚀 *Strategy Deployed to Live Trading*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Pair: {pair}\n"
            f"🆔 Strategy: `{best.strategy_id}`\n"
            f"📊 Score: {best.composite_score:.1f}/100\n"
            f"✅ Win Rate: {best.win_rate*100:.0f}%\n"
            f"💰 Backtest Profit: {best.total_profit_pct:.1f}%\n"
            f"📉 Max Drawdown: {best.max_drawdown*100:.1f}%\n"
            f"📐 Sharpe: {best.sharpe_ratio:.1f}\n\n"
            f"⚡ Live trading service: Running\n"
            f"🔔 You'll receive alerts for entries/exits",
            parse_mode="Markdown"
        )

    finally:
        db.close()


# ──────────────────────────────────────────────
# /stoplive PAIR - Stop Live Trading for a Pair
# ──────────────────────────────────────────────
@authorized
async def cmd_stoplive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop live trading for a specific pair."""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/stoplive PAIR`\nExample: `/stoplive BTC`",
            parse_mode="Markdown"
        )
        return

    pair = context.args[0].upper()
    pair_map = {
        "BTC": "BTC/USDT:USDT", "ETH": "ETH/USDT:USDT",
        "XAU": "XAU/USDT:USDT", "XAG": "XAG/USDT:USDT",
    }
    pair = pair_map.get(pair, pair)

    db = get_db()
    try:
        # Find deployed strategies for this pair
        deployed = db.query(StrategyPerformance).join(
            Strategy, Strategy.id == StrategyPerformance.strategy_id
        ).filter(
            Strategy.pair == pair,
            StrategyPerformance.deployed == True,
            StrategyPerformance.live_active == True
        ).all()

        if not deployed:
            await update.message.reply_text(f"ℹ️ No active live strategies for {pair}")
            return

        count = 0
        for perf in deployed:
            perf.live_active = False
            db.add(perf)
            count += 1

        db.commit()

        await update.message.reply_text(
            f"🛑 Stopped {count} live strategy(s) for {pair}\n"
            f"Open positions will be closed at next check cycle."
        )

    finally:
        db.close()


# ──────────────────────────────────────────────
# /balance - Exchange Balance
# ──────────────────────────────────────────────
@authorized
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show exchange account balance."""
    try:
        from src.live_trading.exchange_connector import ExchangeConnector
        connector = ExchangeConnector(
            exchange_type=settings.live_exchange,
            sandbox=settings.sandbox_mode
        )
        balance = connector.get_balance("USDT")

        msg = (
            f"💰 *Account Balance*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Exchange: {settings.live_exchange}\n"
            f"Mode: {'🔶 Sandbox' if settings.sandbox_mode else '🟢 Live'}\n\n"
            f"Total: ${format_number(balance.get('total', 0))}\n"
            f"Free: ${format_number(balance.get('free', 0))}\n"
            f"Used: ${format_number(balance.get('used', 0))}\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch balance: {str(e)[:200]}")


# ──────────────────────────────────────────────
# /positions - Open Positions
# ──────────────────────────────────────────────
@authorized
async def cmd_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show open positions."""
    db = get_db()
    try:
        positions = db.query(LiveTrade).filter(
            LiveTrade.status == "open"
        ).all()

        if not positions:
            await update.message.reply_text("📭 No open positions.")
            return

        msg = f"📈 *Open Positions ({len(positions)})*\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        for pos in positions[:10]:
            elapsed = datetime.utcnow() - pos.entry_time if pos.entry_time else timedelta(0)
            msg += (
                f"\n*{pos.pair}*\n"
                f"  Entry: ${pos.entry_price:.2f} | Size: {pos.size:.4f}\n"
                f"  SL: ${pos.stop_loss:.2f} | TP: ${pos.take_profit:.2f}\n"
                f"  Duration: {elapsed.seconds // 3600}h {(elapsed.seconds % 3600) // 60}m\n"
            )

        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        db.close()


# ──────────────────────────────────────────────
# /history N - Recent Trades
# ──────────────────────────────────────────────
@authorized
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent closed trades."""
    limit = 10
    if context.args:
        try:
            limit = min(int(context.args[0]), 25)
        except ValueError:
            pass

    db = get_db()
    try:
        trades = db.query(LiveTrade).filter(
            LiveTrade.status == "closed"
        ).order_by(desc(LiveTrade.exit_time)).limit(limit).all()

        if not trades:
            await update.message.reply_text("📭 No trade history yet.")
            return

        total_pnl = sum(t.pnl or 0 for t in trades)
        wins = len([t for t in trades if (t.pnl or 0) > 0])

        msg = (
            f"📜 *Last {len(trades)} Trades*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Total P&L: ${total_pnl:+.2f} | Wins: {wins}/{len(trades)}\n"
        )

        for t in trades[:10]:
            pnl = t.pnl or 0
            emoji = "🟢" if pnl > 0 else "🔴"
            msg += (
                f"\n{emoji} *{t.pair}* ${pnl:+.2f}\n"
                f"  {t.entry_price:.2f} → {t.exit_price:.2f} | "
                f"Reason: {t.exit_reason or '?'}\n"
            )

        await update.message.reply_text(msg, parse_mode="Markdown")

    finally:
        db.close()


# ──────────────────────────────────────────────
# /kill - Emergency Stop All
# ──────────────────────────────────────────────
@authorized
async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Emergency: stop all trading and close all positions."""
    global backtest_running, live_trading_service

    await update.message.reply_text("🚨 *EMERGENCY STOP INITIATED*", parse_mode="Markdown")

    # Stop backtest
    backtest_running = False

    # Stop live trading
    if live_trading_service:
        live_trading_service.stop()

    # Deactivate all deployed strategies
    db = get_db()
    try:
        active = db.query(StrategyPerformance).filter(
            StrategyPerformance.live_active == True
        ).all()

        count = 0
        for perf in active:
            perf.live_active = False
            db.add(perf)
            count += 1

        db.commit()

        # Count open positions
        open_pos = db.query(LiveTrade).filter(LiveTrade.status == "open").count()

        await update.message.reply_text(
            f"🛑 *Emergency Stop Complete*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Backtest: Stopped\n"
            f"• Live trading: Stopped\n"
            f"• Strategies deactivated: {count}\n"
            f"• Open positions: {open_pos}\n\n"
            f"⚠️ Open positions must be closed manually on the exchange "
            f"or will be closed when the service restarts.",
            parse_mode="Markdown"
        )

    finally:
        db.close()


# ──────────────────────────────────────────────
# Auto-Deploy Logic
# ──────────────────────────────────────────────
def _auto_deploy_strategy(strategy_id: str) -> bool:
    """Auto-deploy a strategy that meets the threshold."""
    db = get_db()
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False

        # Check if already deployed
        existing = db.query(StrategyPerformance).filter(
            StrategyPerformance.strategy_id == strategy_id
        ).first()

        if existing and existing.deployed:
            return False

        backtest = db.query(BacktestResult).filter(
            BacktestResult.strategy_id == strategy_id
        ).first()

        if not backtest:
            return False

        # Deploy
        if existing:
            existing.deployed = True
            existing.live_active = True
            db.add(existing)
        else:
            perf = StrategyPerformance(
                strategy_id=strategy_id,
                backtest_total_profit=backtest.total_profit,
                backtest_win_rate=backtest.win_rate,
                backtest_sharpe=backtest.sharpe_ratio,
                deployed=True,
                live_active=True,
            )
            db.add(perf)

        strategy.status = "deployed"
        db.add(strategy)
        db.commit()

        logger.info(f"Auto-deployed strategy {strategy_id} (score: {backtest.composite_score:.1f})")
        return True

    except Exception as e:
        logger.error(f"Auto-deploy error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# ──────────────────────────────────────────────
# Live Trading Service Management
# ──────────────────────────────────────────────
def _ensure_live_trading_running():
    """Start the live trading service if not already running."""
    global live_trading_service, live_trading_thread

    if live_trading_thread and live_trading_thread.is_alive():
        return  # Already running

    def run_live_service():
        global live_trading_service
        try:
            from src.services.live_trader_service import LiveTradingService
            live_trading_service = LiveTradingService()
            live_trading_service.run_continuous(check_interval=60)
        except Exception as e:
            logger.error(f"Live trading service error: {e}", exc_info=True)

    live_trading_thread = threading.Thread(target=run_live_service, daemon=True)
    live_trading_thread.start()
    logger.info("Live trading service started in background thread")


# ──────────────────────────────────────────────
# Main Bot Setup
# ──────────────────────────────────────────────
def main():
    """Start the Telegram bot."""
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID not set in .env")
        sys.exit(1)

    # Initialize database
    init_db()

    logger.info("=" * 60)
    logger.info("GRINDSTONE APEX - TELEGRAM BOT")
    logger.info("=" * 60)
    logger.info(f"Bot token: ...{BOT_TOKEN[-8:]}")
    logger.info(f"Chat ID: {CHAT_ID}")
    logger.info(f"Auto-deploy: {'ON' if AUTO_DEPLOY_ENABLED else 'OFF'} (threshold: {AUTO_DEPLOY_THRESHOLD})")

    # Build application
    app = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("elite", cmd_elite))
    app.add_handler(CommandHandler("inspect", cmd_inspect))
    app.add_handler(CommandHandler("deploy", cmd_deploy))
    app.add_handler(CommandHandler("backtest", cmd_backtest))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("golive", cmd_golive))
    app.add_handler(CommandHandler("stoplive", cmd_stoplive))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("positions", cmd_positions))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("kill", cmd_kill))

    # Send startup message
    async def on_startup(application):
        # Register command menu so "/" shows autocomplete in Telegram
        commands = [
            BotCommand("start", "Welcome & command list"),
            BotCommand("status", "System overview"),
            BotCommand("elite", "Top strategies per pair"),
            BotCommand("inspect", "View strategy details - /inspect ID"),
            BotCommand("backtest", "Start new generation"),
            BotCommand("stop", "Stop current backtest"),
            BotCommand("deploy", "Deploy strategy - /deploy ID"),
            BotCommand("golive", "Auto-deploy best for pair"),
            BotCommand("stoplive", "Stop live trading for pair"),
            BotCommand("balance", "Exchange account balance"),
            BotCommand("positions", "Open positions"),
            BotCommand("history", "Recent trades"),
            BotCommand("kill", "Emergency stop all"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info(f"Registered {len(commands)} commands with Telegram menu")

        db = get_db()
        strats = db.query(Strategy).count()
        elite = db.query(BacktestResult).filter(BacktestResult.meets_criteria == True).count()
        gens = db.query(GenerationRun).count()
        db.close()

        await application.bot.send_message(
            chat_id=CHAT_ID,
            text=(
                "🤖 *Grindstone Apex Bot Online*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 {strats} strategies | ⭐ {elite} elite | 🧬 {gens} generations\n"
                f"Auto-deploy: {'ON' if AUTO_DEPLOY_ENABLED else 'OFF'} (≥{AUTO_DEPLOY_THRESHOLD}/100)\n\n"
                f"Send /start for commands"
            ),
            parse_mode="Markdown"
        )

    app.post_init = on_startup

    # Run bot
    logger.info("Bot starting... Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
