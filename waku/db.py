"""SQLite connection mechanics and the Career schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def open_connection(home: Path, check_same_thread: bool = True) -> sqlite3.Connection:
    # Career serializes its threaded HTTP workers around one connection.
    # busy_timeout bounds waits for another process using the same database.
    conn = sqlite3.connect(home / "state.db", check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=3000")
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
