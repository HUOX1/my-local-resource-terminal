from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import AppSettings, LibraryConfig
from app.config.theme_registry import theme_options
from app.services.backup_restore_service import BackupRestoreService, InvalidBackupError


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None, settings_path: Path | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.settings_path = Path(settings_path) if settings_path else None
        self.backup_service = BackupRestoreService()
        self._result_settings = settings
        self.setWindowTitle("设置")
        self.resize(780, 620)
        self._build_ui()
        self._load(settings)

    @property
    def result_settings(self) -> AppSettings:
        return self._result_settings

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        heading = QLabel("设置")
        heading.setObjectName("dialogHeading")
        root.addWidget(heading)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        nav = QWidget()
        nav.setObjectName("settingsNav")
        nav.setFixedWidth(168)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 10, 8, 10)
        nav_layout.setSpacing(4)

        nav_title = QLabel("设置分类")
        nav_title.setObjectName("sectionLabel")
        nav_layout.addWidget(nav_title)

        self.settings_category_group = QButtonGroup(self)
        self.settings_category_group.setExclusive(True)
        categories = [
            ("外观", "主题与界面外观"),
            ("常规", "路径与存储"),
            ("影片库", "库目录与启用状态"),
            ("播放", "播放器与启动行为"),
            ("备份", "备份与恢复"),
        ]
        self.settings_category_buttons: list[QPushButton] = []
        for index, (title, tooltip) in enumerate(categories):
            button = QPushButton(title)
            button.setObjectName("settingsCategoryButton")
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda checked=False, i=index: self._set_settings_page(i))
            self.settings_category_group.addButton(button, index)
            self.settings_category_buttons.append(button)
            nav_layout.addWidget(button)
        nav_layout.addStretch(1)
        body.addWidget(nav)

        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("settingsStack")
        body.addWidget(self.settings_stack, 1)

        # 外观
        appearance_page, appearance_layout = self._settings_page(
            "外观",
            "选择终端的基础皮肤。主题变化会在保存后自动重启并生效。",
        )
        appearance_form = QFormLayout()
        appearance_form.setSpacing(10)
        self.ui_theme_combo = QComboBox()
        for theme_id, display_name in theme_options():
            self.ui_theme_combo.addItem(display_name, theme_id)
        appearance_form.addRow("主题", self.ui_theme_combo)
        appearance_layout.addLayout(appearance_form)
        appearance_note = QLabel("Flat Pro 与 Flat Pro Light 共用同一套布局、组件和 Motion，只切换完整配色。")
        appearance_note.setWordWrap(True)
        appearance_note.setObjectName("secondaryLabel")
        appearance_layout.addWidget(appearance_note)
        appearance_layout.addStretch(1)
        self.settings_stack.addWidget(appearance_page)

        # 常规
        general_page, general_layout = self._settings_page(
            "常规",
            "应用数据与封面资源的本机存储位置。",
        )
        form = QFormLayout()
        form.setSpacing(10)
        self.data_dir_edit = QLineEdit()
        self.cover_dir_edit = QLineEdit()
        form.addRow("应用数据目录", self._path_row(self.data_dir_edit, self._browse_data_dir))
        form.addRow("集中封面目录", self._path_row(self.cover_dir_edit, self._browse_cover_dir))
        general_layout.addLayout(form)
        general_layout.addStretch(1)
        note = QLabel("影片与游戏档案都保存在应用数据目录并明确分区；影片封面仍使用集中封面目录。删除影片视频或游戏本体不会自动删除永久档案。")
        note.setWordWrap(True)
        note.setObjectName("secondaryLabel")
        general_layout.addWidget(note)
        self.settings_stack.addWidget(general_page)

        # 影片库
        library_page, library_layout = self._settings_page(
            "影片库",
            "管理影片扫描目录、显示名称以及是否参与扫描。",
        )
        self.library_table = QTableWidget(0, 3)
        self.library_table.setHorizontalHeaderLabels(["名称", "路径", "启用"])
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.library_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.library_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.library_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        library_layout.addWidget(self.library_table, 1)
        lib_buttons = QHBoxLayout()
        add_library = QPushButton("添加影片库")
        add_library.setObjectName("primaryButton")
        remove_library = QPushButton("删除所选")
        remove_library.setObjectName("quietButton")
        lib_buttons.addWidget(add_library)
        lib_buttons.addWidget(remove_library)
        lib_buttons.addStretch(1)
        library_layout.addLayout(lib_buttons)
        add_library.clicked.connect(self._add_library)
        remove_library.clicked.connect(self._remove_library)
        self.settings_stack.addWidget(library_page)

        # 播放
        playback_page, playback_layout = self._settings_page(
            "播放与启动",
            "播放器、媒体探测工具与程序启动时的默认行为。",
        )
        playback_form = QFormLayout()
        playback_form.setSpacing(10)
        self.player_mode_combo = QComboBox()
        self.player_mode_combo.addItem("Windows 默认播放器", "system")
        self.player_mode_combo.addItem("指定播放器", "custom")
        self.player_path_edit = QLineEdit()
        self.ffprobe_edit = QLineEdit()
        self.ffmpeg_edit = QLineEdit()
        self.startup_library_combo = QComboBox()
        self.startup_library_combo.addItem("影片", "movies")
        self.startup_library_combo.addItem("游戏", "games")
        playback_form.addRow("播放方式", self.player_mode_combo)
        playback_form.addRow("播放器路径", self._file_row(self.player_path_edit, self._browse_player))
        playback_form.addRow("ffprobe", self._file_row(self.ffprobe_edit, lambda: self._browse_tool(self.ffprobe_edit)))
        playback_form.addRow("FFmpeg", self._file_row(self.ffmpeg_edit, lambda: self._browse_tool(self.ffmpeg_edit)))
        playback_form.addRow("启动默认资源库", self.startup_library_combo)
        self.auto_scan_check = QCheckBox("启动时自动扫描")
        playback_form.addRow("", self.auto_scan_check)
        playback_layout.addLayout(playback_form)
        playback_layout.addStretch(1)
        self.settings_stack.addWidget(playback_page)

        # 备份
        backup_page, backup_layout = self._settings_page(
            "备份与恢复",
            "保存数据库、永久档案和可选视觉资源，或从已有备份恢复。",
        )
        self.include_covers_check = QCheckBox("包含视觉资源")
        self.include_covers_check.setChecked(True)
        backup_layout.addWidget(self.include_covers_check)
        backup_buttons = QHBoxLayout()
        self.create_backup_button = QPushButton("创建备份…")
        self.create_backup_button.setObjectName("primaryButton")
        self.restore_backup_button = QPushButton("从备份恢复…")
        backup_buttons.addWidget(self.create_backup_button)
        backup_buttons.addWidget(self.restore_backup_button)
        backup_buttons.addStretch(1)
        backup_layout.addLayout(backup_buttons)
        backup_note = QLabel("备份不包含影片视频、游戏本体、外部截图、缓存和日志。恢复时使用当前已保存的应用数据/封面/影片库等本机路径；视觉资源同名覆盖，其他现有资源保留。")
        backup_note.setWordWrap(True)
        backup_note.setObjectName("secondaryLabel")
        backup_layout.addWidget(backup_note)
        backup_layout.addStretch(1)
        self.create_backup_button.clicked.connect(self._create_backup)
        self.restore_backup_button.clicked.connect(self._restore_backup)
        if self.settings_path is None:
            self.create_backup_button.setEnabled(False)
            self.restore_backup_button.setEnabled(False)
        self.settings_stack.addWidget(backup_page)

        self._set_settings_page(0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText("保存")
            save_button.setObjectName("primaryButton")
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button is not None:
            cancel_button.setText("取消")
            cancel_button.setObjectName("quietButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _settings_page(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        title_label = QLabel(title)
        title_label.setObjectName("settingsPageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("secondaryLabel")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return page, layout

    def _set_settings_page(self, index: int) -> None:
        if not 0 <= index < self.settings_stack.count():
            return
        self.settings_stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.settings_category_buttons):
            button.setChecked(button_index == index)

    def _path_row(self, edit: QLineEdit, callback) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit, 1)
        button = QPushButton("浏览…")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return widget

    def _file_row(self, edit: QLineEdit, callback) -> QWidget:
        return self._path_row(edit, callback)

    def _load(self, settings: AppSettings) -> None:
        self.data_dir_edit.setText(str(settings.data_dir))
        self.cover_dir_edit.setText(str(settings.cover_dir))
        self.library_table.setRowCount(0)
        for library in settings.libraries:
            self._append_library(library)
        index = self.player_mode_combo.findData(settings.player_mode)
        self.player_mode_combo.setCurrentIndex(max(0, index))
        self.player_path_edit.setText(str(settings.player_path) if settings.player_path else "")
        self.ffprobe_edit.setText(settings.ffprobe_path)
        self.ffmpeg_edit.setText(settings.ffmpeg_path)
        startup_index = self.startup_library_combo.findData(settings.startup_library)
        self.startup_library_combo.setCurrentIndex(max(0, startup_index))
        self.auto_scan_check.setChecked(settings.auto_scan)
        theme_index = self.ui_theme_combo.findData(settings.ui_theme)
        self.ui_theme_combo.setCurrentIndex(max(0, theme_index))

    def _append_library(self, library: LibraryConfig) -> None:
        row = self.library_table.rowCount()
        self.library_table.insertRow(row)
        name = QTableWidgetItem(library.name)
        name.setData(Qt.ItemDataRole.UserRole, library.id)
        path = QTableWidgetItem(str(library.path))
        enabled = QTableWidgetItem()
        enabled.setFlags(enabled.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        enabled.setCheckState(Qt.CheckState.Checked if library.enabled else Qt.CheckState.Unchecked)
        self.library_table.setItem(row, 0, name)
        self.library_table.setItem(row, 1, path)
        self.library_table.setItem(row, 2, enabled)

    def _add_library(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择影片库目录")
        if not path:
            return
        directory = Path(path)
        self._append_library(LibraryConfig(str(uuid4()), directory.name or "影片库", directory, True))

    def _remove_library(self) -> None:
        row = self.library_table.currentRow()
        if row >= 0:
            self.library_table.removeRow(row)

    def _browse_data_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择应用数据目录", self.data_dir_edit.text())
        if path:
            self.data_dir_edit.setText(path)

    def _browse_cover_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择集中封面目录", self.cover_dir_edit.text())
        if path:
            self.cover_dir_edit.setText(path)

    def _browse_player(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择播放器程序", self.player_path_edit.text(), "程序 (*.exe);;所有文件 (*)")
        if path:
            self.player_path_edit.setText(path)

    def _browse_tool(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择程序", edit.text(), "程序 (*.exe);;所有文件 (*)")
        if path:
            edit.setText(path)

    def _create_backup(self) -> None:
        if self.settings_path is None:
            return
        suggested = self.settings.data_dir.parent / self.backup_service.suggested_backup_name()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存备份",
            str(suggested),
            "ZIP 压缩包 (*.zip)",
        )
        if not path:
            return
        try:
            summary = self.backup_service.create_backup(
                self.settings,
                self.settings_path,
                Path(path),
                include_visual_assets=self.include_covers_check.isChecked(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "备份失败", str(exc))
            return
        QMessageBox.information(
            self,
            "备份完成",
            f"备份已保存到：\n{summary.path}\n\n影片/游戏档案：{summary.metadata_files} 个\n影片封面：{summary.cover_files} 个\n游戏视觉资源：{summary.game_asset_files} 个",
        )

    def _restore_backup(self) -> None:
        if self.settings_path is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份 ZIP",
            str(self.settings.data_dir.parent),
            "ZIP 压缩包 (*.zip)",
        )
        if not path:
            return
        backup_path = Path(path)
        try:
            manifest = self.backup_service.inspect_backup(backup_path)
            assessment = self.backup_service.assess_restore(self.settings, backup_path)
        except InvalidBackupError as exc:
            QMessageBox.warning(self, "无法恢复", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "检查备份失败", str(exc))
            return

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("确认恢复")
        lines = [
            "恢复会把数据库、影片档案和游戏档案恢复为备份时的状态。",
            "恢复使用当前电脑已经保存的路径设置，不会套用备份里的旧盘符。",
        ]
        if manifest.includes_visual_assets:
            lines.append("视觉资源采用合并恢复：同名资源覆盖，其他现有资源保留。")
        if assessment.data_will_overwrite or assessment.cover_conflicts:
            lines.append(f"当前目标已有内容：数据库/档案将被覆盖；同名视觉资源 {assessment.cover_conflicts} 个。")
        lines.append("影片视频、游戏本体和外部截图不会被修改。")
        message.setText("\n\n".join(lines))
        restore_button = message.addButton("覆盖并恢复", QMessageBox.ButtonRole.AcceptRole)
        message.addButton("取消恢复", QMessageBox.ButtonRole.RejectRole)
        message.exec()
        if message.clickedButton() is not restore_button:
            return

        try:
            summary = self.backup_service.restore_backup(self.settings, self.settings_path, backup_path)
        except Exception as exc:
            QMessageBox.critical(self, "恢复失败", f"恢复没有完成，已尝试回滚原有资料。\n\n{exc}")
            return

        QMessageBox.information(
            self,
            "恢复完成",
            f"已恢复影片/游戏档案 {summary.metadata_files} 个、影片封面 {summary.cover_files} 个、游戏视觉资源 {summary.game_asset_files} 个。\n\n软件将自动重新启动以载入恢复后的资料。",
        )
        app = QApplication.instance()
        if app is not None:
            app._local_movie_manager_restart_requested = True  # type: ignore[attr-defined]
            app.quit()

    def accept(self) -> None:
        data_text = self.data_dir_edit.text().strip()
        cover_text = self.cover_dir_edit.text().strip()
        if not data_text or not cover_text:
            QMessageBox.warning(self, "设置不完整", "应用数据目录和封面目录不能为空。")
            return
        libraries: list[LibraryConfig] = []
        for row in range(self.library_table.rowCount()):
            name_item = self.library_table.item(row, 0)
            path_item = self.library_table.item(row, 1)
            enabled_item = self.library_table.item(row, 2)
            name = name_item.text().strip() if name_item else ""
            path = path_item.text().strip() if path_item else ""
            if not name or not path:
                QMessageBox.warning(self, "影片库设置错误", f"第 {row + 1} 行的名称或路径为空。")
                return
            library_id = name_item.data(Qt.ItemDataRole.UserRole) or str(uuid4())
            libraries.append(
                LibraryConfig(
                    str(library_id),
                    name,
                    Path(path),
                    enabled_item.checkState() == Qt.CheckState.Checked if enabled_item else True,
                )
            )
        mode = self.player_mode_combo.currentData()
        player_text = self.player_path_edit.text().strip()
        if mode == "custom" and not player_text:
            QMessageBox.warning(self, "播放器设置错误", "选择“指定播放器”时需要填写播放器路径。")
            return
        self._result_settings = AppSettings(
            data_dir=Path(data_text),
            cover_dir=Path(cover_text),
            libraries=libraries,
            player_mode=mode,
            player_path=Path(player_text) if player_text else None,
            ffprobe_path=self.ffprobe_edit.text().strip() or "ffprobe",
            ffmpeg_path=self.ffmpeg_edit.text().strip() or "ffmpeg",
            auto_scan=self.auto_scan_check.isChecked(),
            ui_theme=self.ui_theme_combo.currentData(),
            poster_display_mode="natural",
            sidebar_visible=self.settings.sidebar_visible,
            sidebar_width=self.settings.sidebar_width,
            cover_tool_source_dir=self.settings.cover_tool_source_dir,
            cover_tool_margin_px=self.settings.cover_tool_margin_px,
            sort_key=self.settings.sort_key,
            sort_desc=self.settings.sort_desc,
            startup_library=self.startup_library_combo.currentData(),
            game_sort_key=self.settings.game_sort_key,
            game_sort_desc=self.settings.game_sort_desc,
            movie_filter=self.settings.movie_filter,
            game_filter=self.settings.game_filter,
        )
        super().accept()
