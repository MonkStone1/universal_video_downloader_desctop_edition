"""
Построение виджетов интерфейса.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import config as cfg_mod
from app import core as core
from app import i18n as i18n
from app import queue_model as qm
from app import theme as theme_mod


def build_ui(app):
    """Построение интерфейса — две колонки."""
    c = app.colors
    root = app.root

    style = ttk.Style()
    style.theme_use("default")
    app.style = style

    outer = tk.Frame(root, bg=c["bg"])
    outer.pack(fill=tk.BOTH, expand=True)

    left = tk.Frame(outer, bg=c["bg"], width=380)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=(14, 7), pady=14)
    left.pack_propagate(False)

    build_left_column(app, left)

    right = tk.Frame(outer, bg=c["bg"])
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 14), pady=14)
    build_queue_section(app, right)


def build_left_column(app, parent):
    c = app.colors

    tk.Label(parent, text=i18n.t("url_label"), font=theme_mod.FONT_B,
            bg=c["bg"], fg=c["text"], anchor="w").pack(fill=tk.X)

    url_row = tk.Frame(parent, bg=c["bg"])
    url_row.pack(fill=tk.X, pady=(4, 0))

    app.url_entry = tk.Entry(url_row, font=theme_mod.FONT, bg=c["card"],
                              fg=c["text"], insertbackground=c["text"])
    app.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

    from app.gui.handlers import setup_url_dnd
    if app._dnd_ok:
        setup_url_dnd(app)

    tk.Button(url_row, text="✕", command=app._clear_url_and_preview,
             font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
             cursor="hand2", width=2).pack(side=tk.LEFT)

    btn_row = tk.Frame(parent, bg=c["bg"])
    btn_row.pack(fill=tk.X, pady=(4, 0))

    tk.Button(btn_row, text=i18n.t("paste"), command=app._paste_url,
             bg=c["panel"], fg=c["text"], font=theme_mod.FONT, relief=tk.FLAT,
             cursor="hand2").pack(side=tk.LEFT, padx=(0, 4))

    app.check_btn = tk.Button(btn_row, text=i18n.t("check_link"), command=app._load_preview,
                               bg=theme_mod.GREEN, fg="white", font=theme_mod.FONT_B,
                               relief=tk.FLAT, cursor="hand2")
    app.check_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

    if not app._dnd_ok:
        lbl = tk.Label(parent, text=i18n.t("drag_drop_unavailable"),
                font=("Segoe UI", 7), fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", pady=(2, 0))
        app._register_text(lbl, "drag_drop_unavailable")

    app.host_warning_lbl = tk.Label(parent, text="", font=("Segoe UI", 7),
                                     fg="#e6a817", bg=c["bg"], anchor="w",
                                     wraplength=360, justify=tk.LEFT)
    app.host_warning_lbl.pack(fill=tk.X, pady=(4, 0))

    app.hint_label = tk.Label(
        parent,
        text=i18n.t("hint_text"),
        font=("Segoe UI", 8), fg=c["text_dim"], bg=c["bg"],
        justify=tk.LEFT, anchor="w")
    app.hint_label.pack(fill=tk.X, pady=(16, 0))
    app._register_text(app.hint_label, "hint_text")

    app.settings_panel = tk.Frame(parent, bg=c["bg"])
    build_settings_panel(app, app.settings_panel)

    settings_btn = tk.Button(parent, text=i18n.t("settings_btn"), command=app._open_settings_window,
             font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
             cursor="hand2")
    settings_btn.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
    app._register_text(settings_btn, "settings_btn")


def build_settings_panel(app, parent):
    c = app.colors

    preview_frame = tk.Frame(parent, bg=c["bg"])
    preview_frame.pack(fill=tk.X, pady=(0, 8))

    THUMB_W, THUMB_H = 336, 189
    app._thumb_placeholder = tk.PhotoImage(width=THUMB_W, height=THUMB_H)
    app.thumb_label = tk.Label(preview_frame, bg=c["panel"],
                                image=app._thumb_placeholder,
                                compound=tk.CENTER)
    app.thumb_label.pack(fill=tk.X)

    app.title_label = tk.Label(preview_frame, text="", font=("Segoe UI", 9, "bold"),
                                bg=c["bg"], fg=c["text"], wraplength=334,
                                justify=tk.LEFT, anchor="w")
    app.title_label.pack(fill=tk.X, pady=(4, 0))

    app.meta_label = tk.Label(preview_frame, text="", font=("Segoe UI", 8),
                               fg=c["text_dim"], bg=c["bg"], anchor="w")
    app.meta_label.pack(fill=tk.X)

    mode_frame = tk.LabelFrame(parent, text=i18n.t("mode_frame"), font=theme_mod.FONT,
                               bg=c["bg"], fg=c["text"], padx=8, pady=4)
    mode_frame.pack(fill=tk.X, pady=(0, 6))
    app._register_text(mode_frame, "mode_frame")

    app.mode_var = tk.StringVar(value="video")
    for lbl, val in [("Видео + Аудио", "video"),
                     ("Только Аудио (MP3)", "audio"),
                     ("Только Видео (без звука)", "video_only")]:
        tk.Radiobutton(mode_frame, text=lbl, variable=app.mode_var, value=val,
                      font=theme_mod.FONT, bg=c["bg"], fg=c["text"],
                      activebackground=c["bg"], activeforeground=c["text"],
                      selectcolor=c["panel"]).pack(anchor=tk.W)

    q_row = tk.Frame(parent, bg=c["bg"])
    q_row.pack(fill=tk.X, pady=(0, 4))
    quality_lbl = tk.Label(q_row, text=i18n.t("quality_label"), font=theme_mod.FONT, bg=c["bg"],
            fg=c["text"], width=11, anchor="w")
    quality_lbl.pack(side=tk.LEFT)
    app._register_text(quality_lbl, "quality_label")
    app.quality_var = tk.StringVar(value="Лучшее")
    app.quality_cb = ttk.Combobox(q_row, textvariable=app.quality_var,
                                   values=list(core.QUALITY_HEIGHTS.keys()),
                                   state="readonly", width=14, font=theme_mod.FONT)
    app.quality_cb.pack(side=tk.LEFT)

    cont_row = tk.Frame(parent, bg=c["bg"])
    cont_row.pack(fill=tk.X, pady=(0, 4))
    container_lbl = tk.Label(cont_row, text=i18n.t("container_label"), font=theme_mod.FONT, bg=c["bg"],
            fg=c["text"], width=11, anchor="w")
    container_lbl.pack(side=tk.LEFT)
    app._register_text(container_lbl, "container_label")
    app.container_var = tk.StringVar(value="mp4")
    ttk.Combobox(cont_row, textvariable=app.container_var,
                values=["mp4", "mkv", "webm"], state="readonly",
                width=14, font=theme_mod.FONT).pack(side=tk.LEFT)

    playlist_row = tk.Frame(parent, bg=c["bg"])
    playlist_row.pack(fill=tk.X, pady=(2, 6))
    app.playlist_var = tk.BooleanVar(value=False)
    playlist_cb = tk.Checkbutton(playlist_row, text=i18n.t("playlist"),
                  variable=app.playlist_var, font=theme_mod.FONT, bg=c["bg"], fg=c["text"],
                  activebackground=c["bg"], activeforeground=c["text"],
                  selectcolor=c["panel"])
    playlist_cb.pack(anchor=tk.W)
    app._register_text(playlist_cb, "playlist")

    save_path_lbl = tk.Label(parent, text=i18n.t("save_path_label"), font=theme_mod.FONT_B,
            bg=c["bg"], fg=c["text"], anchor="w")
    save_path_lbl.pack(fill=tk.X)
    app._register_text(save_path_lbl, "save_path_label")

    path_input_row = tk.Frame(parent, bg=c["bg"])
    path_input_row.pack(fill=tk.X, pady=(2, 0))

    app.path_entry = tk.Entry(path_input_row, font=theme_mod.FONT, bg=c["card"],
                               fg=c["text"], insertbackground=c["text"])
    app.path_entry.insert(0, app._config.get("last_save_path", cfg_mod.DEFAULT_CONFIG["last_save_path"]))
    app.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

    from app.gui.handlers import on_path_drop
    if app._dnd_ok:
        app.path_entry.drop_target_register(app._dnd_text)
        app.path_entry.dnd_bind("<<Drop>>", on_path_drop)

    browse_btn = tk.Button(path_input_row, text=i18n.t("browse_btn"), command=app._browse_folder,
             font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
             cursor="hand2")
    browse_btn.pack(side=tk.LEFT)
    app._register_text(browse_btn, "browse_btn")

    app.disk_space_lbl = tk.Label(parent, text="", font=("Segoe UI", 7),
                                   fg=c["text_dim"], bg=c["bg"], anchor="w")
    app.disk_space_lbl.pack(fill=tk.X, pady=(2, 8))

    add_queue_btn = tk.Button(parent, text=i18n.t("add_to_queue_btn"), command=app._add_to_queue,
             bg=theme_mod.GREEN, fg="white", font=theme_mod.FONT_B, relief=tk.FLAT,
             cursor="hand2", pady=4)
    add_queue_btn.pack(fill=tk.X)
    app._register_text(add_queue_btn, "add_to_queue_btn")


def build_queue_section(app, parent):
    c = app.colors

    header = tk.Frame(parent, bg=c["bg"])
    header.pack(fill=tk.X)
    queue_title_lbl = tk.Label(header, text=i18n.t("queue_title"), font=theme_mod.FONT_B,
            bg=c["bg"], fg=c["text"], anchor="w")
    queue_title_lbl.pack(side=tk.LEFT)
    app._register_text(queue_title_lbl, "queue_title")
    app.queue_count_lbl = tk.Label(header, text=i18n.t("queue_count", 0),
                                    font=("Segoe UI", 8), fg=c["text_dim"], bg=c["bg"])
    app.queue_count_lbl.pack(side=tk.RIGHT)
    app._register_text(app.queue_count_lbl, "queue_count", 0)

    canvas_frame = tk.Frame(parent, bg=c["bg"])
    canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

    app.queue_canvas = tk.Canvas(canvas_frame, bg=c["panel"], highlightthickness=0)
    scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=app.queue_canvas.yview)
    app.queue_list_inner = tk.Frame(app.queue_canvas, bg=c["panel"])

    app.queue_list_inner.bind(
        "<Configure>",
        lambda evt: app.queue_canvas.configure(scrollregion=app.queue_canvas.bbox("all"))
    )
    app._canvas_window = app.queue_canvas.create_window(
        (0, 0), window=app.queue_list_inner, anchor="nw")
    app.queue_canvas.configure(yscrollcommand=scroll.set)
    app.queue_canvas.bind(
        "<Configure>",
        lambda evt: app.queue_canvas.itemconfig(app._canvas_window, width=evt.width)
    )

    app.queue_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_wheel(event):
        app.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    app.queue_canvas.bind("<Enter>", lambda e: app.queue_canvas.bind_all("<MouseWheel>", _on_wheel))
    app.queue_canvas.bind("<Leave>", lambda e: app.queue_canvas.unbind_all("<MouseWheel>"))

    btn_row = tk.Frame(parent, bg=c["bg"])
    btn_row.pack(fill=tk.X)
    clear_queue_btn = tk.Button(btn_row, text=i18n.t("clear_queue"), command=app._clear_queue,
             font=theme_mod.FONT, bg=c["panel"], fg=c["text"], relief=tk.FLAT,
             cursor="hand2")
    clear_queue_btn.pack(side=tk.RIGHT, pady=(0, 8))
    app._register_text(clear_queue_btn, "clear_queue")

    app.download_btn = tk.Button(parent, text=i18n.t("download_all"), command=app._start_download,
                                  bg=theme_mod.GREEN, fg="white", font=("Segoe UI", 12, "bold"),
                                  relief=tk.FLAT, activebackground=theme_mod.D_GREEN,
                                  cursor="hand2", pady=8)
    app.download_btn.pack(fill=tk.X, pady=(0, 6))
    app._register_text(app.download_btn, "download_all")

    app.style.configure("green.Horizontal.TProgressbar",
                        troughcolor=c["panel"], background=theme_mod.GREEN, thickness=14)

    app.status_label = tk.Label(parent, text="", font=("Segoe UI", 8),
                                 bg=c["bg"], fg=c["text_dim"], anchor="w",
                                 wraplength=560, justify=tk.LEFT)
    app.status_label.pack(fill=tk.X)
