from app.ui.batch_edit_helpers import parse_batch_terms


def test_parse_batch_terms_accepts_western_and_chinese_separators() -> None:
    assert parse_batch_terms("战队, 精神控制，GIGA、女英雄；收藏; 战队") == [
        "战队",
        "精神控制",
        "GIGA",
        "女英雄",
        "收藏",
    ]


def test_parse_batch_terms_ignores_blank_values_case_insensitively() -> None:
    assert parse_batch_terms("GIGA,, giga，  ，Hero") == ["GIGA", "Hero"]
