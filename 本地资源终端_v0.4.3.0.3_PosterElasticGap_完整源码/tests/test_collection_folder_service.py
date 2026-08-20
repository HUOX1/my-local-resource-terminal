from __future__ import annotations

import json

import pytest

from app.services.collection_folder_service import CollectionFolderService


def test_collection_folder_service_round_trips_one_level_folders(tmp_path):
    path = tmp_path / "collections" / "folders.json"
    service = CollectionFolderService(path)

    movies = service.create("movies", "恐怖")
    games = service.create("games", "PS3")

    reloaded = CollectionFolderService(path)
    assert [(item.id, item.name) for item in reloaded.list("movies")] == [(movies.id, "恐怖")]
    assert [(item.id, item.name) for item in reloaded.list("games")] == [(games.id, "PS3")]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert {item["domain"] for item in payload["folders"]} == {"movies", "games"}


def test_collection_folder_names_are_unique_per_domain_case_insensitively(tmp_path):
    service = CollectionFolderService(tmp_path / "folders.json")
    service.create("movies", "恐怖")
    with pytest.raises(ValueError):
        service.create("movies", "  恐怖  ")
    with pytest.raises(ValueError):
        service.create("movies", "恐怖".upper())
    # Same visible name is allowed in the other library/domain.
    assert service.create("games", "恐怖").domain == "games"


def test_collection_folder_rename_and_delete_are_persistent(tmp_path):
    path = tmp_path / "folders.json"
    service = CollectionFolderService(path)
    folder = service.create("movies", "旧名字")

    renamed = service.rename(folder.id, "新名字")
    assert renamed.name == "新名字"
    assert CollectionFolderService(path).get(folder.id).name == "新名字"

    service.delete(folder.id)
    assert CollectionFolderService(path).get(folder.id) is None
