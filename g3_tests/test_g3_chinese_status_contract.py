from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_feature_map_is_chinese_and_named_g3():
    path = ROOT / "docs" / "v0.6" / "Phase1_Feature_Status.md"
    text = path.read_text(encoding="utf-8")
    assert "G3" in text
    assert "已可用" in text
    assert "待实机验收" in text
    assert "雨世界" in text
    assert "艾尔登法环" in text
    assert "寂静岭" in text
    assert "战神" in text
