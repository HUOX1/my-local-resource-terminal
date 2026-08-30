from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_schema_contains_launch_profile_fields():
    text = (ROOT / "g3_core" / "schema.sql").read_text(encoding="utf-8")
    for field in (
        "profile_type", "launch_exe", "launch_args", "working_directory",
        "content_path", "monitor_exe", "wait_timeout_s", "run_as_admin",
    ):
        assert field in text


def test_models_define_launch_profile():
    text = (ROOT / "g3_core" / "models.py").read_text(encoding="utf-8")
    assert "class LaunchProfile:" in text
    assert 'profile_type: str = "direct"' in text
    assert "monitor_exe: Path | None" in text


def test_backend_exposes_launch_profile_commands():
    text = (ROOT / "g3_core" / "backend_app.py").read_text(encoding="utf-8")
    assert '"game.launch_profile.get"' in text
    assert '"game.launch_profile.update"' in text
