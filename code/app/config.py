"""
Хранение настроек между запусками: последняя папка, тема, параллельность,
незавершённая очередь и т.д.
"""

import json
import os
import sys


def config_dir() -> str:
    """
    Папка для config.json.
    %APPDATA%/VideoDownloader на Windows (стандартное место для
    пользовательских настроек), либо ~/.config/video-downloader на
    других ОС. Так настройки переживают обновление/перемещение exe и
    не требуют прав на запись рядом с программой (Program Files
    обычно доступен только на чтение для обычного пользователя).
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "VideoDownloader")
    return os.path.join(os.path.expanduser("~"), ".config", "video-downloader")


CONFIG_PATH = os.path.join(config_dir(), "config.json")

DEFAULT_CONFIG = {
    "last_save_path": os.path.join(os.path.expanduser("~"), "Videos"),
    "container_format": "mp4",     # mp4 | mkv | webm
    "dark_theme": False,
    "max_parallel": 2,
    "saved_queue": [],             # незавершённые элементы очереди при последнем закрытии
    "last_update_check": None,     # ISO timestamp последней проверки обновлений yt-dlp
    "language": None,              # ru | en | None (None = авто по языку ОС)
}


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # подстраховка на случай повреждённого/неполного файла
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data if isinstance(data, dict) else {})
        return cfg
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> bool:
    try:
        os.makedirs(config_dir(), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        # Не критично — просто не сохранится между запусками,
        # программа не должна падать из-за этого
        return False
