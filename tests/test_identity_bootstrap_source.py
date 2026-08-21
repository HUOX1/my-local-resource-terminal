from pathlib import Path


def test_bootstrap_creates_identity_service_before_main_window_and_no_longer_forces_settings_first() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    assert "IdentityService(path.parent / \"identity\")" in source
    assert "identity_service=identity_service" in source
    assert "if not settings.libraries:" not in source
    assert "if settings.auto_scan and settings.libraries:" in source


def test_main_window_starts_in_identity_shell_and_identity_room_replaces_brand() -> None:
    source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "identity_service" in source
    assert "IdentityShellWidget" in source
    assert "IdentitySidebarRoom" in source
    assert "self.root_stack" in source
    assert "self.root_stack.setCurrentWidget(self.identity_shell)" in source
    assert "def _enter_main_shell" in source
    assert "transition_stack_page(self.root_stack, self.main_shell" in source
    assert 'brand = QLabel("本地资源终端")' not in source
    assert 'subtitle = QLabel("LOCAL COLLECTION")' not in source


def test_version_advances_to_v0408() -> None:
    project = Path("pyproject.toml").read_text(encoding="utf-8")
    main = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert 'version = "0.4.3.1.1"' in project
    assert "v0.4.3.1.1" in main
