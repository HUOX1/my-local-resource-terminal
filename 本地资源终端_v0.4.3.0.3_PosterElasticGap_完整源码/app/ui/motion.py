from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QTimer,
    Qt,
    QVariantAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QMenu, QStackedWidget, QWidget

from app.ui.flat_theme import FlatTokens


ARCHIVE_TRANSITION_MS = 150
ARCHIVE_SLIDE_PX = 12
MOTION_FAST_MS = 110
MOTION_DETAIL_MS = 180
RESPONSIVE_REFLOW_MS = 190
RESPONSIVE_REFLOW_SLIDE_PX = 7
POPUP_SLIDE_PX = 6


def motion_level() -> str:
    return str(getattr(FlatTokens, "MOTION_LEVEL", "off") or "off")


def motion_enabled() -> bool:
    return motion_level() != "off"


def transition_stack_page(
    stack: QStackedWidget,
    target: QWidget,
    *,
    direction: int = 1,
    duration_ms: int | None = None,
    slide_px: int | None = None,
) -> None:
    """Switch a stack page with Flat Pro's short fade/slide transition.

    Re-selecting the already-visible page is intentionally a no-op so metadata
    refreshes do not replay the entrance animation.  An interrupted previous
    transition is fully cleaned before the next one starts.
    """
    if stack.currentWidget() is target:
        return

    previous_cleanup = getattr(stack, "_flat_pro_transition_cleanup", None)
    if callable(previous_cleanup):
        previous_cleanup()

    stack.setCurrentWidget(target)
    if not motion_enabled():
        return

    effect = QGraphicsOpacityEffect(target)
    effect.setOpacity(0.0)
    target.setGraphicsEffect(effect)

    level = motion_level()
    duration = int(duration_ms or (ARCHIVE_TRANSITION_MS if level == "full" else 110))
    distance = ARCHIVE_SLIDE_PX if slide_px is None else int(slide_px)
    if level != "full":
        distance = 0
    base_pos = target.pos()

    group = QParallelAnimationGroup(stack)
    fade = QPropertyAnimation(effect, b"opacity", group)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade)

    slide = QVariantAnimation(group)
    slide.setDuration(duration)
    sign = 1 if direction >= 0 else -1
    slide.setStartValue(float(distance * sign))
    slide.setEndValue(0.0)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)
    slide.valueChanged.connect(
        lambda value, widget=target, origin=base_pos: widget.move(origin.x() + round(float(value)), origin.y())
    )
    group.addAnimation(slide)

    cleaned = False

    def _cleanup() -> None:
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        group.stop()
        target.move(base_pos)
        if target.graphicsEffect() is effect:
            target.setGraphicsEffect(None)
        if getattr(stack, "_flat_pro_transition_group", None) is group:
            stack._flat_pro_transition_group = None
        if getattr(stack, "_flat_pro_transition_cleanup", None) is _cleanup:
            stack._flat_pro_transition_cleanup = None
        group.deleteLater()

    group.finished.connect(_cleanup)
    stack._flat_pro_transition_group = group
    stack._flat_pro_transition_cleanup = _cleanup
    group.start()


def animate_responsive_reflow(
    viewport: QWidget,
    apply_change: Callable[[], None],
    *,
    direction: int = 1,
) -> None:
    """Mask a responsive layout breakpoint with a short old-state cross-fade.

    The layout is allowed to own final geometry.  Motion is applied to a visual
    snapshot of the old state, so QLayout and QPropertyAnimation never fight
    over child geometry while a window is being resized.
    """
    previous_cleanup = getattr(viewport, "_flat_pro_reflow_cleanup", None)
    if callable(previous_cleanup):
        previous_cleanup()

    if not motion_enabled() or not viewport.isVisible() or viewport.width() <= 0 or viewport.height() <= 0:
        apply_change()
        return

    snapshot = viewport.grab()
    apply_change()
    if snapshot.isNull():
        return

    overlay = QLabel(viewport)
    overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    overlay.setScaledContents(True)
    overlay.setPixmap(snapshot)
    overlay.setGeometry(viewport.rect())
    overlay.show()
    overlay.raise_()

    effect = QGraphicsOpacityEffect(overlay)
    effect.setOpacity(1.0)
    overlay.setGraphicsEffect(effect)

    group = QParallelAnimationGroup(viewport)
    fade = QPropertyAnimation(effect, b"opacity", group)
    fade.setDuration(RESPONSIVE_REFLOW_MS)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade)

    slide = QPropertyAnimation(overlay, b"pos", group)
    slide.setDuration(RESPONSIVE_REFLOW_MS)
    slide.setStartValue(QPoint(0, 0))
    slide.setEndValue(QPoint(-RESPONSIVE_REFLOW_SLIDE_PX if direction >= 0 else RESPONSIVE_REFLOW_SLIDE_PX, 0))
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(slide)

    cleaned = False

    def _cleanup() -> None:
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        group.stop()
        if getattr(viewport, "_flat_pro_reflow_cleanup", None) is _cleanup:
            viewport._flat_pro_reflow_cleanup = None
        overlay.deleteLater()
        group.deleteLater()

    group.finished.connect(_cleanup)
    viewport._flat_pro_reflow_cleanup = _cleanup
    group.start()


def show_popup_with_motion(widget: QWidget, target_pos: QPoint) -> None:
    """Show a lightweight popup with the shared Pro fade + rise motion."""
    previous_cleanup = getattr(widget, "_flat_pro_popup_cleanup", None)
    if callable(previous_cleanup):
        previous_cleanup()

    widget.move(target_pos)
    if not motion_enabled():
        widget.show()
        widget.raise_()
        return

    widget.setWindowOpacity(0.0)
    widget.move(target_pos + QPoint(0, POPUP_SLIDE_PX))
    widget.show()
    widget.raise_()

    group = QParallelAnimationGroup(widget)
    fade = QPropertyAnimation(widget, b"windowOpacity", group)
    fade.setDuration(MOTION_FAST_MS)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade)

    slide = QPropertyAnimation(widget, b"pos", group)
    slide.setDuration(MOTION_FAST_MS)
    slide.setStartValue(target_pos + QPoint(0, POPUP_SLIDE_PX))
    slide.setEndValue(target_pos)
    slide.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(slide)

    cleaned = False

    def _cleanup() -> None:
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        group.stop()
        widget.setWindowOpacity(1.0)
        widget.move(target_pos)
        if getattr(widget, "_flat_pro_popup_cleanup", None) is _cleanup:
            widget._flat_pro_popup_cleanup = None
        group.deleteLater()

    group.finished.connect(_cleanup)
    widget._flat_pro_popup_cleanup = _cleanup
    group.start()


def exec_menu_with_motion(menu: QMenu, global_pos: QPoint) -> None:
    """Execute a QMenu while its nested event loop drives a short Pro entrance."""
    if not motion_enabled():
        menu.exec(global_pos)
        return

    menu.setWindowOpacity(0.0)

    def _start() -> None:
        if not menu.isVisible():
            return
        target = menu.pos()
        group = QParallelAnimationGroup(menu)
        fade = QPropertyAnimation(menu, b"windowOpacity", group)
        fade.setDuration(MOTION_FAST_MS)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(fade)

        slide = QPropertyAnimation(menu, b"pos", group)
        slide.setDuration(MOTION_FAST_MS)
        slide.setStartValue(target + QPoint(0, POPUP_SLIDE_PX))
        slide.setEndValue(target)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(slide)
        menu.move(target + QPoint(0, POPUP_SLIDE_PX))
        menu._flat_pro_menu_group = group
        group.start()

    QTimer.singleShot(0, _start)
    menu.exec(global_pos)
    menu.setWindowOpacity(1.0)


def pulse_opacity(widget: QWidget, *, start: float = 0.58) -> None:
    """Give compact controls a restrained shared response without changing geometry."""
    if not motion_enabled():
        return

    previous = getattr(widget, "_flat_pro_pulse_animation", None)
    if previous is not None:
        previous.stop()

    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(float(start))

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(MOTION_FAST_MS)
    animation.setStartValue(float(start))
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _done() -> None:
        effect.setOpacity(1.0)
        widget._flat_pro_pulse_animation = None
        animation.deleteLater()

    animation.finished.connect(_done)
    widget._flat_pro_pulse_animation = animation
    animation.start()
