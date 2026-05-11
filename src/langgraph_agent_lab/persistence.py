"""Checkpointer adapter."""

from __future__ import annotations

import atexit
import sqlite3
from collections.abc import Callable
from contextlib import ExitStack

_CHECKPOINTER_STACK = ExitStack()
atexit.register(_CHECKPOINTER_STACK.close)


def _call_setup_if_available(checkpointer: object) -> None:
    setup = getattr(checkpointer, "setup", None)
    typed_setup: Callable[[], None] | None = setup if callable(setup) else None
    if typed_setup is not None:
        typed_setup()


def build_checkpointer(kind: str = "memory", database_url: str | None = None) -> object | None:
    """Return a LangGraph checkpointer.

    TODO(student): add SQLite/Postgres support for the extension track.
    The starter uses MemorySaver so the lab can run without infrastructure.
    """
    # Implement
    if kind == "none":
        return None
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    if kind == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "SQLite checkpointer requires: pip install langgraph-checkpoint-sqlite"
            ) from exc
        conn = sqlite3.connect(database_url or "checkpoints.db", check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _CHECKPOINTER_STACK.callback(conn.close)
        checkpointer = SqliteSaver(conn=conn)
        _call_setup_if_available(checkpointer)
        return checkpointer
    if kind == "postgres":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:
            raise RuntimeError(
                "Postgres checkpointer requires: pip install "
                "langgraph-checkpoint-postgres psycopg[binary]"
            ) from exc
        if not database_url:
            raise RuntimeError("Postgres checkpointer requires DATABASE_URL in config or .env")
        checkpointer = _CHECKPOINTER_STACK.enter_context(
            PostgresSaver.from_conn_string(database_url)
        )
        _call_setup_if_available(checkpointer)
        return checkpointer
    raise ValueError(f"Unknown checkpointer kind: {kind}")
