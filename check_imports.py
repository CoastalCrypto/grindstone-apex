"""Import verification for grindstone_apex."""
import sys

checks = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "uvicorn"),
    ("sqlalchemy", "SQLAlchemy"),
    ("pydantic", "Pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("psycopg2", "psycopg2-binary"),
    ("dotenv", "python-dotenv"),
    ("redis", "redis"),
    ("ccxt", "ccxt"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("rich", "rich"),
    ("click", "click"),
    ("textual", "textual"),
    ("aiohttp", "aiohttp"),
]

errors = []
for mod, name in checks:
    try:
        __import__(mod)
        print(f"  OK  {name}")
    except ImportError as e:
        print(f"  FAIL {name}: {e}")
        errors.append(name)

print()

# Check src modules
src_checks = [
    "src.config",
    "src.database",
    "src.api.routes",
    "src.api.live_trading_routes",
    "src.api.phase5_routes",
]
for mod in src_checks:
    try:
        __import__(mod)
        print(f"  OK  {mod}")
    except Exception as e:
        print(f"  FAIL {mod}: {e}")
        errors.append(mod)

print()
if errors:
    print(f"FAILED ({len(errors)} issues): {errors}")
    sys.exit(1)
else:
    print("All imports OK! The server is ready to start.")
