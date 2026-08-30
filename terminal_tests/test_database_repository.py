from terminal_core.database import Database
from terminal_core.models import CreateGame
from terminal_core.repository import LibraryRepository


def test_new_database_has_v06_tables(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    assert {"library_items", "games", "media_assets", "terminal_state"} <= db.table_names()


def test_create_and_list_game_round_trip(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    repo = LibraryRepository(db)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    created = repo.create_game(CreateGame(title="Demo", executable_path=exe))
    loaded = repo.get_game(created.id)
    assert loaded is not None
    assert loaded.title == "Demo"
    assert loaded.executable_path == exe.resolve()
    assert repo.list_games()[0].id == created.id


def test_media_asset_manual_source_wins(tmp_path):
    db = Database(tmp_path / "library.db")
    db.initialize()
    repo = LibraryRepository(db)
    exe = tmp_path / "demo.exe"
    exe.write_bytes(b"")
    game = repo.create_game(CreateGame(title="Demo", executable_path=exe))
    auto = tmp_path / "auto.jpg"
    manual = tmp_path / "manual.jpg"
    auto.write_bytes(b"a")
    manual.write_bytes(b"m")
    repo.add_media_asset(game.id, "cover", auto, source="auto", priority=0)
    repo.add_media_asset(game.id, "cover", manual, source="manual", priority=99)
    best = repo.best_media_asset(game.id, "cover")
    assert best is not None
    assert best.path == manual.resolve()
