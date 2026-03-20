"""Market regime detection - identify trending vs ranging conditions."""
import logging
import numpy as np
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime types."""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    VOLATILE = "volatile"


class MarketRegimeDetector:
    """Detect market regime from price action."""

    def __init__(self):
        """Initialize detector."""
        pass

    def detect_regime(self, candles) -> Dict:
        """
        Detect current market regime.

        Args:
            candles: DataFrame with OHLCV data

        Returns:
            Regime analysis dict
        """
        if candles.empty or len(candles) < 50:
            return {"regime": MarketRegime.SIDEWAYS.value, "confidence": 0}

        try:
            close = candles['close'].values
            high = candles['high'].values
            low = candles['low'].values

            # Calculate multiple indicators
            trend = self._calculate_trend(close)
            volatility = self._calculate_volatility(close)
            atr = self._calculate_atr(high, low, close)
            adx = self._calculate_adx(high, low, close)

            # Determine regime
            regime = self._classify_regime(trend, volatility, adx)

            return {
                "regime": regime.value,
                "trend": trend,
                "volatility": volatility,
                "atr": float(atr),
                "adx": float(adx),
                "confidence": self._calculate_confidence(trend, adx)
            }

        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return {"regime": MarketRegime.SIDEWAYS.value, "confidence": 0}

    def _calculate_trend(self, close: np.ndarray) -> float:
        """
        Calculate trend strength.

        Returns:
            Trend value -1 to 1 (negative = downtrend, positive = uptrend)
        """
        try:
            # Calculate SMA
            sma_20 = np.mean(close[-20:])
            sma_50 = np.mean(close[-50:])

            # Price vs SMAs
            current = close[-1]
            trend_strength = (current - sma_50) / sma_50

            # Bias towards SMA relationship
            if sma_20 > sma_50:
                trend_strength += 0.1
            elif sma_20 < sma_50:
                trend_strength -= 0.1

            # Linear regression for momentum
            x = np.arange(len(close[-20:]))
            y = close[-20:]
            coeffs = np.polyfit(x, y, 1)
            momentum = coeffs[0] / close[-1]

            return float(trend_strength + momentum * 0.5)

        except:
            return 0.0

    def _calculate_volatility(self, close: np.ndarray) -> float:
        """Calculate volatility (standard deviation of returns)."""
        try:
            returns = np.diff(close[-50:]) / close[-50:-1]
            volatility = np.std(returns) * 100  # As percentage

            return float(volatility)

        except:
            return 0.0

    def _calculate_atr(self, high: np.ndarray, low: np.ndarray,
                      close: np.ndarray) -> float:
        """Calculate Average True Range."""
        try:
            tr = np.maximum(
                high[-14:] - low[-14:],
                np.maximum(
                    np.abs(high[-14:] - close[-15:-1]),
                    np.abs(low[-14:] - close[-15:-1])
                )
            )
            atr = np.mean(tr)

            return float(atr)

        except:
            return 0.0

    def _calculate_adx(self, high: np.ndarray, low: np.ndarray,
                      close: np.ndarray) -> float:
        """
        Calculate Average Directional Index.

        Returns:
            ADX value 0-100
        """
        try:
            # Directional movements
            up_move = high[-1] - high[-2]
            down_move = low[-2] - low[-1]

            plus_dm = np.maximum(up_move, 0) if up_move > down_move else 0
            minus_dm = np.maximum(down_move, 0) if down_move > up_move else 0

            # True range
            tr = np.maximum(
                high[-1] - low[-1],
                np.maximum(
                    np.abs(high[-1] - close[-2]),
                    np.abs(low[-1] - close[-2])
                )
            )

            # Directional indicators
            plus_di = (plus_dm / tr * 100) if tr > 0 else 0
            minus_di = (minus_dm / tr * 100) if tr > 0 else 0

            # DX
            dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100) \
                 if (plus_di + minus_di) > 0 else 0

            # Simplified ADX (smoothed DX)
            adx = dx * 0.7 + (np.abs(plus_di - minus_di)) * 0.3

            return float(np.clip(adx, 0, 100))

        except:
            return 0.0

    def _classify_regime(self, trend: float, volatility: float,
                        adx: float) -> MarketRegime:
        """
        Classify regime based on indicators.

        Args:
            trend: Trend value -1 to 1
            volatility: Volatility in percent
            adx: ADX value 0-100

        Returns:
            Regime classification
        """
        # Strong directional move
        if adx > 40:
            if trend > 0.05:
                return MarketRegime.STRONG_UPTREND
            elif trend < -0.05:
                return MarketRegime.STRONG_DOWNTREND

        # Weak directional move
        if adx > 25:
            if trend > 0:
                return MarketRegime.WEAK_UPTREND
            else:
                return MarketRegime.WEAK_DOWNTREND

        # High volatility without direction
        if volatility > 3.0:
            return MarketRegime.VOLATILE

        # Ranging/Sideways
        return MarketRegime.SIDEWAYS

    def _calculate_confidence(self, trend: float, adx: float) -> float:
        """Calculate confidence in regime classification."""
        trend_confidence = min(abs(trend) * 2, 1.0)
        adx_confidence = min(adx / 100, 1.0)

        return float((trend_confidence + adx_confidence) / 2)

    def get_recommended_strategies(self, regime_analysis: Dict) -> List[str]:
        """
        Get recommended strategy types for current regime.

        Args:
            regime_analysis: Output from detect_regime()

        Returns:
            List of recommended strategy names
        """
        regime = regime_analysis.get("regime", "sideways")

        recommendations = {
            MarketRegime.STRONG_UPTREND.value: [
                "momentum_follow",
                "trend_following",
                "breakout"
            ],
            MarketRegime.WEAK_UPTREND.value: [
                "pullback",
                "range_bound",
                "mean_reversion"
            ],
            MarketRegime.SIDEWAYS.value: [
                "mean_reversion",
                "range_bound",
                "oscillator_based"
            ],
            MarketRegime.WEAK_DOWNTREND.value: [
                "pullback",
                "range_bound",
                "mean_reversion"
            ],
            MarketRegime.STRONG_DOWNTREND.value: [
                "short_momentum",
                "trend_short",
                "short_breakout"
            ],
            MarketRegime.VOLATILE.value: [
                "options_strategies",
                "volatility_expansion",
                "breakout"
            ]
        }

        return recommendations.get(regime, ["range_bound"])

    def should_pause_trading(self, regime_analysis: Dict) -> bool:
        """
        Determine if trading should be paused.

        Args:
            regime_analysis: Output from detect_regime()

        Returns:
            True if trading should be paused
        """
        # Pause if confidence is too low and regime is volatile
        if regime_analysis.get("confidence", 0) < 0.3 and \
           regime_analysis.get("regime") == MarketRegime.VOLATILE.value:
            return True

        # Pause if volatility is extremely high
        if regime_analysis.get("volatility", 0) > 5.0:
            return True

        return False
