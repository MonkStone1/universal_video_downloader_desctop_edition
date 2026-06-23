"""
Превью видео: загрузка информации, картинки, отображение.
"""

import io
import threading
from tkinter import messagebox
from urllib.request import urlopen, Request

import yt_dlp

from app import core as core
from app import i18n as i18n


def load_preview(app, url: str):
    if not url:
        messagebox.showerror(i18n.t("error"), "Вставьте ссылку на видео")
        return

    ok, err = core.validate_url_syntax(url)
    if not ok:
        messagebox.showerror(i18n.t("invalid_url_title"), err)
        return

    app.check_btn.config(state="disabled", text=i18n.t("checking"))
    app._clear_preview(i18n.t("preview_loading"))
    _fetch_preview_async(app, url)


def _fetch_preview_async(app, url: str):
    def _run():
        host_ok, host_name, host_warn = core.check_host_supported(url)
        if host_warn:
            app._gui(lambda: app.host_warning_lbl.config(text=f"⚠ {host_warn}"))

        try:
            with yt_dlp.YoutubeDL({
                "quiet": True, "no_warnings": True, "skip_download": True,
                "noplaylist": True,
            }) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            app._gui(lambda exc=exc: _on_preview_failed(app, f"Не удалось получить превью: {exc}"))
            return

        if info is None:
            app._gui(lambda: _on_preview_failed(app, "Видео не найдено или недоступно"))
            return

        title = info.get("title") or "—"
        duration = info.get("duration") or 0
        uploader = info.get("uploader") or "—"
        thumb = info.get("thumbnail") or ""
        is_playlist = info.get("_type") == "playlist"

        formats = info.get("formats") or []
        heights = sorted({
            f.get("height") for f in formats
            if f.get("height") and f.get("vcodec", "none") != "none"
        }, reverse=True)
        res_list = ["Лучшее"] + [f"{h}p" for h in heights if f"{h}p" in core.QUALITY_HEIGHTS]
        if len(res_list) == 1:
            res_list = list(core.QUALITY_HEIGHTS.keys())

        mins, secs = divmod(int(duration), 60)
        dur_str = f"{mins}:{secs:02d}" if duration else "—"

        img_tk = None
        try:
            from PIL import Image, ImageTk
            if thumb:
                req = Request(thumb, headers={"User-Agent": "Mozilla/5.0"})
                data = urlopen(req, timeout=6).read()
                img = Image.open(io.BytesIO(data)).convert("RGB").resize((336, 189), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img)
        except Exception:
            pass

        app._gui(lambda: _show_preview(app, title, uploader, dur_str, res_list, img_tk, is_playlist))

    threading.Thread(target=_run, daemon=True).start()


def _on_preview_failed(app, msg: str):
    app.check_btn.config(state="normal", text=i18n.t("check_link"))
    app._clear_preview(msg)


def _show_preview(app, title, uploader, duration, res_list, img_tk, is_playlist):
    app.check_btn.config(state="normal", text=i18n.t("check_link"))
    app._pending_title = title or ""

    if img_tk:
        app.thumb_label.config(image=img_tk)
        app.thumb_label.image = img_tk
    else:
        app.thumb_label.config(image="")
        app.thumb_label.image = None

    short_title = title if len(title) <= 60 else title[:57] + "…"
    prefix = "[Плейлист] " if is_playlist else ""
    app.title_label.config(text=prefix + short_title)
    app.meta_label.config(text=f"{uploader}  •  {duration}")
    app.quality_cb["values"] = res_list
    app.quality_var.set(res_list[0])

    if is_playlist:
        app.playlist_var.set(True)
        app.host_warning_lbl.config(
            text=f"⚠ {i18n.t('playlist_auto')}")
    else:
        app.playlist_var.set(False)

    app._reveal_settings_panel()
