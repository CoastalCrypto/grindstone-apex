import ccxt
import sys

def check_markets():
    print("Connecting to Blofin...")
    try:
        b = ccxt.blofin({'timeout': 15000})
        markets = b.load_markets()
        symbols = list(markets.keys())
        
        precious_metals = [s for s in symbols if 'XAU' in s or 'GOLD' in s or 'XAG' in s or 'SILVER' in s]
        print("Found precious metals:", precious_metals)
        
        # Also print some common ones to see format
        print("Sample symbols:", symbols[:5])
        
    except Exception as e:
        print("Failed to load markets from Blofin:", e)
        sys.exit(1)

if __name__ == "__main__":
    check_markets()
