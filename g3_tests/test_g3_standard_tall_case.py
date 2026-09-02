from __future__ import annotations

import json
import struct
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "g3_frontend" / "scripts" / "game_case_3d.gd"
MODEL = ROOT / "g3_frontend" / "assets" / "models" / "cases" / "standard_tall.glb"


def _glb_json(path: Path) -> dict:
    data = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF"
    assert version == 2
    assert total_length == len(data)
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    assert chunk_type == 0x4E4F534A  # JSON
    payload = data[20 : 20 + chunk_length].decode("utf-8").rstrip("\x00 ")
    return json.loads(payload)


def test_standard_tall_asset_is_shipped_with_chinese_interface_nodes():
    assert MODEL.is_file()
    document = _glb_json(MODEL)
    node_names = {node.get("name", "") for node in document.get("nodes", [])}
    assert "盒体" in node_names
    assert "封面正面" in node_names


def test_case_controller_uses_standard_tall_and_chinese_cover_interface():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'res://assets/models/cases/standard_tall.glb' in text
    assert '"封面正面"' in text
    assert '"cover_front"' in text  # legacy compatibility


def test_real_world_case_is_scaled_to_existing_g3_display_units():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "STANDARD_TALL_DISPLAY_SCALE: float = 10.0" in text
    assert "Vector3.ONE * STANDARD_TALL_DISPLAY_SCALE" in text
