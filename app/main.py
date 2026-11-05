"""Application entry point."""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Psycopg async on Windows requires the selector event loop policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.agents.checkpointer import close_checkpointer
from app.config.postgres_config import engine
from app.routes.core_routes.chat_route import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """"Application lifespan context."""
    yield
    # Shutdown: clean up SQLAlchemy engine & checkpointer connections
    await close_checkpointer()
    await engine.dispose()


app = FastAPI(
    title="Workflow Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
