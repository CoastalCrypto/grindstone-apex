import ccxt
def check():
    b = ccxt.blofin()
    for sym in ['BTC/USDT:USDT', 'XAU/USDT:USDT', 'XAG/USDT:USDT']:
        try:
            candles = b.fetch_ohlcv(sym, '15m', limit=5)
            print(f"Success {sym}: {len(candles)} candles")
        except Exception as e:
            print(f"Error {sym}: {e}")

if __name__ == "__main__":
    check()
