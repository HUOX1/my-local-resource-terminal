from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_movie_archive_page_edits_metadata_inline_instead_of_opening_editor_dialog():
    source = read("app/ui/movie_archive_page.py")
    assert "metadata_patch_requested = Signal(str, object)" in source
    assert "cover_change_requested = Signal(str)" in source
    assert "open_folder_requested = Signal(str)" in source
    assert "relink_requested = Signal(str)" in source
    assert "delete_requested = Signal(str)" in source
    assert "edit_requested = Signal(str)" not in source
    assert 'QPushButton("编辑档案")' not in source
    assert "class InlineEditableField(QWidget)" in source
    assert "class StarRatingEditor(QWidget)" in source


def test_movie_archive_exposes_all_old_dialog_editable_metadata_on_the_page():
    source = read("app/ui/movie_archive_page.py")
    for token in (
        "title_field",
        "code_field",
        "cover_key_field",
        "actors_field",
        "series_field",
        "studio_field",
        "release_field",
        "tags_field",
        "rating_editor",
        "play_time_label",
        "notes_edit",
        "change_cover_button",
        "open_folder_button",
        "relink_button",
        "delete_button",
    ):
        assert token in source
    for pattern in (
        '_emit_text_patch("code", value)',
        '_emit_text_patch("cover_key", value)',
        '_emit_text_patch("title", value)',
        '_emit_list_patch("actors", value)',
        '_emit_text_patch("series", value)',
        '_emit_text_patch("studio", value)',
        '_emit_text_patch("release_date", value)',
        '_emit_list_patch("tags", value)',
        'MovieMetadataPatch(rating=value)',
        'MovieMetadataPatch(notes=value)',
    ):
        assert pattern in source


def test_hard_media_data_remains_read_only_and_play_time_is_a_stat():
    source = read("app/ui/movie_archive_page.py")
    assert "media_summary_label" in source
    assert "path_label" in source
    assert "play_time_label" in source
    assert "total_play_seconds" in source
    assert "subtitle_label" in source
    assert "availability_label" in source
    assert "media_summary_edit" not in source
    assert "watched_button" not in source
    assert "favorite_button" not in source


def test_main_window_handles_movie_archive_edits_without_movie_detail_dialog():
    source = read("app/ui/main_window.py")
    assert "from app.ui.movie_detail import MovieDetailDialog" not in source
    assert "MovieDetailDialog(" not in source
    assert "def _edit_movie_archive" not in source
    assert "metadata_patch_requested.connect(self._update_movie_archive_metadata)" in source
    assert "cover_change_requested.connect(self._change_movie_archive_cover)" in source
    assert "open_folder_requested.connect(self._open_movie_archive_folder)" in source
    assert "relink_requested.connect(self._relink_movie_archive)" in source
    assert "delete_requested.connect(self._delete_movie_archive)" in source
    assert "def _update_movie_archive_metadata" in source
    assert "self.catalog.update_metadata(uuid, patch)" in source
    assert "def _change_movie_archive_cover" in source
    assert "self.cover_service.replace(record.metadata.cover_key, Path(path))" in source
    assert "def _relink_movie_archive" in source
    assert "self.catalog.relink_video(uuid, Path(path))" in source
    assert "def _delete_movie_archive" in source
    assert "self.catalog.delete_archive(uuid)" in source
