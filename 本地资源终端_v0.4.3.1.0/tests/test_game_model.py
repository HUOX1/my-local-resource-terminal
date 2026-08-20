from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.game import GameMetadata, GameSession


def test_game_metadata_normalizes_tags_and_rating():
    game = GameMetadata.new("Demo")
    game.tags = ["RPG", " rpg ", "单机"]
    game.rating = 5

    game.normalize()

    assert game.tags == ["RPG", "单机"]
    assert game.title == "Demo"


def test_game_metadata_rejects_rating_outside_zero_to_five():
    with pytest.raises(ValueError):
        GameMetadata.new("Demo", rating=6)


def test_completed_session_recalculates_aggregates():
    start = datetime(2026, 8, 17, 1, 0, tzinfo=timezone.utc)
    game = GameMetadata.new("Demo", added_at=start)
    game.sessions = [
        GameSession.completed(game.uuid, start, start + timedelta(seconds=61)),
        GameSession.completed(game.uuid, start + timedelta(hours=1), start + timedelta(hours=1, seconds=39)),
    ]

    game.recalculate_play_stats()

    assert game.total_play_seconds == 100
    assert game.play_count == 2
    assert game.first_played_at == start
    assert game.last_played_at == start + timedelta(hours=1, seconds=39)
