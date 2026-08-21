from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_window_uses_natural_poster_delegate_without_legacy_mode_setting() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "MovieCardDelegate(self.grid_view)" in source
    assert "set_poster_display_mode" not in source
    assert "settings.poster_display_mode" not in source


def test_main_window_supports_multi_selection_and_batch_edit_menu() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert source.count("SelectionMode.ExtendedSelection") >= 2
    assert 'addMenu("批量编辑")' in source
    assert '"添加标签…"' in source
    assert '"删除标签…"' in source
    assert '"设置厂商…"' in source
    assert '"设置系列…"' in source
    assert "batch_update_metadata" in source
    assert "batch_update_tags" in source


def test_library_switch_preserves_runtime_window_size_without_visible_deferred_resize() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "runtime_size = self.size()" in source
    assert "runtime_minimum = self.minimumSize()" in source
    assert "runtime_maximum = self.maximumSize()" in source
    assert "self.setFixedSize(runtime_size)" in source
    assert "self.setMinimumSize(runtime_minimum)" in source
    assert "self.setMaximumSize(runtime_maximum)" in source
    assert "_restore_runtime_size" not in source
    assert "QTimer.singleShot(0" not in source
    assert "saveGeometry" not in source


def test_multi_episode_playback_is_explicitly_wired_from_archive_and_context_menu() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "self.movie_archive_page.episode_play_requested.connect(self._play_movie_episode)" in source
    assert "self.movie_archive_page.episode_relink_requested.connect(self._relink_movie_episode)" in source
    assert "self.movie_archive_page.episode_folder_requested.connect(self._open_movie_episode_folder)" in source
    assert "build_episode_actions(record.episodes)" in source
    assert 'play_menu = menu.addMenu("播放")' in source
    assert "def _play_movie_episode(self, movie_uuid: str, episode_uuid: str)" in source
    assert "self.catalog.episode_for_playback(movie_uuid, episode_uuid)" in source
    assert "self.viewing_service.start_playback(movie_uuid, handle)" in source
