from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "MinaDosEscravosEternos"
SAVE_FILE_NAME = "save_eternal_mine.json"


def _user_data_root() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base)

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home)

    return Path.home() / ".local" / "share"


def get_app_data_dir() -> Path:
    app_dir = _user_data_root() / APP_DIR_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_save_path() -> Path:
    return get_app_data_dir() / SAVE_FILE_NAME


def get_legacy_save_path(base_dir: str | Path | None = None) -> Path:
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    return base / SAVE_FILE_NAME
