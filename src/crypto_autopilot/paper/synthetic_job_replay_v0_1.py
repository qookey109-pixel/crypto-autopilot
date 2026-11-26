"""Synthetic replay ledger; not a production authority or D1 adapter.

SQLite behavior in CI does not establish Cloudflare D1 atomicity, trusted
identity, account costs, or protection against other database writers.
"""
from __future__ import annotations

import re
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS synthetic_job_claim (
    repository_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt TEXT NOT NULL,
    check_run_id TEXT NOT NULL,
    writer_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    PRIMARY KEY (repository_id, run_id, attempt, check_run_id, writer_id),
    UNIQUE (repository_id, writer_id, slot_id)
)
"""
_NUMBER = re.compile(r"[1-9][0-9]{0,19}\Z")
_WRITER = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_SLOT = re.compile(r"slot:(0|[1-9][0-9]{0,15})\Z")


def initialize_synthetic_replay_ledger(connection: sqlite3.Connection) -> None:
    """Initialize a test-only database, outside admission."""
    connection.execute(_SCHEMA)
    connection.commit()


def claim_synthetic_job(connection: sqlite3.Connection, *, repository_id: str,
                        run_id: str, attempt: str, check_run_id: str,
                        writer_id: str, slot_id: str) -> bool:
    """Atomically claim once, without accepting token jti as replay identity.

    A False result includes duplicates, lock failures and unknown outcomes.
    Never use this return value to enable a production operation.
    """
    if (
        not all(isinstance(x, str) and _NUMBER.fullmatch(x)
                for x in (repository_id, run_id, attempt, check_run_id))
        or attempt != "1"
        or not isinstance(writer_id, str) or not _WRITER.fullmatch(writer_id)
        or not isinstance(slot_id, str) or not _SLOT.fullmatch(slot_id)
        or connection.in_transaction
    ):
        return False
    try:
        connection.execute(
            "INSERT INTO synthetic_job_claim "
            "(repository_id, run_id, attempt, check_run_id, writer_id, slot_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (repository_id, run_id, attempt, check_run_id, writer_id, slot_id),
        )
        connection.commit()
        return True
    except sqlite3.Error:
        connection.rollback()
        return False
