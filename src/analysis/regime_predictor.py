"""Market regime predictor - forecast market condition transitions."""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RegimeTransitionModel:
    """Predicts market regime transitions using historical patterns."""

    def __init__(self, lookback_periods: int = 100):
        """
        Initialize predictor.

        Args:
            lookback_periods: Number of candles to analyze
        """
        self.lookback_periods = lookback_periods
        self.transition_matrix = None  # Markov transition matrix
        self.regime_patterns = {}

    def fit(self, historical_regimes: List[str]) -> None:
        """
        Fit transition model from historical regimes.

        Args:
            historical_regimes: List of regime names in order
        """
        if len(historical_regimes) < 2:
            return

        unique_regimes = list(set(historical_regimes))
        n_regimes = len(unique_regimes)

        # Initialize transition matrix
        self.transition_matrix = np.zeros((n_regimes, n_regimes))

        # Count transitions
        for i in range(len(historical_regimes) - 1):
            from_regime = unique_regimes.index(historical_regimes[i])
            to_regime = unique_regimes.index(historical_regimes[i + 1])
            self.transition_matrix[from_regime, to_regime] += 1

        # Normalize to probabilities
        row_sums = self.transition_matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1  # Avoid division by zero
        self.transition_matrix = self.transition_matrix / row_sums

        logger.info(f"Fitted transition matrix with {n_regimes} regimes")

    def predict_next_regime(self, current_regime: str) -> Dict[str, float]:
        """
        Predict probability of next regime.

        Args:
            current_regime: Current market regime

        Returns:
            Dict of regime probabilities
        """
        if self.transition_matrix is None:
            return {"unknown": 1.0}

        unique_regimes = ["strong_uptrend", "weak_uptrend", "sideways",
                         "weak_downtrend", "strong_downtrend", "volatile"]

        if current_regime not in unique_regimes:
            return {r: 1/len(unique_regimes) for r in unique_regimes}

        from_idx = unique_regimes.index(current_regime)
        probabilities = self.transition_matrix[from_idx]

        return {regime: float(prob) for regime, prob in zip(unique_regimes, probabilities)}

    def predict_regime_sequence(self, current_regime: str, steps: int = 5) -> List[Dict]:
        """
        Predict sequence of regime changes.

        Args:
            current_regime: Current regime
            steps: Number of periods to predict

        Returns:
            List of regime probability dicts
        """
        sequence = []
        current = current_regime

        for _ in range(steps):
            next_probs = self.predict_next_regime(current)
            sequence.append(next_probs)

            # Select most likely next regime
            current = max(next_probs.items(), key=lambda x: x[1])[0]

        return sequence


class RegimeFeatureExtractor:
    """Extract features for regime prediction from price action."""

    @staticmethod
    def extract_features(candles: Dict[str, np.ndarray],
                        lookback: int = 20) -> np.ndarray:
        """
        Extract features for regime prediction.

        Args:
            candles: Dict with 'close', 'high', 'low', 'volume'
            lookback: Lookback period

        Returns:
            Feature vector
        """
        close = candles.get("close", np.array([]))
        high = candles.get("high", np.array([]))
        low = candles.get("low", np.array([]))
        volume = candles.get("volume", np.array([]))

        if len(close) < lookback:
            return np.zeros(20)

        recent_close = close[-lookback:]
        recent_high = high[-lookback:]
        recent_low = low[-lookback:]
        recent_volume = volume[-lookback:]

        features = []

        # Momentum
        momentum = (close[-1] - close[-lookback]) / close[-lookback]
        features.append(momentum)

        # Volatility
        returns = np.diff(recent_close) / recent_close[:-1]
        volatility = np.std(returns)
        features.append(volatility)

        # Trend strength
        sma_short = np.mean(recent_close[-5:])
        sma_long = np.mean(recent_close)
        trend = (sma_short - sma_long) / sma_long
        features.append(trend)

        # Volume trend
        vol_trend = np.mean(recent_volume[-5:]) / np.mean(recent_volume)
        features.append(vol_trend)

        # Range
        range_pct = (recent_high.max() - recent_low.min()) / recent_close[-1]
        features.append(range_pct)

        # RSI
        rsi = RegimeFeatureExtractor._calculate_rsi(recent_close, 14)
        features.append(rsi)

        # MACD
        macd = RegimeFeatureExtractor._calculate_macd(recent_close)
        features.append(macd)

        # Bollinger Band position
        bb_pos = RegimeFeatureExtractor._calculate_bb_position(recent_close, 20, 2)
        features.append(bb_pos)

        # ADX
        adx = RegimeFeatureExtractor._calculate_adx(recent_high, recent_low, recent_close)
        features.append(adx)

        # Mean reversion indicator
        mean_reversion = RegimeFeatureExtractor._calculate_mean_reversion(recent_close)
        features.append(mean_reversion)

        # Pad to 20 features
        while len(features) < 20:
            features.append(0)

        return np.array(features[:20])

    @staticmethod
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI."""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100 if avg_gain > 0 else 50

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi / 100)  # Normalize to 0-1

    @staticmethod
    def _calculate_macd(prices: np.ndarray) -> float:
        """Calculate MACD."""
        ema_12 = np.mean(prices[-12:]) if len(prices) >= 12 else np.mean(prices)
        ema_26 = np.mean(prices[-26:]) if len(prices) >= 26 else np.mean(prices)

        macd = ema_12 - ema_26

        return float(np.tanh(macd / prices[-1]))  # Normalize

    @staticmethod
    def _calculate_bb_position(prices: np.ndarray, period: int = 20,
                               std_dev: float = 2) -> float:
        """Calculate Bollinger Band position (0-1)."""
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])

        bb_upper = sma + std_dev * std
        bb_lower = sma - std_dev * std

        current_price = prices[-1]

        position = (current_price - bb_lower) / (bb_upper - bb_lower)

        return float(np.clip(position, 0, 1))

    @staticmethod
    def _calculate_adx(high: np.ndarray, low: np.ndarray,
                      close: np.ndarray, period: int = 14) -> float:
        """Calculate ADX."""
        tr = np.maximum(
            high[-period:] - low[-period:],
            np.maximum(
                np.abs(high[-period:] - close[-period-1:-1]),
                np.abs(low[-period:] - close[-period-1:-1])
            )
        )

        up_move = high[-period:] - high[-period-1:-1]
        down_move = low[-period-1:-1] - low[-period:]

        plus_dm = np.where(up_move > down_move, np.maximum(up_move, 0), 0)
        minus_dm = np.where(down_move > up_move, np.maximum(down_move, 0), 0)

        plus_di = 100 * np.mean(plus_dm) / np.mean(tr) if np.mean(tr) > 0 else 0
        minus_di = 100 * np.mean(minus_dm) / np.mean(tr) if np.mean(tr) > 0 else 0

        adx = abs(plus_di - minus_di) / (plus_di + minus_di + 0.01)

        return float(np.clip(adx / 100, 0, 1))

    @staticmethod
    def _calculate_mean_reversion(prices: np.ndarray) -> float:
        """Calculate mean reversion tendency."""
        if len(prices) < 5:
            return 0

        returns = np.diff(prices) / prices[:-1]

        # Check if returns show mean reversion (negative autocorrelation)
        autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]

        return float(max(0, -autocorr))  # Positive for mean reversion


class RegimePredictionModel:
    """ML-based regime prediction (simplified)."""

    def __init__(self):
        """Initialize predictor."""
        self.transition_model = RegimeTransitionModel()
        self.feature_extractor = RegimeFeatureExtractor()

    def predict_regime_change_probability(self, current_regime: str,
                                         candles: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Predict probability of regime change.

        Args:
            current_regime: Current regime
            candles: Market data

        Returns:
            Dict with change probabilities
        """
        # Extract features
        features = self.feature_extractor.extract_features(candles)

        # Get transition probabilities
        transition_probs = self.transition_model.predict_next_regime(current_regime)

        # Combine with feature-based prediction
        # Features indicating high probability of change
        volatility = features[1]
        trend_strength = abs(features[2])

        change_probability = min(0.9, volatility * 2 + trend_strength * 0.5)

        return {
            "change_probability": float(change_probability),
            "current_regime": current_regime,
            "next_regime_probs": transition_probs,
            "features": features.tolist(),
            "volatility": float(features[1]),
            "trend_strength": float(abs(features[2]))
        }

    def get_regime_forecast(self, current_regime: str,
                           candles: Dict[str, np.ndarray],
                           periods: int = 5) -> List[Dict]:
        """
        Forecast regime for next N periods.

        Args:
            current_regime: Current regime
            candles: Market data
            periods: Number of periods

        Returns:
            List of period forecasts
        """
        forecast = []

        for period in range(periods):
            prediction = self.predict_regime_change_probability(current_regime, candles)
            forecast.append(prediction)

            # Update regime based on most likely next state
            next_probs = prediction["next_regime_probs"]
            current_regime = max(next_probs.items(), key=lambda x: x[1])[0]

        return forecast
