from app.services.episode_parser import natural_name_key, parse_episode_identity


def test_parses_supported_episode_suffixes() -> None:
    cases = {
        "01": (None, 1),
        "作品_02": (None, 2),
        "作品-E03": (None, 3),
        "作品 EP04": (None, 4),
        "S01E05": (1, 5),
        "show.s02e06": (2, 6),
        "show_ep07": (None, 7),
    }

    for stem, expected in cases.items():
        identity = parse_episode_identity(stem)
        assert identity.reliable is True
        assert (identity.season_number, identity.episode_number) == expected


def test_does_not_treat_unrelated_embedded_digits_as_episode() -> None:
    identity = parse_episode_identity("Part2Final")

    assert identity.reliable is False
    assert identity.season_number is None
    assert identity.episode_number is None


def test_natural_name_key_orders_numeric_segments_numerically() -> None:
    names = ["作品_10.mkv", "作品_2.mkv", "作品_1.mkv"]

    assert sorted(names, key=natural_name_key) == [
        "作品_1.mkv",
        "作品_2.mkv",
        "作品_10.mkv",
    ]
