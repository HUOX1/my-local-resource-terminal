from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "tools" / "run_retro_smoke.bat"
RUNNER = ROOT / "tools" / "retro_smoke_runner.py"
SMOKE = ROOT / "tests" / "test_retro_gui_smoke.py"


def test_local_windows_smoke_contract():
    assert BATCH.exists(), "Local Windows smoke launcher is missing"
    assert RUNNER.exists(), "Local smoke runner is missing"
    assert SMOKE.exists(), "Retro GUI smoke scenario is missing"

    batch = BATCH.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    smoke = SMOKE.read_text(encoding="utf-8")

    assert "retro_smoke_runner.py" in batch
    assert "QT_QPA_PLATFORM=" in batch
    assert ".venv\\Scripts\\python.exe" in batch
    assert "retro-smoke-local" in runner
    assert "latest.log" in runner
    assert "platformName" in runner
    assert "test_scene_draw_pipeline_exercises_focus_details_and_chrome" in runner
    assert "test_real_widget_resize_and_repaint_does_not_route_python_exceptions" in runner
    assert "test_scene_sound_settings_and_semantic_events_are_safe" in runner
    assert "sound packs / mapping / semantic events" in runner
    assert 'os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")' not in smoke


def test_local_runner_reports_missing_pyside_cleanly_when_runtime_is_absent(tmp_path):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)  # keep this source test independent of any accidental project install
    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    # This test environment intentionally has no PySide6. The runner should
    # report that prerequisite cleanly rather than crashing inside logging.
    assert result.returncode == 2, result.stdout + result.stderr
    assert "PySide6 could not be imported" in result.stdout
    assert "AttributeError" not in result.stdout + result.stderr
