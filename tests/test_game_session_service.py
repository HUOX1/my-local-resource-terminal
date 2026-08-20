from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.database import Database
from app.models.game import GameMetadata
from app.repositories.game_repository import GameRepository
from app.services.game_metadata_service import GameMetadataService
from app.services.game_session_service import GameSessionService


class Clock:
    def __init__(self, now):
        self.value = now

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


def build_service(tmp_path, clock, running):
    db = Database(tmp_path / "library.db")
    db.initialize()
    repo = GameRepository(db)
    metadata = GameMetadataService(tmp_path / "games")
    state_path = tmp_path / "state" / "active_game_session.json"
    state_path.parent.mkdir()
    service = GameSessionService(
        repo,
        metadata,
        state_path,
        process_paths=lambda: set(running),
        now=clock.now,
    )
    return service, repo, metadata, state_path


def make_game(tmp_path):
    launch = tmp_path / "launcher.exe"
    timing = tmp_path / "game.exe"
    launch.write_bytes(b"")
    timing.write_bytes(b"")
    game = GameMetadata.new("Demo")
    game.launch_exe = str(launch)
    game.timing_exe = str(timing)
    return game


def test_session_starts_only_after_terminal_request_and_timing_process_appears(tmp_path):
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    clock = Clock(start)
    running = set()
    service, repo, metadata, _ = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)

    service.poll()
    assert service.active_game_uuid is None

    assert service.request_launch(game) is True
    clock.advance(12)
    service.poll()
    assert service.active_game_uuid is None

    running.add(game.timing_exe)
    service.poll()

    assert service.active_game_uuid == game.uuid
    assert service.elapsed_seconds == 0
    assert service.active_session.started_at == clock.now()


def test_second_game_cannot_take_timing_ownership(tmp_path):
    clock = Clock(datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc))
    running = set()
    service, repo, metadata, _ = build_service(tmp_path, clock, running)
    a = make_game(tmp_path)
    b = GameMetadata.new("Other")
    other = tmp_path / "other.exe"
    other.write_bytes(b"")
    b.launch_exe = str(other)
    b.timing_exe = str(other)
    for game in (a, b):
        metadata.save(game)
        repo.upsert_game(game)

    assert service.request_launch(a) is True
    running.add(a.timing_exe)
    service.poll()
    assert service.request_launch(b) is False
    assert service.active_game_uuid == a.uuid


def test_waiting_request_times_out_without_history(tmp_path):
    clock = Clock(datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc))
    running = set()
    service, repo, metadata, _ = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)
    service.request_launch(game)

    clock.advance(301)
    service.poll()

    assert service.active_game_uuid is None
    assert service.waiting_game_uuid is None
    assert repo.get(game.uuid).metadata.sessions == []


def test_checkpoint_overwrites_single_active_session_and_completion_is_exact(tmp_path):
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    clock = Clock(start)
    running = set()
    service, repo, metadata, state_path = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)
    service.request_launch(game)
    running.add(game.timing_exe)
    service.poll()

    clock.advance(30)
    service.poll()
    service.checkpoint()
    first_text = state_path.read_text(encoding="utf-8")
    clock.advance(30)
    service.poll()
    service.checkpoint()
    second_text = state_path.read_text(encoding="utf-8")
    assert first_text != second_text
    with repo.database.connect() as con:
        assert con.execute("SELECT COUNT(*) AS c FROM game_sessions WHERE status='active'").fetchone()["c"] == 1

    clock.advance(7)
    running.clear()
    service.poll()

    restored = metadata.load(game.uuid)
    assert restored.total_play_seconds == 67
    assert restored.play_count == 1
    assert restored.sessions[0].duration_seconds == 67
    assert not state_path.exists()


def test_recovery_closes_at_last_checkpoint_when_process_is_gone(tmp_path):
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    clock = Clock(start)
    running = set()
    service, repo, metadata, state_path = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)
    service.request_launch(game)
    running.add(game.timing_exe)
    service.poll()
    clock.advance(30)
    service.poll()
    service.checkpoint()

    running.clear()
    clock.advance(100)
    recovered = GameSessionService(
        repo,
        metadata,
        state_path,
        process_paths=lambda: set(running),
        now=clock.now,
    )
    recovered.recover()

    archived = metadata.load(game.uuid)
    assert archived.sessions[0].status == "recovered"
    assert archived.sessions[0].duration_seconds == 30
    assert not state_path.exists()


def test_recovery_continues_same_session_when_process_is_alive(tmp_path):
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    clock = Clock(start)
    running = set()
    service, repo, metadata, state_path = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)
    service.request_launch(game)
    running.add(game.timing_exe)
    service.poll()
    session_id = service.active_session.id
    clock.advance(30)
    service.checkpoint()
    clock.advance(70)

    recovered = GameSessionService(repo, metadata, state_path, process_paths=lambda: set(running), now=clock.now)
    recovered.recover()

    assert recovered.active_session.id == session_id
    assert recovered.elapsed_seconds == 100


def test_explicit_shutdown_finishes_to_current_second(tmp_path):
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    clock = Clock(start)
    running = set()
    service, repo, metadata, _ = build_service(tmp_path, clock, running)
    game = make_game(tmp_path)
    metadata.save(game)
    repo.upsert_game(game)
    service.request_launch(game)
    running.add(game.timing_exe)
    service.poll()
    clock.advance(19)

    service.finish_active()

    assert metadata.load(game.uuid).total_play_seconds == 19
    assert service.active_game_uuid is None
