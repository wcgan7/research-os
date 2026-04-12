"""Generic record CRUD against SQLite."""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import TypeVar

from research_os.store.models import BaseRecord, Paper

T = TypeVar("T", bound=BaseRecord)

# Pre-compute which fields are list types by checking default_factory
# With `from __future__ import annotations`, f.type is a string, so we
# detect list fields by checking if the annotation string starts with "list[".
_LIST_FIELD_CACHE: dict[type, set[str]] = {}


def _list_fields_for(cls: type) -> set[str]:
    if cls not in _LIST_FIELD_CACHE:
        names = set()
        for f in dataclasses.fields(cls):
            ann = f.type if isinstance(f.type, str) else str(f.type)
            if ann.startswith("list["):
                names.add(f.name)
        _LIST_FIELD_CACHE[cls] = names
    return _LIST_FIELD_CACHE[cls]


class Store:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _serialize(record: T) -> dict:
        d = dataclasses.asdict(record)
        for name in _list_fields_for(type(record)):
            d[name] = json.dumps(d[name])
        return d

    @staticmethod
    def _deserialize(cls: type[T], row: sqlite3.Row) -> T:
        kwargs = dict(row)
        for name in _list_fields_for(cls):
            if isinstance(kwargs.get(name), str):
                kwargs[name] = json.loads(kwargs[name])
        return cls(**kwargs)

    # ── CRUD ─────────────────────────────────────────────────────

    def save(self, record: T) -> T:
        """Insert or replace a record. Updates updated_at."""
        record.updated_at = datetime.now(timezone.utc).isoformat()
        data = self._serialize(record)
        table = record.__table_name__
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        self.conn.execute(
            f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        return record

    def get(self, cls: type[T], record_id: str) -> T | None:
        table = cls.__table_name__
        row = self.conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None:
            return None
        return self._deserialize(cls, row)

    def query(self, cls: type[T], **filters) -> list[T]:
        table = cls.__table_name__
        where_parts = []
        values = []
        for k, v in filters.items():
            where_parts.append(f"{k} = ?")
            values.append(v)
        where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        rows = self.conn.execute(
            f"SELECT * FROM {table}{where} ORDER BY created_at DESC", values
        ).fetchall()
        return [self._deserialize(cls, r) for r in rows]

    def delete(self, cls: type[T], record_id: str) -> bool:
        table = cls.__table_name__
        cur = self.conn.execute(
            f"DELETE FROM {table} WHERE id = ?", (record_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def count(self, cls: type[T], **filters) -> int:
        table = cls.__table_name__
        where_parts = []
        values = []
        for k, v in filters.items():
            where_parts.append(f"{k} = ?")
            values.append(v)
        where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
        row = self.conn.execute(
            f"SELECT COUNT(*) as cnt FROM {table}{where}", values
        ).fetchone()
        return row["cnt"]

    # ── dedup ────────────────────────────────────────────────────

    def find_duplicate(
        self,
        review_id: str,
        doi: str | None = None,
        external_id: str | None = None,
        title: str | None = None,
    ) -> Paper | None:
        """3-tier duplicate detection: DOI > external_id > fuzzy title."""
        # Tier 1: exact DOI
        if doi:
            rows = self.conn.execute(
                "SELECT * FROM papers WHERE review_id = ? AND doi = ?",
                (review_id, doi),
            ).fetchall()
            if rows:
                return self._deserialize(Paper, rows[0])

        # Tier 2: exact external_id
        if external_id:
            rows = self.conn.execute(
                "SELECT * FROM papers WHERE review_id = ? AND external_id = ?",
                (review_id, external_id),
            ).fetchall()
            if rows:
                return self._deserialize(Paper, rows[0])

        # Tier 3: fuzzy title match
        if title:
            norm_title = title.strip().lower()
            candidates = self.conn.execute(
                "SELECT * FROM papers WHERE review_id = ?", (review_id,)
            ).fetchall()
            for row in candidates:
                existing_title = (row["title"] or "").strip().lower()
                if SequenceMatcher(None, norm_title, existing_title).ratio() > 0.85:
                    return self._deserialize(Paper, row)

        return None
