from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.db.database import Database
from app.models.game import GameMetadata, GameSession
from app.repositories.game_repository import GameRepository


def build_repo(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    return GameRepository(db)


def test_game_repository_round_trip_and_delete(tmp_path):
    repo = build_repo(tmp_path)
    exe = tmp_path / "game.exe"
    exe.write_bytes(b"")
    game = GameMetadata.new("Demo")
    game.launch_exe = str(exe)
    game.timing_exe = str(exe)
    game.tags = ["RPG", "单机"]
    game.favorite = True

    repo.upsert_game(game)
    restored = repo.get(game.uuid)

    assert restored is not None
    assert restored.metadata.title == "Demo"
    assert restored.metadata.tags == ["RPG", "单机"]
    assert restored.installed is True

    repo.delete(game.uuid)
    assert repo.get(game.uuid) is None


def test_game_repository_persists_sessions_and_rebuilds(tmp_path):
    repo = build_repo(tmp_path)
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    game = GameMetadata.new("Demo", added_at=start)
    game.sessions = [GameSession.completed(game.uuid, start, start + timedelta(seconds=42))]
    game.recalculate_play_stats()

    repo.rebuild_from_archives([game])
    restored = repo.get(game.uuid)

    assert restored is not None
    assert restored.metadata.total_play_seconds == 42
    assert restored.metadata.sessions[0].duration_seconds == 42


def test_game_repository_search_filters_and_sorts(tmp_path):
    repo = build_repo(tmp_path)
    installed_exe = tmp_path / "installed.exe"
    installed_exe.write_bytes(b"")
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 2, 1, tzinfo=timezone.utc)

    a = GameMetadata.new("Alpha", added_at=older)
    a.launch_exe = str(installed_exe)
    a.timing_exe = str(installed_exe)
    a.favorite = True
    a.rating = 3
    a.total_play_seconds = 100
    a.play_count = 2
    a.last_played_at = older

    b = GameMetadata.new("Beta", added_at=newer)
    b.launch_exe = str(tmp_path / "missing.exe")
    b.timing_exe = b.launch_exe
    b.rating = 5
    b.total_play_seconds = 200
    b.play_count = 4
    b.last_played_at = newer

    repo.upsert_game(a)
    repo.upsert_game(b)

    assert [r.metadata.title for r in repo.search(favorite=True)] == ["Alpha"]
    assert [r.metadata.title for r in repo.search(installed=True)] == ["Alpha"]
    assert [r.metadata.title for r in repo.search(installed=False)] == ["Beta"]
    assert [r.metadata.title for r in repo.search(sort="total_play_seconds", descending=True)] == ["Beta", "Alpha"]
    assert [r.metadata.title for r in repo.search(sort="last_played_at", descending=True)] == ["Beta", "Alpha"]


def test_upsert_game_preserves_active_session_checkpoint(tmp_path):
    repo = build_repo(tmp_path)
    now = datetime(2026, 8, 17, 2, 0, tzinfo=timezone.utc)
    game = GameMetadata.new("Demo", added_at=now)
    repo.upsert_game(game)
    active = GameSession.active(game.uuid, now)
    active.duration_seconds = 30
    active.last_checkpoint_at = now + timedelta(seconds=30)
    repo.upsert_active_session(active)

    game.notes = "edited while playing"
    repo.upsert_game(game)

    with repo.database.connect() as connection:
        row = connection.execute(
            "SELECT status, duration_seconds FROM game_sessions WHERE id=?",
            (active.id,),
        ).fetchone()
    assert row is not None
    assert row["status"] == "active"
    assert row["duration_seconds"] == 30


def test_game_repository_round_trip_preserves_description(tmp_path):
    repo = build_repo(tmp_path)
    game = GameMetadata.new("Demo")
    game.description = "作品介绍"
    game.notes = "我的记录"
    repo.upsert_game(game)

    restored = repo.get(game.uuid)

    assert restored is not None
    assert restored.metadata.description == "作品介绍"
    assert restored.metadata.notes == "我的记录"
