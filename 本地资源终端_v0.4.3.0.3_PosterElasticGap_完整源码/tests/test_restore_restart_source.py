from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_successful_restore_requests_automatic_restart_before_quitting() -> None:
    source = (ROOT / "app" / "ui" / "settings_dialog.py").read_text(encoding="utf-8")

    restore_done_at = source.index('"恢复完成"')
    restart_message_at = source.index("软件将自动重新启动")
    restart_request_at = source.index("_local_movie_manager_restart_requested")
    quit_at = source.index("app.quit()", restart_request_at)

    assert restore_done_at < restart_message_at < restart_request_at < quit_at


def test_main_releases_single_instance_gate_before_relaunching_after_restore() -> None:
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")

    exec_at = source.index("exit_code = app.exec()")
    restart_check_at = source.index("_local_movie_manager_restart_requested", exec_at)
    release_at = source.index("single_instance_gate.release()", restart_check_at)
    relaunch_at = source.index("restart_application()", release_at)

    assert exec_at < restart_check_at < release_at < relaunch_at


def test_single_instance_gate_has_explicit_release_for_restart_handoff() -> None:
    source = (ROOT / "app" / "single_instance.py").read_text(encoding="utf-8")

    assert "def release(self) -> None:" in source
    assert "self._server.close()" in source
    assert "QLocalServer.removeServer(self.server_name)" in source


def test_restart_helper_relaunches_the_same_python_entrypoint_without_shell_scripts() -> None:
    path = ROOT / "app" / "restart.py"
    assert path.is_file(), "restart helper must exist"
    source = path.read_text(encoding="utf-8")

    assert "sys.executable" in source
    assert '"-m", "app.main"' in source
    assert "getattr(sys, \"frozen\", False)" in source
    assert "subprocess.Popen" in source
