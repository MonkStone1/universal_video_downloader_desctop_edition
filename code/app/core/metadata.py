"""
Валидация ссылок, проверка поддерживаемых хостов, оценка размера файла.
"""

import os
import shutil

import yt_dlp

_extractor_cache = None


def _get_extractors():
    global _extractor_cache
    if _extractor_cache is None:
        _extractor_cache = list(yt_dlp.extractor.gen_extractors())
    return _extractor_cache


def validate_url_syntax(url: str) -> tuple[bool, str]:
    """Базовая синтаксическая проверка без сетевых запросов."""
    url = url.strip()
    if not url:
        return False, "Ссылка пуста"
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "Ссылка должна начинаться с http:// или https://"

    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
    except ValueError:
        return False, "Некорректный формат ссылки"

    if not parsed.netloc:
        return False, "В ссылке отсутствует домен (хост)"
    hostname = parsed.hostname or ""
    if "." not in hostname and hostname != "localhost":
        return False, "Домен в ссылке выглядит некорректно"

    return True, ""


def check_host_supported(url: str) -> tuple[bool, str, str]:
    """
    Проверяет, какой экстрактор yt-dlp подходит для ссылки — без сетевого
    запроса (только сопоставление по паттерну URL).
    """
    ok, err = validate_url_syntax(url)
    if not ok:
        return False, "", err

    try:
        extractors = _get_extractors()
    except Exception:
        return True, "", "Не удалось проверить поддержку сайта"

    for ie in extractors:
        name = getattr(ie, "IE_NAME", type(ie).__name__)
        if name == "generic":
            continue
        try:
            if ie.suitable(url):
                return True, name, ""
        except Exception:
            continue

    try:
        for ie in extractors:
            name = getattr(ie, "IE_NAME", type(ie).__name__)
            if name == "generic" and ie.suitable(url):
                return True, name, (
                    "Сайт не входит в список специально поддерживаемых "
                    "yt-dlp — скачивание может не сработать"
                )
    except Exception:
        pass

    return True, "", "Не удалось точно определить сайт"


def get_free_space(path: str) -> int | None:
    """Свободное место в байтах для диска, на котором лежит path."""
    try:
        check_path = path
        while check_path and not os.path.exists(check_path):
            parent = os.path.dirname(check_path.rstrip("/\\"))
            if parent == check_path:
                break
            check_path = parent
        if not check_path or not os.path.exists(check_path):
            return None
        return shutil.disk_usage(check_path).free
    except OSError:
        return None


def estimate_download_size(url: str, fmt: str) -> int | None:
    """Примерный размер файла по метаданным yt-dlp (без скачивания)."""
    try:
        opts = {
            "quiet": True, "no_warnings": True, "skip_download": True,
            "noplaylist": True, "format": fmt,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            return None

        requested = info.get("requested_formats")
        if requested:
            total = 0
            for f in requested:
                size = f.get("filesize") or f.get("filesize_approx")
                if size:
                    total += size
                else:
                    return None
            return total

        return info.get("filesize") or info.get("filesize_approx")
    except Exception:
        return None


def check_disk_space(save_path: str, required_bytes: int | None) -> tuple[bool, str]:
    """Проверяет, достаточно ли места на диске."""
    if required_bytes is None:
        return True, ""

    free = get_free_space(save_path)
    if free is None:
        return True, ""

    from app.core.formats import DISK_SPACE_SAFETY_MARGIN
    needed = required_bytes * DISK_SPACE_SAFETY_MARGIN
    if free < needed:
        free_mb = free / 1_048_576
        needed_mb = needed / 1_048_576
        return False, (
            f"Недостаточно места на диске: доступно {free_mb:.0f} МБ, "
            f"требуется примерно {needed_mb:.0f} МБ"
        )
    return True, ""
