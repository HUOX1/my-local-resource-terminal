from pathlib import Path


def test_identity_shell_supports_setup_entry_editor_and_gif_avatar() -> None:
    source = Path("app/ui/identity_shell.py").read_text(encoding="utf-8")
    assert "class IdentityAvatarWidget" in source
    assert "QMovie" in source
    assert "show_setup_state" in source
    assert "show_entry_state" in source
    assert "identity_created = Signal" in source
    assert "enter_requested = Signal" in source
    assert "identity_changed = Signal" in source
    assert "选择头像" in source
    assert "选择头像框" in source
    assert "建立身份" in source
    assert "点击头像进入" in source
    assert "我的身份" in source


def test_identity_sidebar_room_replaces_brand_area_and_is_themeable() -> None:
    source = Path("app/ui/identity_shell.py").read_text(encoding="utf-8")
    theme = Path("app/ui/flat_theme.py").read_text(encoding="utf-8")
    assert "class IdentitySidebarRoom" in source
    assert 'setObjectName("identitySidebarRoom")' in source
    assert "identitySidebarRoom" in theme
    assert "identityShell" in theme
