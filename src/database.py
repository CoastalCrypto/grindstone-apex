"""Database configuration and models."""
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:password@localhost/grindstone_apex")

# SQLite doesn't support pool_size/max_overflow
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv("DATABASE_ECHO", "False").lower() == "true",
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=40
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Strategy(Base):
    """Strategy definition and metadata."""
    __tablename__ = "strategies"

    id = Column(String(50), primary_key=True, index=True)
    pair = Column(String(20), nullable=False, index=True)

    # Parameters
    timeframes = Column(JSON, nullable=False)  # [15, 60, 240]
    indicators = Column(JSON, nullable=False)  # Dict of indicator params
    position_sizing = Column(JSON, nullable=False)
    risk_management = Column(JSON, nullable=False)

    # Metadata
    source = Column(String(50), nullable=False)  # 'genetic_algo' or 'transformer'
    generation_id = Column(Integer, nullable=False, index=True)
    parent_strategy_id = Column(String(50), ForeignKey("strategies.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, backtested, elite, deployed, retired, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    backtest_results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")
    live_trades = relationship("LiveTrade", back_populates="strategy", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_pair_generation', 'pair', 'generation_id'),
        Index('idx_status_pair', 'status', 'pair'),
    )

    @property
    def parent_id(self) -> str:
        """Alias for parent_strategy_id for backwards compatibility."""
        return self.parent_strategy_id

    @parent_id.setter
    def parent_id(self, value: str):
        self.parent_strategy_id = value


class BacktestResult(Base):
    """Results from backtesting a strategy."""
    __tablename__ = "backtest_results"

    id = Column(String(50), primary_key=True, index=True)
    strategy_id = Column(String(50), ForeignKey("strategies.id"), nullable=False, index=True)

    # Metrics
    total_profit = Column(Float, nullable=False)
    total_profit_pct = Column(Float, nullable=False)
    win_count = Column(Integer, nullable=False)
    loss_count = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)

    # Risk Metrics
    sharpe_ratio = Column(Float, nullable=False)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=True)
    recovery_factor = Column(Float, nullable=True)

    # Trade Details
    avg_trade_duration = Column(Float, nullable=True)  # in hours
    best_trade = Column(Float, nullable=True)
    worst_trade = Column(Float, nullable=True)

    # Scoring
    composite_score = Column(Float, nullable=False, index=True)  # 0-100
    meets_criteria = Column(Boolean, default=False, index=True)

    # Full Results (JSON backup)
    full_metrics = Column(JSON, nullable=False)

    # Timing
    backtest_start_date = Column(DateTime, nullable=False)
    backtest_end_date = Column(DateTime, nullable=False)
    tested_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    strategy = relationship("Strategy", back_populates="backtest_results")

    __table_args__ = (
        Index('idx_strategy_score', 'strategy_id', 'composite_score'),
    )


class LiveTrade(Base):
    """Individual trades executed in live trading."""
    __tablename__ = "live_trades"

    id = Column(String(50), primary_key=True, index=True)
    strategy_id = Column(String(50), ForeignKey("strategies.id"), nullable=False, index=True)

    # Trade Details
    pair = Column(String(20), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=True)

    # Sizing
    size = Column(Float, nullable=False)
    entry_value = Column(Float, nullable=False)

    # P&L
    pnl = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)

    # Order IDs
    entry_order_id = Column(String(50), nullable=True)
    exit_order_id = Column(String(50), nullable=True)

    # Status
    status = Column(String(20), default="open")  # open, closed, cancelled
    exit_reason = Column(String(50), nullable=True)  # tp, sl, manual, cancelled

    # Execution
    fees_paid = Column(Float, default=0.0)
    slippage = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    strategy = relationship("Strategy", back_populates="live_trades")

    __table_args__ = (
        Index('idx_strategy_pair_time', 'strategy_id', 'pair', 'entry_time'),
    )


class StrategyPerformance(Base):
    """Summary performance metrics for each strategy (updated continuously)."""
    __tablename__ = "strategy_performance"

    id = Column(String(50), primary_key=True, index=True, default=lambda: f"perf_{uuid.uuid4().hex[:12]}")
    strategy_id = Column(String(50), ForeignKey("strategies.id"), unique=True, nullable=False)

    # Backtest Summary
    backtest_total_profit = Column(Float, nullable=True)
    backtest_win_rate = Column(Float, nullable=True)
    backtest_sharpe = Column(Float, nullable=True)

    # Live Trading Summary (updated as trades close)
    live_total_profit = Column(Float, default=0.0)
    live_total_trades = Column(Integer, default=0)
    live_win_rate = Column(Float, nullable=True)
    live_last_updated = Column(DateTime, nullable=True)

    # Comparison
    live_vs_backtest_drift = Column(Float, nullable=True)
    performance_stable = Column(Boolean, default=True)

    # Status
    deployed = Column(Boolean, default=False)
    live_active = Column(Boolean, default=True)  # Whether actively trading right now
    retired = Column(Boolean, default=False)
    retirement_reason = Column(String(200), nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_deployed_profit', 'deployed', 'live_total_profit'),
    )


class GenerationRun(Base):
    """Track each generation run of strategy generation."""
    __tablename__ = "generation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generation_id = Column(Integer, unique=True, nullable=False, index=True)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Statistics
    strategies_generated = Column(Integer, default=0)
    strategies_backtested = Column(Integer, default=0)
    strategies_passed = Column(Integer, default=0)

    # Sources
    ga_strategies = Column(Integer, default=0)
    transformer_strategies = Column(Integer, default=0)

    # Results
    top_strategy_id = Column(String(50), nullable=True)
    top_strategy_score = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    error_message = Column(String(500), nullable=True)

    run_metadata = Column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index('idx_status_date', 'status', 'started_at'),
    )


class SystemMetrics(Base):
    """System health and performance metrics."""
    __tablename__ = "system_metrics"

    id = Column(String(50), primary_key=True, index=True)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Generation
    strategies_in_queue = Column(Integer, default=0)
    backtest_queue_time = Column(Float, nullable=True)  # seconds

    # Performance
    avg_backtest_time = Column(Float, nullable=True)  # seconds per strategy
    total_strategies_tested = Column(Integer, default=0)

    # System Health
    database_size_gb = Column(Float, nullable=True)
    cache_size_gb = Column(Float, nullable=True)
    cpu_usage_pct = Column(Float, nullable=True)
    memory_usage_pct = Column(Float, nullable=True)

    # Account
    account_balance = Column(Float, nullable=True)
    account_free = Column(Float, nullable=True)
    account_used = Column(Float, nullable=True)
    total_live_profit = Column(Float, default=0.0)
    active_strategies = Column(Integer, default=0)
    open_positions = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
    )


def init_db():
    """Initialize all database tables."""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_db():
    """Get database session (for FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
