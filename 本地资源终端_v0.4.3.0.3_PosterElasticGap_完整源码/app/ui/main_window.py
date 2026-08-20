from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from PySide6.QtCore import QItemSelectionModel, QPoint, QSize, QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models.game import GameMetadataPatch, GameRecord
from app.models.movie import MovieMetadataPatch, MovieRecord
from app.services.catalog_service import MovieFilter
from app.services.player_service import PlaybackError
from app.services.identity_service import IdentityService
from app.services.giga_cover_cropper import GigaCoverCropper
from app.ui.app_chrome import AppTitleBar
from app.ui.batch_edit_helpers import parse_batch_terms
from app.ui.flat_icons import flat_icon
from app.ui.flat_theme import FlatTokens
from app.ui.game_delegate import GameCardDelegate
from app.ui.game_archive_page import GameArchivePage
from app.ui.game_edit_dialog import GameEditDialog
from app.ui.game_models import GameListModel
from app.ui.poster_view import PosterWallListView
from app.ui.giga_cover_dialog import GigaCoverDialog
from app.ui.identity_shell import IdentityEditDialog, IdentityShellWidget, IdentitySidebarRoom
from app.ui.manual_cover_crop_dialog import ManualCoverCropDialog
from app.ui.movie_delegate import MovieCardDelegate
from app.ui.movie_archive_page import MovieArchivePage
from app.ui.movie_models import MovieListModel, MovieTableModel
from app.ui.motion import exec_menu_with_motion, show_popup_with_motion, transition_stack_page
from app.ui.sidebar_motion import sidebar_motion_progress, sidebar_text_progress
from app.ui.sidebar_splitter import TwoStateSidebarSplitter
from app.ui.navigation_button import NavigationButton
from app.ui.scan_worker import ScanWorker
from app.ui.window_hit_test import edge_zone
from app.ui.window_resize import WindowResizeFrame


class MainWindow(QMainWindow):
    settings_requested = Signal()
    cover_tool_state_changed = Signal(str, int)
    movie_view_state_changed = Signal(str, bool, str)
    game_view_state_changed = Signal(str, bool, str)
    # Backward-compatible signal name for old bootstrap/tests. Movie sort changes emit both.
    sort_state_changed = Signal(str, bool)
    identity_entered = Signal()

    def __init__(
        self,
        catalog_service,
        scanner,
        settings,
        cover_service,
        player_service,
        viewing_service,
        collection_folder_service=None,
        game_catalog=None,
        game_launcher=None,
        game_session_service=None,
        screenshot_service=None,
        identity_service: IdentityService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.catalog = catalog_service
        self.scanner = scanner
        self.settings = settings
        self.cover_service = cover_service
        self.player_service = player_service
        self.viewing_service = viewing_service
        self.collection_folders = collection_folder_service
        self.game_catalog = game_catalog
        self.game_launcher = game_launcher
        self.game_session_service = game_session_service
        self.screenshot_service = screenshot_service
        self._temporary_identity_root = None
        if identity_service is None:
            self._temporary_identity_root = TemporaryDirectory(prefix="lrt-identity-")
            identity_service = IdentityService(Path(self._temporary_identity_root.name) / "identity")
        self.identity_service = identity_service
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self._movie_view_index = 0
        self.current_library = "movies"
        self._current_folder_ids: dict[str, str | None] = {"movies": None, "games": None}
        self._game_tick_count = 0
        self._catalog_status_text = "就绪"
        if sys.platform == "win32":
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("本地资源终端 · v0.4.3.0.3")
        self.resize(1320, 840)
        self._build_ui()
        self._resize_frame = WindowResizeFrame(self) if sys.platform == "win32" else None
        self.switch_library(getattr(settings, "startup_library", "movies"), clear_search=False)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("appRoot")
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central)

        self.title_bar = AppTitleBar(self, central)
        central_layout.addWidget(self.title_bar)

        self.root_stack = QStackedWidget()
        central_layout.addWidget(self.root_stack, 1)

        self.identity_shell = IdentityShellWidget(self.identity_service)
        self.root_stack.addWidget(self.identity_shell)

        self.main_shell = QWidget()
        self.main_shell.setObjectName("mainShell")
        root = QHBoxLayout(self.main_shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.root_stack.addWidget(self.main_shell)

        self.main_splitter = TwoStateSidebarSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(TwoStateSidebarSplitter.HANDLE_WIDTH)
        self.main_splitter.configure_widths(expanded=FlatTokens.SIDEBAR_WIDTH)
        root.addWidget(self.main_splitter)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(72)
        self.sidebar.setMaximumWidth(FlatTokens.SIDEBAR_WIDTH)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(14, 18, 14, 14)
        self.sidebar_layout.setSpacing(6)
        sidebar_layout = self.sidebar_layout

        self.identity_room = IdentitySidebarRoom(self.identity_service)
        sidebar_layout.addWidget(self.identity_room)
        sidebar_layout.addSpacing(10)

        self.library_section_label = QLabel("媒体库")
        self.library_section_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(self.library_section_label)

        self.movie_library_button = NavigationButton("影片")
        self.game_library_button = NavigationButton("游戏")
        for button, icon_name in (
            (self.movie_library_button, "movie"),
            (self.game_library_button, "game"),
        ):
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.set_nav_icon(icon_name)
            button.setIconSize(QSize(21, 21))
            sidebar_layout.addWidget(button)

        library_group = QButtonGroup(self)
        library_group.setExclusive(True)
        library_group.addButton(self.movie_library_button)
        library_group.addButton(self.game_library_button)

        sidebar_layout.addSpacing(20)
        self.system_section_label = QLabel("系统")
        self.system_section_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(self.system_section_label)

        self.settings_button = NavigationButton("设置")
        self.settings_button.setObjectName("sidebarAction")
        self.settings_button.set_nav_icon("settings")
        self.settings_button.setIconSize(QSize(21, 21))
        sidebar_layout.addWidget(self.settings_button)
        sidebar_layout.addStretch(1)
        self.main_splitter.addWidget(self.sidebar)

        content = QWidget()
        content.setObjectName("contentSurface")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(22, 10, 18, 14)
        content_layout.setSpacing(14)
        self.main_splitter.addWidget(content)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([FlatTokens.SIDEBAR_WIDTH, max(1, self.width() - FlatTokens.SIDEBAR_WIDTH)])
        self._sidebar_section_motion = []
        for label in (self.library_section_label, self.system_section_label):
            effect = QGraphicsOpacityEffect(label)
            effect.setOpacity(1.0)
            label.setGraphicsEffect(effect)
            self._sidebar_section_motion.append((label, effect, max(1, label.sizeHint().height())))
        self.main_splitter.sidebar_width_changed.connect(self._update_sidebar_motion)
        initial_sidebar_expanded = int(getattr(self.settings, "sidebar_width", FlatTokens.SIDEBAR_WIDTH)) > 104
        self.main_splitter.set_sidebar_expanded(initial_sidebar_expanded, animated=False)
        if FlatTokens.MOTION_LEVEL != "full":
            self._set_sidebar_compact(False)

        self.content_page_stack = QStackedWidget()
        content_layout.addWidget(self.content_page_stack, 1)
        self.library_page = QWidget()
        self.library_page.setObjectName("libraryPage")
        library_layout = QVBoxLayout(self.library_page)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(14)
        self.content_page_stack.addWidget(self.library_page)

        self.library_tools_popup = QFrame(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.library_tools_popup.setObjectName("libraryToolsPopup")
        popup_layout = QVBoxLayout(self.library_tools_popup)
        popup_layout.setContentsMargins(14, 14, 14, 14)
        popup_layout.setSpacing(10)

        search_label = QLabel("搜索")
        search_label.setObjectName("popupSectionLabel")
        popup_layout.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("toolbarSearch")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(330)
        popup_layout.addWidget(self.search_edit)

        find_row = QHBoxLayout()
        find_row.setSpacing(8)
        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("toolbarCombo")
        self.filter_combo.setMinimumWidth(140)
        find_row.addWidget(self.filter_combo, 1)
        self.sort_combo = QComboBox()
        self.sort_combo.setObjectName("toolbarCombo")
        self.sort_combo.setMinimumWidth(150)
        find_row.addWidget(self.sort_combo, 1)
        self.sort_direction_button = QPushButton("↓")
        self.sort_direction_button.setObjectName("toolButton")
        self.sort_direction_button.setToolTip("切换升序 / 降序")
        find_row.addWidget(self.sort_direction_button)
        popup_layout.addLayout(find_row)

        folder_label = QLabel("分类文件夹")
        folder_label.setObjectName("popupSectionLabel")
        popup_layout.addWidget(folder_label)
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.folder_combo = QComboBox()
        self.folder_combo.setObjectName("toolbarCombo")
        self.folder_combo.setMinimumWidth(180)
        folder_row.addWidget(self.folder_combo, 1)
        self.new_folder_button = QPushButton()
        self.new_folder_button.setObjectName("toolButton")
        self.new_folder_button.setIcon(flat_icon("search_add"))
        self.new_folder_button.setIconSize(QSize(18, 18))
        self.new_folder_button.setToolTip("新建分类文件夹")
        folder_row.addWidget(self.new_folder_button)
        self.rename_folder_button = QPushButton("重命名")
        self.rename_folder_button.setObjectName("toolButton")
        self.rename_folder_button.setToolTip("重命名当前分类文件夹")
        folder_row.addWidget(self.rename_folder_button)
        self.delete_folder_button = QPushButton("删除")
        self.delete_folder_button.setObjectName("toolButton")
        self.delete_folder_button.setToolTip("删除当前分类文件夹；档案会回到未分类")
        folder_row.addWidget(self.delete_folder_button)
        popup_layout.addLayout(folder_row)

        self.movie_tools_label = QLabel("影片工具")
        self.movie_tools_label.setObjectName("popupSectionLabel")
        popup_layout.addWidget(self.movie_tools_label)
        self.movie_tools_panel = QWidget()
        movie_tools_layout = QHBoxLayout(self.movie_tools_panel)
        movie_tools_layout.setContentsMargins(0, 0, 0, 0)
        movie_tools_layout.setSpacing(8)
        self.view_button = QPushButton("列表视图")
        self.view_button.setIcon(flat_icon("list"))
        self.rescan_button = QPushButton("重新扫描")
        self.rescan_button.setIcon(flat_icon("scan"))
        self.cover_tools_button = QPushButton("封面工具")
        self.cover_tools_button.setIcon(flat_icon("cover"))
        for button in (self.view_button, self.rescan_button, self.cover_tools_button):
            button.setIconSize(QSize(18, 18))
            movie_tools_layout.addWidget(button)
        popup_layout.addWidget(self.movie_tools_panel)

        self.view_stack = QStackedWidget()
        library_layout.addWidget(self.view_stack, 1)

        self.content_status_bar = QWidget()
        self.content_status_bar.setObjectName("contentStatusBar")
        status_layout = QHBoxLayout(self.content_status_bar)
        status_layout.setContentsMargins(4, 0, 2, 0)
        status_layout.setSpacing(8)
        self.content_status_icon = QLabel()
        self.content_status_icon.setObjectName("contentStatusIcon")
        status_layout.addWidget(self.content_status_icon)
        self.content_status_label = QLabel(self._catalog_status_text)
        self.content_status_label.setObjectName("contentStatusText")
        status_layout.addWidget(self.content_status_label)
        status_layout.addStretch(1)
        self.active_game_label = QLabel()
        self.active_game_label.setVisible(False)
        self.active_game_label.setObjectName("contentStatusActiveGame")
        status_layout.addWidget(self.active_game_label)

        self.library_tools_button = QPushButton()
        self.library_tools_button.setObjectName("statusActionButton")
        self.library_tools_button.setIcon(flat_icon("search"))
        self.library_tools_button.setIconSize(QSize(18, 18))
        self.library_tools_button.setToolTip("搜索 / 筛选 / 排序")
        status_layout.addWidget(self.library_tools_button)

        self.add_game_button = QPushButton()
        self.add_game_button.setObjectName("statusActionButton")
        self.add_game_button.setIcon(flat_icon("add"))
        self.add_game_button.setIconSize(QSize(18, 18))
        self.add_game_button.setToolTip("添加游戏")
        status_layout.addWidget(self.add_game_button)

        library_layout.addWidget(self.content_status_bar)
        self.statusBar().setVisible(False)

        self.grid_model = MovieListModel()
        self.grid_view = PosterWallListView()
        self.grid_view.setModel(self.grid_model)
        self.grid_delegate = MovieCardDelegate(self.grid_view)
        self.grid_view.setItemDelegate(self.grid_delegate)
        self.grid_model.modelReset.connect(self.grid_delegate.clear_cache)
        self._configure_poster_view(self.grid_view, multi=True)
        self.grid_view.set_poster_delegate(self.grid_delegate)
        self.view_stack.addWidget(self.grid_view)

        self.table_model = MovieTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_view.setSortingEnabled(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.view_stack.addWidget(self.table_view)

        self.game_model = GameListModel()
        self.game_view = PosterWallListView()
        self.game_view.setModel(self.game_model)
        self.game_delegate = GameCardDelegate(self.game_view)
        self.game_view.setItemDelegate(self.game_delegate)
        self.game_model.modelReset.connect(self.game_delegate.clear_cache)
        self._configure_poster_view(self.game_view, multi=False)
        self.game_view.set_poster_delegate(self.game_delegate)
        self.view_stack.addWidget(self.game_view)

        self.movie_archive_page = MovieArchivePage()
        self.content_page_stack.addWidget(self.movie_archive_page)
        self.game_archive_page = GameArchivePage(self.screenshot_service)
        self.content_page_stack.addWidget(self.game_archive_page)
        self.content_page_stack.setCurrentWidget(self.library_page)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self.search_edit.textChanged.connect(lambda _text: self._search_timer.start())
        self._search_timer.timeout.connect(self.refresh_catalog)
        self.movie_library_button.clicked.connect(lambda: self.switch_library("movies"))
        self.game_library_button.clicked.connect(lambda: self.switch_library("games"))
        self.filter_combo.currentIndexChanged.connect(self._filter_changed)
        self.sort_combo.currentIndexChanged.connect(self._sort_changed)
        self.sort_direction_button.clicked.connect(self._toggle_sort_direction)
        self.folder_combo.currentIndexChanged.connect(self._folder_changed)
        self.new_folder_button.clicked.connect(self._create_collection_folder)
        self.rename_folder_button.clicked.connect(self._rename_collection_folder)
        self.delete_folder_button.clicked.connect(self._delete_collection_folder)
        self.view_button.clicked.connect(self._toggle_view)
        self.rescan_button.clicked.connect(self.start_scan)
        self.cover_tools_button.clicked.connect(self._open_cover_tools)
        self.library_tools_button.clicked.connect(self._toggle_library_tools_popup)
        self.add_game_button.clicked.connect(self._add_game)
        self.movie_archive_page.back_requested.connect(self._close_movie_archive)
        self.movie_archive_page.play_requested.connect(self._play_movie_by_uuid)
        self.movie_archive_page.metadata_patch_requested.connect(self._update_movie_archive_metadata)
        self.movie_archive_page.cover_change_requested.connect(self._change_movie_archive_cover)
        self.movie_archive_page.open_folder_requested.connect(self._open_movie_archive_folder)
        self.movie_archive_page.relink_requested.connect(self._relink_movie_archive)
        self.movie_archive_page.delete_requested.connect(self._delete_movie_archive)
        self.game_archive_page.back_requested.connect(self._close_game_archive)
        self.game_archive_page.launch_requested.connect(self._launch_game_by_uuid)
        self.game_archive_page.metadata_patch_requested.connect(self._update_game_archive_metadata)
        self.game_archive_page.archive_media_change_requested.connect(self._change_game_archive_media)
        self.game_archive_page.archive_media_clear_requested.connect(self._clear_game_archive_media)
        self.game_archive_page.cover_change_requested.connect(self._change_game_archive_cover)
        self.game_archive_page.cover_crop_requested.connect(self._crop_game_archive_cover)
        self.game_archive_page.cover_clear_requested.connect(self._clear_game_archive_cover)
        self.game_archive_page.preview_change_requested.connect(self._change_game_archive_preview)
        self.game_archive_page.preview_clear_requested.connect(self._clear_game_archive_preview)
        self.game_archive_page.launch_exe_browse_requested.connect(self._browse_game_archive_launch_exe)
        self.game_archive_page.timing_exe_browse_requested.connect(self._browse_game_archive_timing_exe)
        self.game_archive_page.workdir_browse_requested.connect(self._browse_game_archive_workdir)
        self.game_archive_page.screenshot_dir_browse_requested.connect(self._browse_game_archive_screenshot_dir)
        self.settings_button.clicked.connect(lambda: self.settings_requested.emit())
        self.identity_shell.enter_requested.connect(self._enter_main_shell)
        self.identity_shell.identity_created.connect(self._identity_changed)
        self.identity_shell.identity_changed.connect(self._identity_changed)
        self.identity_room.edit_requested.connect(self._open_identity_editor)
        self.root_stack.setCurrentWidget(self.identity_shell)

        self.grid_view.doubleClicked.connect(lambda index: self._open_detail(self.grid_model.movie_at(index.row())))
        self.table_view.doubleClicked.connect(lambda index: self._open_detail(self.table_model.movie_at(index.row())))
        self.game_view.doubleClicked.connect(lambda index: self._open_game_detail(self.game_model.game_at(index.row())))
        self.grid_view.customContextMenuRequested.connect(
            lambda pos: self._show_movie_context_menu(self.grid_view, pos, self.grid_model)
        )
        self.table_view.customContextMenuRequested.connect(
            lambda pos: self._show_movie_context_menu(self.table_view, pos, self.table_model)
        )
        self.game_view.customContextMenuRequested.connect(self._show_game_context_menu)

        self._game_timer = QTimer(self)
        self._game_timer.setInterval(1000)
        self._game_timer.timeout.connect(self._game_timer_tick)
        self._game_timer.start()

        self._movie_timer = QTimer(self)
        self._movie_timer.setInterval(1000)
        self._movie_timer.timeout.connect(self._movie_timer_tick)
        self._movie_timer.start()

    def _update_sidebar_motion(self, width: int) -> None:
        progress = sidebar_motion_progress(width, minimum=72, expanded=FlatTokens.SIDEBAR_WIDTH)
        text_progress = sidebar_text_progress(progress)
        self.movie_library_button.set_sidebar_motion_progress(progress)
        self.game_library_button.set_sidebar_motion_progress(progress)
        self.settings_button.set_sidebar_motion_progress(progress)
        self.identity_room.set_motion_progress(progress)

        for label, effect, full_height in self._sidebar_section_motion:
            label.setVisible(text_progress > 0.0)
            effect.setOpacity(text_progress)
            label.setMaximumHeight(round(full_height * text_progress))

        margin = round(8 + 6 * progress)
        self.sidebar_layout.setContentsMargins(margin, 18, margin, 14)
        compact_hint = text_progress < 0.28
        for button, tip in (
            (self.movie_library_button, "影片"),
            (self.game_library_button, "游戏"),
            (self.settings_button, "设置"),
        ):
            button.setToolTip(tip if compact_hint else "")

    def _set_sidebar_compact(self, compact: bool) -> None:
        self.library_section_label.setVisible(not compact)
        self.system_section_label.setVisible(not compact)
        self.identity_room.set_compact(compact)
        self.movie_library_button.setText("" if compact else "影片")
        self.game_library_button.setText("" if compact else "游戏")
        self.settings_button.setText("" if compact else "设置")
        for button, tip in (
            (self.movie_library_button, "影片"),
            (self.game_library_button, "游戏"),
            (self.settings_button, "设置"),
        ):
            button.setToolTip(tip if compact else "")
            button.setProperty("compactSidebar", compact)
            button.style().unpolish(button)
            button.style().polish(button)
        margin = 8 if compact else 14
        self.sidebar_layout.setContentsMargins(margin, 18, margin, 14)

    def _enter_main_shell(self) -> None:
        identity = self.identity_service.load()
        if identity is None:
            self.identity_shell.show_setup_state()
            return
        self.identity_room.set_identity(identity)
        transition_stack_page(self.root_stack, self.main_shell, direction=1)
        if not self.settings.libraries:
            self.settings_requested.emit()
        self.identity_entered.emit()

    def _identity_changed(self, identity) -> None:
        self.identity_room.set_identity(identity)
        if self.root_stack.currentWidget() is self.identity_shell:
            self.identity_shell.show_entry_state(identity)

    def _open_identity_editor(self) -> None:
        dialog = IdentityEditDialog(self.identity_service, self)
        dialog.identity_changed.connect(self._identity_changed)
        dialog.exec()

    @staticmethod
    def _configure_poster_view(view: QListView, *, multi: bool) -> None:
        view.setViewMode(QListView.ViewMode.IconMode)
        view.setResizeMode(QListView.ResizeMode.Fixed)
        view.setUniformItemSizes(False)
        view.setWrapping(False)
        # Explicit poster targets require Free movement in QListView, but drag
        # reordering remains disabled so users cannot move archive entries.
        view.setMovement(QListView.Movement.Free)
        view.setDragEnabled(False)
        view.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        view.setMouseTracking(True)
        view.viewport().setMouseTracking(True)
        view.setSpacing(0)
        view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
            if multi
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.verticalScrollBar().setSingleStep(28)

    def _toggle_library_tools_popup(self) -> None:
        if self.library_tools_popup.isVisible():
            self.library_tools_popup.hide()
            return
        self.library_tools_popup.adjustSize()
        button_top_left = self.library_tools_button.mapToGlobal(QPoint(0, 0))
        popup_size = self.library_tools_popup.sizeHint()
        x = button_top_left.x() + self.library_tools_button.width() - popup_size.width()
        y = button_top_left.y() - popup_size.height() - 8
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            x = max(available.left() + 8, min(x, available.right() - popup_size.width() - 8))
            y = max(available.top() + 8, y)
        show_popup_with_motion(self.library_tools_popup, QPoint(x, y))

    def _update_content_status_icon(self) -> None:
        kind = "cartridge" if self.current_library == "games" else "movie"
        icon = flat_icon(kind, 18, color=FlatTokens.TEXT_MUTED)
        self.content_status_icon.setPixmap(icon.pixmap(18, 18))

    def _set_catalog_status(self, message: str) -> None:
        self._catalog_status_text = message
        self.content_status_label.setText(message)

    def _show_status_message(self, message: str, timeout: int = 0) -> None:
        self.content_status_label.setText(message)
        if timeout > 0:
            QTimer.singleShot(
                timeout,
                lambda expected=message: (
                    self.content_status_label.setText(self._catalog_status_text)
                    if self.content_status_label.text() == expected
                    else None
                ),
            )

    def switch_library(self, library: str, *, clear_search: bool = True) -> None:
        runtime_size = self.size()
        runtime_minimum = self.minimumSize()
        runtime_maximum = self.maximumSize()
        self.setFixedSize(runtime_size)
        try:
            if hasattr(self, "content_page_stack") and self.content_page_stack.currentWidget() is not self.library_page:
                if self.content_page_stack.currentWidget() is self.game_archive_page:
                    self._close_game_archive()
                elif self.content_page_stack.currentWidget() is self.movie_archive_page:
                    self._close_movie_archive()
            library = "games" if library == "games" and self.game_catalog is not None else "movies"
            changed = library != self.current_library
            self.current_library = library
            self.movie_library_button.setChecked(library == "movies")
            self.game_library_button.setChecked(library == "games")
            self.game_library_button.setEnabled(self.game_catalog is not None)
            if clear_search and changed:
                self.search_edit.clear()
            self._configure_library_controls()
            self.refresh_catalog()
        finally:
            self.setMinimumSize(runtime_minimum)
            self.setMaximumSize(runtime_maximum)

    def _configure_library_controls(self) -> None:
        self.library_tools_popup.hide()
        self.filter_combo.blockSignals(True)
        self.sort_combo.blockSignals(True)
        self.folder_combo.blockSignals(True)
        self.filter_combo.clear()
        self.sort_combo.clear()
        if self.current_library == "movies":
            self.search_edit.setPlaceholderText("搜索编号、标题、演员、系列、厂商、标签……")
            self._add_movie_filters()
            for label, key in (
                ("最近添加", "added_at"),
                ("编号", "code"),
                ("标题", "title"),
                ("发行日期", "release_date"),
                ("评分", "rating"),
                ("最后观看", "last_watched_at"),
                ("观看次数", "play_count"),
            ):
                self.sort_combo.addItem(label, key)
            self._set_combo_data(self.sort_combo, self.settings.sort_key)
            self._set_filter_key(getattr(self.settings, "movie_filter", "all"))
            self.sort_direction_button.setText("↓" if self.settings.sort_desc else "↑")
            self.view_stack.setCurrentIndex(self._movie_view_index)
            self.view_button.setVisible(True)
            self.rescan_button.setVisible(True)
            self.cover_tools_button.setVisible(True)
            self.movie_tools_label.setVisible(True)
            self.movie_tools_panel.setVisible(True)
            self.add_game_button.setVisible(False)
        else:
            self.search_edit.setPlaceholderText("搜索游戏、系列、开发商、发行商、标签……")
            self._add_game_filters()
            for label, key in (
                ("最近添加", "added_at"),
                ("游戏名称", "title"),
                ("发行日期", "release_date"),
                ("评分", "rating"),
                ("累计游玩时间", "total_play_seconds"),
                ("最近游玩", "last_played_at"),
                ("游玩次数", "play_count"),
            ):
                self.sort_combo.addItem(label, key)
            self._set_combo_data(self.sort_combo, self.settings.game_sort_key)
            self._set_filter_key(getattr(self.settings, "game_filter", "all"))
            self.sort_direction_button.setText("↓" if self.settings.game_sort_desc else "↑")
            self.view_stack.setCurrentIndex(2)
            self.view_button.setVisible(False)
            self.rescan_button.setVisible(False)
            self.cover_tools_button.setVisible(False)
            self.movie_tools_label.setVisible(False)
            self.movie_tools_panel.setVisible(False)
            self.add_game_button.setVisible(True)
        self._refresh_folder_controls()
        self.filter_combo.blockSignals(False)
        self.sort_combo.blockSignals(False)
        self.folder_combo.blockSignals(False)
        self._update_content_status_icon()

    def _add_movie_filters(self) -> None:
        options = [
            ("全部", {"key": "all"}),
            ("收藏", {"key": "favorite", "favorite": True}),
            ("未观看", {"key": "unwatched", "watched": False}),
            ("已观看", {"key": "watched", "watched": True}),
            ("本地可播放", {"key": "available", "availability_status": "available"}),
            ("仅档案", {"key": "offline", "availability_status": "offline"}),
            ("有字幕", {"key": "subtitle", "subtitle_status": True}),
            ("无字幕", {"key": "no_subtitle", "subtitle_status": False}),
        ]
        for label, data in options:
            self.filter_combo.addItem(label, data)
        for library in self.settings.libraries:
            if library.enabled:
                self.filter_combo.addItem(f"影片库：{library.name}", {"key": "library", "library_id": library.id})
        try:
            tags = self.catalog.common_tags(20)
        except Exception:
            tags = []
        for tag in tags:
            self.filter_combo.addItem(f"标签：{tag}", {"key": "tag", "tag": tag})

    def _add_game_filters(self) -> None:
        for label, data in (
            ("全部", {"key": "all"}),
            ("收藏", {"key": "favorite", "favorite": True}),
            ("已安装", {"key": "installed", "installed": True}),
            ("未安装", {"key": "uninstalled", "installed": False}),
            ("最近游玩", {"key": "recent", "recently_played": True}),
        ):
            self.filter_combo.addItem(label, data)
        if self.game_catalog is not None:
            try:
                tags = self.game_catalog.common_tags(20)
            except Exception:
                tags = []
            for tag in tags:
                self.filter_combo.addItem(f"标签：{tag}", {"key": "tag", "tag": tag})

    def _set_filter_key(self, key: str) -> None:
        for index in range(self.filter_combo.count()):
            data = self.filter_combo.itemData(index)
            if isinstance(data, dict) and data.get("key") == key:
                self.filter_combo.setCurrentIndex(index)
                return
        self.filter_combo.setCurrentIndex(0)

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    def _current_filter_data(self) -> dict:
        data = self.filter_combo.currentData()
        return data if isinstance(data, dict) else {"key": "all"}

    def _current_movie_filter(self) -> MovieFilter:
        data = self._current_filter_data()
        return MovieFilter(
            library_id=data.get("library_id"),
            favorite=data.get("favorite"),
            watched=data.get("watched"),
            subtitle_status=data.get("subtitle_status"),
            availability_status=data.get("availability_status"),
            tag=data.get("tag"),
            folder_id=self._current_folder_id(),
        )

    def _current_folder_id(self) -> str | None:
        return self._current_folder_ids.get(self.current_library)

    def _refresh_folder_controls(self) -> None:
        selected = self._current_folder_id()
        self.folder_combo.clear()
        self.folder_combo.addItem("全部内容", None)
        folders = []
        if self.collection_folders is not None:
            try:
                folders = self.collection_folders.list(self.current_library)
            except Exception as exc:
                self._show_status_message(f"读取分类文件夹失败：{exc}", 5000)
        for folder in folders:
            self.folder_combo.addItem(folder.name, folder.id)
        index = self.folder_combo.findData(selected) if selected else 0
        if index < 0:
            self._current_folder_ids[self.current_library] = None
            index = 0
        self.folder_combo.setCurrentIndex(index)
        has_current = bool(self._current_folder_id())
        enabled = self.collection_folders is not None
        self.folder_combo.setEnabled(enabled)
        self.new_folder_button.setEnabled(enabled)
        self.rename_folder_button.setEnabled(enabled and has_current)
        self.delete_folder_button.setEnabled(enabled and has_current)

    def _folder_changed(self, _index: int) -> None:
        folder_id = self.folder_combo.currentData()
        self._current_folder_ids[self.current_library] = str(folder_id) if folder_id else None
        has_current = bool(self._current_folder_id())
        self.rename_folder_button.setEnabled(self.collection_folders is not None and has_current)
        self.delete_folder_button.setEnabled(self.collection_folders is not None and has_current)
        self.refresh_catalog()

    def _create_collection_folder(self) -> None:
        if self.collection_folders is None:
            return
        name, accepted = QInputDialog.getText(self, "新建分类文件夹", "文件夹名称：")
        if not accepted or not name.strip():
            return
        try:
            folder = self.collection_folders.create(self.current_library, name)
        except Exception as exc:
            QMessageBox.warning(self, "新建文件夹失败", str(exc))
            return
        self._configure_library_controls()
        self._show_status_message(f"已新建分类文件夹：{folder.name}", 3000)

    def _rename_collection_folder(self) -> None:
        if self.collection_folders is None:
            return
        folder = self.collection_folders.get(self._current_folder_id())
        if folder is None:
            return
        name, accepted = QInputDialog.getText(
            self, "重命名分类文件夹", "新的名称：", text=folder.name
        )
        if not accepted or not name.strip():
            return
        try:
            renamed = self.collection_folders.rename(folder.id, name)
        except Exception as exc:
            QMessageBox.warning(self, "重命名失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()
        self._show_status_message(f"分类文件夹已改名：{renamed.name}", 3000)

    def _delete_collection_folder(self) -> None:
        if self.collection_folders is None:
            return
        folder = self.collection_folders.get(self._current_folder_id())
        if folder is None:
            return
        catalog = self.game_catalog if folder.domain == "games" else self.catalog
        try:
            members = catalog.folder_member_uuids(folder.id) if catalog is not None else []
        except Exception as exc:
            QMessageBox.warning(self, "读取文件夹失败", str(exc))
            return
        answer = QMessageBox.question(
            self,
            "删除分类文件夹",
            f"删除「{folder.name}」？\n\n其中 {len(members)} 条档案会回到未分类；档案和本地文件都不会删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if members:
                catalog.set_folder(members, None)
            try:
                self.collection_folders.delete(folder.id)
            except Exception:
                if members:
                    catalog.set_folder(members, folder.id)
                raise
        except Exception as exc:
            QMessageBox.warning(self, "删除文件夹失败", str(exc))
            return
        self._current_folder_ids[folder.domain] = None
        self._configure_library_controls()
        self.refresh_catalog()
        self._show_status_message(f"已删除分类文件夹：{folder.name}", 3000)

    def _folder_status_text(self, count: int, unit: str) -> str:
        folder = self.collection_folders.get(self._current_folder_id()) if self.collection_folders else None
        count_text = f"{count} {unit}"
        return f"{folder.name} · {count_text}" if folder is not None else count_text

    def refresh_catalog(self) -> None:
        if self.current_library == "games":
            self._refresh_games()
        else:
            self._refresh_movies()

    def _refresh_movies(self) -> None:
        try:
            movies = self.catalog.list_movies(
                self.search_edit.text(),
                self._current_movie_filter(),
                sort=self.settings.sort_key,
                descending=self.settings.sort_desc,
            )
        except Exception as exc:
            self._show_status_message(f"读取影片库失败：{exc}", 6000)
            return
        self.grid_model.set_movies(movies)
        self.table_model.set_movies(movies)
        self._set_catalog_status(self._folder_status_text(len(movies), "部影片"))
        if (
            self.content_page_stack.currentWidget() is self.movie_archive_page
            and self.movie_archive_page.movie_uuid
        ):
            try:
                current = self.catalog.get(self.movie_archive_page.movie_uuid)
            except Exception:
                current = None
            if current is not None:
                self.movie_archive_page.set_record(current)

    def _refresh_games(self) -> None:
        if self.game_catalog is None:
            self.game_model.set_games([])
            return
        data = self._current_filter_data()
        try:
            games = self.game_catalog.list_games(
                self.search_edit.text(),
                favorite=data.get("favorite"),
                installed=data.get("installed"),
                recently_played=data.get("recently_played"),
                tag=data.get("tag"),
                folder_id=self._current_folder_id(),
                sort=self.settings.game_sort_key,
                descending=self.settings.game_sort_desc,
            )
        except Exception as exc:
            self._show_status_message(f"读取游戏库失败：{exc}", 6000)
            return
        self.game_model.set_games(games)
        self._set_catalog_status(self._folder_status_text(len(games), "个游戏"))
        if (
            self.content_page_stack.currentWidget() is self.game_archive_page
            and self.game_archive_page.game_uuid
        ):
            try:
                current = self.game_catalog.get(self.game_archive_page.game_uuid)
            except Exception:
                current = None
            if current is not None:
                self.game_archive_page.set_record(current)

    def _filter_changed(self, _index: int) -> None:
        key = str(self._current_filter_data().get("key") or "all")
        if self.current_library == "movies":
            persistent = key if key in {"all", "favorite", "watched", "unwatched"} else "all"
            self.movie_view_state_changed.emit(self.settings.sort_key, self.settings.sort_desc, persistent)
        else:
            persistent = key if key in {"all", "favorite", "installed", "uninstalled", "recent"} else "all"
            self.game_view_state_changed.emit(self.settings.game_sort_key, self.settings.game_sort_desc, persistent)
        self.refresh_catalog()

    def _sort_changed(self, _index: int) -> None:
        key = str(self.sort_combo.currentData() or ("last_played_at" if self.current_library == "games" else "code"))
        if self.current_library == "games":
            self.game_view_state_changed.emit(key, self.settings.game_sort_desc, getattr(self.settings, "game_filter", "all"))
        else:
            self.sort_state_changed.emit(key, self.settings.sort_desc)
            self.movie_view_state_changed.emit(key, self.settings.sort_desc, getattr(self.settings, "movie_filter", "all"))
        self.refresh_catalog()

    def _toggle_sort_direction(self) -> None:
        if self.current_library == "games":
            descending = not self.settings.game_sort_desc
            key = str(self.sort_combo.currentData() or "last_played_at")
            self.sort_direction_button.setText("↓" if descending else "↑")
            self.game_view_state_changed.emit(key, descending, getattr(self.settings, "game_filter", "all"))
        else:
            descending = not self.settings.sort_desc
            key = str(self.sort_combo.currentData() or "code")
            self.sort_direction_button.setText("↓" if descending else "↑")
            self.sort_state_changed.emit(key, descending)
            self.movie_view_state_changed.emit(key, descending, getattr(self.settings, "movie_filter", "all"))
        self.refresh_catalog()

    def apply_settings(self, settings) -> None:
        self.settings = settings
        if hasattr(self.catalog, "settings"):
            self.catalog.settings = settings
        self.game_archive_page.screenshot_service = self.screenshot_service
        self._configure_library_controls()
        self.refresh_catalog()

    def _toggle_view(self) -> None:
        if self.current_library != "movies":
            return
        if self._movie_view_index == 0:
            self._movie_view_index = 1
            self.view_button.setText("封面墙")
            self.view_button.setIcon(flat_icon("grid"))
        else:
            self._movie_view_index = 0
            self.view_button.setText("列表视图")
            self.view_button.setIcon(flat_icon("list"))
        self.view_stack.setCurrentIndex(self._movie_view_index)

    def _open_cover_tools(self) -> None:
        dialog = GigaCoverDialog(
            self.settings.cover_dir,
            self.cover_service,
            self,
            source_dir=self.settings.cover_tool_source_dir,
            margin_px=self.settings.cover_tool_margin_px,
        )
        dialog.covers_changed.connect(self.refresh_catalog)
        dialog.exec()
        self.cover_tool_state_changed.emit(dialog.source_edit.text().strip(), dialog.margin_spin.value())

    def start_scan(self) -> None:
        if self._scan_thread and self._scan_thread.isRunning():
            self._show_status_message("正在扫描影片库……")
            return
        self.rescan_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self._show_status_message("正在扫描影片库……")
        thread = QThread(self)
        worker = ScanWorker(self.scanner, self.settings)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._scan_finished)
        worker.failed.connect(self._scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._scan_thread_cleared)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _scan_finished(self, summary) -> None:
        self.rescan_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self._configure_library_controls()
        self.refresh_catalog()
        self._show_status_message(
            f"扫描完成：新增 {summary.new} / 更新 {summary.updated} / 离线 {summary.offline} / 错误 {len(summary.errors)}",
            10000,
        )
        if summary.ambiguities:
            QMessageBox.information(
                self,
                "存在待确认的匹配",
                f"有 {len(summary.ambiguities)} 个影片文件与多个旧档案匹配，程序没有自动覆盖。",
            )

    def _scan_failed(self, message: str) -> None:
        self.rescan_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self._show_status_message("扫描失败", 5000)
        QMessageBox.warning(self, "扫描失败", message)

    def _scan_thread_cleared(self) -> None:
        self._scan_thread = None
        self._scan_worker = None

    def _open_detail(self, record: MovieRecord | None) -> None:
        if record is None:
            return
        self.library_tools_popup.hide()
        self.movie_archive_page.set_record(record)
        transition_stack_page(self.content_page_stack, self.movie_archive_page, direction=1)

    def _close_movie_archive(self) -> None:
        transition_stack_page(self.content_page_stack, self.library_page, direction=-1)

    def _play_movie_by_uuid(self, uuid: str) -> None:
        record = self.catalog.get(uuid) if self.catalog else None
        self._play_record(record)
        if self.movie_archive_page.movie_uuid == uuid:
            updated = self.catalog.get(uuid) if self.catalog else None
            if updated is not None:
                self.movie_archive_page.set_record(updated)
                self.content_page_stack.setCurrentWidget(self.movie_archive_page)

    def _refresh_movie_archive(self, uuid: str) -> None:
        self.refresh_catalog()
        if self.movie_archive_page.movie_uuid != uuid:
            return
        record = self.catalog.get(uuid) if self.catalog else None
        if record is not None:
            self.movie_archive_page.set_record(record)
            self.content_page_stack.setCurrentWidget(self.movie_archive_page)

    def _update_movie_archive_metadata(self, uuid: str, patch: MovieMetadataPatch) -> None:
        if self.catalog is None:
            return
        try:
            self.catalog.update_metadata(uuid, patch)
        except Exception as exc:
            QMessageBox.warning(self, "更新失败", str(exc))
            self._refresh_movie_archive(uuid)
            return
        self._refresh_movie_archive(uuid)
        self._show_status_message("影片档案已保存", 1800)

    def _change_movie_archive_cover(self, uuid: str) -> None:
        if self.catalog is None or self.cover_service is None:
            return
        record = self.catalog.get(uuid)
        if record is None:
            return
        if not record.metadata.cover_key.strip():
            QMessageBox.information(self, "需要封面键", "请先在影片资料中填写封面键，再更换封面。")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择封面",
            "",
            "图片 (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
        )
        if not path:
            return
        try:
            self.cover_service.replace(record.metadata.cover_key, Path(path))
            self.catalog.refresh_cover(uuid)
        except Exception as exc:
            QMessageBox.warning(self, "更换封面失败", str(exc))
            return
        self._refresh_movie_archive(uuid)
        self._show_status_message("影片封面已更新", 2500)

    def _open_movie_archive_folder(self, uuid: str) -> None:
        record = self.catalog.get(uuid) if self.catalog else None
        if record is not None:
            self._open_folder(record)

    def _relink_movie_archive(self, uuid: str) -> None:
        if self.catalog is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "关联本地影片",
            "",
            "影片文件 (*.mp4 *.mkv *.avi *.mov *.wmv *.m4v *.ts *.webm)",
        )
        if not path:
            return
        try:
            self.catalog.relink_video(uuid, Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "关联失败", str(exc))
            return
        self._refresh_movie_archive(uuid)
        self._show_status_message("本地影片文件已重新关联", 2500)

    def _delete_movie_archive(self, uuid: str) -> None:
        if self.catalog is None:
            return
        answer = QMessageBox.question(
            self,
            "删除影片档案",
            "确定永久删除这条影片档案吗？\n\n视频文件和集中封面不会被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.catalog.delete_archive(uuid)
        except Exception as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            return
        if self.movie_archive_page.movie_uuid == uuid:
            self._close_movie_archive()
        self.refresh_catalog()
        self._show_status_message("影片档案已删除", 2500)

    def _populate_move_to_folder_menu(self, menu: QMenu, uuids: list[str]) -> None:
        move_menu = menu.addMenu("移动到文件夹")
        unfiled = move_menu.addAction("未分类")
        unfiled.triggered.connect(lambda: self._move_records_to_folder(uuids, None))
        folders = []
        if self.collection_folders is not None:
            try:
                folders = self.collection_folders.list(self.current_library)
            except Exception as exc:
                error = move_menu.addAction(f"读取失败：{exc}")
                error.setEnabled(False)
                return
        if folders:
            move_menu.addSeparator()
        for folder in folders:
            action = move_menu.addAction(folder.name)
            action.triggered.connect(
                lambda _checked=False, folder_id=folder.id: self._move_records_to_folder(uuids, folder_id)
            )

    def _move_records_to_folder(self, uuids: list[str], folder_id: str | None) -> None:
        catalog = self.game_catalog if self.current_library == "games" else self.catalog
        if catalog is None:
            return
        if folder_id and self.collection_folders is not None:
            folder = self.collection_folders.get(folder_id)
            if folder is None or folder.domain != self.current_library:
                QMessageBox.warning(self, "移动失败", "目标分类文件夹不存在或不属于当前媒体库。")
                return
        try:
            catalog.set_folder(uuids, folder_id)
        except Exception as exc:
            QMessageBox.warning(self, "移动失败", str(exc))
            return
        self.refresh_catalog()
        target = self.collection_folders.get(folder_id).name if folder_id and self.collection_folders else "未分类"
        self._show_status_message(f"已移动 {len(uuids)} 条档案到「{target}」", 3000)

    def _show_movie_context_menu(self, view, pos, model) -> None:
        index = view.indexAt(pos)
        if not index.isValid():
            return
        self._ensure_context_row_selected(view, index)
        records = self._selected_records(view, model)
        if not records:
            return
        menu = QMenu(view)
        if len(records) > 1:
            self._populate_batch_menu(menu, records)
        else:
            record = records[0]
            play_action = QAction("播放", menu)
            play_action.setEnabled(record.runtime.availability_status == "available")
            play_action.triggered.connect(lambda: self._play_record(record))
            menu.addAction(play_action)
            detail_action = menu.addAction("影片档案")
            detail_action.triggered.connect(lambda: self._open_detail(record))
            self._populate_move_to_folder_menu(menu, [record.metadata.uuid])
            folder_action = menu.addAction("打开所在文件夹")
            folder_action.setEnabled(record.runtime.availability_status == "available")
            folder_action.triggered.connect(lambda: self._open_folder(record))
        exec_menu_with_motion(menu, view.viewport().mapToGlobal(pos))

    def _ensure_context_row_selected(self, view, index) -> None:
        selected_rows = {item.row() for item in view.selectionModel().selectedIndexes()}
        if index.row() in selected_rows:
            return
        flags = QItemSelectionModel.SelectionFlag.ClearAndSelect
        if view is self.table_view:
            flags |= QItemSelectionModel.SelectionFlag.Rows
        view.selectionModel().select(index, flags)
        view.setCurrentIndex(index)

    @staticmethod
    def _selected_records(view, model) -> list[MovieRecord]:
        rows = sorted({item.row() for item in view.selectionModel().selectedIndexes()})
        records: list[MovieRecord] = []
        for row in rows:
            record = model.movie_at(row)
            if record is not None:
                records.append(record)
        return records

    def _populate_batch_menu(self, menu: QMenu, records: list[MovieRecord]) -> None:
        summary = menu.addAction(f"已选择 {len(records)} 部影片")
        summary.setEnabled(False)
        batch_menu = menu.addMenu("批量编辑")
        batch_menu.addAction("添加标签…").triggered.connect(lambda: self._batch_tags(records, remove=False))
        batch_menu.addAction("删除标签…").triggered.connect(lambda: self._batch_tags(records, remove=True))
        batch_menu.addSeparator()
        batch_menu.addAction("设置厂商…").triggered.connect(
            lambda: self._batch_text_field(records, field="studio", label="厂商")
        )
        batch_menu.addAction("设置系列…").triggered.connect(
            lambda: self._batch_text_field(records, field="series", label="系列")
        )
        batch_menu.addSeparator()
        self._populate_move_to_folder_menu(
            batch_menu, [record.metadata.uuid for record in records]
        )

    def _batch_tags(self, records: list[MovieRecord], *, remove: bool) -> None:
        verb = "删除" if remove else "添加"
        text, accepted = QInputDialog.getText(self, f"批量{verb}标签", "输入标签，多个标签可用逗号分隔：")
        if not accepted:
            return
        tags = parse_batch_terms(text)
        if not tags:
            QMessageBox.information(self, "没有标签", "请输入至少一个标签。")
            return
        if not self._confirm_batch(len(records), f"{verb}标签：{'、'.join(tags)}"):
            return
        try:
            self.catalog.batch_update_tags([record.metadata.uuid for record in records], tags, remove=remove)
        except Exception as exc:
            QMessageBox.warning(self, "批量更新失败", str(exc))
            return
        self._batch_finished(len(records))

    def _batch_text_field(self, records: list[MovieRecord], *, field: str, label: str) -> None:
        value, accepted = QInputDialog.getText(self, f"批量设置{label}", f"输入新的{label}（留空会清空原值）：")
        if not accepted:
            return
        description = f"清空{label}" if not value.strip() else f"把{label}设置为「{value.strip()}」"
        if not self._confirm_batch(len(records), description):
            return
        try:
            self.catalog.batch_update_metadata(
                [record.metadata.uuid for record in records],
                MovieMetadataPatch(**{field: value.strip()}),
            )
        except Exception as exc:
            QMessageBox.warning(self, "批量更新失败", str(exc))
            return
        self._batch_finished(len(records))

    def _batch_patch(self, records: list[MovieRecord], patch: MovieMetadataPatch, description: str) -> None:
        if not self._confirm_batch(len(records), description):
            return
        try:
            self.catalog.batch_update_metadata([record.metadata.uuid for record in records], patch)
        except Exception as exc:
            QMessageBox.warning(self, "批量更新失败", str(exc))
            return
        self._batch_finished(len(records))

    def _confirm_batch(self, count: int, description: str) -> bool:
        answer = QMessageBox.question(
            self,
            "确认批量编辑",
            f"{description}。\n\n将修改 {count} 部影片，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _batch_finished(self, count: int) -> None:
        self._configure_library_controls()
        self.refresh_catalog()
        self._show_status_message(f"已批量更新 {count} 部影片", 5000)

    def _play_record(self, record: MovieRecord | None) -> None:
        if record is None:
            return
        if not record.runtime.video_path:
            QMessageBox.information(self, "当前无法播放", "这部影片目前只有档案，没有已关联的本地视频文件。")
            return
        try:
            handle = self.player_service.play(Path(record.runtime.video_path), self.settings)
            self.viewing_service.start_playback(record.metadata.uuid, handle)
            self.refresh_catalog()
        except PlaybackError as exc:
            QMessageBox.warning(self, "无法播放", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "播放失败", str(exc))

    def _open_folder(self, record: MovieRecord) -> None:
        if record.runtime.video_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(record.runtime.video_path).parent)))

    def _patch_record(self, record: MovieRecord, patch: MovieMetadataPatch) -> None:
        try:
            self.catalog.update_metadata(record.metadata.uuid, patch)
        except Exception as exc:
            QMessageBox.warning(self, "更新失败", str(exc))
            return
        self.refresh_catalog()

    def _add_game(self) -> None:
        if self.game_catalog is None:
            return
        dialog = GameEditDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        data = dialog.result_data
        try:
            self.game_catalog.create_game(
                title=data.title,
                series=data.series,
                developer=data.developer,
                publisher=data.publisher,
                release_date=data.release_date,
                tags=data.tags,
                rating=data.rating,
                favorite=data.favorite,
                notes=data.notes,
                launch_exe=data.launch_exe,
                timing_exe=data.timing_exe,
                launch_args=data.launch_args,
                working_directory=data.working_directory,
                screenshot_directory=data.screenshot_directory,
                cover_source=data.cover_source,
                preview_source=data.preview_source,
            )
        except Exception as exc:
            QMessageBox.warning(self, "添加游戏失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()

    def _launch_game(self, record: GameRecord | None) -> None:
        if record is None or self.game_launcher is None:
            return
        try:
            self.game_launcher.launch(record.metadata)
        except Exception as exc:
            QMessageBox.warning(self, "启动游戏失败", str(exc))
            return
        if self.game_session_service is not None:
            self.game_session_service.request_launch(record.metadata)

    def _launch_game_by_uuid(self, uuid: str) -> None:
        record = self.game_catalog.get(uuid) if self.game_catalog else None
        self._launch_game(record)

    def _open_game_detail(self, record: GameRecord) -> None:
        self.library_tools_popup.hide()
        self.game_archive_page.screenshot_service = self.screenshot_service
        self.game_archive_page.set_record(record)
        transition_stack_page(self.content_page_stack, self.game_archive_page, direction=1)

    def _close_game_archive(self) -> None:
        self.game_archive_page.deactivate()
        transition_stack_page(self.content_page_stack, self.library_page, direction=-1)

    def _refresh_game_archive(self, uuid: str) -> None:
        self._configure_library_controls()
        self.refresh_catalog()
        if self.game_archive_page.game_uuid != uuid or self.game_catalog is None:
            return
        record = self.game_catalog.get(uuid)
        if record is not None:
            self.game_archive_page.set_record(record)
            self.content_page_stack.setCurrentWidget(self.game_archive_page)

    def _update_game_archive_metadata(self, uuid: str, patch: GameMetadataPatch) -> None:
        if self.game_catalog is None:
            return
        if patch.title is not None and not patch.title.strip():
            QMessageBox.information(self, "信息不完整", "游戏名称不能为空。")
            self._refresh_game_archive(uuid)
            return
        if patch.launch_exe is not None and not patch.launch_exe.strip():
            QMessageBox.information(self, "信息不完整", "启动 EXE 不能为空。")
            self._refresh_game_archive(uuid)
            return
        if patch.timing_exe is not None and not patch.timing_exe.strip():
            QMessageBox.information(self, "信息不完整", "计时 EXE 不能为空。")
            self._refresh_game_archive(uuid)
            return
        try:
            updated = self.game_catalog.update_game(uuid, patch)
        except Exception as exc:
            QMessageBox.warning(self, "保存游戏失败", str(exc))
            self._refresh_game_archive(uuid)
            return
        self._configure_library_controls()
        self.refresh_catalog()
        self.game_archive_page.set_record(updated)
        self.content_page_stack.setCurrentWidget(self.game_archive_page)
        self._show_status_message("游戏档案已保存", 1800)

    def _update_game_archive_assets(
        self,
        uuid: str,
        *,
        cover_source: Path | None = None,
        preview_source: Path | None = None,
        remove_cover: bool = False,
        remove_preview: bool = False,
        status: str = "游戏档案已更新",
    ) -> None:
        if self.game_catalog is None:
            return
        try:
            updated = self.game_catalog.update_game(
                uuid,
                GameMetadataPatch(),
                cover_source=cover_source,
                preview_source=preview_source,
                remove_cover=remove_cover,
                remove_preview=remove_preview,
            )
        except Exception as exc:
            QMessageBox.warning(self, "更新游戏失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()
        self.game_archive_page.set_record(updated)
        self.content_page_stack.setCurrentWidget(self.game_archive_page)
        self._show_status_message(status, 2500)

    def _change_game_archive_cover(self, uuid: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择游戏封面", "", "图片 (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if path:
            self._update_game_archive_assets(uuid, cover_source=Path(path), status="游戏封面已更新")

    def _crop_game_archive_cover(self, uuid: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择需要裁剪的游戏封面", "", "图片 (*.jpg *.jpeg *.png *.webp)"
        )
        if not path:
            return
        with TemporaryDirectory(prefix="local-resource-terminal-game-cover-") as temporary:
            try:
                crop_dialog = ManualCoverCropDialog(
                    Path(path),
                    Path(temporary),
                    GigaCoverCropper(),
                    parent=self,
                )
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "无法打开封面", str(exc))
                return
            if crop_dialog.exec() != QDialog.DialogCode.Accepted or crop_dialog.saved_candidate is None:
                return
            cropped_path = crop_dialog.saved_candidate.output_path
            if not cropped_path.is_file():
                QMessageBox.warning(self, "裁剪失败", "裁剪后的封面文件不存在。")
                return
            self._update_game_archive_assets(uuid, cover_source=cropped_path, status="裁剪封面已导入")

    def _clear_game_archive_cover(self, uuid: str) -> None:
        self._update_game_archive_assets(uuid, remove_cover=True, status="游戏封面已清除")

    def _change_game_archive_preview(self, uuid: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 GIF 动态预览", "", "GIF 动图 (*.gif)")
        if path:
            self._update_game_archive_assets(uuid, preview_source=Path(path), status="游戏 GIF 已更新")

    def _clear_game_archive_preview(self, uuid: str) -> None:
        self._update_game_archive_assets(uuid, remove_preview=True, status="游戏 GIF 已清除")

    def _browse_game_archive_launch_exe(self, uuid: str) -> None:
        record = self.game_catalog.get(uuid) if self.game_catalog else None
        if record is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择启动 EXE", record.metadata.launch_exe, "程序 (*.exe);;所有文件 (*)"
        )
        if path:
            patch = GameMetadataPatch(launch_exe=path)
            if not record.metadata.working_directory:
                patch.working_directory = str(Path(path).parent)
            self._update_game_archive_metadata(uuid, patch)

    def _browse_game_archive_timing_exe(self, uuid: str) -> None:
        record = self.game_catalog.get(uuid) if self.game_catalog else None
        if record is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择计时 EXE", record.metadata.timing_exe, "程序 (*.exe);;所有文件 (*)"
        )
        if path:
            self._update_game_archive_metadata(uuid, GameMetadataPatch(timing_exe=path))

    def _browse_game_archive_workdir(self, uuid: str) -> None:
        record = self.game_catalog.get(uuid) if self.game_catalog else None
        if record is None:
            return
        path = QFileDialog.getExistingDirectory(self, "选择工作目录", record.metadata.working_directory)
        if path:
            self._update_game_archive_metadata(uuid, GameMetadataPatch(working_directory=path))

    def _browse_game_archive_screenshot_dir(self, uuid: str) -> None:
        record = self.game_catalog.get(uuid) if self.game_catalog else None
        if record is None:
            return
        path = QFileDialog.getExistingDirectory(
            self, "选择截图目录", record.metadata.screenshot_directory or ""
        )
        if path:
            self._update_game_archive_metadata(uuid, GameMetadataPatch(screenshot_directory=path))

    def _change_game_archive_media(self, uuid: str) -> None:
        if self.game_catalog is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择档案展示图",
            "",
            "图片 / GIF (*.jpg *.jpeg *.png *.webp *.bmp *.gif)",
        )
        if not path:
            return
        try:
            updated = self.game_catalog.update_archive_media(uuid, source=Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "展示图更新失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()
        self.game_archive_page.set_record(updated)
        self.content_page_stack.setCurrentWidget(self.game_archive_page)
        self._show_status_message("游戏档案展示图已更新", 3000)

    def _clear_game_archive_media(self, uuid: str) -> None:
        if self.game_catalog is None:
            return
        try:
            updated = self.game_catalog.update_archive_media(uuid, remove=True)
        except Exception as exc:
            QMessageBox.warning(self, "清除展示图失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()
        self.game_archive_page.set_record(updated)
        self.content_page_stack.setCurrentWidget(self.game_archive_page)
        self._show_status_message("已清除专属展示图", 3000)

    def _show_game_context_menu(self, pos) -> None:
        index = self.game_view.indexAt(pos)
        if not index.isValid():
            return
        record = self.game_model.game_at(index.row())
        if record is None:
            return
        menu = QMenu(self.game_view)
        launch = menu.addAction("启动游戏")
        launch.setEnabled(record.installed)
        launch.triggered.connect(lambda: self._launch_game(record))
        menu.addAction("游戏档案").triggered.connect(lambda: self._open_game_detail(record))
        menu.addSeparator()
        menu.addAction("取消收藏" if record.metadata.favorite else "收藏").triggered.connect(
            lambda: self._toggle_game_favorite(record)
        )
        self._populate_move_to_folder_menu(menu, [record.metadata.uuid])
        menu.addSeparator()
        game_dir = menu.addAction("打开游戏目录")
        game_dir.setEnabled(bool(record.metadata.launch_exe and Path(record.metadata.launch_exe).parent.is_dir()))
        game_dir.triggered.connect(lambda: self._open_path(Path(record.metadata.launch_exe).parent))
        shot_dir = menu.addAction("打开截图目录")
        shot_dir.setEnabled(bool(record.metadata.screenshot_directory and Path(record.metadata.screenshot_directory).is_dir()))
        shot_dir.triggered.connect(lambda: self._open_path(Path(record.metadata.screenshot_directory)))
        menu.addSeparator()
        menu.addAction("删除游戏档案…").triggered.connect(lambda: self._delete_game(record))
        exec_menu_with_motion(menu, self.game_view.viewport().mapToGlobal(pos))

    def _toggle_game_favorite(self, record: GameRecord) -> None:
        if self.game_catalog is None:
            return
        try:
            self.game_catalog.update_game(
                record.metadata.uuid,
                GameMetadataPatch(favorite=not record.metadata.favorite),
            )
        except Exception as exc:
            QMessageBox.warning(self, "更新失败", str(exc))
            return
        self.refresh_catalog()

    def _delete_game(self, record: GameRecord) -> None:
        if self.game_catalog is None:
            return
        answer = QMessageBox.question(
            self,
            "删除游戏档案",
            "只会删除终端中的游戏档案、游玩记录、封面和 GIF。\n\n不会删除游戏文件、存档或外部截图。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.game_catalog.delete_game(record.metadata.uuid)
        except Exception as exc:
            QMessageBox.warning(self, "删除失败", str(exc))
            return
        self._configure_library_controls()
        self.refresh_catalog()

    @staticmethod
    def _open_path(path: Path) -> None:
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _game_timer_tick(self) -> None:
        if self.game_session_service is None:
            self.active_game_label.setVisible(False)
            return
        before = self.game_session_service.active_game_uuid
        try:
            self.game_session_service.poll()
        except Exception as exc:
            self._show_status_message(f"游戏计时检查失败：{exc}", 5000)
            return
        after = self.game_session_service.active_game_uuid
        if after:
            self._game_tick_count += 1
            elapsed = self.game_session_service.elapsed_seconds
            self.active_game_label.setText(
                f"正在记录：{self.game_session_service.active_game_title or '游戏'}  {_format_duration(elapsed)}"
            )
            self.active_game_label.setVisible(True)
            if self._game_tick_count % 30 == 0:
                try:
                    self.game_session_service.checkpoint()
                except Exception as exc:
                    self._show_status_message(f"游戏时长检查点保存失败：{exc}", 5000)
        else:
            self._game_tick_count = 0
            self.active_game_label.setVisible(False)
        if before and not after and self.current_library == "games":
            self.refresh_catalog()


    def _movie_timer_tick(self) -> None:
        if self.viewing_service is None or not hasattr(self.viewing_service, "poll_playbacks"):
            return
        try:
            finished = self.viewing_service.poll_playbacks()
        except Exception as exc:
            self._show_status_message(f"影片播放时长保存失败：{exc}", 5000)
            return
        if not finished:
            return
        self.refresh_catalog()
        current_uuid = self.movie_archive_page.movie_uuid
        if current_uuid in finished:
            record = self.catalog.get(current_uuid) if self.catalog else None
            if record is not None:
                self.movie_archive_page.set_record(record)

    def closeEvent(self, event) -> None:
        if self.game_session_service is not None and self.game_session_service.active_game_uuid:
            answer = QMessageBox.question(
                self,
                "游戏正在计时",
                "当前有游戏正在记录游玩时间。关闭终端将停止本次时长记录。",
                QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            try:
                self.game_session_service.finish_active()
            except Exception as exc:
                QMessageBox.warning(self, "结束计时失败", str(exc))
                event.ignore()
                return
        if self.viewing_service is not None and hasattr(self.viewing_service, "finish_all_playbacks"):
            try:
                self.viewing_service.finish_all_playbacks()
            except Exception as exc:
                self._show_status_message(f"影片播放时长保存失败：{exc}", 5000)
        super().closeEvent(event)

    def nativeEvent(self, event_type, message):  # noqa: N802 - Qt override
        # Windows keeps native resize semantics even though the visible title bar is theme-owned.
        WM_NCHITTEST = 0x0084
        if sys.platform == "win32" and getattr(self, "_resize_frame", None) is None and not self.isMaximized():
            import ctypes
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if int(msg.message) == WM_NCHITTEST:
                rect = wintypes.RECT()
                hwnd = int(self.winId())
                if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    raw = int(msg.lParam)
                    screen_x = raw & 0xFFFF
                    screen_y = (raw >> 16) & 0xFFFF
                    if screen_x & 0x8000:
                        screen_x -= 0x10000
                    if screen_y & 0x8000:
                        screen_y -= 0x10000
                    border = max(6, int(round(7 * self.devicePixelRatioF())))
                    zone = edge_zone(
                        rect.right - rect.left,
                        rect.bottom - rect.top,
                        screen_x - rect.left,
                        screen_y - rect.top,
                        border,
                    )
                    hit_results = {
                        "left": 10,          # HTLEFT
                        "right": 11,         # HTRIGHT
                        "top": 12,           # HTTOP
                        "top_left": 13,      # HTTOPLEFT
                        "top_right": 14,     # HTTOPRIGHT
                        "bottom": 15,        # HTBOTTOM
                        "bottom_left": 16,   # HTBOTTOMLEFT
                        "bottom_right": 17,  # HTBOTTOMRIGHT
                    }
                    if zone in hit_results:
                        return True, hit_results[zone]
        return super().nativeEvent(event_type, message)


def _format_duration(duration_seconds: int) -> str:
    total = max(0, int(duration_seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
