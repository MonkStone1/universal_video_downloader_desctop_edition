"""
Системный трей. Изолирован отдельно, чтобы основной код GUI не знал
деталей pystray и корректно работал, если библиотека не установлена.
"""

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    from app import i18n as i18n
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False

import threading


class TrayManager:
    """
    Обёртка над pystray.Icon. Если pystray/Pillow не установлены —
    все методы становятся безопасными no-op, чтобы вызывающему коду
    не нужно было проверять доступность на каждом вызове.
    """

    def __init__(self, on_show, on_quit):
        self._icon = None
        self._on_show = on_show
        self._on_quit = on_quit

    @property
    def available(self) -> bool:
        return TRAY_AVAILABLE

    def start(self):
        if not TRAY_AVAILABLE:
            return

        def _show(_icon, _item):
            self._on_show()

        def _quit(_icon, _item):
            self.stop()
            self._on_quit()

        img = Image.new("RGBA", (64, 64), (46, 213, 115, 255))
        menu = pystray.Menu(
            pystray.MenuItem(i18n.t("tray_show") if I18N_AVAILABLE else "Show", _show, default=True),
            pystray.MenuItem(i18n.t("tray_quit") if I18N_AVAILABLE else "Quit", _quit),
        )
        self._icon = pystray.Icon(
            "downloader",
            img,
            i18n.t("tray_title") if I18N_AVAILABLE else "Video Downloader",
            menu
        )
        threading.Thread(target=self._icon.run, daemon=True).start()

    def notify(self, title: str, message: str):
        if not TRAY_AVAILABLE or not self._icon:
            return
        try:
            self._icon.notify(message, title)
        except Exception:
            pass

    def stop(self):
        if not TRAY_AVAILABLE or not self._icon:
            return
        try:
            self._icon.stop()
        except Exception:
            pass
