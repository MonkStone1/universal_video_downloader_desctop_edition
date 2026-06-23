"""
Проверка и обновление версии yt-dlp.

ВАЖНО про обновление в скомпилированном .exe:
Nuitka/PyInstaller запекают yt-dlp прямо в бинарник — там нет
интерпретатора Python с pip, поэтому "обновить" в полном смысле
нельзя без пересборки exe. Поэтому здесь:
  - проверка новой версии работает всегда (просто HTTP-запрос к PyPI)
  - реальное обновление через pip работает только при запуске из
    исходников (`python downloader.py`), где есть доступ к pip
  - если programма запущена как .exe — пользователю показывается
    честное сообщение с инструкцией, а не молчаливая no-op кнопка
"""

import json
import subprocess
import sys
import urllib.request

try:
    from app import i18n as i18n
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False

import yt_dlp

PYPI_URL = "https://pypi.org/pypi/yt-dlp/json"


def is_frozen() -> bool:
    """True если запущено как собранный exe (Nuitka/PyInstaller), не как .py скрипт."""
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def get_current_version() -> str:
    return yt_dlp.version.__version__


def get_latest_version(timeout: int = 8) -> str | None:
    """Запрашивает последнюю версию yt-dlp с PyPI. None при ошибке сети."""
    try:
        req = urllib.request.Request(
            PYPI_URL, headers={"User-Agent": "Mozilla/5.0 (VideoDownloader)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return data.get("info", {}).get("version")
    except Exception:
        return None


def check_for_update() -> tuple[bool, str, str]:
    """
    Возвращает (доступно_обновление, текущая_версия, последняя_версия_или_сообщение_ошибки).
    Сравнение версий: yt-dlp использует формат YYYY.MM.DD, поэтому
    простое строковое сравнение после нормализации точек работает
    корректно для определения "новее/старее".
    """
    current = get_current_version()
    latest = get_latest_version()

    if latest is None:
        msg = "Не удалось проверить обновления (нет сети?)" if not I18N_AVAILABLE else i18n.t("check_updates_failed")
        return False, current, msg

    if latest == current:
        return False, current, latest

    # Сравниваем как кортежи чисел (на случай различий типа 06.09 vs 6.9)
    def _norm(v: str) -> tuple:
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    try:
        is_newer = _norm(latest) > _norm(current)
    except Exception:
        is_newer = latest != current

    return is_newer, current, latest


def perform_update() -> tuple[bool, str]:
    """
    Пытается обновить yt-dlp через pip. Работает только если запущено
    из исходников (есть доступ к pip текущего интерпретатора).
    В .exe возвращает понятное сообщение вместо попытки обновления.
    """
    if is_frozen():
        msg = (
            "Программа запущена как .exe — автообновление недоступно.\n"
            "yt-dlp встроен прямо в исполняемый файл при сборке.\n\n"
            "Чтобы обновить: пересобери .exe заново через build.bat — "
            "он автоматически установит последнюю версию yt-dlp перед сборкой."
        ) if not I18N_AVAILABLE else i18n.t("update_frozen_exe")
        return False, msg

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            msg = "yt-dlp успешно обновлён. Перезапустите программу, чтобы изменения вступили в силу." if not I18N_AVAILABLE else i18n.t("update_success")
            return True, msg
        err_msg = f"pip вернул ошибку:\n{result.stderr[-500:]}" if not I18N_AVAILABLE else i18n.t("update_pip_error", result.stderr[-500:])
        return False, err_msg
    except subprocess.TimeoutExpired:
        msg = "Обновление заняло слишком много времени и было прервано" if not I18N_AVAILABLE else i18n.t("update_timeout")
        return False, msg
    except Exception as e:
        msg = f"Не удалось запустить обновление: {e}" if not I18N_AVAILABLE else i18n.t("update_exception", str(e))
        return False, msg
