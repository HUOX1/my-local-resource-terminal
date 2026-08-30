from pathlib import Path
import sys
import time

from g3_core.database import Database
from g3_core.models import CreateGame
from g3_core.repository import LibraryRepository
from g3_core.services.game_runtime import GameRuntime


def _repo(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    return LibraryRepository(db)


def test_runtime_launches_without_shell_and_records_stats(tmp_path):
    repo = _repo(tmp_path)
    game = repo.create_game(CreateGame(
        title="Sleeper",
        executable_path=Path(sys.executable),
        launch_args='-c "import time; time.sleep(0.05)"',
        working_directory=str(tmp_path),
    ))
    runtime = GameRuntime(repo)
    running = runtime.launch(game)
    assert running.process.pid > 0
    result = runtime.wait_for_exit_blocking(running)
    assert result.item_id == game.id
    assert result.exit_code == 0
    loaded = repo.get_game(game.id)
    assert loaded is not None
    assert loaded.last_played_at is not None
    assert loaded.playtime_seconds >= 0


def test_runtime_rejects_missing_executable(tmp_path):
    repo = _repo(tmp_path)
    missing = tmp_path / "missing.exe"
    game = repo.create_game(CreateGame(title="Demo", executable_path=Path(sys.executable)))
    game.executable_path = missing
    runtime = GameRuntime(repo)
    try:
        runtime.launch(game)
    except FileNotFoundError as exc:
        assert Path(exc.args[0]) == missing
    else:
        raise AssertionError("missing executable was launched")
