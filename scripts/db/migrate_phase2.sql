-- Phase 2 migration: add memory_events table (SQLite-safe)
CREATE TABLE IF NOT EXISTS memory_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backend TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ts TIMESTAMP NOT NULL,
    details_json TEXT
);
