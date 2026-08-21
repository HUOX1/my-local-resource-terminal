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


def test_multi_episode_archive_uses_compact_buttons_and_icon_only_details_entry():
    source = (ROOT / "app" / "ui" / "movie_archive_page.py").read_text(encoding="utf-8")
    dialog_source = (ROOT / "app" / "ui" / "movie_episode_dialog.py").read_text(encoding="utf-8")

    assert "episode_play_requested = Signal(str, str)" in source
    assert "episode_relink_requested = Signal(str, str)" in source
    assert "episode_folder_requested = Signal(str, str)" in source
    assert "build_episode_actions(record.episodes)" in source
    assert 'self.episode_details_button.setText("")' in source
    assert 'self.episode_details_button.setToolTip("剧集详情")' in source
    assert 'self.episode_details_button.setIcon(flat_icon("info"))' in source
    assert 'QPushButton("剧集详情")' not in source
    assert "class MovieEpisodeDialog(QDialog)" in dialog_source
    assert "relink_requested = Signal(str, str)" in dialog_source
    assert "open_folder_requested = Signal(str, str)" in dialog_source
