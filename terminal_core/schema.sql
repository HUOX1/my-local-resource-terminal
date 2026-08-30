PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS library_items (
    id TEXT PRIMARY KEY,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    sort_title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    item_id TEXT PRIMARY KEY REFERENCES library_items(id) ON DELETE CASCADE,
    executable_path TEXT NOT NULL,
    launch_args TEXT NOT NULL DEFAULT '',
    working_directory TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    playtime_seconds INTEGER NOT NULL DEFAULT 0,
    last_played_at TEXT,
    installed_state TEXT NOT NULL DEFAULT 'installed'
);

CREATE TABLE IF NOT EXISTS media_assets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES library_items(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    cache_path TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL CHECK (source IN ('manual', 'auto', 'generated'))
);

CREATE TABLE IF NOT EXISTS terminal_state (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);
