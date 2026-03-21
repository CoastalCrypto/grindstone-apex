"""Configuration management."""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://trader:password@localhost/grindstone_apex"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 86400

    # Exchange API
    exchange_type: str = "blofin"
    exchange_api_key: str = ""
    exchange_secret: str = ""
    exchange_password: str = ""
    exchange_sandbox: bool = True

    # Strategy Configuration
    backtest_year_range: int = 365
    strategy_test_timeframes: List[int] = [15, 60, 240]  # 15m, 1h, 4h
    target_win_rate: float = 0.40
    target_profit_pct: float = 0.20
    target_sharpe_ratio: float = 1.0

    # Ralph Loop Configuration
    elite_threshold: float = 0.20  # Keep top 20%
    mutation_rate: float = 0.15
    second_chance_mutations: int = 5
    strategies_per_generation: int = 500

    # Position Sizing
    position_size_type: str = "percent_of_balance"
    position_size_amount: float = 0.5
    max_positions: int = 1
    leverage: float = 1.0

    # Risk Management
    stop_loss_atr_multiplier: float = 3.5
    take_profit_percent: float = 0.20
    breakeven_on_profit: bool = True
    max_drawdown_limit: float = 0.30

    # Live Trading
    live_trading_enabled: bool = False
    deploy_top_n_strategies: int = 2
    pairs_to_trade: str = "BTC/USDT:USDT,ETH/USDT:USDT,XAU/USDT:USDT,XAG/USDT:USDT"
    target_weekly_profit_usdt: float = 7500
    performance_drift_threshold: float = 0.15

    # Live Exchange Connection (distinct from backtest exchange)
    live_exchange: str = "coinbase"
    live_api_key: str = ""
    live_api_secret: str = ""
    live_api_password: str = ""
    sandbox_mode: bool = True

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # System
    log_level: str = "INFO"
    workers: int = 4
    env: str = "development"
    initial_account_balance: float = 10000.0
    trading_fees: float = 0.001  # 0.1%

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def pairs_list(self) -> List[str]:
        """Get list of trading pairs."""
        return [p.strip() for p in self.pairs_to_trade.split(",")]

    @property
    def timeframes_list(self) -> List[int]:
        """Get list of timeframes (in minutes)."""
        return self.strategy_test_timeframes


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
