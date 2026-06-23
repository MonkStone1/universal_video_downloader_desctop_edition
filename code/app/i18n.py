"""
Система локализации. Поддерживаемые языки: русский (ru), английский (en).
Автовыбор по языку ОС, fallback на английский.
"""

import locale
import os
import sys

SUPPORTED_LANGS = ("ru", "en")

_DEFAULT_LANG = "en"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        # Общие
        "app_title": "Загрузчик видео / аудио",
        "ok": "OK",
        "cancel": "Отмена",
        "error": "Ошибка",
        "settings": "Настройки",
        "language": "Язык",
        "language_changed": "Язык изменён. Изменения вступят в силу при следующем запуске.",
        # Окно настроек
        "settings_window_title": "Настройки программы",
        "appearance": "Внешний вид",
        "dark_theme": "Тёмная тема (применяется при следующем запуске)",
        "performance": "Производительность",
        "parallel_downloads": "Одновременных загрузок:",
        "update_ytdlp": "Обновление yt-dlp",
        "current_version": "Текущая версия: {}",
        "check_updates": "Проверить обновления",
        "update": "Обновить",
        "theme_changed": "Новая тема будет применена при следующем запуске программы.",
        # Левая колонка
        "url_label": "Ссылка на видео:",
        "paste": "Вставить",
        "check_link": "🔍 Проверить ссылку",
        "checking": "Проверка…",
        "hint_text": (
            "Вставьте ссылку и нажмите\n"
            "«Проверить ссылку», чтобы\n"
            "выбрать качество, формат и папку."
        ),
        "drag_drop_unavailable": (
            "Перетаскивание ссылок недоступно — нет пакета tkinterdnd2"
        ),
        "mode": "Режим",
        "mode_frame": " Режим ",
        "video_audio": "Видео + Аудио",
        "audio_only": "Только Аудио (MP3)",
        "video_only": "Только Видео (без звука)",
        "quality": "Качество:",
        "quality_label": "Качество:",
        "best": "Лучшее",
        "container": "Контейнер:",
        "container_label": "Контейнер:",
        "save_path": "Папка для сохранения:",
        "save_path_label": "Папка для сохранения:",
        "browse": "Обзор…",
        "browse_btn": "Обзор…",
        "free_space": "Свободно на диске: {:.1f} ГБ",
        "add_to_queue": "+ Добавить в очередь",
        "add_to_queue_btn": "+ Добавить в очередь",
        "settings_btn": "⚙ Настройки программы",
        # Превью / проверка ссылки
        "preview_loading": "Загрузка превью…",
        "video_not_found": "Видео не найдено или недоступно",
        "playlist_auto": (
            "⚠ Это плейлист — галочка «Скачать как плейлист» "
            "включена автоматически"
        ),
        # Правая колонка - очередь
        "queue_title": "Очередь загрузки:",
        "queue_count": "Элементов в очереди: {}",
        "clear_queue": "Очистить очередь",
        "download_all": "Скачать всё",
        "download_all_disabled": "Нечего качать",
        "queue_empty": "Очередь пуста. Добавьте хотя бы одну ссылку.",
        "all_downloaded": "Все элементы уже скачаны. Удалите их или добавьте новые ссылки.",
        # Статусы
        "status_pending": "В очереди",
        "status_downloading": "Загрузка…",
        "status_done": "Готово",
        "status_error": "Ошибка",
        "status_cancelled": "Отменено",
        "preparing": "Подготовка…",
        "processing": "Обработка файла…",
        # Прогресс
        "speed": "{:.1f} МБ/с",
        "eta": "{}с",
        "eta_dash": "—",
        "progress_format": "{}%  •  {}  •  осталось {}",
        # Диалоги
        "download_in_progress": "Сейчас выполняется загрузка. Закрыть программу всё равно?",
        "minimize_to_tray": "Сейчас выполняется загрузка. Свернуть в трей?",
        "invalid_url": "Вставьте ссылку на видео",
        "invalid_url_title": "Некорректная ссылка",
        "select_save_path": "Сначала укажите папку для сохранения",
        "path_invalid_chars": "Путь содержит недопустимые символы",
        "host_may_not_support": "Сайт может не поддерживаться",
        "add_anyway": "{}\\n\\nВсё равно добавить в очередь?",
        "cannot_remove_downloading": "Этот элемент сейчас скачивается. Сначала отмените загрузку (⏹).",
        "remove_partial": (
            "Загрузка была прервана. Удалить частично скачанный файл?\\n\\n{}"
        ),
        "cannot_clear_queue": "Дождитесь окончания текущей загрузки (или отмените её)",
        "open_folder_error": "Не удалось открыть папку:\\n{}",
        "remove_error": "Не удалось удалить файл:\\n{}",
        # Загрузка
        "downloading_n_items": "Загрузка {} элементов (до {} одновременно)…",
        "finished": "Готово: успешно скачано {} из {}",
        "nothing_downloaded": "Ничего не скачано: {} ошибок",
        "download_error_title": "Ничего не скачано",
        "no_download_error": "Не удалось скачать ни одного файла.\\n\\n{}",
        "completed": "Завершено — {}",
        "download_completed": "Загрузка завершена",
        "files_downloaded": "Скачано файлов: {}",
        "cancelled": "Отменено пользователем",
        # Обновление
        "update_available": "Доступна новая версия: {} (у вас {})",
        "up_to_date": "У вас актуальная версия ({})",
        "checking_updates": "Проверка обновлений…",
        "updating": "Обновление…",
        "update_done_ok": "Обновление завершено успешно.",
        "update_done_fail": "Не удалось обновить.",
        "check_updates_failed": "Не удалось проверить обновления (нет сети?)",
        "update_frozen_exe": (
            "Программа запущена как .exe — автообновление недоступно.\n"
            "yt-dlp встроен прямо в исполняемый файл при сборке.\n\n"
            "Чтобы обновить: пересобери .exe заново через build.bat — "
            "он автоматически установит последнюю версию yt-dlp перед сборкой."
        ),
        "update_success": "yt-dlp успешно обновлён. Перезапустите программу, чтобы изменения вступили в силу.",
        "update_pip_error": "pip вернул ошибку:\n{}",
        "update_timeout": "Обновление заняло слишком много времени и было прервано",
        "update_exception": "Не удалось запустить обновление: {}",
        # Настройки скачивания
        "playlist": "Скачать как плейлист целиком",
        # Плейлист тег
        "playlist_tag": " [плейлист]",
        # Дополнительные строки GUI
        "cancel_btn": "⏹",
        "open_folder_btn": "📁",
        "delete_btn": "✕",
        "remove_partial_title": "Удалить частичный файл?",
        "settings_btn": "⚙ Настройки программы",
        "appearance_frame": " Внешний вид ",
        "performance_frame": " Производительность ",
        "update_frame": " Обновление yt-dlp ",
        "checking": "Проверка…",
        "preview_loading": "Загрузка превью…",
        "cancelling": "Отмена…",
        "preparing": "Подготовка очереди…",
        # Трей
        "tray_title": "Загрузчик видео",
        "tray_show": "Показать",
        "tray_quit": "Выход",
        # Установщик
        "installer_title": "Установка Video Downloader",
        "welcome": "Добро пожаловать в мастер установки Video Downloader",
        "select_language": "Выберите язык установки:",
        "install": "Установить",
        "finish": "Завершение установки",
        "run_program": "Запустить Video Downloader",
    },
    "en": {
        # General
        "app_title": "Video / Audio Downloader",
        "ok": "OK",
        "cancel": "Cancel",
        "error": "Error",
        "settings": "Settings",
        "language": "Language",
        "language_changed": "Language changed. Restart the application to apply.",
        # Settings window
        "settings_window_title": "Application Settings",
        "appearance": "Appearance",
        "appearance_frame": " Appearance ",
        "dark_theme": "Dark theme (applied on next launch)",
        "performance": "Performance",
        "performance_frame": " Performance ",
        "parallel_downloads": "Parallel downloads:",
        "update_ytdlp": "yt-dlp Update",
        "update_frame": " yt-dlp Update ",
        "current_version": "Current version: {}",
        "check_updates": "Check for updates",
        "update": "Update",
        "theme_changed": "New theme will be applied on next launch.",
        # Left column
        "url_label": "Video URL:",
        "paste": "Paste",
        "check_link": "🔍 Check link",
        "checking": "Checking…",
        "hint_text": (
            "Paste a link and press\n"
            "«Check link» to choose\n"
            "quality, format and folder."
        ),
        "drag_drop_unavailable": (
            "Drag & drop unavailable — tkinterdnd2 package is missing"
        ),
        "mode": "Mode",
        "mode_frame": " Mode ",
        "video_audio": "Video + Audio",
        "audio_only": "Audio only (MP3)",
        "video_only": "Video only (no sound)",
        "quality": "Quality:",
        "quality_label": "Quality:",
        "best": "Best",
        "container": "Container:",
        "container_label": "Container:",
        "save_path": "Save folder:",
        "save_path_label": "Save folder:",
        "browse": "Browse…",
        "browse_btn": "Browse…",
        "free_space": "Free space: {:.1f} GB",
        "add_to_queue": "+ Add to queue",
        "add_to_queue_btn": "+ Add to queue",
        "settings_btn": "⚙ Settings",
        # Preview / check link
        "preview_loading": "Loading preview…",
        "video_not_found": "Video not found or unavailable",
        "playlist_auto": (
            "⚠ This is a playlist — «Download as playlist» "
            "has been enabled automatically"
        ),
        # Right column - queue
        "queue_title": "Download queue:",
        "queue_count": "Items in queue: {}",
        "clear_queue": "Clear queue",
        "download_all": "Download all",
        "download_all_disabled": "Nothing to download",
        "queue_empty": "Queue is empty. Add at least one link.",
        "all_downloaded": "All items already downloaded. Remove them or add new links.",
        # Statuses
        "status_pending": "Pending",
        "status_downloading": "Downloading…",
        "status_done": "Done",
        "status_error": "Error",
        "status_cancelled": "Cancelled",
        "preparing": "Preparing…",
        "processing": "Processing file…",
        # Progress
        "speed": "{:.1f} MB/s",
        "eta": "{}s",
        "eta_dash": "—",
        "progress_format": "{}%  •  {}  •  {} remaining",
        # Dialogs
        "download_in_progress": "A download is in progress. Close anyway?",
        "minimize_to_tray": "A download is in progress. Minimize to tray?",
        "invalid_url": "Paste a video link",
        "invalid_url_title": "Invalid URL",
        "select_save_path": "Please select a save folder first",
        "path_invalid_chars": "Path contains invalid characters",
        "host_may_not_support": "This site may not be supported",
        "add_anyway": "{}\\n\\nAdd to queue anyway?",
        "cannot_remove_downloading": "This item is currently downloading. Cancel it first (⏹).",
        "remove_partial": (
            "Download was interrupted. Delete the partial file?\\n\\n{}"
        ),
        "cannot_clear_queue": "Wait for the current download to finish (or cancel it)",
        "open_folder_error": "Failed to open folder:\\n{}",
        "remove_error": "Failed to delete file:\\n{}",
        # Download
        "downloading_n_items": "Downloading {} items (up to {} at a time)…",
        "finished": "Done: {} of {} downloaded successfully",
        "nothing_downloaded": "Nothing downloaded: {} errors",
        "download_error_title": "Nothing downloaded",
        "no_download_error": "Failed to download any files.\\n\\n{}",
        "completed": "Completed — {}",
        "download_completed": "Download completed",
        "files_downloaded": "Files downloaded: {}",
        "cancelled": "Cancelled by user",
        # Update
        "update_available": "New version available: {} (you have {})",
        "up_to_date": "You have the latest version ({})",
        "checking_updates": "Checking for updates…",
        "updating": "Updating…",
        "update_done_ok": "Update completed successfully.",
        "update_done_fail": "Failed to update.",
        "check_updates_failed": "Failed to check for updates (no network?)",
        "update_frozen_exe": (
            "The program is running as .exe — auto-update is not available.\n"
            "yt-dlp is built directly into the executable.\n\n"
            "To update: rebuild the .exe using build.bat — "
            "it will automatically install the latest yt-dlp before building."
        ),
        "update_success": "yt-dlp updated successfully. Restart the app for changes to take effect.",
        "update_pip_error": "pip returned an error:\n{}",
        "update_timeout": "Update took too long and was interrupted",
        "update_exception": "Failed to start update: {}",
        # Download settings
        "playlist": "Download as full playlist",
        # Playlist tag
        "playlist_tag": " [playlist]",
        # Additional UI
        "cancel_btn": "⏹",
        "open_folder_btn": "📁",
        "delete_btn": "✕",
        "remove_partial_title": "Delete partial file?",
        "cancelling": "Cancelling…",
        "preparing": "Preparing…",
        # Tray
        "tray_title": "Video / Audio Downloader",
        "tray_show": "Show",
        "tray_quit": "Quit",
        # Installer
        "installer_title": "Video Downloader Setup",
        "welcome": "Welcome to Video Downloader Setup Wizard",
        "select_language": "Select setup language:",
        "install": "Install",
        "finish": "Completing Setup",
        "run_program": "Launch Video Downloader",
    },
}


def _detect_os_lang() -> str:
    """Определяет язык ОС и возвращает код 'ru' или 'en'."""
    try:
        # Windows: GetUserDefaultUILanguage / GetSystemDefaultUILanguage
        if sys.platform == "win32":
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # Primary language part (lower 10 bits)
            primary = lang_id & 0x3FF
            if primary == 0x19:  # Russian
                return "ru"
            return "en"
        # POSIX
        loc = locale.getdefaultlocale()[0] or ""
        if loc.startswith("ru") or loc.startswith("be") or loc.startswith("uk"):
            return "ru"
        return "en"
    except Exception:
        return _DEFAULT_LANG


def get_lang() -> str:
    """Возвращает текущий язык приложения ('ru' | 'en')."""
    try:
        from app import config as cfg_mod
        cfg = cfg_mod.load_config()
        lang = cfg.get("language")
        if lang in SUPPORTED_LANGS:
            return lang
    except Exception:
        pass
    return _detect_os_lang()


def set_lang(lang: str) -> None:
    """Сохраняет выбранный язык в конфиг."""
    if lang not in SUPPORTED_LANGS:
        lang = _DEFAULT_LANG
    try:
        from app import config as cfg_mod
        cfg = cfg_mod.load_config()
        cfg["language"] = lang
        cfg_mod.save_config(cfg)
    except Exception:
        pass


def t(key: str, *args) -> str:
    """Вернуть переведённую строку по ключу."""
    lang = get_lang()
    text = _TRANSLATIONS.get(lang, _TRANSLATIONS[_DEFAULT_LANG]).get(key)
    if text is None:
        text = _TRANSLATIONS[_DEFAULT_LANG].get(key, key)
    try:
        return text.format(*args)
    except (IndexError, KeyError):
        return text
