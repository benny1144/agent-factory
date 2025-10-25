from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from utils.paths import PROJECT_ROOT

_DEFAULT_SQLITE = f"sqlite:///{(PROJECT_ROOT / 'data' / 'agent_factory.sqlite').as_posix()}"


@dataclass
class MemoryConfig:
    database_url: str


def _db_url() -> str:
    return os.getenv("DATABASE_URL") or _DEFAULT_SQLITE


def _ensure_engine() -> Engine:
    url = _db_url()
    # If using sqlite, ensure directory exists
    if url.startswith("sqlite"):
        db_path = PROJECT_ROOT / "data"
        db_path.mkdir(parents=True, exist_ok=True)
    return create_engine(url, future=True)


# SQLAlchemy table definitions (SQLModel is optional; using Core for minimal deps)
metadata = MetaData()

agent_runs = Table(
    "agent_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agent", String(255), nullable=False),
    Column("task", String(255), nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("status", String(50), nullable=True),
    Column("trace_id", String(64), nullable=True),
)

tool_registry = Table(
    "tool_registry",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tool_name", String(255), nullable=False),
    Column("path", String(1024), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("schema_json", JSON, nullable=True),
)

knowledge_ingest = Table(
    "knowledge_ingest",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_path", String(1024), nullable=False),
    Column("vector_count", Integer, nullable=False),
    Column("curator", String(255), nullable=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
)

# Phase 2: memory_events table to track MemoryEngine operations
memory_events = Table(
    "memory_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("backend", String(64), nullable=False),
    Column("event_type", String(64), nullable=False),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("details_json", JSON, nullable=True),
)

# Phase 3: memory_weights table for dynamic prioritization
memory_weights = Table(
    "memory_weights",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agent", String(255), nullable=False),
    Column("context_key", String(255), nullable=False),
    Column("weight", Float, nullable=False, default=1.0),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def init_db(engine: Optional[Engine] = None) -> Engine:
    """Initialize database and create tables if missing."""
    engine = engine or _ensure_engine()
    metadata.create_all(engine)
    return engine


@contextlib.contextmanager
def session_scope(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    engine = engine or _ensure_engine()
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


@contextlib.contextmanager
def trace_run(agent: str, task: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
    """Context manager to trace an agent run.

    Usage:
        with trace_run("GenesisCrew", task="kickoff") as trace:
            ...
            # Optionally set trace["status"] = "success" before exit

    The manager writes a row into agent_runs at enter and updates it at exit.
    """
    engine = init_db()
    started = datetime.now(timezone.utc)
    row = {
        "agent": agent,
        "task": task,
        "started_at": started,
        "finished_at": None,
        "status": None,
        "trace_id": os.getenv("TRACE_ID"),
    }
    with session_scope(engine) as s:
        res = s.execute(insert(agent_runs).values(**row))
        run_id = res.inserted_primary_key[0]
        context: Dict[str, Any] = {"run_id": run_id, "agent": agent, "task": task, "status": None}
    try:
        yield context
    finally:
        finished = datetime.now(timezone.utc)
        with session_scope(engine) as s:
            s.execute(
                agent_runs.update().where(agent_runs.c.id == context["run_id"]).values(
                    finished_at=finished, status=context.get("status")
                )
            )


def register_tool(tool_name: str, path: Path, schema: Optional[Dict[str, Any]] = None, engine: Optional[Engine] = None) -> int:
    engine = engine or init_db()
    with session_scope(engine) as s:
        res = s.execute(
            insert(tool_registry).values(
                tool_name=tool_name,
                path=str(path),
                created_at=datetime.now(timezone.utc),
                schema_json=schema or None,
            )
        )
        return int(res.inserted_primary_key[0])


def insert_ingest(source_path: Path, vector_count: int, curator: Optional[str] = None, engine: Optional[Engine] = None) -> int:
    engine = engine or init_db()
    with session_scope(engine) as s:
        res = s.execute(
            insert(knowledge_ingest).values(
                source_path=str(source_path),
                vector_count=int(vector_count),
                curator=curator,
                timestamp=datetime.now(timezone.utc),
            )
        )
        return int(res.inserted_primary_key[0])


def insert_memory_event(backend: str, event_type: str, details_json: Optional[Dict[str, Any]] = None, engine: Optional[Engine] = None) -> int:
    """Insert a memory event row for MemoryEngine operations."""
    engine = engine or init_db()
    with session_scope(engine) as s:
        res = s.execute(
            insert(memory_events).values(
                backend=backend,
                event_type=event_type,
                ts=datetime.now(timezone.utc),
                details_json=details_json or None,
            )
        )
        return int(res.inserted_primary_key[0])


def select_all(table: Table, engine: Optional[Engine] = None) -> list[dict[str, Any]]:
    engine = engine or init_db()
    with session_scope(engine) as s:
        rows = s.execute(select(table)).mappings().all()
        return [dict(r) for r in rows]


def adjust_memory_weight(agent: str, context_key: str, delta: float, engine: Optional[Engine] = None) -> int:
    """Adjust or set memory weight for a given agent/context.

    Inserts a new row capturing the latest weight value (delta stored as absolute weight for simplicity).
    """
    engine = engine or init_db()
    # sanitize delta
    try:
        val = float(delta)
    except Exception:
        val = 1.0
    if val != val or val in (float("inf"), float("-inf")):
        val = 1.0
    with session_scope(engine) as s:
        res = s.execute(
            insert(memory_weights).values(
                agent=agent,
                context_key=context_key,
                weight=val,
                updated_at=datetime.now(timezone.utc),
            )
        )
        return int(res.inserted_primary_key[0])


def get_recent_weights(agent: str, limit: int = 5, engine: Optional[Engine] = None) -> list[dict[str, Any]]:
    """Return recent memory weight rows for the given agent.

    Results are ordered by updated_at descending and limited to the specified count.
    """
    engine = engine or init_db()
    with session_scope(engine) as s:
        rows = (
            s.execute(
                select(memory_weights)
                .where(memory_weights.c.agent == agent)
                .order_by(memory_weights.c.updated_at.desc())
                .limit(limit)
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


# Phase 6: governance_history table for HITL/HOTL oversight records
# Defined here to be included in metadata.create_all via init_db()
governance_history = Table(
    "governance_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("agent", String(255), nullable=True),
    Column("action", String(255), nullable=True),
    Column("reason", Text, nullable=True),
    Column("approver", String(255), nullable=True),
)


def record_governance_event(agent: str, action: str, reason: str, approver: str) -> int:
    """Record a governance (HITL) event into the governance_history table.

    Args:
        agent: Agent name or identifier.
        action: Action performed (approve, deny, override).
        reason: Human-provided reason or context string.
        approver: Human operator identifier.
    Returns:
        Inserted primary key id.
    """
    engine = init_db()
    with session_scope(engine) as s:
        res = s.execute(
            insert(governance_history).values(
                timestamp=datetime.now(timezone.utc),
                agent=agent,
                action=action,
                reason=reason,
                approver=approver,
            )
        )
        return int(res.inserted_primary_key[0])


__all__ = [
    "init_db",
    "trace_run",
    "register_tool",
    "insert_ingest",
    "insert_memory_event",
    "select_all",
    "adjust_memory_weight",
    "get_recent_weights",
    "record_governance_event",
    "agent_runs",
    "tool_registry",
    "knowledge_ingest",
    "memory_events",
    "memory_weights",
    "governance_history",
]