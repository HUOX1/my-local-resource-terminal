from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_single_instance_gate_uses_qt_local_ipc_without_lock_files() -> None:
    path = ROOT / "app" / "single_instance.py"
    assert path.is_file(), "single-instance gate module must exist"
    source = path.read_text(encoding="utf-8")
    assert "QLocalServer" in source
    assert "QLocalSocket" in source
    assert 'b"activate\\n"' in source
    assert "removeServer" in source
    assert ".lock" not in source
    assert "lockfile" not in source.lower()


def test_single_instance_gate_can_queue_activation_until_window_exists() -> None:
    source = (ROOT / "app" / "single_instance.py").read_text(encoding="utf-8")
    assert "_pending_activation" in source
    assert "set_activation_handler" in source
    assert "_request_activation" in source


def test_bootstrap_checks_single_instance_before_loading_settings_or_services() -> None:
    source = (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")
    assert "from app.single_instance import SingleInstanceGate" in source
    assert 'SingleInstanceGate("LocalMovieManager.SingleInstance.v1")' in source
    acquire_at = source.index("single_instance_gate.acquire()")
    settings_at = source.index("path = Path(settings_path)")
    services_at = source.index("bundle = build_services(settings)")
    assert acquire_at < settings_at < services_at
    assert "_local_movie_manager_secondary_instance" in source
    assert "_local_movie_manager_single_instance_gate" in source


def test_primary_registers_window_activation_handler() -> None:
    source = (ROOT / "app" / "bootstrap.py").read_text(encoding="utf-8")
    for token in (
        "window.isMinimized()",
        "window.showNormal()",
        "window.raise_()",
        "window.activateWindow()",
        "single_instance_gate.set_activation_handler",
    ):
        assert token in source


def test_main_skips_event_loop_for_secondary_instance() -> None:
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'getattr(app, "_local_movie_manager_secondary_instance", False)' in source
    secondary_at = source.index("_local_movie_manager_secondary_instance")
    exec_at = source.index("app.exec()")
    assert secondary_at < exec_at
