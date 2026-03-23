"""Historical data loader for backtesting."""
import pandas as pd
import yfinance as yf
import ccxt
import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Redis connection for caching
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True
)
CACHE_TTL = int(os.getenv("REDIS_TTL", 86400))


class HistoricalDataLoader:
    """Load and cache historical market data for backtesting."""

    def __init__(self, source: str = "yfinance"):
        """
        Initialize data loader.

        Args:
            source: 'yfinance' or 'ccxt' for exchange data
        """
        self.source = source
        if source == "ccxt":
            from src.config import get_settings
            settings = get_settings()
            self.exchange = getattr(ccxt, settings.exchange_type)({
                "apiKey": settings.exchange_api_key,
                "secret": settings.exchange_secret,
                "password": settings.exchange_password,
                "enableRateLimit": True,
            })

    def load_candles(
        self,
        pair: str,
        timeframe: int,
        days_back: int = 365,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Load OHLCV candles for a pair.

        Args:
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe in minutes (15, 60, 240)
            days_back: How many days of history to load
            use_cache: Whether to use Redis cache

        Returns:
            DataFrame with columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
        cache_key = f"candles:{pair}:{timeframe}:{days_back}"

        # Try cache first
        if use_cache:
            cached = redis_client.get(cache_key)
            if cached:
                logger.info(f"Loaded {pair} {timeframe}m from cache")
                from io import StringIO
                cached_str = cached if isinstance(cached, str) else cached.decode("utf-8")
                df = pd.read_json(StringIO(cached_str))
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                return df

        # Fetch from source
        logger.info(f"Fetching {pair} {timeframe}m from {self.source}...")
        if self.source == "yfinance":
            df = self._fetch_from_yfinance(pair, timeframe, days_back)
        else:
            df = self._fetch_from_ccxt(pair, timeframe, days_back)

        # Cache result
        if use_cache and len(df) > 0:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                df.to_json(date_format='iso')
            )
            logger.info(f"Cached {pair} {timeframe}m ({len(df)} candles)")

        return df

    def _fetch_from_yfinance(self, pair: str, timeframe: int, days_back: int) -> pd.DataFrame:
        """Fetch data from yfinance."""
        try:
            # Convert timeframe to pandas frequency
            freq_map = {15: "15min", 60: "1h", 240: "4h"}
            interval = freq_map.get(timeframe, f"{timeframe}min")

            # Get end date
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            # Fetch data
            data = yf.download(
                pair,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False
            )

            if data.empty:
                logger.warning(f"No data found for {pair} {timeframe}m")
                return pd.DataFrame()

            # Standardize column names
            data = data.reset_index()
            data.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

            # Clean data
            data = data.dropna()
            data = data[data['volume'] > 0]

            logger.info(f"Fetched {len(data)} candles for {pair} {timeframe}m")
            return data

        except Exception as e:
            logger.error(f"Error fetching {pair} from yfinance: {e}")
            return pd.DataFrame()

    def _fetch_from_ccxt(self, pair: str, timeframe: int, days_back: int) -> pd.DataFrame:
        """Fetch data from CCXT exchange."""
        try:
            # Convert timeframe to CCXT format
            # Blofin uses 1H/4H not 60m/240m
            tf_map = {1: "1m", 5: "5m", 15: "15m", 30: "30m",
                       60: "1H", 120: "2H", 240: "4H", 360: "6H",
                       720: "12H", 1440: "1D"}
            timeframe_str = tf_map.get(timeframe, f"{timeframe}m")

            all_candles = []
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            current_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)

            # Fetch in chunks (CCXT has limits)
            while current_timestamp < end_timestamp:
                candles = self.exchange.fetch_ohlcv(
                    pair,
                    timeframe=timeframe_str,
                    since=current_timestamp,
                    limit=1000
                )

                if not candles:
                    break

                all_candles.extend(candles)
                current_timestamp = candles[-1][0] + 1

            # Convert to DataFrame
            if not all_candles:
                logger.warning(f"No data found for {pair} {timeframe}m on {self.source}")
                return pd.DataFrame()

            df = pd.DataFrame(
                all_candles,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.drop_duplicates(subset=['timestamp'])
            df = df.sort_values('timestamp')

            logger.info(f"Fetched {len(df)} candles for {pair} {timeframe}m from {self.source}")
            return df

        except Exception as e:
            logger.error(f"Error fetching {pair} from CCXT: {e}")
            return pd.DataFrame()

    def align_timeframes(self, pair: str) -> Dict[int, pd.DataFrame]:
        """
        Load and align multiple timeframes for a pair.

        Returns:
            Dict mapping timeframe (minutes) to DataFrame
        """
        timeframes = [15, 60, 240]  # 15m, 1h, 4h
        data = {}

        for tf in timeframes:
            df = self.load_candles(pair, tf)
            if not df.empty:
                data[tf] = df
            else:
                logger.warning(f"Failed to load {tf}m data for {pair}")

        # Align to common timestamps (intersection)
        if len(data) < len(timeframes):
            logger.warning(f"Could not load all timeframes for {pair}")
            return data

        # Keep only timestamps present in all timeframes
        common_timestamps = set(data[15]['timestamp'])
        for tf in [60, 240]:
            common_timestamps &= set(data[tf]['timestamp'])

        for tf in timeframes:
            data[tf] = data[tf][data[tf]['timestamp'].isin(common_timestamps)]
            data[tf] = data[tf].sort_values('timestamp').reset_index(drop=True)

        logger.info(f"Aligned {len(common_timestamps)} candles for {pair} across timeframes")
        return data

    def get_multiple_pairs(self, pairs: list, timeframe: int, days_back: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Load data for multiple pairs.

        Args:
            pairs: List of trading pairs
            timeframe: Timeframe in minutes
            days_back: Days of history

        Returns:
            Dict mapping pair to DataFrame
        """
        data = {}
        for pair in pairs:
            df = self.load_candles(pair, timeframe, days_back)
            if not df.empty:
                data[pair] = df
            else:
                logger.warning(f"Failed to load data for {pair}")

        return data

    def clear_cache(self, pair: Optional[str] = None):
        """Clear cached data."""
        if pair:
            # Clear specific pair
            pattern = f"candles:{pair}:*"
            for key in redis_client.scan_iter(match=pattern):
                redis_client.delete(key)
            logger.info(f"Cleared cache for {pair}")
        else:
            # Clear all candle data
            for key in redis_client.scan_iter(match="candles:*"):
                redis_client.delete(key)
            logger.info("Cleared all candle cache")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "total_cached_keys": sum(1 for _ in redis_client.scan_iter(match="candles:*")),
            "cache_memory_usage": redis_client.info("memory")
        }


# Singleton instance
_loader = None


def get_data_loader(source: str = "ccxt") -> HistoricalDataLoader:
    """Get or create data loader instance."""
    global _loader
    if _loader is None:
        _loader = HistoricalDataLoader(source=source)
    return _loader
