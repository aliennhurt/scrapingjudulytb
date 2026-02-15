
from fastapi import FastAPI
from app.api import collect
from app.db.init_db import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
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
    return {"message": "YouTube Pattern Detector API is running."}
