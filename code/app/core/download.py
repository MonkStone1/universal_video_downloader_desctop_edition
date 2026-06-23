"""
Запуск скачивания одного элемента очереди.
"""

import os

import yt_dlp
import yt_dlp.utils

from app.core.formats import build_format_string, QUALITY_HEIGHTS
from app.core.metadata import check_disk_space, get_free_space


DISK_SPACE_SAFETY_MARGIN = 1.3


def _guess_extension(item: dict) -> str:
    """Определяем ожидаемое расширение файла."""
    mode = item.get("mode", "video")
    if mode == "audio":
        return "mp3"
    return item.get("container", "mp4")


def make_unique_outtmpl_if_needed(item: dict, base_template: str) -> str:
    """Если файл уже существует, возвращает уникальный путь с суффиксом."""
    title = item.get("title", "")
    if not title:
        return base_template

    save_path = item["save_path"]
    expected_ext = _guess_extension(item)

    import re as _re
    safe = _re.sub(r'[<>:"/\\|?*]', '', title)
    safe = _re.sub(r'\s+', ' ', safe).strip().rstrip('. ')
    safe = safe[:200]
    if not safe:
        return base_template

    counter = 1
    while counter <= 999:
        if counter == 1:
            candidate = os.path.join(save_path, f"{safe}.{expected_ext}")
        else:
            candidate = os.path.join(save_path, f"{safe} ({counter}).{expected_ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1

    return base_template


def get_ydl_options(item: dict, hooks: list, unique_template: str | None = None) -> dict:
    is_playlist = item.get("playlist", False)

    if is_playlist:
        template = os.path.join(
            item["save_path"],
            "%(playlist_title|Playlist).100s",
            "%(playlist_index)03d - %(title).150s.%(ext)s",
        )
    else:
        template = unique_template or os.path.join(item["save_path"], "%(title).200s.%(ext)s")

    fmt = build_format_string(item["mode"], item["quality"])

    opts = {
        "format": fmt,
        "outtmpl": template,
        "progress_hooks": hooks,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not is_playlist,
        "ignoreerrors": "only_download" if is_playlist else False,
        "retries": 3,
        "nooverwrites": True,
    }

    if item["mode"] == "audio":
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        opts["merge_output_format"] = item.get("container", "mp4")

    return opts


class _ProgressHook:
    """Адаптер для передачи внешнего progress_hook в yt-dlp."""

    def __init__(self, hook):
        self._hook = hook

    def __call__(self, d):
        return self._hook(d)


def download_one(item: dict, progress_hook) -> tuple[bool, str, str]:
    """
    Скачивает один элемент очереди.
    Возвращает (успех, текст_ошибки_или_пусто, путь_к_финальному_файлу_или_папке).
    """
    try:
        os.makedirs(item["save_path"], exist_ok=True)
    except OSError as e:
        return False, f"Не удалось создать папку '{item['save_path']}': {e}", ""

    try:
        files_before = set(os.listdir(item["save_path"]))
    except OSError:
        files_before = set()

    unique_template = None
    if not item.get("playlist", False):
        base_template = os.path.join(item["save_path"], "%(title).200s.%(ext)s")
        unique_template = make_unique_outtmpl_if_needed(item, base_template)

    opts = get_ydl_options(item, [_ProgressHook(progress_hook)], unique_template)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ret_code = ydl.download([item["url"]])
    except yt_dlp.utils.DownloadCancelled:
        return False, "Отменено пользователем", ""
    except yt_dlp.utils.DownloadError as e:
        if item["_cancel_flag"].get("cancelled"):
            return False, "Отменено пользователем", ""
        return False, str(e), ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", ""

    if ret_code != 0:
        return False, "yt-dlp вернул код ошибки (загрузка не завершена)", ""

    try:
        files_after = set(os.listdir(item["save_path"]))
    except OSError:
        files_after = set()

    new_files = [
        os.path.join(item["save_path"], f)
        for f in (files_after - files_before)
        if not f.endswith(".part") and not f.endswith(".ytdl") and not f.startswith(".")
    ]
    new_files = [f for f in new_files if os.path.exists(f) and os.path.getsize(f) > 0]

    if item.get("playlist"):
        if new_files:
            return True, "", item["save_path"]
        return False, "Не удалось скачать ни одного видео из плейлиста", ""

    if not new_files:
        try:
            all_files = [
                os.path.join(item["save_path"], f)
                for f in os.listdir(item["save_path"])
                if not f.endswith(".part") and not f.endswith(".ytdl") and not f.startswith(".")
            ]
            all_files = [f for f in all_files if os.path.exists(f) and os.path.getsize(f) > 0]
            if all_files:
                newest = max(all_files, key=os.path.getmtime)
                return True, "", newest
        except OSError:
            pass
        return False, "Файл не появился в папке после загрузки", ""

    final = max(new_files, key=os.path.getsize)
    return True, "", final
