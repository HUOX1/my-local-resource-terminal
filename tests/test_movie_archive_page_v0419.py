from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_movie_archive_page_is_in_content_page_and_uses_existing_movie_fields():
    source = (ROOT / "app" / "ui" / "movie_archive_page.py").read_text(encoding="utf-8")
    assert "class MovieArchivePage(QWidget)" in source
    assert "back_requested = Signal()" in source
    assert "play_requested = Signal(str)" in source
    assert "metadata_patch_requested = Signal(str, object)" in source
    for token in (
        "actors_field",
        "series_field",
        "studio_field",
        "release_field",
        "tags_field",
        "notes_edit",
        "play_time_label",
        "media_summary_label",
        "path_label",
        "cover_label",
    ):
        assert token in source
    assert "def set_record(self, record: MovieRecord)" in source


def test_main_window_opens_movie_archive_in_content_stack_and_uses_page_as_editor():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "from app.ui.movie_archive_page import MovieArchivePage" in source
    assert "self.movie_archive_page = MovieArchivePage()" in source
    assert "self.content_page_stack.addWidget(self.movie_archive_page)" in source
    assert "self.movie_archive_page.set_record(record)" in source
    assert "self.content_page_stack.setCurrentWidget(self.movie_archive_page)" in source
    assert "def _close_movie_archive" in source
    assert "def _update_movie_archive_metadata" in source
    assert "MovieDetailDialog(" not in source


def test_movie_archive_play_signal_launches_current_movie_and_page_refreshes_after_catalog_change():
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "self.movie_archive_page.play_requested.connect(self._play_movie_by_uuid)" in source
    assert "def _play_movie_by_uuid" in source
    assert "self.movie_archive_page.movie_uuid" in source
