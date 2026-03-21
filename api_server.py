"""Simple API starter without TUI import."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Create app
from src.api.routes import router
from src.database import init_db

app = FastAPI(title="Grindstone Apex", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["trading"])

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Grindstone Apex API running"}

@app.on_event("startup")
async def startup():
    init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
