PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS movies (
    uuid TEXT PRIMARY KEY,
    cover_key TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    series TEXT NOT NULL DEFAULT '',
    studio TEXT NOT NULL DEFAULT '',
    release_date TEXT NOT NULL DEFAULT '',
    rating INTEGER NOT NULL DEFAULT 0 CHECK(rating BETWEEN 0 AND 5),
    watched INTEGER NOT NULL DEFAULT 0,
    play_count INTEGER NOT NULL DEFAULT 0,
    total_play_seconds INTEGER NOT NULL DEFAULT 0,
    favorite INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    folder_id TEXT,
    first_watched_at TEXT,
    last_watched_at TEXT,
    added_at TEXT,
    video_path TEXT,
    library_id TEXT,
    availability_status TEXT NOT NULL DEFAULT 'offline' CHECK(availability_status IN ('available','offline')),
    subtitle_status INTEGER NOT NULL DEFAULT 0,
    duration REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    file_size INTEGER,
    cover_path TEXT,
    last_scanned_at TEXT
);

CREATE TABLE IF NOT EXISTS movie_episodes (
    uuid TEXT PRIMARY KEY,
    movie_uuid TEXT NOT NULL REFERENCES movies(uuid) ON DELETE CASCADE,
    display_order INTEGER NOT NULL,
    episode_number INTEGER,
    season_number INTEGER,
    source_name TEXT NOT NULL DEFAULT '',
    video_path TEXT,
    library_id TEXT,
    availability_status TEXT NOT NULL DEFAULT 'offline' CHECK(availability_status IN ('available','offline')),
    subtitle_status INTEGER NOT NULL DEFAULT 0,
    duration REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    file_size INTEGER,
    last_scanned_at TEXT
);

CREATE TABLE IF NOT EXISTS libraries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS actors (
    name TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS movie_actors (
    movie_uuid TEXT NOT NULL REFERENCES movies(uuid) ON DELETE CASCADE,
    actor_name TEXT NOT NULL REFERENCES actors(name) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (movie_uuid, actor_name)
);

CREATE TABLE IF NOT EXISTS tags (
    name TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS movie_tags (
    movie_uuid TEXT NOT NULL REFERENCES movies(uuid) ON DELETE CASCADE,
    tag_name TEXT NOT NULL REFERENCES tags(name) ON DELETE CASCADE,
    PRIMARY KEY (movie_uuid, tag_name)
);

CREATE TABLE IF NOT EXISTS play_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_uuid TEXT NOT NULL REFERENCES movies(uuid) ON DELETE CASCADE,
    played_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_movies_cover_key ON movies(cover_key COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_movies_availability ON movies(availability_status);
CREATE INDEX IF NOT EXISTS idx_movies_favorite ON movies(favorite);
CREATE INDEX IF NOT EXISTS idx_movies_watched ON movies(watched);
CREATE INDEX IF NOT EXISTS idx_play_events_movie ON play_events(movie_uuid, played_at);
CREATE INDEX IF NOT EXISTS idx_movie_episodes_movie ON movie_episodes(movie_uuid);
CREATE INDEX IF NOT EXISTS idx_movie_episodes_video_path ON movie_episodes(video_path);
CREATE INDEX IF NOT EXISTS idx_movie_episodes_library_status ON movie_episodes(library_id, availability_status);
CREATE INDEX IF NOT EXISTS idx_movie_episodes_order ON movie_episodes(movie_uuid, display_order);


CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    uuid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    series TEXT NOT NULL DEFAULT '',
    developer TEXT NOT NULL DEFAULT '',
    publisher TEXT NOT NULL DEFAULT '',
    release_date TEXT NOT NULL DEFAULT '',
    rating INTEGER NOT NULL DEFAULT 0 CHECK(rating BETWEEN 0 AND 5),
    favorite INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL,
    launch_exe TEXT NOT NULL DEFAULT '',
    launch_args TEXT NOT NULL DEFAULT '',
    working_directory TEXT NOT NULL DEFAULT '',
    timing_exe TEXT NOT NULL DEFAULT '',
    cover_path TEXT,
    preview_gif_path TEXT,
    archive_media_path TEXT,
    screenshot_directory TEXT,
    folder_id TEXT,
    total_play_seconds INTEGER NOT NULL DEFAULT 0,
    play_count INTEGER NOT NULL DEFAULT 0,
    first_played_at TEXT,
    last_played_at TEXT
);

CREATE TABLE IF NOT EXISTS game_tags (
    game_uuid TEXT NOT NULL REFERENCES games(uuid) ON DELETE CASCADE,
    tag_name TEXT NOT NULL,
    PRIMARY KEY (game_uuid, tag_name)
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id TEXT PRIMARY KEY,
    game_uuid TEXT NOT NULL REFERENCES games(uuid) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    last_checkpoint_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('active','completed','recovered'))
);

CREATE INDEX IF NOT EXISTS idx_games_title ON games(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_games_favorite ON games(favorite);
CREATE INDEX IF NOT EXISTS idx_games_added_at ON games(added_at);
CREATE INDEX IF NOT EXISTS idx_games_last_played_at ON games(last_played_at);
CREATE INDEX IF NOT EXISTS idx_games_total_play_seconds ON games(total_play_seconds);
CREATE INDEX IF NOT EXISTS idx_game_sessions_game ON game_sessions(game_uuid, started_at);
