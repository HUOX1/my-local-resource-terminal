from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from app.config.theme_registry import (
    DEFAULT_THEME_ID,
    THEMES,
    ThemeSpec,
    get_theme,
    resolve_theme_id,
)


class FlatTokens:
    BACKGROUND = "#0F1115"
    SURFACE = "#171A1F"
    SURFACE_RAISED = "#1C2026"
    SURFACE_HOVER = "#222730"
    BORDER = "#252B33"
    BORDER_STRONG = "#353D48"
    TEXT_PRIMARY = "#EEF2F7"
    TEXT_SECONDARY = "#A2ACB9"
    TEXT_MUTED = "#6F7B89"
    ACCENT = "#4F7FD8"
    ACCENT_HOVER = "#5E8CE4"
    ACCENT_PRESSED = "#4069B7"
    ACCENT_SOFT = "#192640"
    ACCENT_SOFT_TEXT = "#A9C5FF"
    ACCENT_FOREGROUND = "#FFFFFF"
    SUCCESS = "#4CC38A"
    DANGER = "#F0616D"
    DANGER_BORDER = "#6D343A"
    DANGER_TEXT = "#FF8B95"
    DANGER_HOVER_BG = "#3A2024"
    DANGER_HOVER_TEXT = "#FFD6DA"
    CHROME_SURFACE = "#13161A"
    CHROME_BORDER = "#222831"
    CHROME_TEXT = "#DCE3EC"
    CHROME_BUTTON_HOVER = "#20252C"
    NAV_SELECTED_BG = "#12161B"
    NAV_SELECTED_TEXT = "#E8EEF8"
    NAV_INSET_DARK = "#080B0E"
    NAV_INSET_LIGHT = "#414B58"
    NAV_STYLE = "sunken_card"
    MOTION_LEVEL = "full"

    RADIUS_SMALL = 5
    RADIUS_MEDIUM = 7
    RADIUS_LARGE = 9

    SPACE_1 = 4
    SPACE_2 = 8
    SPACE_3 = 12
    SPACE_4 = 16
    SPACE_5 = 24

    CONTROL_HEIGHT = 34
    SIDEBAR_WIDTH = 196
    TITLEBAR_HEIGHT = 38
    NAV_HEIGHT = 44


def theme_display_name(theme_id: str) -> str:
    return get_theme(theme_id).display_name


def activate_theme(theme_id: str) -> str:
    resolved_id = resolve_theme_id(theme_id)
    spec = get_theme(resolved_id)
    mapping = {
        "BACKGROUND": spec.background,
        "SURFACE": spec.surface,
        "SURFACE_RAISED": spec.surface_raised,
        "SURFACE_HOVER": spec.surface_hover,
        "BORDER": spec.border,
        "BORDER_STRONG": spec.border_strong,
        "TEXT_PRIMARY": spec.text_primary,
        "TEXT_SECONDARY": spec.text_secondary,
        "TEXT_MUTED": spec.text_muted,
        "ACCENT": spec.accent,
        "ACCENT_HOVER": spec.accent_hover,
        "ACCENT_PRESSED": spec.accent_pressed,
        "ACCENT_SOFT": spec.accent_soft,
        "ACCENT_SOFT_TEXT": spec.accent_soft_text,
        "ACCENT_FOREGROUND": spec.accent_foreground,
        "SUCCESS": spec.success,
        "DANGER": spec.danger,
        "DANGER_BORDER": spec.danger_border,
        "DANGER_TEXT": spec.danger_text,
        "DANGER_HOVER_BG": spec.danger_hover_bg,
        "DANGER_HOVER_TEXT": spec.danger_hover_text,
        "CHROME_SURFACE": spec.chrome_surface,
        "CHROME_BORDER": spec.chrome_border,
        "CHROME_TEXT": spec.chrome_text,
        "CHROME_BUTTON_HOVER": spec.chrome_button_hover,
        "NAV_SELECTED_BG": spec.nav_selected_bg,
        "NAV_SELECTED_TEXT": spec.nav_selected_text,
        "NAV_INSET_DARK": spec.nav_inset_dark,
        "NAV_INSET_LIGHT": spec.nav_inset_light,
        "NAV_STYLE": spec.nav_style,
        "MOTION_LEVEL": spec.motion_level,
        "RADIUS_SMALL": spec.metrics.radius_small,
        "RADIUS_MEDIUM": spec.metrics.radius_medium,
        "RADIUS_LARGE": spec.metrics.radius_large,
        "SPACE_1": spec.metrics.space_1,
        "SPACE_2": spec.metrics.space_2,
        "SPACE_3": spec.metrics.space_3,
        "SPACE_4": spec.metrics.space_4,
        "SPACE_5": spec.metrics.space_5,
        "CONTROL_HEIGHT": spec.metrics.control_height,
        "SIDEBAR_WIDTH": spec.metrics.sidebar_width,
        "TITLEBAR_HEIGHT": spec.metrics.titlebar_height,
        "NAV_HEIGHT": spec.metrics.nav_height,
    }
    for name, value in mapping.items():
        setattr(FlatTokens, name, value)
    return resolved_id


def build_flat_stylesheet() -> str:
    t = FlatTokens
    if t.NAV_STYLE == "inset":
        nav_checked_style = f"""
    background: {t.NAV_SELECTED_BG};
    color: {t.NAV_SELECTED_TEXT};
    font-weight: 600;
    border-top-color: {t.NAV_INSET_DARK};
    border-left-color: {t.NAV_INSET_DARK};
    border-right-color: {t.NAV_INSET_LIGHT};
    border-bottom-color: {t.NAV_INSET_LIGHT};
    padding-top: 1px;
    padding-left: 15px;
"""
    elif t.NAV_STYLE == "sunken_card":
        nav_checked_style = f"""
    background: transparent;
    color: {t.NAV_SELECTED_TEXT};
    font-weight: 600;
    border-color: transparent;
    padding-top: 1px;
    padding-left: 14px;
"""
    elif t.NAV_STYLE == "pressed_card":
        nav_checked_style = f"""
    background: transparent;
    color: {t.NAV_SELECTED_TEXT};
    font-weight: 600;
    border-color: transparent;
    padding-top: 1px;
    padding-left: 14px;
"""
    else:
        nav_checked_style = f"""
    background: {t.ACCENT};
    color: {t.ACCENT_FOREGROUND};
    font-weight: 600;
    border-color: {t.ACCENT};
"""

    if t.NAV_STYLE == "inset":
        button_pressed_style = f"""
    background: {t.SURFACE};
    border-top-color: {t.NAV_INSET_DARK};
    border-left-color: {t.NAV_INSET_DARK};
    border-right-color: {t.NAV_INSET_LIGHT};
    border-bottom-color: {t.NAV_INSET_LIGHT};
    padding-top: 1px;
"""
        titlebar_pressed_style = f"""
    background: {t.SURFACE};
    border-top: 1px solid {t.NAV_INSET_DARK};
    border-left: 1px solid {t.NAV_INSET_DARK};
    border-right: 1px solid {t.NAV_INSET_LIGHT};
    border-bottom: 1px solid {t.NAV_INSET_LIGHT};
    padding-top: 1px;
"""
    else:
        button_pressed_style = f"""
    background: {t.SURFACE};
"""
        titlebar_pressed_style = f"""
    background: {t.SURFACE_HOVER};
"""

    return f"""
QWidget {{
    color: {t.TEXT_PRIMARY};
    font-size: 13px;
}}
QMainWindow, QDialog, QMessageBox {{
    background: {t.BACKGROUND};
}}
QWidget#appRoot {{
    background: {t.BACKGROUND};
}}
QWidget#appTitleBar {{
    background: {t.CHROME_SURFACE};
    border-bottom: 1px solid {t.CHROME_BORDER};
}}
QLabel#appTitleText {{
    color: {t.CHROME_TEXT};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#appTitleVersion {{
    color: {t.TEXT_MUTED};
    font-size: 10px;
}}
QPushButton#titleBarButton, QPushButton#titleBarCloseButton {{
    min-height: {t.TITLEBAR_HEIGHT - 1}px;
    max-height: {t.TITLEBAR_HEIGHT - 1}px;
    min-width: 46px;
    max-width: 46px;
    padding: 0;
    margin: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    color: {t.CHROME_TEXT};
    font-size: 15px;
}}
QPushButton#titleBarButton:hover {{
    background: {t.CHROME_BUTTON_HOVER};
}}
QPushButton#titleBarButton:pressed {{
{titlebar_pressed_style}
}}
QPushButton#titleBarCloseButton:hover {{
    background: {t.DANGER};
    color: #FFFFFF;
}}
QPushButton#titleBarCloseButton:pressed {{
    background: {t.DANGER_HOVER_BG};
}}
QWidget#identityShell {{
    background: {t.BACKGROUND};
}}
QWidget#identityShellCard {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_LARGE}px;
}}
QLabel#identityShellTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#identityEntryName {{
    color: {t.TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 700;
}}
QWidget#identitySidebarRoom {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QWidget#identitySidebarRoom:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
}}
QLabel#identitySidebarName {{
    color: {t.TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#identitySidebarKind {{
    color: {t.TEXT_MUTED};
    font-size: 9px;
}}
QWidget#sidebar {{
    background: {t.SURFACE};
    border: 0;
}}
QSplitter#mainSplitter {{
    background: transparent;
}}
QSplitter#mainSplitter::handle {{
    background: transparent;
    width: 24px;
}}
QSplitter#mainSplitter::handle:hover {{
    background: transparent;
}}
QWidget#contentSurface {{
    background: {t.BACKGROUND};
}}
QWidget#settingsNav {{
    background: {t.SURFACE};
    border: 1px solid {t.CHROME_BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QWidget#settingsPage {{
    background: {t.SURFACE};
    border: 1px solid {t.CHROME_BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QStackedWidget#settingsStack {{
    background: transparent;
    border: 0;
}}
QLabel#settingsPageTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 17px;
    font-weight: 700;
}}
QPushButton#settingsCategoryButton {{
    min-height: 40px;
    padding: 0 12px;
    text-align: left;
    background: transparent;
    border: 0;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_SECONDARY};
    font-size: 13px;
}}
QPushButton#settingsCategoryButton:hover {{
    background: {t.SURFACE_HOVER};
    color: {t.TEXT_PRIMARY};
}}
QPushButton#settingsCategoryButton:checked {{
    background: {t.ACCENT_SOFT};
    color: {t.ACCENT_SOFT_TEXT};
    font-weight: 600;
}}
QPushButton#settingsCategoryButton:pressed {{
{button_pressed_style}
}}
QFrame#libraryToolsPopup {{
    background: {t.SURFACE};
    border: 1px solid {t.CHROME_BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QLabel#popupSectionLabel {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
}}
QLineEdit#toolbarSearch, QComboBox#toolbarCombo {{
    background: {t.SURFACE_RAISED};
    border-color: {t.CHROME_BORDER};
}}
QLineEdit#toolbarSearch:hover, QComboBox#toolbarCombo:hover {{
    border-color: {t.BORDER_STRONG};
}}
QLabel#brandLabel {{
    color: {t.TEXT_PRIMARY};
    font-size: 17px;
    font-weight: 700;
}}
QLabel#versionLabel, QLabel#secondaryLabel {{
    color: {t.TEXT_SECONDARY};
}}
QLabel#sectionLabel {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.7px;
    padding: 6px 8px 2px 8px;
}}
QLabel#dialogHeading {{
    color: {t.TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 700;
}}
QLabel#dialogSectionTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 700;
}}
QWidget#panelCard {{
    background: {t.SURFACE};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QLabel#previewFrame {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
    color: {t.TEXT_MUTED};
}}
QPushButton {{
    min-height: {t.CONTROL_HEIGHT}px;
    padding: 0 12px;
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_PRIMARY};
}}
QPushButton:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER_STRONG};
}}
QPushButton:focus {{
    border-color: {t.ACCENT_SOFT_TEXT};
}}
QPushButton:pressed {{
{button_pressed_style}
}}
QPushButton:disabled {{
    color: {t.TEXT_MUTED};
    background: {t.SURFACE};
    border-color: {t.BORDER};
}}
QPushButton#primaryButton {{
    background: {t.ACCENT};
    border-color: {t.ACCENT};
    color: {t.ACCENT_FOREGROUND};
    font-weight: 600;
}}
QPushButton#primaryButton:hover {{
    background: {t.ACCENT_HOVER};
    border-color: {t.ACCENT_HOVER};
}}
QPushButton#primaryButton:pressed {{
    background: {t.ACCENT_PRESSED};
    border-color: {t.ACCENT_PRESSED};
}}
QPushButton#dangerButton {{
    background: transparent;
    border-color: {t.DANGER_BORDER};
    color: {t.DANGER_TEXT};
}}
QPushButton#dangerButton:hover {{
    background: {t.DANGER_HOVER_BG};
    border-color: {t.DANGER};
    color: {t.DANGER_HOVER_TEXT};
}}
QPushButton#quietButton {{
    background: transparent;
    border-color: transparent;
    color: {t.TEXT_SECONDARY};
}}
QPushButton#quietButton:hover {{
    background: {t.SURFACE_HOVER};
    color: {t.TEXT_PRIMARY};
}}
QPushButton#navButton {{
    min-height: {t.NAV_HEIGHT}px;
    max-height: {t.NAV_HEIGHT}px;
    padding: 0 14px;
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_SECONDARY};
    font-size: 14px;
}}
QPushButton#navButton:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
    color: {t.TEXT_PRIMARY};
}}
QPushButton#navButton:checked {{
{nav_checked_style}
}}
QPushButton#sidebarAction {{
    min-height: 42px;
    padding: 0 14px;
    text-align: left;
    background: transparent;
    border: 0;
    color: {t.TEXT_SECONDARY};
}}
QPushButton#sidebarAction:hover {{
    background: {t.SURFACE_HOVER};
    color: {t.TEXT_PRIMARY};
}}
QPushButton#sidebarAction:pressed {{
{button_pressed_style}
    color: {t.TEXT_PRIMARY};
}}
QPushButton#navButton[compactSidebar="true"], QPushButton#sidebarAction[compactSidebar="true"] {{
    padding: 0;
    text-align: center;
}}
QPushButton#toolButton {{
    min-width: 34px;
    max-width: 34px;
    padding: 0;
}}
QPushButton#statusActionButton {{
    min-width: 28px;
    max-width: 28px;
    min-height: 24px;
    max-height: 24px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_MUTED};
}}
QPushButton#statusActionButton:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
}}
QPushButton#statusActionButton:pressed {{
    background: {t.SURFACE};
    border-color: {t.BORDER_STRONG};
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    min-height: {t.CONTROL_HEIGHT}px;
    padding: 0 10px;
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_SMALL}px;
    selection-background-color: {t.ACCENT};
    selection-color: {t.ACCENT_FOREGROUND};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
    border-color: {t.ACCENT};
}}
QComboBox::drop-down {{
    border: 0;
    width: 26px;
}}
QComboBox QAbstractItemView {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.CHROME_BORDER};
    selection-background-color: {t.SURFACE_HOVER};
    selection-color: {t.TEXT_PRIMARY};
    outline: 0;
}}
QAbstractItemView {{
    background: {t.BACKGROUND};
    alternate-background-color: {t.SURFACE};
    border: 0;
    outline: 0;
    selection-background-color: {t.ACCENT_SOFT};
    selection-color: {t.TEXT_PRIMARY};
}}
QListView {{
    padding: 4px;
}}
QTableView {{
    gridline-color: {t.BORDER};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QHeaderView::section {{
    background: {t.SURFACE};
    color: {t.TEXT_SECONDARY};
    padding: 8px;
    border: 0;
    border-right: 1px solid {t.BORDER};
    border-bottom: 1px solid {t.BORDER};
}}
QMenu {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.CHROME_BORDER};
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 28px 7px 10px;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_SECONDARY};
}}
QMenu::item:selected {{
    background: {t.SURFACE_HOVER};
    color: {t.TEXT_PRIMARY};
}}
QMenu::separator {{
    height: 1px;
    background: {t.CHROME_BORDER};
    margin: 5px 8px;
}}
QWidget#movieArchivePage, QWidget#movieArchiveContent {{
    background: transparent;
}}
QPushButton#movieArchiveBackButton {{
    min-width: 38px;
    max-width: 38px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    background: transparent;
    color: {t.TEXT_SECONDARY};
    font-size: 20px;
}}
QPushButton#movieArchiveBackButton:hover {{
    background: {t.SURFACE_HOVER};
    color: {t.TEXT_PRIMARY};
    border-color: {t.BORDER};
}}
QFrame#movieArchiveHero, QFrame#movieArchiveCard {{
    background: {t.SURFACE};
    border: 1px solid {t.CHROME_BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QLabel#movieArchiveCover {{
    background: transparent;
    border: 0;
    color: {t.TEXT_MUTED};
}}
QLabel#movieArchiveTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 25px;
    font-weight: 700;
}}
QLabel#movieArchiveMeta {{
    color: {t.TEXT_SECONDARY};
    font-size: 13px;
}}
QLabel#movieArchiveStat {{
    color: {t.ACCENT_SOFT_TEXT};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#movieArchiveSectionTitle {{
    color: {t.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#movieArchiveBodyText, QLabel#movieArchiveValue {{
    color: {t.TEXT_SECONDARY};
}}
QLabel#movieArchiveTitle, QLabel#movieArchiveMeta, QLabel#movieArchiveEditableValue, QLabel#gameArchiveEditableValue {{
    border: 0;
    border-bottom: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    padding: 2px 4px;
}}
QLabel#movieArchiveTitle:hover, QLabel#movieArchiveMeta:hover, QLabel#movieArchiveEditableValue:hover, QLabel#gameArchiveEditableValue:hover {{
    background: {t.SURFACE_HOVER};
    border-bottom: 1px solid {t.BORDER};
    color: {t.TEXT_PRIMARY};
}}
QLabel#movieArchiveMutedText, QLabel#movieArchivePath {{
    color: {t.TEXT_MUTED};
}}
QLineEdit#movieArchiveInlineEdit, QLineEdit#gameArchiveInlineEdit {{
    min-height: 26px;
    padding: 1px 4px;
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.BORDER};
    border-radius: 0;
    color: {t.TEXT_SECONDARY};
}}
QLineEdit#movieArchiveInlineEdit:hover, QLineEdit#gameArchiveInlineEdit:hover {{
    border-bottom: 1px solid {t.BORDER_STRONG};
}}
QLineEdit#movieArchiveInlineEdit:focus, QLineEdit#gameArchiveInlineEdit:focus {{
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.ACCENT};
    color: {t.TEXT_PRIMARY};
}}
QLineEdit#movieArchiveTitleEdit, QLineEdit#gameArchiveTitleEdit {{
    min-height: 38px;
    padding: 0 4px;
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.BORDER};
    border-radius: 0;
    color: {t.TEXT_PRIMARY};
    font-size: 25px;
    font-weight: 700;
}}
QLineEdit#movieArchiveTitleEdit:hover, QLineEdit#gameArchiveTitleEdit:hover {{
    border-bottom: 1px solid {t.BORDER_STRONG};
}}
QLineEdit#movieArchiveTitleEdit:focus, QLineEdit#gameArchiveTitleEdit:focus {{
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.ACCENT};
}}
QPushButton#movieArchiveStarButton {{
    min-width: 27px;
    max-width: 27px;
    min-height: 27px;
    max-height: 27px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.ACCENT_SOFT_TEXT};
    font-size: 19px;
}}
QPushButton#movieArchiveStarButton:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
}}
QTextEdit#movieArchiveNotesEdit, QTextEdit#gameArchiveNotesEdit {{
    min-height: 92px;
    padding: 8px 4px;
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.CHROME_BORDER};
    border-radius: 0;
    color: {t.TEXT_SECONDARY};
}}
QTextEdit#movieArchiveNotesEdit:hover, QTextEdit#gameArchiveNotesEdit:hover {{
    border-bottom: 1px solid {t.BORDER};
}}
QTextEdit#movieArchiveNotesEdit:focus, QTextEdit#gameArchiveNotesEdit:focus {{
    background: transparent;
    border: 0;
    border-bottom: 1px solid {t.ACCENT};
    color: {t.TEXT_PRIMARY};
}}
QScrollArea#movieArchiveScroll {{
    background: transparent;
    border: 0;
}}
QWidget#gameArchivePage {{
    background: transparent;
}}
QPushButton#gameArchiveBackButton {{
    min-width: 40px;
    max-width: 40px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    color: {t.TEXT_SECONDARY};
    font-size: 22px;
    font-weight: 500;
}}
QPushButton#gameArchiveBackButton:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
    color: {t.TEXT_PRIMARY};
}}
QWidget#gameArchiveHero {{
    background: {t.SURFACE};
    border: 0;
    border-radius: {t.RADIUS_LARGE}px;
}}
QLabel#gameArchiveTitle {{
    color: {t.TEXT_PRIMARY};
    font-size: 28px;
    font-weight: 750;
}}
QLabel#gameArchiveHeroMeta {{
    color: {t.TEXT_SECONDARY};
    font-size: 13px;
}}
QLabel#gameArchiveStat {{
    color: {t.TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 600;
}}
QFrame#gameArchiveCard {{
    background: {t.SURFACE};
    border: 1px solid {t.CHROME_BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
}}
QLabel#gameArchiveSectionTitle {{
    color: {t.TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
}}
QLabel#gameArchiveBodyText, QLabel#gameArchiveValue {{
    color: {t.TEXT_SECONDARY};
}}
QLabel#gameArchiveMutedText {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
}}
QListWidget#gameArchiveMediaList {{
    background: transparent;
    border: 0;
    padding: 0;
}}
QListWidget#gameArchiveMediaList::item {{
    color: {t.TEXT_SECONDARY};
    border: 1px solid transparent;
    border-radius: {t.RADIUS_SMALL}px;
    padding: 4px;
}}
QListWidget#gameArchiveMediaList::item:hover {{
    background: {t.SURFACE_HOVER};
    border-color: {t.BORDER};
}}
QListWidget#gameArchiveMediaList::item:selected {{
    background: {t.ACCENT_SOFT};
    border-color: {t.BORDER_STRONG};
    color: {t.TEXT_PRIMARY};
}}
QScrollArea#gameArchiveScroll {{
    background: transparent;
    border: 0;
}}
QWidget#contentStatusBar {{
    min-height: 28px;
    max-height: 28px;
    background: transparent;
    border-top: 1px solid {t.CHROME_BORDER};
}}
QLabel#contentStatusIcon {{
    min-width: 18px;
    max-width: 18px;
}}
QLabel#contentStatusText, QLabel#contentStatusActiveGame {{
    color: {t.TEXT_MUTED};
    font-size: 11px;
}}
QStatusBar {{
    background: {t.SURFACE};
    color: {t.TEXT_SECONDARY};
    border-top: 1px solid {t.BORDER};
}}
QStatusBar::item {{
    border: 0;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    margin: 2px 1px;
}}
QScrollBar::handle:vertical {{
    background: {t.BORDER};
    min-height: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.BORDER_STRONG};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}
QGroupBox {{
    margin-top: 12px;
    padding-top: 10px;
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: {t.TEXT_SECONDARY};
}}
QTextEdit, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_SMALL}px;
    selection-background-color: {t.ACCENT};
    selection-color: {t.ACCENT_FOREGROUND};
}}
QTabWidget::pane {{
    border: 1px solid {t.BORDER};
    border-radius: {t.RADIUS_MEDIUM}px;
    background: {t.SURFACE};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {t.TEXT_SECONDARY};
    padding: 8px 14px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{
    color: {t.TEXT_PRIMARY};
}}
QTabBar::tab:selected {{
    color: {t.TEXT_PRIMARY};
    border-bottom-color: {t.ACCENT};
}}
QCheckBox, QRadioButton {{
    spacing: 7px;
    color: {t.TEXT_PRIMARY};
}}
QProgressBar {{
    background: {t.SURFACE_RAISED};
    border: 1px solid {t.BORDER};
    border-radius: 5px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {t.ACCENT};
    border-radius: 4px;
}}
QToolTip {{
    background: {t.SURFACE_RAISED};
    color: {t.TEXT_PRIMARY};
    border: 1px solid {t.BORDER};
    padding: 5px 7px;
}}
"""


def apply_theme(app: QApplication, theme_id: str) -> str:
    resolved_id = activate_theme(theme_id)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(FlatTokens.BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(FlatTokens.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(FlatTokens.SURFACE_RAISED))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(FlatTokens.SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(FlatTokens.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(FlatTokens.SURFACE_RAISED))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(FlatTokens.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(FlatTokens.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(FlatTokens.ACCENT_FOREGROUND))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(FlatTokens.TEXT_MUTED))
    app.setPalette(palette)
    app.setStyleSheet(build_flat_stylesheet())
    return resolved_id


def apply_flat_theme(app: QApplication) -> None:
    """Backward-compatible alias for tests/local integrations using the first Flat preview."""
    apply_theme(app, DEFAULT_THEME_ID)
