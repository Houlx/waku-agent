"""One SQLite file (state.db) holds everything Waku remembers and does.

This mirrors the Hermes approach on the whiteboard: SQLite + FTS5, no server.
Open it yourself anytime:  sqlite3 ~/.waku/state.db '.tables'
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
-- Flagship-task artifact: events the calendar tool creates. The deterministic
-- eval asserts directly on rows in this table ("did the meeting trigger?").
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    start TEXT NOT NULL,           -- ISO 8601
    "end" TEXT,
    attendees TEXT DEFAULT '',     -- comma-separated
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Semantic memory: durable facts about you, your people, your projects.
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY,
    subject TEXT NOT NULL,         -- who/what the fact is about, e.g. 'alex'
    content TEXT NOT NULL,         -- the fact itself
    source TEXT DEFAULT 'user',    -- 'user' (told directly) or 'consolidation'
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    subject, content, content=facts, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS facts_ai AFTER INSERT ON facts BEGIN
    INSERT INTO facts_fts(rowid, subject, content) VALUES (new.id, new.subject, new.content);
END;
CREATE TRIGGER IF NOT EXISTS facts_ad AFTER DELETE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, subject, content) VALUES ('delete', old.id, old.subject, old.content);
END;
CREATE TRIGGER IF NOT EXISTS facts_au AFTER UPDATE ON facts BEGIN
    INSERT INTO facts_fts(facts_fts, rowid, subject, content) VALUES ('delete', old.id, old.subject, old.content);
    INSERT INTO facts_fts(rowid, subject, content) VALUES (new.id, new.subject, new.content);
END;

-- Episodic memory: dated things that happened (past chats, distilled).
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY,
    happened_at TEXT NOT NULL,     -- ISO 8601 date of the episode
    summary TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    summary, content=episodes, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
    INSERT INTO episodes_fts(rowid, summary) VALUES (new.id, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
    INSERT INTO episodes_fts(episodes_fts, rowid, summary) VALUES ('delete', old.id, old.summary);
END;

-- Raw chat log ("save the messages" box). Consolidation reads from here.
-- session_id tags each row with which conversation it belongs to, so the
-- dashboard can offer "New chat" and switch between past sessions (like a
-- chat app). Everything shares this one table — sessions are just a label.
CREATE TABLE IF NOT EXISTS chat_log (
    id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,            -- 'user' | 'assistant'
    content TEXT NOT NULL,
    consolidated INTEGER DEFAULT 0,
    session_id TEXT DEFAULT 'default',
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive, idempotent column upgrades for databases created before a
    column existed. SQLite has no 'ADD COLUMN IF NOT EXISTS', so we check."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_log)").fetchall()}
    if "session_id" not in cols:
        conn.execute("ALTER TABLE chat_log ADD COLUMN session_id TEXT DEFAULT 'default'")
        conn.commit()
    if "source" not in cols:
        # which gateway a message came in through (cli / voice / telegram / dashboard)
        conn.execute("ALTER TABLE chat_log ADD COLUMN source TEXT DEFAULT 'cli'")
        conn.commit()
    if "meta" not in cols:
        # per-turn telemetry as JSON on the assistant row (gate decision,
        # latency, iterations, tools) — so reopening a thread still shows how
        # each answer was produced, not just the plain text.
        conn.execute("ALTER TABLE chat_log ADD COLUMN meta TEXT")
        conn.commit()


def open_connection(home: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    # check_same_thread=False lets the dashboard's threaded HTTP server reuse
    # one agent connection across worker threads (guarded by a lock). busy_timeout
    # avoids "database is locked" when the dashboard reads while a chat writes.
    conn = sqlite3.connect(home / "state.db", check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


def connect(home: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open the general assistant database, including its legacy migrations."""
    conn = open_connection(home, check_same_thread)
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
    except BaseException:
        conn.close()
        raise
    return conn


def connect_career(home: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    """Open Career tables in the same file, leaving any legacy tables untouched."""
    conn = open_connection(home, check_same_thread)
    try:
        initialize_career(conn)
    except BaseException:
        conn.close()
        raise
    return conn


CAREER_SCHEMA = """
CREATE TABLE IF NOT EXISTS career_profile (
 id INTEGER PRIMARY KEY CHECK(id=1), raw_input_json TEXT NOT NULL,
 normalized_json TEXT, user_edits_json TEXT NOT NULL DEFAULT '{}',
 confirmed INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS career_evidence (
 id INTEGER PRIMARY KEY, evidence_id TEXT UNIQUE NOT NULL, source_id TEXT NOT NULL,
 source_type TEXT NOT NULL, raw_text TEXT NOT NULL, normalized_json TEXT NOT NULL,
 search_text TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE VIRTUAL TABLE IF NOT EXISTS career_evidence_fts USING fts5(
 search_text, content=career_evidence, content_rowid=id
);
CREATE TRIGGER IF NOT EXISTS career_evidence_ai AFTER INSERT ON career_evidence BEGIN
 INSERT INTO career_evidence_fts(rowid,search_text) VALUES(new.id,new.search_text);
END;
CREATE TRIGGER IF NOT EXISTS career_evidence_ad AFTER DELETE ON career_evidence BEGIN
 INSERT INTO career_evidence_fts(career_evidence_fts,rowid,search_text)
 VALUES('delete',old.id,old.search_text);
END;
CREATE TRIGGER IF NOT EXISTS career_evidence_au AFTER UPDATE ON career_evidence BEGIN
 INSERT INTO career_evidence_fts(career_evidence_fts,rowid,search_text)
 VALUES('delete',old.id,old.search_text);
 INSERT INTO career_evidence_fts(rowid,search_text) VALUES(new.id,new.search_text);
END;
CREATE TABLE IF NOT EXISTS jobs (
 id TEXT PRIMARY KEY, raw_jd TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
 summary TEXT NOT NULL DEFAULT '', responsibilities_json TEXT NOT NULL DEFAULT '[]',
 status TEXT NOT NULL DEFAULT 'pending', outdated INTEGER NOT NULL DEFAULT 0,
 coverage REAL, report_json TEXT, activity_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS job_requirements (
 id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id), text TEXT NOT NULL,
 category TEXT NOT NULL, importance TEXT NOT NULL, keywords_json TEXT NOT NULL,
 source_excerpt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_matches (
 requirement_id TEXT PRIMARY KEY REFERENCES job_requirements(id), status TEXT NOT NULL,
 evidence_ids_json TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS resumes (
 id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id),
 language TEXT NOT NULL, content_json TEXT NOT NULL, outdated INTEGER NOT NULL DEFAULT 0, activity_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

"""



def initialize_career(conn: sqlite3.Connection) -> None:
    """Initialize opt-in Career tables without changing conversational memory."""
    conn.executescript(CAREER_SCHEMA)
