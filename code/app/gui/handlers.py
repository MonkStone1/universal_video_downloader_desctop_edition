"""
Обработчики событий и служебные методы GUI.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from app import config as cfg_mod
from app import core as core
from app import i18n as i18n
from app import theme as theme_mod
from app import updater

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    from tkinterdnd2 import DND_TEXT, TkinterDnD
    DND_OK = True
except ImportError:
    DND_OK = False

import threading


def setup_url_dnd(app):
    def _on_drop(event):
        raw = event.data.strip()
        if raw.startswith("{") and raw.endswith("}"):
            raw = raw[1:-1]
        first_line = raw.splitlines()[0].strip() if raw else ""
        if first_line:
            app.url_entry.delete(0, tk.END)
            app.url_entry.insert(0, first_line)
            app._clear_preview()

    app.url_entry.drop_target_register(DND_TEXT)
    app.url_entry.dnd_bind("<<Drop>>", _on_drop)


def on_path_drop(event):
    raw = event.data.strip()
    if raw.startswith("{") and raw.endswith("}"):
        raw = raw[1:-1]
    first_line = raw.splitlines()[0].strip() if raw else ""
    if first_line and os.path.isdir(first_line):
        # Это метод App, вызываемый из lambda в build_settings_panel
        pass


def clear_url_and_preview(app):
    app.url_entry.delete(0, tk.END)
    app._pending_title = ""
    app._clear_preview()
    app._hide_settings_panel()


def paste_url(app):
    try:
        text = app.root.clipboard_get().strip()
    except tk.TclError:
        return
    app.url_entry.delete(0, tk.END)
    app.url_entry.insert(0, text)
    app._pending_title = ""
    app._clear_preview()


def clear_preview(app, msg: str = ""):
    app.thumb_label.config(image="")
    app.thumb_label.image = None
    app.title_label.config(text=msg or "")
    app.meta_label.config(text="")
    app.host_warning_lbl.config(text="")
    app.quality_cb["values"] = list(core.QUALITY_HEIGHTS.keys())
    app.quality_var.set("Лучшее")


def browse_folder(app):
    d = filedialog.askdirectory()
    if d:
        app.path_entry.delete(0, tk.END)
        app.path_entry.insert(0, d)
        app._config["last_save_path"] = d
        cfg_mod.save_config(app._config)
        app._update_disk_space_label(d)


def update_disk_space_label(app, path: str):
    free = core.get_free_space(path)
    if free is None:
        app.disk_space_lbl.config(text="")
        return
    free_gb = free / 1_073_741_824
    app.disk_space_lbl.config(text=f"Свободно на диске: {free_gb:.1f} ГБ")


def toggle_theme(app):
    app._config["dark_theme"] = app.dark_var.get()
    cfg_mod.save_config(app._config)
    messagebox.showinfo("Тема изменена",
                        "Новая тема будет применена при следующем запуске программы.")


def on_parallel_change(app, *_args):
    try:
        n = max(1, min(5, int(app.parallel_var.get())))
    except ValueError:
        n = 2
    app._config["max_parallel"] = n
    cfg_mod.save_config(app._config)


def check_for_updates(app):
    app.check_update_btn.config(state=tk.DISABLED)
    app.update_status_lbl.config(text=i18n.t("checking_updates"), fg=app.colors["text_dim"])

    def _run():
        has_update, current, latest = updater.check_for_update()
        app._gui(lambda: on_update_check_done(app, has_update, current, latest))

    threading.Thread(target=_run, daemon=True).start()


def on_update_check_done(app, has_update: bool, current: str, latest: str):
    app.check_update_btn.config(state=tk.NORMAL)
    if has_update:
        app.update_status_lbl.config(
            text=f"Доступна новая версия: {latest} (у вас {current})", fg="#e6a817")
        app.do_update_btn.config(state=tk.NORMAL)
    elif "." in str(latest):
        app.update_status_lbl.config(text=f"У вас актуальная версия ({current})", fg="#27ae60")
        app.do_update_btn.config(state=tk.DISABLED)
    else:
        app.update_status_lbl.config(text=str(latest), fg="#e74c3c")
        app.do_update_btn.config(state=tk.DISABLED)


def perform_update(app):
    app.do_update_btn.config(state=tk.DISABLED)
    app.update_status_lbl.config(text=i18n.t("updating"), fg=app.colors["text_dim"])

    def _run():
        ok, msg = updater.perform_update()
        app._gui(lambda: on_update_done(app, ok, msg))

    threading.Thread(target=_run, daemon=True).start()


def on_update_done(app, ok: bool, msg: str):
    app.update_status_lbl.config(text=msg, fg="#27ae60" if ok else "#e74c3c")
    if ok:
        app.do_update_btn.config(state=tk.DISABLED)
    else:
        app.do_update_btn.config(state=tk.NORMAL)


def reveal_settings_panel(app):
    if not app.settings_panel.winfo_ismapped():
        app.hint_label.pack_forget()
        app.settings_panel.pack(fill=tk.X, pady=(4, 0))


def hide_settings_panel(app):
    if app.settings_panel.winfo_ismapped():
        app.settings_panel.pack_forget()
        app.hint_label.pack(fill=tk.X, pady=(16, 0))
