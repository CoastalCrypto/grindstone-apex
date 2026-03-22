# Grindstone Apex — Complete Setup Guide

This guide walks you through every step to get Grindstone Apex running on your computer, from installing Python to running your first backtest and deploying a strategy to live trading.

No coding experience required. Just follow each step.

---

## Table of Contents

1. [Install Python](#step-1-install-python)
2. [Download the Project](#step-2-download-the-project)
3. [Create a Virtual Environment](#step-3-create-a-virtual-environment)
4. [Install Dependencies](#step-4-install-dependencies)
5. [Create a Blofin Account](#step-5-create-a-blofin-account)
6. [Get Blofin API Keys](#step-6-get-blofin-api-keys)
7. [Create a Telegram Bot](#step-7-create-a-telegram-bot)
8. [Get Your Telegram Chat ID](#step-8-get-your-telegram-chat-id)
9. [Configure the .env File](#step-9-configure-the-env-file)
10. [Run the Telegram Bot](#step-10-run-the-telegram-bot)
11. [Run Your First Backtest](#step-11-run-your-first-backtest)
12. [View and Inspect Strategies](#step-12-view-and-inspect-strategies)
13. [Deploy a Strategy to Live Trading](#step-13-deploy-a-strategy-to-live-trading)
14. [Run the TUI Dashboard (Optional)](#step-14-run-the-tui-dashboard-optional)
15. [Keep It Running 24/7](#step-15-keep-it-running-247)
16. [Troubleshooting](#troubleshooting)

---

## Step 1: Install Python

You need Python 3.10 or newer.

### Windows

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.12 or 3.13 (latest stable)
3. Run the installer
4. **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom of the installer
5. Click "Install Now"
6. Verify it works — open Command Prompt (Win+R, type `cmd`, press Enter) and type:

```
python --version
```

You should see something like `Python 3.12.x`.

### Mac

```bash
brew install python@3.12
```

Or download from [python.org/downloads](https://www.python.org/downloads/).

### Linux

```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
```

---

## Step 2: Download the Project

### Option A: Using Git (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/grindstone_apex.git
cd grindstone_apex
```

### Option B: Download ZIP

1. Go to the GitHub repository
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file to a folder (e.g., `C:\Users\YourName\Documents\grindstone_apex`)
5. Open Command Prompt and navigate to it:

```
cd C:\Users\YourName\Documents\grindstone_apex
```

---

## Step 3: Create a Virtual Environment

A virtual environment keeps the project's dependencies separate from your system Python. Do this from inside the project folder.

### Windows

```
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your command line.

### Mac / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 4: Install Dependencies

With your virtual environment activated:

```
pip install -r requirements.txt
```

This installs everything the bot needs (ccxt, vectorbt, telegram, etc.). It may take 2-5 minutes.

**If you see errors about `ta-lib`**: This library requires a C dependency. You can skip it — the bot doesn't require it. Remove the `ta-lib` line from `requirements.txt` and run `pip install -r requirements.txt` again.

**If you see errors about `torch`**: PyTorch is large (~2GB). If you don't need the transformer neural network features, you can remove `torch` and `transformers` from `requirements.txt`.

---

## Step 5: Create a Blofin Account

Blofin is the crypto exchange where the bot trades.

1. Go to [blofin.com](https://blofin.com)
2. Sign up for an account
3. Complete identity verification (KYC) if required
4. Deposit funds (start small — $50-100 is fine for testing)

---

## Step 6: Get Blofin API Keys

1. Log in to Blofin
2. Go to **Account** → **API Management**
3. Click **Create API Key**
4. Set permissions:
   - **Read** — enabled
   - **Trade** — enabled
   - **Withdraw** — **DISABLED** (never enable this for a bot)
5. Set an API passphrase (remember this — you'll need it)
6. Copy your:
   - **API Key**
   - **Secret Key**
   - **Passphrase**

Keep these safe. Never share them.

---

## Step 7: Create a Telegram Bot

1. Open Telegram on your phone or desktop
2. Search for **@BotFather** and start a chat
3. Send: `/newbot`
4. BotFather will ask for a name — enter: `Grindstone Apex` (or whatever you like)
5. BotFather will ask for a username — enter something unique like: `grindstone_apex_bot`
6. BotFather will give you a **bot token** that looks like:

```
8598647728:AAGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Copy this token. You'll need it in Step 9.

---

## Step 8: Get Your Telegram Chat ID

You need your personal chat ID so the bot only responds to you.

1. Search for **@userinfobot** on Telegram and start a chat
2. Send any message
3. It will reply with your **ID** — a number like `7034978634`
4. Copy this number

---

## Step 9: Configure the .env File

Create a file called `.env` in the project root folder (same folder as `telegram_bot.py`).

### Windows

Open Notepad and paste the following, filling in your values:

```env
# Exchange Configuration
EXCHANGE_TYPE=blofin
BLOFIN_API_KEY=your_api_key_here
BLOFIN_API_SECRET=your_secret_key_here
BLOFIN_PASSPHRASE=your_passphrase_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Database
DATABASE_URL=sqlite:///grindstone_apex.db

# Trading Settings (optional — these are defaults)
DEFAULT_PAIRS=BTC/USDT:USDT,ETH/USDT:USDT,XAU/USDT:USDT,XAG/USDT:USDT
DEFAULT_TIMEFRAME=15m
AUTO_DEPLOY_ENABLED=false
AUTO_DEPLOY_THRESHOLD=85
```

Save it as `.env` (make sure it's not saved as `.env.txt` — in Notepad, change "Save as type" to "All Files").

### Mac / Linux

```bash
cp .env.example .env
nano .env
# Fill in your values, save with Ctrl+X
```

---

## Step 10: Run the Telegram Bot

With your virtual environment activated and `.env` configured:

```
python telegram_bot.py
```

You should see:

```
============================================================
GRINDSTONE APEX - TELEGRAM BOT
============================================================
Bot token: ...xxxxxxxx
Chat ID: 7034978634
Auto-deploy: OFF (threshold: 85)
Bot starting... Press Ctrl+C to stop.
```

And you'll get a startup message in Telegram.

---

## Step 11: Run Your First Backtest

In your Telegram chat with the bot:

1. Type `/` — you'll see the full command menu appear
2. Tap `/backtest`
3. The bot will:
   - Fetch live market data from Blofin (15-minute candles)
   - Generate 500 random strategies across 9 types
   - Backtest each one against real data
   - Score them and save results
4. Wait for the results message (usually 2-10 minutes depending on your computer)
5. Run `/backtest` again to start Generation 2 — this time it breeds from the winners

**Tip**: Run 5-10 generations before expecting good strategies. Evolution takes time.

---

## Step 12: View and Inspect Strategies

After backtesting completes:

1. Send `/elite` to see the top strategies per pair
2. Each strategy shows a short ID, score, win rate, and strategy type:

```
📈 BTC/USDT:USDT
  1. `a1b2c3d4` Score: 72.3 | Win: 58% | Profit: 4.2% (ema_crossover long)
  2. `e5f6g7h8` Score: 65.1 | Win: 52% | Profit: 2.8% (macd short)
```

3. Send `/inspect a1b2c3d4` to see full details:
   - Strategy type and direction (long/short)
   - All indicator parameters
   - Risk management settings
   - Full backtest metrics (Sharpe, drawdown, profit factor, trade count)

---

## Step 13: Deploy a Strategy to Live Trading

Once you find a strategy you like:

1. Send `/deploy a1b2c3d4` (using the short ID from `/elite`)
2. The bot confirms deployment with all the details
3. The strategy is now live-trading on Blofin

**Monitor your positions:**

- `/positions` — see open trades
- `/balance` — check your account balance
- `/history 10` — see the last 10 closed trades

**Stop trading:**

- `/stoplive BTC` — stop trading for a specific pair
- `/kill` — emergency stop: close all positions and halt everything

**Important safety tips:**

- Start with auto-deploy OFF (`AUTO_DEPLOY_ENABLED=false` in `.env`)
- Always inspect strategies before deploying
- Start with a small account balance
- Monitor the first few trades closely

---

## Step 14: Run the TUI Dashboard (Optional)

For a terminal-based visual dashboard:

```
python main.py
```

This shows real-time generation progress, strategy leaderboards, and system status in your terminal.

---

## Step 15: Keep It Running 24/7

### Windows — Run as Background Service

1. Create a `.bat` file called `start_bot.bat`:

```bat
@echo off
cd C:\Users\YourName\Documents\grindstone_apex
call venv\Scripts\activate
python telegram_bot.py
```

2. Press Win+R, type `shell:startup`, press Enter
3. Copy `start_bot.bat` into this folder — the bot will now start automatically when you log in

### Linux — Run with systemd

Create `/etc/systemd/system/grindstone.service`:

```ini
[Unit]
Description=Grindstone Apex Trading Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/grindstone_apex
ExecStart=/home/yourusername/grindstone_apex/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable grindstone
sudo systemctl start grindstone
```

### VPS / Cloud Server

For true 24/7 operation, run the bot on a cheap VPS ($5-10/month):

- DigitalOcean (1GB droplet)
- Vultr
- Hetzner

Upload the project, install dependencies, and run with `systemd` or `tmux`/`screen`.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'xxx'"

Your virtual environment isn't activated, or you missed installing dependencies.

```
venv\Scripts\activate
pip install -r requirements.txt
```

### "TypeError: can't multiply sequence by non-int of type 'float'"

This was a bug in mutation — make sure you have the latest code that skips non-numeric parameters in `genetic_algorithm.py`.

### Bot says "No qualifying strategies" after /elite

You need to run more generations. The first 1-3 generations often have no strategies that meet the minimum criteria. Keep running `/backtest` — by generation 5-10 you should see elite strategies emerging.

### "Connection error" or "Network unreachable"

Check your internet connection. The bot needs to reach Blofin's API to fetch market data. If you're behind a firewall or VPN, make sure `api.blofin.com` is accessible.

### "Invalid API key"

Double-check your `.env` file:

- No extra spaces around the `=` sign
- No quotes around the values
- The passphrase matches exactly what you set on Blofin

### TUI won't start

Make sure you have `textual` installed:

```
pip install textual>=0.45.0
```

### How to update the code

```
git pull origin main
pip install -r requirements.txt
```

Then restart the bot (`Ctrl+C` and `python telegram_bot.py`).

---

## Adding More Trading Pairs

Edit the `PAIRS` list in `run_backtest.py` or `telegram_bot.py`:

```python
PAIRS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "SOL/USDT:USDT",   # add new pairs like this
    "DOGE/USDT:USDT",
]
```

Any pair available on Blofin as a USDT perpetual future can be added.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `EXCHANGE_TYPE` | `blofin` | Exchange to use |
| `BLOFIN_API_KEY` | — | Your Blofin API key |
| `BLOFIN_API_SECRET` | — | Your Blofin API secret |
| `BLOFIN_PASSPHRASE` | — | Your Blofin API passphrase |
| `TELEGRAM_BOT_TOKEN` | — | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | — | Your Telegram user ID |
| `DATABASE_URL` | `sqlite:///grindstone_apex.db` | Database connection string |
| `AUTO_DEPLOY_ENABLED` | `false` | Auto-deploy strategies scoring above threshold |
| `AUTO_DEPLOY_THRESHOLD` | `85` | Minimum score for auto-deploy (0-100) |
| `DEFAULT_PAIRS` | BTC,ETH,XAU,XAG | Pairs to backtest |
| `DEFAULT_TIMEFRAME` | `15m` | Candle timeframe |

---

*Questions? Open an issue on GitHub or check the README for more details.*
