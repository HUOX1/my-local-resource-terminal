from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_movie_delegate_reuses_cover_work_between_repaints() -> None:
    source = (ROOT / "app" / "ui" / "movie_delegate.py").read_text(encoding="utf-8")
    assert "self._cover_size_cache" in source
    assert "self._scaled_pixmap_cache" in source
    assert "def clear_cache" in source
    assert "def _scaled_cover_pixmap" in source

    paint_source = source.split("def paint", 1)[1]
    assert "QPixmap(str(cover_path))" not in paint_source
    assert ".scaled(" not in paint_source


def test_movie_model_reset_invalidates_delegate_poster_cache() -> None:
    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "self.grid_model.modelReset.connect(self.grid_delegate.clear_cache)" in source
