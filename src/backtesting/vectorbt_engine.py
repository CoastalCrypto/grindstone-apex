"""Fast backtesting engine with multiple strategy types and long/short support."""
import pandas as pd
import numpy as np
import vectorbt as vbt
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings

from .metrics import Trade, BacktestMetrics, calculate_atr

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class VectorBTBacktestEngine:
    """High-speed backtesting using VectorBT library with multi-indicator support."""

    def __init__(self, initial_balance: float = 10000.0, fees: float = 0.001):
        self.initial_balance = initial_balance
        self.fees = fees
        self.metrics_calculator = BacktestMetrics(initial_balance)

    def backtest_strategy(
        self,
        candles: pd.DataFrame,
        strategy_params: dict,
        strategy_id: str = None
    ) -> Dict:
        """Backtest a strategy against historical data."""
        try:
            buy_signals, sell_signals = self._generate_signals(candles, strategy_params)

            if buy_signals.sum() == 0:
                logger.warning(f"No buy signals generated for {strategy_id}")
                return self._empty_result()

            direction = strategy_params.get('direction', 'long')
            trades = self._execute_trades(candles, buy_signals, sell_signals, strategy_params, direction)

            if not trades:
                logger.warning(f"No trades executed for {strategy_id}")
                return self._empty_result()

            metrics = self.metrics_calculator.calculate(trades, strategy_params)

            return {
                "strategy_id": strategy_id,
                "num_trades": len(trades),
                "metrics": metrics,
                "trades": trades,
                "timestamp": datetime.utcnow(),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error backtesting strategy {strategy_id}: {e}")
            result = self._empty_result()
            result["error"] = str(e)
            return result

    def _generate_signals(
        self,
        candles: pd.DataFrame,
        strategy_params: dict
    ) -> Tuple[pd.Series, pd.Series]:
        """Generate buy/sell signals based on strategy type and indicators."""
        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        volume = candles['volume'].values
        n = len(close)

        buy_signal = np.zeros(n, dtype=bool)
        sell_signal = np.zeros(n, dtype=bool)

        strategy_type = strategy_params.get('strategy_type', 'sma_crossover')
        indicators = strategy_params.get('indicators', {})

        # ─── SMA CROSSOVER ───
        if strategy_type == 'sma_crossover':
            fast_p = int(round(indicators.get('sma_fast', 20)))
            slow_p = int(round(indicators.get('sma_slow', 50)))
            if fast_p >= slow_p:
                slow_p = fast_p + 20

            sma_fast = self._calculate_sma(close, fast_p)
            sma_slow = self._calculate_sma(close, slow_p)

            buy_signal = (sma_fast > sma_slow) & (np.roll(sma_fast, 1) <= np.roll(sma_slow, 1))
            sell_signal = (sma_fast < sma_slow) & (np.roll(sma_fast, 1) >= np.roll(sma_slow, 1))

        # ─── EMA CROSSOVER ───
        elif strategy_type == 'ema_crossover':
            fast_p = int(round(indicators.get('ema_fast', 12)))
            slow_p = int(round(indicators.get('ema_slow', 26)))
            if fast_p >= slow_p:
                slow_p = fast_p + 14

            ema_fast = self._calculate_ema(close, fast_p)
            ema_slow = self._calculate_ema(close, slow_p)

            buy_signal = (ema_fast > ema_slow) & (np.roll(ema_fast, 1) <= np.roll(ema_slow, 1))
            sell_signal = (ema_fast < ema_slow) & (np.roll(ema_fast, 1) >= np.roll(ema_slow, 1))

        # ─── BREAKOUT (Donchian Channel) ───
        elif strategy_type == 'breakout':
            period = int(round(indicators.get('breakout_period', 20)))
            rolling_high = pd.Series(high).rolling(period).max().values
            rolling_low = pd.Series(low).rolling(period).min().values

            buy_signal = close > np.roll(rolling_high, 1)
            sell_signal = close < np.roll(rolling_low, 1)

        # ─── VOLUME BREAKOUT ───
        elif strategy_type == 'volume_breakout':
            vol_period = int(round(indicators.get('volume_period', 20)))
            vol_mult = indicators.get('volume_multiplier', 2.0)
            price_period = int(round(indicators.get('price_period', 10)))

            avg_volume = pd.Series(volume).rolling(vol_period).mean().values
            volume_spike = volume > (avg_volume * vol_mult)

            price_up = close > np.roll(close, 1)
            price_down = close < np.roll(close, 1)

            buy_signal = volume_spike & price_up
            sell_signal = volume_spike & price_down

        # ─── RSI MEAN REVERSION ───
        elif strategy_type == 'rsi_reversal':
            rsi_period = int(round(indicators.get('rsi_period', 14)))
            rsi_buy = indicators.get('rsi_threshold_buy', 30)
            rsi_sell = indicators.get('rsi_threshold_sell', 70)

            rsi = self._calculate_rsi(close, rsi_period)

            # Buy when RSI crosses up from oversold
            buy_signal = (rsi > rsi_buy) & (np.roll(rsi, 1) <= rsi_buy)
            # Sell when RSI crosses down from overbought
            sell_signal = (rsi < rsi_sell) & (np.roll(rsi, 1) >= rsi_sell)

        # ─── BOLLINGER BOUNCE ───
        elif strategy_type == 'bollinger_bounce':
            bb_period = int(round(indicators.get('bollinger_period', 20)))
            bb_std = indicators.get('bollinger_std', 2.0)

            bb_upper, bb_lower, bb_mid = self._calculate_bollinger_bands(close, bb_period, bb_std)

            # Buy on bounce off lower band
            buy_signal = (close <= bb_lower) & (np.roll(close, 1) > np.roll(bb_lower, 1))
            # Sell on bounce off upper band
            sell_signal = (close >= bb_upper) & (np.roll(close, 1) < np.roll(bb_upper, 1))

        # ─── MACD ───
        elif strategy_type == 'macd':
            fast_p = int(round(indicators.get('macd_fast', 12)))
            slow_p = int(round(indicators.get('macd_slow', 26)))
            signal_p = int(round(indicators.get('macd_signal', 9)))

            macd_line, signal_line = self._calculate_macd(close, fast_p, slow_p, signal_p)

            buy_signal = (macd_line > signal_line) & (np.roll(macd_line, 1) <= np.roll(signal_line, 1))
            sell_signal = (macd_line < signal_line) & (np.roll(macd_line, 1) >= np.roll(signal_line, 1))

        # ─── OPENING RANGE BREAKOUT (ORB) ───
        elif strategy_type == 'orb':
            orb_bars = int(round(indicators.get('orb_bars', 4)))  # First N bars of "session"
            # Simulate session breaks every 96 bars (24 hours of 15m)
            session_len = 96
            for start in range(0, n - session_len, session_len):
                orb_end = min(start + orb_bars, n)
                orb_high = np.max(high[start:orb_end])
                orb_low = np.min(low[start:orb_end])

                for j in range(orb_end, min(start + session_len, n)):
                    if close[j] > orb_high and not buy_signal[j]:
                        buy_signal[j] = True
                        break
                for j in range(orb_end, min(start + session_len, n)):
                    if close[j] < orb_low and not sell_signal[j]:
                        sell_signal[j] = True
                        break

        # ─── LIQUIDITY SWEEP ───
        elif strategy_type == 'liquidity_sweep':
            lookback = int(round(indicators.get('sweep_lookback', 20)))
            reclaim_bars = int(round(indicators.get('reclaim_bars', 3)))

            for i in range(lookback + reclaim_bars, n):
                recent_low = np.min(low[i - lookback:i])
                recent_high = np.max(high[i - lookback:i])

                # Bullish sweep: price dips below recent low then reclaims
                if low[i] < recent_low and close[i] > recent_low:
                    buy_signal[i] = True

                # Bearish sweep: price spikes above recent high then drops
                if high[i] > recent_high and close[i] < recent_high:
                    sell_signal[i] = True

        elif strategy_type == 'fib_retracement':
            fib_lookback = int(round(indicators.get('fib_lookback', 50)))
            fib_level = indicators.get('fib_level', 0.618)
            fib_tolerance = indicators.get('fib_tolerance', 0.005)
            trend_period = int(round(indicators.get('trend_period', 30)))

            # EMA for trend direction
            trend_ema = self._calculate_ema(close, trend_period)

            for i in range(fib_lookback + 1, n):
                window_high = np.max(high[i - fib_lookback:i])
                window_low = np.min(low[i - fib_lookback:i])
                swing_range = window_high - window_low

                if swing_range < 1e-10:
                    continue

                # Uptrend: price above EMA, pullback to fib level = buy
                if close[i] > trend_ema[i]:
                    fib_price = window_high - (swing_range * fib_level)
                    if abs(close[i] - fib_price) / fib_price < fib_tolerance:
                        buy_signal[i] = True
                    if close[i] >= window_high * 0.998:
                        sell_signal[i] = True

                # Downtrend: price below EMA, pullback up to fib level = sell
                elif close[i] < trend_ema[i]:
                    fib_price = window_low + (swing_range * fib_level)
                    if abs(close[i] - fib_price) / fib_price < fib_tolerance:
                        sell_signal[i] = True
                    if close[i] <= window_low * 1.002:
                        buy_signal[i] = True

        # ─── STOCHASTIC OSCILLATOR ───
        elif strategy_type == 'stochastic':
            k_period = int(round(indicators.get('stoch_k_period', 14)))
            d_period = int(round(indicators.get('stoch_d_period', 3)))
            oversold = indicators.get('stoch_oversold', 20)
            overbought = indicators.get('stoch_overbought', 80)

            k, d = self._calculate_stochastic(high, low, close, k_period, d_period)

            # Buy when %K crosses above %D in oversold zone
            for i in range(1, n):
                if not np.isnan(k[i]) and not np.isnan(d[i]):
                    if k[i] > d[i] and k[i - 1] <= d[i - 1] and k[i] < oversold + 15:
                        buy_signal[i] = True
                    if k[i] < d[i] and k[i - 1] >= d[i - 1] and k[i] > overbought - 15:
                        sell_signal[i] = True

        # ─── ADX TREND ───
        elif strategy_type == 'adx_trend':
            adx_period = int(round(indicators.get('adx_period', 14)))
            adx_thresh = indicators.get('adx_threshold', 25.0)
            di_period = int(round(indicators.get('di_period', 14)))

            adx, plus_di, minus_di = self._calculate_adx(high, low, close, adx_period)

            for i in range(1, n):
                if np.isnan(adx[i]):
                    continue
                # Strong trend + DI crossover
                if adx[i] > adx_thresh:
                    if plus_di[i] > minus_di[i] and plus_di[i - 1] <= minus_di[i - 1]:
                        buy_signal[i] = True
                    elif minus_di[i] > plus_di[i] and minus_di[i - 1] <= plus_di[i - 1]:
                        sell_signal[i] = True

        # ─── ICHIMOKU CLOUD ───
        elif strategy_type == 'ichimoku':
            tenkan_p = int(round(indicators.get('tenkan_period', 9)))
            kijun_p = int(round(indicators.get('kijun_period', 26)))
            senkou_b_p = int(round(indicators.get('senkou_b_period', 52)))

            ichi = self._calculate_ichimoku(high, low, close, tenkan_p, kijun_p, senkou_b_p)
            tenkan = ichi["tenkan"]
            kijun = ichi["kijun"]
            senkou_a = ichi["senkou_a"]
            senkou_b = ichi["senkou_b"]

            for i in range(1, n):
                if np.isnan(tenkan[i]) or np.isnan(kijun[i]):
                    continue
                # TK cross above cloud = buy
                if (tenkan[i] > kijun[i] and tenkan[i - 1] <= kijun[i - 1]
                        and close[i] > max(senkou_a[i], senkou_b[i])):
                    buy_signal[i] = True
                # TK cross below cloud = sell
                elif (tenkan[i] < kijun[i] and tenkan[i - 1] >= kijun[i - 1]
                      and close[i] < min(senkou_a[i], senkou_b[i])):
                    sell_signal[i] = True

        # ─── ACCUMULATION/DISTRIBUTION LINE ───
        elif strategy_type == 'ad_line':
            fast_p = int(round(indicators.get('ad_ema_fast', 5)))
            slow_p = int(round(indicators.get('ad_ema_slow', 20)))

            ad = self._calculate_ad_line(high, low, close, volume)
            ad_fast = self._calculate_ema(ad, fast_p)
            ad_slow = self._calculate_ema(ad, slow_p)

            # AD line EMA crossover signals
            buy_signal = (ad_fast > ad_slow) & (np.roll(ad_fast, 1) <= np.roll(ad_slow, 1))
            sell_signal = (ad_fast < ad_slow) & (np.roll(ad_fast, 1) >= np.roll(ad_slow, 1))

        # ─── AROON INDICATOR ───
        elif strategy_type == 'aroon':
            aroon_period = int(round(indicators.get('aroon_period', 25)))
            aroon_thresh = indicators.get('aroon_threshold', 70.0)

            aroon_up, aroon_down = self._calculate_aroon(high, low, aroon_period)

            for i in range(1, n):
                if np.isnan(aroon_up[i]):
                    continue
                # Aroon Up crosses above threshold and above Aroon Down
                if aroon_up[i] > aroon_thresh and aroon_up[i] > aroon_down[i] and aroon_up[i - 1] <= aroon_down[i - 1]:
                    buy_signal[i] = True
                if aroon_down[i] > aroon_thresh and aroon_down[i] > aroon_up[i] and aroon_down[i - 1] <= aroon_up[i - 1]:
                    sell_signal[i] = True

        # ─── COMBO: Multiple indicators must agree ───
        elif strategy_type == 'combo':
            combo_str = indicators.get('combo_indicators', 'rsi,macd')
            combo_list = [x.strip() for x in combo_str.split(',')]

            # Calculate individual buy/sell signals for each indicator
            all_buy = np.ones(n, dtype=bool)
            all_sell = np.ones(n, dtype=bool)
            has_any = False

            for ind in combo_list:
                b = np.zeros(n, dtype=bool)
                s = np.zeros(n, dtype=bool)

                if ind == 'rsi':
                    rsi_p = int(round(indicators.get('rsi_period', 14)))
                    rsi_buy = indicators.get('rsi_threshold_buy', 30)
                    rsi_sell = indicators.get('rsi_threshold_sell', 70)
                    rsi = self._calculate_rsi(close, rsi_p)
                    b = (rsi > rsi_buy) & (np.roll(rsi, 1) <= rsi_buy)
                    s = (rsi < rsi_sell) & (np.roll(rsi, 1) >= rsi_sell)

                elif ind == 'macd':
                    fp = int(round(indicators.get('macd_fast', 12)))
                    sp = int(round(indicators.get('macd_slow', 26)))
                    sgp = int(round(indicators.get('macd_signal', 9)))
                    ml, sl = self._calculate_macd(close, fp, sp, sgp)
                    b = (ml > sl) & (np.roll(ml, 1) <= np.roll(sl, 1))
                    s = (ml < sl) & (np.roll(ml, 1) >= np.roll(sl, 1))

                elif ind == 'bollinger':
                    bp = int(round(indicators.get('bollinger_period', 20)))
                    bs = indicators.get('bollinger_std', 2.0)
                    bb_u, bb_l, bb_m = self._calculate_bollinger_bands(close, bp, bs)
                    b = close <= bb_l
                    s = close >= bb_u

                elif ind == 'stochastic':
                    kp = int(round(indicators.get('stoch_k_period', 14)))
                    dp = int(round(indicators.get('stoch_d_period', 3)))
                    k, d = self._calculate_stochastic(high, low, close, kp, dp)
                    os_lvl = indicators.get('stoch_oversold', 20)
                    ob_lvl = indicators.get('stoch_overbought', 80)
                    for i in range(1, n):
                        if not np.isnan(k[i]) and not np.isnan(d[i]):
                            if k[i] > d[i] and k[i - 1] <= d[i - 1] and k[i] < os_lvl + 15:
                                b[i] = True
                            if k[i] < d[i] and k[i - 1] >= d[i - 1] and k[i] > ob_lvl - 15:
                                s[i] = True

                elif ind == 'adx':
                    ap = int(round(indicators.get('adx_period', 14)))
                    adx, pdi, mdi = self._calculate_adx(high, low, close, ap)
                    at = indicators.get('adx_threshold', 25.0)
                    for i in range(1, n):
                        if not np.isnan(adx[i]) and adx[i] > at:
                            if pdi[i] > mdi[i]:
                                b[i] = True
                            else:
                                s[i] = True

                elif ind == 'ema':
                    fp = int(round(indicators.get('ema_fast', 12)))
                    sp = int(round(indicators.get('ema_slow', 26)))
                    if fp >= sp:
                        sp = fp + 14
                    ef = self._calculate_ema(close, fp)
                    es = self._calculate_ema(close, sp)
                    b = (ef > es) & (np.roll(ef, 1) <= np.roll(es, 1))
                    s = (ef < es) & (np.roll(ef, 1) >= np.roll(es, 1))

                elif ind == 'volume':
                    vp = int(round(indicators.get('volume_period', 20)))
                    vm = indicators.get('volume_multiplier', 2.0)
                    avg_vol = pd.Series(volume).rolling(vp).mean().values
                    vol_spike = volume > (avg_vol * vm)
                    b = vol_spike & (close > np.roll(close, 1))
                    s = vol_spike & (close < np.roll(close, 1))

                has_any = True
                # For combo: use OR within 3-bar window to allow slight timing differences
                # Then AND across all indicators
                b_wide = np.zeros(n, dtype=bool)
                s_wide = np.zeros(n, dtype=bool)
                for i in range(n):
                    lo = max(0, i - 2)
                    if np.any(b[lo:i + 1]):
                        b_wide[i] = True
                    if np.any(s[lo:i + 1]):
                        s_wide[i] = True

                all_buy = all_buy & b_wide
                all_sell = all_sell & s_wide

            if has_any:
                buy_signal = all_buy
                sell_signal = all_sell

        # ─── Apply RSI filter if present (for any strategy type) ───
        if 'rsi_filter' in indicators and strategy_type not in ['rsi_reversal']:
            rsi = self._calculate_rsi(close, 14)
            rsi_max = indicators.get('rsi_filter', 75)
            buy_signal = buy_signal & (rsi < rsi_max)

        # Clean signals
        buy_signal[0] = False
        sell_signal[0] = False
        buy_signal = self._remove_consecutive(buy_signal)
        sell_signal = self._remove_consecutive(sell_signal)

        return pd.Series(buy_signal), pd.Series(sell_signal)

    def _execute_trades(
        self,
        candles: pd.DataFrame,
        buy_signals: pd.Series,
        sell_signals: pd.Series,
        strategy_params: dict,
        direction: str = 'long'
    ) -> List[Trade]:
        """Execute trades with long/short support."""
        trades = []
        position_active = False
        entry_price = None
        entry_time = None
        entry_index = None

        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        timestamps = candles['timestamp'].values

        risk_params = strategy_params.get('risk_management', {})
        atr_mult = risk_params.get('stop_loss_atr', 2.0)
        tp_percent = risk_params.get('take_profit_percent', 0.05)

        # Calculate ATR
        df_atr = candles.copy()
        df_atr['atr'] = calculate_atr(df_atr['high'], df_atr['low'], df_atr['close'], period=14)
        atr_values = df_atr['atr'].values

        # Position sizing
        pos_size_amount = strategy_params.get('position_sizing', {}).get('size_amount', 0.3)
        position_value = self.initial_balance * pos_size_amount

        is_short = (direction == 'short')

        # For shorts: buy_signal = entry, sell_signal = exit (inverted)
        if is_short:
            entry_signals = sell_signals
            exit_signals = buy_signals
        else:
            entry_signals = buy_signals
            exit_signals = sell_signals

        for i in range(len(candles)):
            current_price = close[i]
            current_time = timestamps[i]
            current_atr = atr_values[i] if not np.isnan(atr_values[i]) else current_price * 0.01

            # Entry
            if not position_active and entry_signals.iloc[i]:
                position_active = True
                entry_price = current_price
                entry_time = current_time
                entry_index = i

            # Exit
            elif position_active and entry_index is not None:
                if is_short:
                    stop_loss = entry_price + (current_atr * atr_mult)
                    take_profit = entry_price * (1 - tp_percent)
                else:
                    stop_loss = entry_price - (current_atr * atr_mult)
                    take_profit = entry_price * (1 + tp_percent)

                exit_price = None
                exit_reason = None

                if is_short:
                    if current_price <= take_profit:
                        exit_price = take_profit
                        exit_reason = "tp"
                    elif current_price >= stop_loss:
                        exit_price = stop_loss
                        exit_reason = "sl"
                    elif exit_signals.iloc[i]:
                        exit_price = current_price
                        exit_reason = "signal"
                else:
                    if current_price >= take_profit:
                        exit_price = take_profit
                        exit_reason = "tp"
                    elif current_price <= stop_loss:
                        exit_price = stop_loss
                        exit_reason = "sl"
                    elif exit_signals.iloc[i]:
                        exit_price = current_price
                        exit_reason = "signal"

                if exit_price is not None:
                    size = position_value / entry_price
                    fees = size * entry_price * self.fees + size * exit_price * self.fees

                    if is_short:
                        pnl = (entry_price - exit_price) * size - fees
                    else:
                        pnl = (exit_price - entry_price) * size - fees

                    # Create trade with adjusted exit_price to encode PnL correctly
                    # Trade.pnl = (exit - entry) * size - fees, so for shorts we swap
                    if is_short:
                        trade = Trade(
                            entry_price=exit_price,   # Swap so pnl calculates correctly
                            exit_price=entry_price,
                            size=size,
                            entry_time=pd.Timestamp(entry_time),
                            exit_time=pd.Timestamp(current_time),
                            fees=fees
                        )
                    else:
                        trade = Trade(
                            entry_price=entry_price,
                            exit_price=exit_price,
                            size=size,
                            entry_time=pd.Timestamp(entry_time),
                            exit_time=pd.Timestamp(current_time),
                            fees=fees
                        )

                    trades.append(trade)
                    position_active = False
                    entry_price = None
                    entry_time = None
                    entry_index = None

        # Close open position at end
        if position_active and entry_price is not None:
            exit_price = close[-1]
            size = position_value / entry_price
            fees = size * entry_price * self.fees + size * exit_price * self.fees

            if is_short:
                trade = Trade(
                    entry_price=exit_price,
                    exit_price=entry_price,
                    size=size,
                    entry_time=pd.Timestamp(entry_time),
                    exit_time=pd.Timestamp(timestamps[-1]),
                    fees=fees
                )
            else:
                trade = Trade(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    size=size,
                    entry_time=pd.Timestamp(entry_time),
                    exit_time=pd.Timestamp(timestamps[-1]),
                    fees=fees
                )
            trades.append(trade)

        return trades

    # ─── Indicator Calculations ───

    def _calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        return pd.Series(prices).rolling(window=max(period, 2)).mean().values

    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        return pd.Series(prices).ewm(span=max(period, 2), adjust=False).mean().values

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        delta = pd.Series(prices).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.values

    def _calculate_bollinger_bands(
        self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        sma = self._calculate_sma(prices, period)
        std = pd.Series(prices).rolling(window=period).std().values
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower, sma

    def _calculate_macd(
        self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray]:
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal, adjust=False).mean().values
        return macd_line, signal_line

    def _calculate_stochastic(self, high: np.ndarray, low: np.ndarray,
                                close: np.ndarray, k_period: int = 14,
                                d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Stochastic Oscillator %K and %D."""
        h = pd.Series(high).rolling(k_period).max()
        l = pd.Series(low).rolling(k_period).min()
        k = 100 * ((pd.Series(close) - l) / (h - l + 1e-10))
        d = k.rolling(d_period).mean()
        return k.values, d.values

    def _calculate_adx(self, high: np.ndarray, low: np.ndarray,
                       close: np.ndarray, period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate ADX, +DI, -DI."""
        h, l, c = pd.Series(high), pd.Series(low), pd.Series(close)
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        up_move = h - h.shift(1)
        down_move = l.shift(1) - l
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        plus_di = 100 * (plus_dm.rolling(period).mean() / (atr + 1e-10))
        minus_di = 100 * (minus_dm.rolling(period).mean() / (atr + 1e-10))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        adx = dx.rolling(period).mean()
        return adx.values, plus_di.values, minus_di.values

    def _calculate_ichimoku(self, high: np.ndarray, low: np.ndarray,
                            close: np.ndarray, tenkan: int = 9,
                            kijun: int = 26, senkou_b: int = 52) -> dict:
        """Calculate Ichimoku cloud components."""
        h, l = pd.Series(high), pd.Series(low)
        tenkan_sen = (h.rolling(tenkan).max() + l.rolling(tenkan).min()) / 2
        kijun_sen = (h.rolling(kijun).max() + l.rolling(kijun).min()) / 2
        senkou_a = ((tenkan_sen + kijun_sen) / 2)
        senkou_b_line = ((h.rolling(senkou_b).max() + l.rolling(senkou_b).min()) / 2)
        return {
            "tenkan": tenkan_sen.values,
            "kijun": kijun_sen.values,
            "senkou_a": senkou_a.values,
            "senkou_b": senkou_b_line.values,
        }

    def _calculate_ad_line(self, high: np.ndarray, low: np.ndarray,
                           close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Calculate Accumulation/Distribution Line."""
        mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
        mfv = mfm * volume
        return np.cumsum(mfv)

    def _calculate_aroon(self, high: np.ndarray, low: np.ndarray,
                         period: int = 25) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Aroon Up and Aroon Down."""
        n = len(high)
        aroon_up = np.full(n, np.nan)
        aroon_down = np.full(n, np.nan)
        for i in range(period, n):
            window_h = high[i - period:i + 1]
            window_l = low[i - period:i + 1]
            days_since_high = period - np.argmax(window_h)
            days_since_low = period - np.argmin(window_l)
            aroon_up[i] = 100 * (period - days_since_high) / period
            aroon_down[i] = 100 * (period - days_since_low) / period
        return aroon_up, aroon_down

    def _remove_consecutive(self, signals: np.ndarray) -> np.ndarray:
        signals = signals.copy()
        for i in range(1, len(signals)):
            if signals[i] and signals[i - 1]:
                signals[i] = False
        return signals

    def _empty_result(self) -> Dict:
        return {
            "strategy_id": None,
            "num_trades": 0,
            "metrics": self.metrics_calculator._empty_metrics(),
            "trades": [],
            "timestamp": datetime.utcnow(),
            "success": False,
        }


def backtest_strategy(strategy: dict, candles: pd.DataFrame, **kwargs) -> Dict:
    """Convenience function for backtesting."""
    engine = VectorBTBacktestEngine(**kwargs)
    return engine.backtest_strategy(candles, strategy)
