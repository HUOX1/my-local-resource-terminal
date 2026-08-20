from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from app.models.game import GameMetadata, GameSession
from app.services.game_metadata_service import GameMetadataService


def test_game_archive_round_trip_preserves_completed_sessions(tmp_path):
    service = GameMetadataService(tmp_path / "games")
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    game = GameMetadata.new("Demo", added_at=start)
    game.launch_exe = r"D:\\Games\\Demo\\demo.exe"
    game.timing_exe = r"D:\\Games\\Demo\\bin\\demo.exe"
    game.tags = ["RPG", "单机"]
    game.sessions.append(GameSession.completed(game.uuid, start, start + timedelta(seconds=60)))
    game.recalculate_play_stats()

    service.save(game)
    restored = service.load(game.uuid)

    assert restored.title == "Demo"
    assert restored.launch_exe == game.launch_exe
    assert restored.tags == ["RPG", "单机"]
    assert restored.total_play_seconds == 60
    assert restored.sessions[0].duration_seconds == 60


def test_game_archive_save_is_atomic_and_valid_json(tmp_path):
    service = GameMetadataService(tmp_path / "games")
    game = GameMetadata.new("Demo")

    service.save(game)

    payload = json.loads(service.path_for(game.uuid).read_text(encoding="utf-8"))
    assert payload["uuid"] == game.uuid
    assert not list((tmp_path / "games").glob("*.tmp"))


def test_game_load_all_skips_corrupt_json(tmp_path):
    service = GameMetadataService(tmp_path / "games")
    good = GameMetadata.new("Good")
    service.save(good)
    (tmp_path / "games" / "broken.json").write_text("{", encoding="utf-8")

    games, errors = service.load_all()

    assert [game.uuid for game in games] == [good.uuid]
    assert len(errors) == 1


def test_game_archive_description_round_trip_and_old_json_default(tmp_path):
    service = GameMetadataService(tmp_path / "games")
    game = GameMetadata.new("Demo")
    game.description = "一款关于循环与生存的游戏。"
    game.notes = "我自己的记录"
    service.save(game)

    restored = service.load(game.uuid)
    assert restored.description == "一款关于循环与生存的游戏。"
    assert restored.notes == "我自己的记录"

    payload = json.loads(service.path_for(game.uuid).read_text(encoding="utf-8"))
    payload.pop("description")
    service.path_for(game.uuid).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    legacy = service.load(game.uuid)
    assert legacy.description == ""


def test_game_folder_id_round_trip_and_legacy_default(tmp_path):
    service = GameMetadataService(tmp_path / "games")
    game = GameMetadata.new("Folder Demo")
    game.folder_id = "folder-games-1"
    service.save(game)

    restored = service.load(game.uuid)
    assert restored.folder_id == "folder-games-1"

    payload = json.loads(service.path_for(game.uuid).read_text(encoding="utf-8"))
    payload.pop("folder_id")
    service.path_for(game.uuid).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert service.load(game.uuid).folder_id is None
