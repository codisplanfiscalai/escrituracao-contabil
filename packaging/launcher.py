"""Packaging entry point for the SAME local application, without extra routes."""
from pathlib import Path
import os
import signal
import sys

# Direct source execution and PyInstaller analysis both resolve the project.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import local_app


def main():
    if getattr(sys, "frozen", False):
        # The unpacked resources and the installed executable are separate paths.
        # Keep private SQLite outside the whole installed application directory.
        local_app.PROJECT_ROOT = Path(sys.executable).resolve().parent
    args = sys.argv[1:]
    if os.name == "nt" and not any(arg == "--database" or arg.startswith("--database=") for arg in args):
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        args = ["--database", str(root / "EscrituracaoContabil" / "accounting.sqlite3"), *args]

    def stop(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, stop)
    local_app.main(args)


if __name__ == "__main__":
    main()
