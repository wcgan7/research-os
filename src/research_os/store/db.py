"""SQLite connection and schema initialization."""

from __future__ import annotations

import dataclasses
import sqlite3
import types
from pathlib import Path
from typing import Union, get_args, get_origin

from research_os.store.models import ALL_RECORD_TYPES


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def _sql_type(annotation) -> str:
    """Map a resolved Python type annotation to a SQLite column type."""
    origin = get_origin(annotation)

    # list[...] → TEXT (JSON-serialized)
    if origin is list:
        return "TEXT"

    # Union types (int | None, Optional[int], etc.)
    if origin is Union or isinstance(annotation, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if args:
            return _sql_type(args[0])
        return "TEXT"

    if annotation is int:
        return "INTEGER"
    if annotation is float:
        return "REAL"
    return "TEXT"


def _resolve_fields(cls) -> list[tuple[str, type]]:
    """Resolve stringified annotations back to real types for a dataclass."""
    hints = {}
    # Walk MRO to collect all type hints
    for klass in reversed(cls.__mro__):
        if hasattr(klass, "__annotations__"):
            hints.update(
                {
                    k: v
                    for k, v in getattr(klass, "__annotations__", {}).items()
                    if not k.startswith("_")
                }
            )
    # Evaluate string annotations in the module's namespace
    import research_os.store.models as models_mod

    ns = vars(models_mod)
    resolved = {}
    for name, ann in hints.items():
        if isinstance(ann, str):
            resolved[name] = eval(ann, ns)  # noqa: S307
        else:
            resolved[name] = ann
    return [(f.name, resolved.get(f.name, str)) for f in dataclasses.fields(cls)]


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables for all record types if they don't exist.

    Also adds any missing columns to existing tables (forward migration).
    """
    for cls in ALL_RECORD_TYPES:
        table = cls.__table_name__
        columns = []
        field_defs = _resolve_fields(cls)
        for name, resolved_type in field_defs:
            if name == "id":
                columns.append("id TEXT PRIMARY KEY")
            else:
                columns.append(f"{name} {_sql_type(resolved_type)}")
        ddl = f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})"
        conn.execute(ddl)

        # Add any missing columns to existing tables
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, resolved_type in field_defs:
            if name not in existing:
                col_type = _sql_type(resolved_type)
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")

    conn.commit()
