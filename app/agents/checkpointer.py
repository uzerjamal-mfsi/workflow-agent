"""LangGraph checkpointer factory."""
import asyncio
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing_extensions import AsyncContextManager

from app.config.env_config import get_settings

_memory_saver: MemorySaver | None = None
_postgres_saver: AsyncPostgresSaver | None = None
_postgres_cm: AsyncContextManager[AsyncPostgresSaver] | None = None
_lock: asyncio.Lock | None = None
_lock_loop: asyncio.AbstractEventLoop | None = None


def _get_lock() -> asyncio.Lock:
    """Return an asyncio.Lock bound to the current running event loop."""
    global _lock, _lock_loop
    loop = asyncio.get_running_loop()
    if _lock is None or _lock_loop is not loop:
        _lock = asyncio.Lock()
        _lock_loop = loop
    return _lock


async def init_checkpointer() -> BaseCheckpointSaver[Any]:
    """Initialize the active checkpointer during startup with concurrency protection."""
    global _memory_saver, _postgres_saver, _postgres_cm
    async with _get_lock():
        settings = get_settings()

        if settings.CHECKPOINTER_TYPE == "postgres":
            if _postgres_saver is None:
                _postgres_cm = AsyncPostgresSaver.from_conn_string(settings.raw_postgres_url)
                _postgres_saver = await _postgres_cm.__aenter__()
                await _postgres_saver.setup()
            return _postgres_saver

        if _memory_saver is None:
            _memory_saver = MemorySaver()
        return _memory_saver


async def get_checkpointer() -> BaseCheckpointSaver[Any]:
    """Return the active checkpointer based on CHECKPOINTER_TYPE."""
    if _postgres_saver is not None:
        return _postgres_saver
    if _memory_saver is not None:
        return _memory_saver
    return await init_checkpointer()


async def close_checkpointer() -> None:
    """Cleanly close the Postgres checkpointer if open."""
    global _postgres_cm, _postgres_saver, _memory_saver
    async with _get_lock():
        if _postgres_cm is not None:
            _ = await _postgres_cm.__aexit__(None, None, None)
            _postgres_cm = None
            _postgres_saver = None
        _memory_saver = None
