"""
Модель элемента очереди загрузки. Чисто данные — без виджетов tkinter,
чтобы можно было тестировать и сериализовать независимо от GUI.
"""

import uuid

VALID_MODES = ("video", "audio", "video_only")
VALID_CONTAINERS = ("mp4", "mkv", "webm")

STATUS_PENDING = "pending"
STATUS_DOWNLOADING = "downloading"
STATUS_DONE = "done"
STATUS_ERROR = "error"
STATUS_CANCELLED = "cancelled"

MODE_LABELS = {
    "video": "Видео+Аудио",
    "audio": "Аудио (MP3)",
    "video_only": "Видео без звука",
}

STATUS_COLORS = {
    STATUS_PENDING: "#636e72",
    STATUS_DOWNLOADING: "#1a6fc4",
    STATUS_DONE: "#27ae60",
    STATUS_ERROR: "#e74c3c",
    STATUS_CANCELLED: "#e6a817",
}

STATUS_LABELS = {
    STATUS_PENDING: "В очереди",
    STATUS_DOWNLOADING: "Загрузка…",
    STATUS_DONE: "Готово",
    STATUS_ERROR: "Ошибка",
    STATUS_CANCELLED: "Отменено",
}


def make_item(url: str, mode: str, quality: str, save_path: str,
             container: str = "mp4", playlist: bool = False,
             title: str = "") -> dict:
    if mode not in VALID_MODES:
        raise ValueError(f"Недопустимый режим: {mode}")
    if container not in VALID_CONTAINERS:
        container = "mp4"

    return {
        "id": uuid.uuid4().hex[:8],
        "url": url,
        "title": title or "",
        "mode": mode,
        "quality": quality,
        "save_path": save_path,
        "container": container,
        "playlist": bool(playlist),   # скачивать как плейлист целиком
        "status": STATUS_PENDING,
        "error": None,
        "final_path": None,           # путь к готовому файлу/папке для "Открыть папку"
        "_partial_path": None,         # путь к частичному файлу во время загрузки
        "_cancel_flag": {"cancelled": False},  # мутабельный объект для остановки из др. потока
    }


def item_to_dict_for_save(item: dict) -> dict:
    """Сериализуемая часть item (без виджетов/runtime-объектов) — для config.json."""
    return {
        "url": item["url"],
        "title": item.get("title", ""),
        "mode": item["mode"],
        "quality": item["quality"],
        "save_path": item["save_path"],
        "container": item.get("container", "mp4"),
        "playlist": item.get("playlist", False),
    }


def item_from_saved_dict(entry: dict) -> dict | None:
    """Восстановить item из сохранённого словаря. None если данные битые."""
    try:
        return make_item(
            entry["url"], entry["mode"], entry["quality"],
            entry["save_path"], entry.get("container", "mp4"),
            entry.get("playlist", False),
            title=entry.get("title", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None