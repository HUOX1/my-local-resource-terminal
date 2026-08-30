from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "g3_frontend" / "scripts" / "game_case_3d.gd"


def test_case_controller_loads_glb_asset():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'res://assets/models/game_case.glb' in text
    assert 'res://assets/models/game_case_placeholder.glb' in text
    assert "load(" in text or "ResourceLoader.load" in text


def test_case_final_path_does_not_construct_boxmesh_or_front_quad():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "BoxMesh.new()" not in text
    assert "QuadMesh.new()" not in text


def test_model_asset_contract_doc_exists():
    assert (ROOT / "g3_frontend" / "assets" / "models" / "README.md").is_file()
