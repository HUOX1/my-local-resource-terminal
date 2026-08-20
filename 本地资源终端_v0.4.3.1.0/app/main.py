from __future__ import annotations

from app.bootstrap import build_application
from app.restart import restart_application


def main() -> int:
    app = build_application()
    if getattr(app, "_local_movie_manager_secondary_instance", False):
        return 0
    exit_code = app.exec()
    if getattr(app, "_local_movie_manager_restart_requested", False):
        single_instance_gate = getattr(app, "_local_movie_manager_single_instance_gate", None)
        if single_instance_gate is not None:
            single_instance_gate.release()
        restart_application()
        return 0
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
