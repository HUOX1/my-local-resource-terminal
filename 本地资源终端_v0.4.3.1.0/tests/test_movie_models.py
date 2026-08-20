import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt

from app.models.movie import MovieMetadata, MovieRecord, MovieRuntime
from app.ui.movie_models import MovieListModel, MovieTableModel


def make_record(index: int = 0, status: str = "offline") -> MovieRecord:
    return MovieRecord(
        MovieMetadata.new(f"CODE-{index}", f"CODE-{index}"),
        MovieRuntime(availability_status=status),
    )


def test_list_model_exposes_offline_status(qtbot):
    record = make_record()
    model = MovieListModel([record])
    index = model.index(0, 0)
    assert model.data(index, MovieListModel.AvailabilityRole) == "offline"
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == record.metadata.code


def test_table_model_has_expected_columns(qtbot):
    model = MovieTableModel([make_record()])
    assert model.columnCount() == 12
    assert model.rowCount() == 1


def test_list_model_handles_two_thousand_records_without_widgets(qtbot):
    model = MovieListModel([make_record(i) for i in range(2000)])
    assert model.rowCount() == 2000
