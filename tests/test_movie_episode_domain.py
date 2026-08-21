from app.models.movie import (
    MovieEpisodeMetadata,
    MovieEpisodeRecord,
    MovieEpisodeRuntime,
    MovieMetadata,
    MovieRecord,
    MovieRuntime,
    legacy_episode_uuid,
)


def test_legacy_episode_uuid_is_deterministic() -> None:
    assert legacy_episode_uuid("legacy") == "e3b45b99-bcfb-5601-8168-a1f50ae86289"
    assert legacy_episode_uuid("legacy") == legacy_episode_uuid("legacy")
    assert legacy_episode_uuid("movie-1") != legacy_episode_uuid("legacy")


def test_movie_metadata_keeps_episodes_in_display_order() -> None:
    movie = MovieMetadata(
        uuid="work-1",
        cover_key="Series",
        episodes=[
            MovieEpisodeMetadata(uuid="episode-2", display_order=2, source_name="02.mkv"),
            MovieEpisodeMetadata(uuid="episode-1", display_order=1, source_name="01.mkv"),
        ],
    )

    assert [episode.uuid for episode in movie.episodes] == ["episode-1", "episode-2"]


def test_single_episode_is_exposed_only_for_exactly_one_child() -> None:
    episode = MovieEpisodeRecord(
        MovieEpisodeMetadata(uuid="episode-1", display_order=1),
        MovieEpisodeRuntime(video_path="/media/01.mkv", availability_status="available"),
    )
    single = MovieRecord(MovieMetadata(uuid="single", cover_key="Single"), MovieRuntime(), [episode])
    multi = MovieRecord(
        MovieMetadata(uuid="multi", cover_key="Multi"),
        MovieRuntime(availability_status="available"),
        [
            episode,
            MovieEpisodeRecord(
                MovieEpisodeMetadata(uuid="episode-2", display_order=2),
                MovieEpisodeRuntime(video_path="/media/02.mkv", availability_status="offline"),
            ),
        ],
    )

    assert single.single_episode() is episode
    assert multi.single_episode() is None
    assert [item.metadata.uuid for item in multi.playable_episodes()] == ["episode-1"]
    assert multi.episode("episode-2") is multi.episodes[1]
    assert multi.episode("missing") is None
