from __future__ import annotations

import faulthandler
import importlib.util
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "retro-smoke-local"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
RUN_DIR = ARTIFACT_ROOT / STAMP
LATEST_LOG = ARTIFACT_ROOT / "latest.log"


def _ensure_project_root_on_sys_path() -> None:
    """Make repository imports work when launched as tools\retro_smoke_runner.py."""
    root = str(ROOT)
    if not sys.path or sys.path[0] != root:
        try:
            sys.path.remove(root)
        except ValueError:
            pass
        sys.path.insert(0, root)


class Tee:
    def __init__(self, *streams) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def _load_smoke_module():
    smoke_path = ROOT / "tests" / "test_retro_gui_smoke.py"
    spec = importlib.util.spec_from_file_location("retro_gui_smoke_local", smoke_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load smoke module: {smoke_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    os.chdir(ROOT)
    _ensure_project_root_on_sys_path()
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")
    os.environ["RETRO_SMOKE_ARTIFACT_DIR"] = str(RUN_DIR)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    with LATEST_LOG.open("w", encoding="utf-8", errors="replace") as log:
        sys.stdout = Tee(original_stdout, log)
        sys.stderr = Tee(original_stderr, log)
        try:
            faulthandler.enable(file=original_stderr, all_threads=True)
            print("=== Retro Local GUI Smoke ===")
            print(f"Root: {ROOT}")
            print(f"Artifacts: {RUN_DIR}")
            print(f"Python: {sys.version.split()[0]}")

            try:
                from PySide6.QtCore import qVersion
                from PySide6.QtWidgets import QApplication
            except Exception:
                print("[FAIL] PySide6 could not be imported from this Python environment.")
                traceback.print_exc()
                return 2

            smoke = _load_smoke_module()
            app = smoke.get_app()
            print(f"PySide6 / Qt: {qVersion()}")
            print(f"Qt platform: {QApplication.platformName()}")
            if sys.platform == "win32" and QApplication.platformName().lower() != "windows":
                print("[WARN] Native Windows Qt platform is not active; check QT_QPA_PLATFORM.")

            checks = [
                (
                    "draw pipeline: browse/focus/MORE/system/chrome",
                    smoke.test_scene_draw_pipeline_exercises_focus_details_and_chrome,
                ),
                (
                    "native widget resize/repaint",
                    smoke.test_real_widget_resize_and_repaint_does_not_route_python_exceptions,
                ),
                (
                    "archive edit dialogs",
                    smoke.test_archive_edit_dialogs_build_scroll_and_metadata_patches,
                ),
                (
                    "minimum window / long focus title",
                    smoke.test_minimum_window_and_long_focus_title_layout,
                ),
                (
                    "clean background base",
                    smoke.test_background_base_is_horizontally_uniform_without_waves,
                ),
                (
                    "ambient symbols behind showcase",
                    smoke.test_ambient_symbols_render_behind_showcase_without_breaking_scene,
                ),
                (
                    "idle ambient timer budget",
                    smoke.test_idle_ambient_refresh_budget_stays_near_15fps,
                ),
                (
                    "scene search / settings / font",
                    smoke.test_scene_search_settings_and_font_controls,
                ),
                (
                    "sound packs / mapping / semantic events",
                    smoke.test_scene_sound_settings_and_semantic_events_are_safe,
                ),
                (
                    "showcase 4-up / click / hover / wrap",
                    smoke.test_showcase_four_item_click_hover_and_wrap,
                ),
            ]

            failures = 0
            for name, check in checks:
                print(f"\n[RUN ] {name}")
                try:
                    check()
                except BaseException:
                    failures += 1
                    print(f"[FAIL] {name}")
                    traceback.print_exc()
                else:
                    print(f"[PASS] {name}")
                app.processEvents()

            print("\n=== Result ===")
            if failures:
                print(f"FAIL ({failures}/{len(checks)} checks failed)")
                print(f"Log: {LATEST_LOG}")
                return 1

            print(f"PASS ({len(checks)}/{len(checks)} checks passed)")
            print(f"Log: {LATEST_LOG}")
            print(f"Screenshots: {RUN_DIR}")
            return 0
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


if __name__ == "__main__":
    raise SystemExit(main())
