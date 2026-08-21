from pathlib import Path


def test_settings_dialog_exposes_backup_restore_and_visual_assets_only_in_settings() -> None:
    source = Path("app/ui/settings_dialog.py").read_text(encoding="utf-8")
    assert "备份与恢复" in source
    assert "包含视觉资源" in source
    assert "include_visual_assets=" in source
    assert "创建备份" in source
    assert "从备份恢复" in source
    assert "外部截图" in source

    main_source = Path("app/ui/main_window.py").read_text(encoding="utf-8")
    assert "创建备份" not in main_source
    assert "从备份恢复" not in main_source


def test_settings_dialog_exposes_startup_library_choice() -> None:
    source = Path("app/ui/settings_dialog.py").read_text(encoding="utf-8")
    assert "启动默认资源库" in source
    assert 'addItem("影片", "movies")' in source
    assert 'addItem("游戏", "games")' in source
    assert "startup_library=self.startup_library_combo.currentData()" in source


def test_bootstrap_passes_settings_path_to_settings_dialog() -> None:
    source = Path("app/bootstrap.py").read_text(encoding="utf-8")
    assert "SettingsDialog(settings, settings_path=path)" not in source
    assert "SettingsDialog(current, window, settings_path=path)" in source
