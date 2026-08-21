from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieRecord,
    MovieRuntime,
)
from app.services.cover_matching import movie_cover_keys


def test_movie_cover_keys_include_work_and_every_episode_source_name() -> None:
    record = MovieRecord(
        MovieMetadata(
            uuid="work",
            cover_key="SHOW",
            code="SHOW-ALT",
            title="标题",
            episodes=[
                MovieEpisodeMetadata("episode-1", 1, source_name="SHOW_01.mkv"),
                MovieEpisodeMetadata("episode-2", 2, source_name="SHOW_02.mkv"),
            ],
        ),
        MovieRuntime(),
        [
            MovieEpisodeRecord(
                MovieEpisodeMetadata("episode-1", 1, source_name="SHOW_01.mkv"),
                MovieEpisodeRuntime(video_path="D:/Media/SHOW/SHOW_01.mkv"),
            ),
            MovieEpisodeRecord(
                MovieEpisodeMetadata("episode-2", 2, source_name="SHOW_02.mkv"),
                MovieEpisodeRuntime(video_path="D:/Media/SHOW/SHOW_02.mkv"),
            ),
        ],
    )

    assert movie_cover_keys([record]) == [
        "标题",
        "SHOW",
        "SHOW-ALT",
        "SHOW_01.mkv",
        "SHOW_01",
        "D:/Media/SHOW/SHOW_01.mkv",
        "SHOW_02.mkv",
        "SHOW_02",
        "D:/Media/SHOW/SHOW_02.mkv",
    ]


def test_movie_cover_keys_deduplicate_case_and_punctuation_variants() -> None:
    record = MovieRecord(
        MovieMetadata(uuid="work", cover_key="SHOW-01", code="show_01", title="Show 01"),
        MovieRuntime(),
    )

    assert movie_cover_keys([record]) == ["Show 01"]
