from __future__ import annotations

from .logging_setup import configure_logging
from .paths import TerminalPaths
from .settings import TerminalSettings


def main() -> int:
    paths = TerminalPaths.from_environment().ensure()
    configure_logging(paths.logs)
    settings = TerminalSettings.load(paths.settings)
    if not paths.settings.exists():
        settings.save(paths.settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
