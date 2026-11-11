"""Application entry point."""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Psycopg async on Windows requires the selector event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.agents.checkpointer import close_checkpointer, init_checkpointer
from app.config.postgres_config import engine
from app.config.tracing_config import setup_tracing
from app.routes.core_routes.chat_route import router as chat_router

setup_tracing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context."""
    setup_tracing()
    await init_checkpointer()
    yield
    # Shutdown: clean up SQLAlchemy engine & checkpointer connections
    await close_checkpointer()
    await engine.dispose()


app = FastAPI(
    title="Workflow Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
