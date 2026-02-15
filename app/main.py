
from fastapi import FastAPI
from app.api import collect
from app.db.init_db import init_db
from contextlib import asynccontextmanager
import traceback
import sys

# Global variable to store startup errors
startup_error = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global startup_error
    try:
        init_db()
    except Exception as e:
        startup_error = e
        print(f"Startup error: {e}", file=sys.stderr)
        traceback.print_exc()
    
    yield
    # Shutdown

app = FastAPI(
    title="YouTube Winning Pattern Detector",
    description="Backend for collecting YouTube data and generating title templates.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(collect.router, prefix="/api")

@app.get("/")
def read_root():
    if startup_error:
        return {
            "message": "YouTube Pattern Detector API started with ERRORS",
            "status": "unhealthy", 
            "error": str(startup_error)
        }
    return {"message": "YouTube Pattern Detector API is running.", "status": "healthy"}

@app.get("/health")
def health_check():
    if startup_error:
        return {
            "status": "error",
            "db": "disconnected",
            "error": str(startup_error),
            "traceback": traceback.format_exc()
        }
    return {"status": "ok", "db": "connected"}
