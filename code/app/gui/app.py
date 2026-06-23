"""
Построение графического интерфейса.

Layout: слева - ссылка + кнопка проверки + (после проверки) настройки
скачивания + кнопка добавления в очередь; справа - очередь и кнопки,
с ней связанные. Настройки скачивания (путь/качество/режим/контейнер/
плейлист) показываются только после нажатия "Проверить ссылку" - до
этого посередине видна только подсказка, что нужно сначала проверить
ссылку. Это уменьшает число одновременно видимых элементов и не даёт
интерфейсу разрастаться вертикально.

Тема/параллельность/обновление yt-dlp вынесены в отдельное окно
"Настройки" (Toplevel), чтобы не конкурировать за место с основной
колонкой.
"""

import io
import os
import queue
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox, ttk
from urllib.request import urlopen, Request

import yt_dlp

from app import config as cfg_mod
from app import core as core
from app import i18n as i18n
from app import queue_model as qm
from app import theme as theme_mod
from app import tray as tray_mod
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

import tkinter as tk


class App:
    def __init__(self):
        self._config = cfg_mod.load_config()
        self.colors = theme_mod.get_colors(bool(self._config.get("dark_theme")))

        self.queue_items: dict[str, dict] = {}
        self.item_order: list[str] = []
        self._pending_title: str = ""  # заголовок последнего проверенного видео

        self._gui_queue: "queue.Queue" = queue.Queue()
        self._settings_win = None  # окно настроек (Toplevel), открыто/None

        # Список зарегистрированных виджетов для смены языка
        self._lang_widgets: list[tuple] = []

        self.root = TkinterDnD.Tk() if DND_OK else tk.Tk()
        self.root.title(i18n.t("app_title"))
        self.root.geometry("980x740")
        self.root.minsize(860, 520)
        self.root.configure(bg=self.colors["bg"])

        self.tray = tray_mod.TrayManager(
            on_show=lambda: self._gui(self._show_window),
            on_quit=lambda: self._gui(self.root.destroy),
        )

        self._build_ui()

        self.root.bind("<Unmap>", self._on_minimize)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._restore_queue_from_config()
        self.tray.start()
        self._warm_extractor_cache_async()
        self.root.after(60, self._poll_gui)

    # ─────────────────────────────────────────────────────────
    # GUI thread-safety helpers
    # ─────────────────────────────────────────────────────────

    def _gui(self, fn):
        """Поставить вызов fn() в очередь для выполнения в главном потоке."""
        self._gui_queue.put(fn)

    def _poll_gui(self):
        try:
            while True:
                fn = self._gui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(60, self._poll_gui)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()

    def _on_minimize(self, event):
        if event.widget is self.root and self.root.state() == "iconic" and self.tray.available:
            self.root.withdraw()

    def _on_close(self):
        if any(it["status"] == qm.STATUS_DOWNLOADING for it in self.queue_items.values()):
            if not messagebox.askyesno(
                i18n.t("download_in_progress"),
                i18n.t("download_in_progress")
            ):
                return
        self.tray.stop()
        self.root.destroy()

    # ─────────────────────────────────────────────────────────
    # Локализация
    # ─────────────────────────────────────────────────────────

    def _register_text(self, widget, key: str, *args):
        """Зарегистрировать виджет для автоматического обновления текста при смене языка."""
        self._lang_widgets.append((widget, key, args))

    def _apply_language(self):
        """Обновить текст всех зарегистрированных виджетов."""
        for widget, key, args in self._lang_widgets:
            try:
                # Toplevel использует title() вместо config(text=...)
                if hasattr(widget, 'title') and isinstance(widget, tk.Toplevel):
                    widget.title(i18n.t(key, *args))
                else:
                    widget.config(text=i18n.t(key, *args))
            except Exception:
                pass
        self.root.title(i18n.t("app_title"))

    def _warm_extractor_cache_async(self):
        """Прогревает кэш экстракторов yt-dlp в фоне, чтобы первая
        проверка хоста при добавлении в очередь не подвисала на ~0.3-0.4с."""
        def _run():
            try:
                core._get_extractors()
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────────────────
    # Построение интерфейса — две колонки
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        c = self.colors
        root = self.root

        style = ttk.Style()
        style.theme_use("default")
        self.style = style

        outer = tk.Frame(root, bg=c["bg"])
        outer.pack(fill=tk.BOTH, expand=True)

        # ── Левая колонка: ссылка + (после проверки) настройки ──
        left = tk.Frame(outer, bg=c["bg"], width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(14, 7), pady=14)
        left.pack_propagate(False)

        self._build_left_column(left)

        # ── Правая колонка: очередь ──
        right = tk.Frame(outer, bg=c["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(7, 14), pady=14)

        self._build_queue_section(right)

    def _build_left_column(self, parent):
        c = self.colors

        tk.Label(parent, text=i18n.t("url_label"), font=theme_mod.FONT_B,
                bg=c["bg"], fg=c["text"], anchor="w").pack(fill=tk.X)

        url_row = tk.Frame(parent, bg=c["bg"])
        url_row.pack(fill=tk.X, pady=(4, 0))

        self.url_entry = tk.Entry(url_row, font=theme_mod.FONT, bg=c["card"],
                                  fg=c["text"], insertbackground=c["text"])
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        if DND_OK:
            self._setup_url_dnd()

        tk.Button(url_row, text="✕", command=self._clear_url_and_preview,
                 font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
                 cursor="hand2", width=2).pack(side=tk.LEFT)

        btn_row = tk.Frame(parent, bg=c["bg"])
        btn_row.pack(fill=tk.X, pady=(4, 0))

        tk.Button(btn_row, text=i18n.t("paste"), command=self._paste_url,
                 bg=c["panel"], fg=c["text"], font=theme_mod.FONT, relief=tk.FLAT,
                 cursor="hand2").pack(side=tk.LEFT, padx=(0, 4))

        # Кнопка "Проверить ссылку" - до её нажатия настройки скачивания
        # скрыты, после - появляются ниже. Переименовано из "Превью" для
        # ясности: эта кнопка не просто показывает картинку, а открывает
        # весь блок настроек.
        self.check_btn = tk.Button(btn_row, text=i18n.t("check_link"), command=self._load_preview,
                                   bg=theme_mod.GREEN, fg="white", font=theme_mod.FONT_B,
                                   relief=tk.FLAT, cursor="hand2")
        self.check_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if not DND_OK:
            lbl = tk.Label(parent, text=i18n.t("drag_drop_unavailable"),
                    font=("Segoe UI", 7), fg=c["text_dim"], bg=c["bg"]).pack(anchor="w", pady=(2, 0))
            self._register_text(lbl, "drag_drop_unavailable")

        self.host_warning_lbl = tk.Label(parent, text="", font=("Segoe UI", 7),
                                         fg="#e6a817", bg=c["bg"], anchor="w",
                                         wraplength=360, justify=tk.LEFT)
        self.host_warning_lbl.pack(fill=tk.X, pady=(4, 0))

        # Подсказка, видна только пока настройки ещё не раскрыты
        self.hint_label = tk.Label(
            parent,
            text=i18n.t("hint_text"),
            font=("Segoe UI", 8), fg=c["text_dim"], bg=c["bg"],
            justify=tk.LEFT, anchor="w")
        self.hint_label.pack(fill=tk.X, pady=(16, 0))
        self._register_text(self.hint_label, "hint_text")

        # ── Контейнер настроек — построен заранее, но скрыт (pack/unpack) ──
        self.settings_panel = tk.Frame(parent, bg=c["bg"])
        self._build_settings_panel(self.settings_panel)
        # не паковим settings_panel сейчас — появится после первой проверки

        # ── Кнопка открытия окна "Настройки программы" — всегда внизу слева ──
        settings_btn = tk.Button(parent, text=i18n.t("settings_btn"), command=self._open_settings_window,
                 font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
                 cursor="hand2")
        settings_btn.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        self._register_text(settings_btn, "settings_btn")

    def _build_settings_panel(self, parent):
        """
        Блок настроек скачивания: превью, режим, качество, контейнер,
        плейлист, путь, кнопка добавления в очередь. Строится один раз,
        но physически появляется в layout только после первой успешной
        проверки ссылки (см. _show_preview / _reveal_settings_panel).
        """
        c = self.colors

        # ── Превью: картинка на всю ширину + текст под ней ──
        preview_frame = tk.Frame(parent, bg=c["bg"])
        preview_frame.pack(fill=tk.X, pady=(0, 8))

        # Фиксируем пиксельный размер плейсхолдера через пустой PhotoImage.
        # Без этого width/height у Label работают в символах, а не пикселях.
        THUMB_W, THUMB_H = 336, 189
        self._thumb_placeholder = tk.PhotoImage(width=THUMB_W, height=THUMB_H)
        self.thumb_label = tk.Label(preview_frame, bg=c["panel"],
                                    image=self._thumb_placeholder,
                                    compound=tk.CENTER)
        self.thumb_label.pack(fill=tk.X)

        self.title_label = tk.Label(preview_frame, text="", font=("Segoe UI", 9, "bold"),
                                    bg=c["bg"], fg=c["text"], wraplength=334,
                                    justify=tk.LEFT, anchor="w")
        self.title_label.pack(fill=tk.X, pady=(4, 0))

        self.meta_label = tk.Label(preview_frame, text="", font=("Segoe UI", 8),
                                   fg=c["text_dim"], bg=c["bg"], anchor="w")
        self.meta_label.pack(fill=tk.X)

        mode_frame = tk.LabelFrame(parent, text=i18n.t("mode_frame"), font=theme_mod.FONT,
                                   bg=c["bg"], fg=c["text"], padx=8, pady=4)
        mode_frame.pack(fill=tk.X, pady=(0, 6))
        self._register_text(mode_frame, "mode_frame")

        self.mode_var = tk.StringVar(value="video")
        for lbl, val in [("Видео + Аудио", "video"),
                         ("Только Аудио (MP3)", "audio"),
                         ("Только Видео (без звука)", "video_only")]:
            tk.Radiobutton(mode_frame, text=lbl, variable=self.mode_var, value=val,
                          font=theme_mod.FONT, bg=c["bg"], fg=c["text"],
                          activebackground=c["bg"], activeforeground=c["text"],
                          selectcolor=c["panel"]).pack(anchor=tk.W)

        q_row = tk.Frame(parent, bg=c["bg"])
        q_row.pack(fill=tk.X, pady=(0, 4))
        quality_lbl = tk.Label(q_row, text=i18n.t("quality_label"), font=theme_mod.FONT, bg=c["bg"],
                fg=c["text"], width=11, anchor="w")
        quality_lbl.pack(side=tk.LEFT)
        self._register_text(quality_lbl, "quality_label")
        self.quality_var = tk.StringVar(value="Лучшее")
        self.quality_cb = ttk.Combobox(q_row, textvariable=self.quality_var,
                                       values=list(core.QUALITY_HEIGHTS.keys()),
                                       state="readonly", width=14, font=theme_mod.FONT)
        self.quality_cb.pack(side=tk.LEFT)

        cont_row = tk.Frame(parent, bg=c["bg"])
        cont_row.pack(fill=tk.X, pady=(0, 4))
        container_lbl = tk.Label(cont_row, text=i18n.t("container_label"), font=theme_mod.FONT, bg=c["bg"],
                fg=c["text"], width=11, anchor="w")
        container_lbl.pack(side=tk.LEFT)
        self._register_text(container_lbl, "container_label")
        self.container_var = tk.StringVar(value="mp4")
        ttk.Combobox(cont_row, textvariable=self.container_var,
                    values=["mp4", "mkv", "webm"], state="readonly",
                    width=14, font=theme_mod.FONT).pack(side=tk.LEFT)

        playlist_row = tk.Frame(parent, bg=c["bg"])
        playlist_row.pack(fill=tk.X, pady=(2, 6))
        self.playlist_var = tk.BooleanVar(value=False)
        playlist_cb = tk.Checkbutton(playlist_row, text=i18n.t("playlist"),
                      variable=self.playlist_var, font=theme_mod.FONT, bg=c["bg"], fg=c["text"],
                      activebackground=c["bg"], activeforeground=c["text"],
                      selectcolor=c["panel"])
        playlist_cb.pack(anchor=tk.W)
        self._register_text(playlist_cb, "playlist")

        save_path_lbl = tk.Label(parent, text=i18n.t("save_path_label"), font=theme_mod.FONT_B,
                bg=c["bg"], fg=c["text"], anchor="w")
        save_path_lbl.pack(fill=tk.X)
        self._register_text(save_path_lbl, "save_path_label")

        path_input_row = tk.Frame(parent, bg=c["bg"])
        path_input_row.pack(fill=tk.X, pady=(2, 0))

        self.path_entry = tk.Entry(path_input_row, font=theme_mod.FONT, bg=c["card"],
                                   fg=c["text"], insertbackground=c["text"])
        self.path_entry.insert(0, self._config.get("last_save_path", cfg_mod.DEFAULT_CONFIG["last_save_path"]))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        if DND_OK:
            def _on_path_drop(event):
                raw = event.data.strip()
                if raw.startswith("{") and raw.endswith("}"):
                    raw = raw[1:-1]
                first_line = raw.splitlines()[0].strip() if raw else ""
                if first_line and os.path.isdir(first_line):
                    self.path_entry.delete(0, tk.END)
                    self.path_entry.insert(0, first_line)

            self.path_entry.drop_target_register(DND_TEXT)
            self.path_entry.dnd_bind("<<Drop>>", _on_path_drop)

        browse_btn = tk.Button(path_input_row, text=i18n.t("browse_btn"), command=self._browse_folder,
                 font=theme_mod.FONT, relief=tk.FLAT, bg=c["panel"], fg=c["text"],
                 cursor="hand2")
        browse_btn.pack(side=tk.LEFT)
        self._register_text(browse_btn, "browse_btn")

        self.disk_space_lbl = tk.Label(parent, text="", font=("Segoe UI", 7),
                                       fg=c["text_dim"], bg=c["bg"], anchor="w")
        self.disk_space_lbl.pack(fill=tk.X, pady=(2, 8))

        add_queue_btn = tk.Button(parent, text=i18n.t("add_to_queue_btn"), command=self._add_to_queue,
                 bg=theme_mod.GREEN, fg="white", font=theme_mod.FONT_B, relief=tk.FLAT,
                 cursor="hand2", pady=4)
        add_queue_btn.pack(fill=tk.X)
        self._register_text(add_queue_btn, "add_to_queue_btn")

    def _reveal_settings_panel(self):
        """Показывает блок настроек после первой успешной проверки ссылки."""
        if not self.settings_panel.winfo_ismapped():
            self.hint_label.pack_forget()
            self.settings_panel.pack(fill=tk.X, pady=(4, 0))

    def _hide_settings_panel(self):
        """Скрывает блок настроек и возвращает подсказку (после добавления в очередь)."""
        if self.settings_panel.winfo_ismapped():
            self.settings_panel.pack_forget()
            self.hint_label.pack(fill=tk.X, pady=(16, 0))

    def _setup_url_dnd(self):
        def _on_drop(event):
            raw = event.data.strip()
            if raw.startswith("{") and raw.endswith("}"):
                raw = raw[1:-1]
            first_line = raw.splitlines()[0].strip() if raw else ""
            if first_line:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, first_line)
                self._clear_preview()

        self.url_entry.drop_target_register(DND_TEXT)
        self.url_entry.dnd_bind("<<Drop>>", _on_drop)

    # ─────────────────────────────────────────────────────────
    # Окно "Настройки программы" (тема / параллельность / обновление)
    # ─────────────────────────────────────────────────────────

    def _open_settings_window(self):
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_set()
            return

        c = self.colors
        win = tk.Toplevel(self.root)
        win.title(i18n.t("settings_window_title"))
        win.geometry("420x320")
        win.resizable(False, False)
        win.configure(bg=c["bg"])
        self._settings_win = win
        self._register_text(win, "settings_window_title")

        def _on_settings_close():
            self._settings_win = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", _on_settings_close)

        pad = dict(padx=14, pady=8)

        # ── Язык ──
        lang_frame = tk.LabelFrame(win, text=i18n.t("language"), font=theme_mod.FONT,
                                    bg=c["bg"], fg=c["text"], padx=10, pady=8)
        lang_frame.pack(fill=tk.X, **pad)
        self._register_text(lang_frame, "language")

        current_lang = self._config.get("language") or i18n._detect_os_lang()
        self.lang_var = tk.StringVar(value=current_lang)
        lang_cb = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=[("ru", "Русский"), ("en", "English")],
            state="readonly",
            width=14,
            font=theme_mod.FONT,
        )
        # Show readable names but store codes
        lang_cb["values"] = ["Русский", "English"]
        lang_cb.set("Русский" if current_lang == "ru" else "English")

        def _on_lang_change(*_):
            val = self.lang_var.get()
            new_lang = "ru" if val == "Русский" else "en"
            old_lang = self._config.get("language") or i18n._detect_os_lang()
            if new_lang != old_lang:
                self._config["language"] = new_lang
                cfg_mod.save_config(self._config)
                messagebox.showinfo(
                    i18n.t("language"),
                    i18n.t("language_changed")
                )

        lang_cb.bind("<<ComboboxSelected>>", _on_lang_change)
        lang_cb.pack(side=tk.LEFT, padx=(0, 8))

        theme_frame = tk.LabelFrame(win, text=i18n.t("appearance_frame"), font=theme_mod.FONT,
                                    bg=c["bg"], fg=c["text"], padx=10, pady=8)
        theme_frame.pack(fill=tk.X, **pad)
        self._register_text(theme_frame, "appearance_frame")

        self.dark_var = tk.BooleanVar(value=bool(self._config.get("dark_theme")))
        dark_cb = tk.Checkbutton(theme_frame, text=i18n.t("dark_theme"),
                      variable=self.dark_var, command=self._toggle_theme,
                      font=theme_mod.FONT, bg=c["bg"], fg=c["text"],
                      activebackground=c["bg"], activeforeground=c["text"],
                      selectcolor=c["panel"], wraplength=380, justify=tk.LEFT)
        dark_cb.pack(anchor=tk.W)
        self._register_text(dark_cb, "dark_theme")

        perf_frame = tk.LabelFrame(win, text=i18n.t("performance_frame"), font=theme_mod.FONT,
                                   bg=c["bg"], fg=c["text"], padx=10, pady=8)
        perf_frame.pack(fill=tk.X, **pad)
        self._register_text(perf_frame, "performance_frame")

        parallel_row = tk.Frame(perf_frame, bg=c["bg"])
        parallel_row.pack(fill=tk.X)
        parallel_lbl = tk.Label(parallel_row, text=i18n.t("parallel_downloads"), font=theme_mod.FONT,
                bg=c["bg"], fg=c["text"])
        parallel_lbl.pack(side=tk.LEFT)
        self._register_text(parallel_lbl, "parallel_downloads")
        self.parallel_var = tk.StringVar(value=str(self._config.get("max_parallel", 2)))
        parallel_cb = ttk.Combobox(parallel_row, textvariable=self.parallel_var,
                                   values=["1", "2", "3", "4", "5"], state="readonly",
                                   width=4, font=theme_mod.FONT)
        parallel_cb.pack(side=tk.LEFT, padx=(8, 0))
        parallel_cb.bind("<<ComboboxSelected>>", self._on_parallel_change)

        update_frame = tk.LabelFrame(win, text=i18n.t("update_frame"), font=theme_mod.FONT,
                                     bg=c["bg"], fg=c["text"], padx=10, pady=8)
        update_frame.pack(fill=tk.X, **pad)
        self._register_text(update_frame, "update_frame")

        self.version_lbl = tk.Label(update_frame, text=i18n.t("current_version", updater.get_current_version()),
                                    font=theme_mod.FONT, bg=c["bg"], fg=c["text"], anchor="w")
        self.version_lbl.pack(fill=tk.X)
        self._register_text(self.version_lbl, "current_version", updater.get_current_version())

        update_btn_row = tk.Frame(update_frame, bg=c["bg"])
        update_btn_row.pack(fill=tk.X, pady=(6, 0))

        self.check_update_btn = tk.Button(update_btn_row, text=i18n.t("check_updates"),
                                          command=self._check_for_updates,
                                          font=theme_mod.FONT, relief=tk.FLAT,
                                          bg=c["panel"], fg=c["text"], cursor="hand2")
        self.check_update_btn.pack(side=tk.LEFT, padx=(0, 6))
        self._register_text(self.check_update_btn, "check_updates")

        self.do_update_btn = tk.Button(update_btn_row, text=i18n.t("update"),
                                       command=self._perform_update,
                                       font=theme_mod.FONT, relief=tk.FLAT,
                                       bg=c["panel"], fg=c["text"], cursor="hand2",
                                       state=tk.DISABLED)
        self.do_update_btn.pack(side=tk.LEFT)
        self._register_text(self.do_update_btn, "update")

        self.update_status_lbl = tk.Label(update_frame, text="", font=("Segoe UI", 8),
                                          fg=c["text_dim"], bg=c["bg"], anchor="w",
                                          wraplength=380, justify=tk.LEFT)
        self.update_status_lbl.pack(fill=tk.X, pady=(6, 0))

    # ─────────────────────────────────────────────────────────
    # Очередь — правая колонка
    # ─────────────────────────────────────────────────────────

    def _build_queue_section(self, parent):
        c = self.colors

        header = tk.Frame(parent, bg=c["bg"])
        header.pack(fill=tk.X)
        queue_title_lbl = tk.Label(header, text=i18n.t("queue_title"), font=theme_mod.FONT_B,
                bg=c["bg"], fg=c["text"], anchor="w")
        queue_title_lbl.pack(side=tk.LEFT)
        self._register_text(queue_title_lbl, "queue_title")
        self.queue_count_lbl = tk.Label(header, text=i18n.t("queue_count", 0),
                                        font=("Segoe UI", 8), fg=c["text_dim"], bg=c["bg"])
        self.queue_count_lbl.pack(side=tk.RIGHT)
        self._register_text(self.queue_count_lbl, "queue_count", 0)

        canvas_frame = tk.Frame(parent, bg=c["bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        self.queue_canvas = tk.Canvas(canvas_frame, bg=c["panel"], highlightthickness=0)
        scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.queue_canvas.yview)
        self.queue_list_inner = tk.Frame(self.queue_canvas, bg=c["panel"])

        self.queue_list_inner.bind(
            "<Configure>",
            lambda evt: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
        )
        self._canvas_window = self.queue_canvas.create_window(
            (0, 0), window=self.queue_list_inner, anchor="nw")
        self.queue_canvas.configure(yscrollcommand=scroll.set)
        self.queue_canvas.bind(
            "<Configure>",
            lambda evt: self.queue_canvas.itemconfig(self._canvas_window, width=evt.width)
        )

        self.queue_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_wheel(event):
            self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.queue_canvas.bind("<Enter>", lambda e: self.queue_canvas.bind_all("<MouseWheel>", _on_wheel))
        self.queue_canvas.bind("<Leave>", lambda e: self.queue_canvas.unbind_all("<MouseWheel>"))

        btn_row = tk.Frame(parent, bg=c["bg"])
        btn_row.pack(fill=tk.X)
        clear_queue_btn = tk.Button(btn_row, text=i18n.t("clear_queue"), command=self._clear_queue,
                 font=theme_mod.FONT, bg=c["panel"], fg=c["text"], relief=tk.FLAT,
                 cursor="hand2")
        clear_queue_btn.pack(side=tk.RIGHT, pady=(0, 8))
        self._register_text(clear_queue_btn, "clear_queue")

        self.download_btn = tk.Button(parent, text=i18n.t("download_all"), command=self._start_download,
                                      bg=theme_mod.GREEN, fg="white", font=("Segoe UI", 12, "bold"),
                                      relief=tk.FLAT, activebackground=theme_mod.D_GREEN,
                                      cursor="hand2", pady=8)
        self.download_btn.pack(fill=tk.X, pady=(0, 6))
        self._register_text(self.download_btn, "download_all")

        self.style.configure("green.Horizontal.TProgressbar",
                            troughcolor=c["panel"], background=theme_mod.GREEN, thickness=14)

        self.status_label = tk.Label(parent, text="", font=("Segoe UI", 8),
                                     bg=c["bg"], fg=c["text_dim"], anchor="w",
                                     wraplength=560, justify=tk.LEFT)
        self.status_label.pack(fill=tk.X)

    # ─────────────────────────────────────────────────────────
    # Превью / проверка ссылки
    # ─────────────────────────────────────────────────────────

    def _clear_url_and_preview(self):
        self.url_entry.delete(0, tk.END)
        self._pending_title = ""
        self._clear_preview()
        self._hide_settings_panel()

    def _paste_url(self):
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, text)
        self._pending_title = ""
        self._clear_preview()

    def _clear_preview(self, msg: str = ""):
        self.thumb_label.config(image="")
        self.thumb_label.image = None
        self.title_label.config(text=msg or "")
        self.meta_label.config(text="")
        self.host_warning_lbl.config(text="")
        self.quality_cb["values"] = ["Лучшее"]
        self.quality_var.set("Лучшее")

    def _load_preview(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Ошибка", "Вставьте ссылку на видео")
            return

        ok, err = core.validate_url_syntax(url)
        if not ok:
            messagebox.showerror("Некорректная ссылка", err)
            return

        self.check_btn.config(state=tk.DISABLED, text=i18n.t("checking"))
        self._clear_preview(i18n.t("preview_loading"))
        self._fetch_preview_async(url)

    def _fetch_preview_async(self, url: str):
        def _run():
            host_ok, host_name, host_warn = core.check_host_supported(url)
            if host_warn:
                self._gui(lambda: self.host_warning_lbl.config(text=f"⚠ {host_warn}"))

            try:
                with yt_dlp.YoutubeDL({
                    "quiet": True, "no_warnings": True, "skip_download": True,
                    "noplaylist": True,
                }) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as exc:
                self._gui(lambda exc=exc: self._on_preview_failed(f"Не удалось получить превью: {exc}"))
                return

            if info is None:
                self._gui(lambda: self._on_preview_failed("Видео не найдено или недоступно"))
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
            res_list = ["Лучшее"] + [f"{h}p" for h in heights]
            if len(res_list) == 1:
                res_list = list(core.QUALITY_HEIGHTS.keys())

            mins, secs = divmod(int(duration), 60)
            dur_str = f"{mins}:{secs:02d}" if duration else "—"

            img_tk = None
            if PIL_OK and thumb:
                try:
                    req = Request(thumb, headers={"User-Agent": "Mozilla/5.0"})
                    data = urlopen(req, timeout=6).read()
                    img = Image.open(io.BytesIO(data)).convert("RGB").resize((336, 189), Image.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)
                except Exception:
                    pass

            self._gui(lambda: self._show_preview(title, uploader, dur_str, res_list, img_tk, is_playlist))

        threading.Thread(target=_run, daemon=True).start()

    def _on_preview_failed(self, msg: str):
        self.check_btn.config(state=tk.NORMAL, text=i18n.t("check_link"))
        self._clear_preview(msg)

    def _show_preview(self, title, uploader, duration, res_list, img_tk, is_playlist):
        self.check_btn.config(state=tk.NORMAL, text=i18n.t("check_link"))
        self._pending_title = title or ""

        if img_tk:
            self.thumb_label.config(image=img_tk)
            self.thumb_label.image = img_tk
        else:
            self.thumb_label.config(image="")
            self.thumb_label.image = None

        short_title = title if len(title) <= 60 else title[:57] + "…"
        prefix = "[Плейлист] " if is_playlist else ""
        self.title_label.config(text=prefix + short_title)
        self.meta_label.config(text=f"{uploader}  •  {duration}")
        self.quality_cb["values"] = res_list
        self.quality_var.set(res_list[0])

        if is_playlist:
            self.playlist_var.set(True)
            self.host_warning_lbl.config(
                text=f"⚠ {i18n.t('playlist_auto')}")
        else:
            self.playlist_var.set(False)

        self._reveal_settings_panel()

    # ─────────────────────────────────────────────────────────
    # Папка / диск
    # ─────────────────────────────────────────────────────────

    def _browse_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)
            self._config["last_save_path"] = d
            cfg_mod.save_config(self._config)
            self._update_disk_space_label(d)

    def _update_disk_space_label(self, path: str):
        free = core.get_free_space(path)
        if free is None:
            self.disk_space_lbl.config(text="")
            return
        free_gb = free / 1_073_741_824
        self.disk_space_lbl.config(text=f"Свободно на диске: {free_gb:.1f} ГБ")

    # ─────────────────────────────────────────────────────────
    # Настройки: тема / параллельность / обновление
    # ─────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self._config["dark_theme"] = self.dark_var.get()
        cfg_mod.save_config(self._config)
        messagebox.showinfo("Тема изменена",
                            "Новая тема будет применена при следующем запуске программы.")

    def _on_parallel_change(self, *_args):
        try:
            n = max(1, min(5, int(self.parallel_var.get())))
        except ValueError:
            n = 2
        self._config["max_parallel"] = n
        cfg_mod.save_config(self._config)

    def _check_for_updates(self):
        self.check_update_btn.config(state=tk.DISABLED)
        self.update_status_lbl.config(text=i18n.t("checking_updates"), fg=self.colors["text_dim"])

        def _run():
            has_update, current, latest = updater.check_for_update()
            self._gui(lambda: self._on_update_check_done(has_update, current, latest))

        threading.Thread(target=_run, daemon=True).start()

    def _on_update_check_done(self, has_update: bool, current: str, latest: str):
        self.check_update_btn.config(state=tk.NORMAL)
        if has_update:
            self.update_status_lbl.config(
                text=f"Доступна новая версия: {latest} (у вас {current})", fg="#e6a817")
            self.do_update_btn.config(state=tk.NORMAL)
        elif "." in str(latest):
            self.update_status_lbl.config(text=f"У вас актуальная версия ({current})", fg="#27ae60")
            self.do_update_btn.config(state=tk.DISABLED)
        else:
            self.update_status_lbl.config(text=str(latest), fg="#e74c3c")
            self.do_update_btn.config(state=tk.DISABLED)

    def _perform_update(self):
        self.do_update_btn.config(state=tk.DISABLED)
        self.update_status_lbl.config(text=i18n.t("updating"), fg=self.colors["text_dim"])

        def _run():
            ok, msg = updater.perform_update()
            self._gui(lambda: self._on_update_done(ok, msg))

        threading.Thread(target=_run, daemon=True).start()

    def _on_update_done(self, ok: bool, msg: str):
        self.update_status_lbl.config(text=msg, fg="#27ae60" if ok else "#e74c3c")
        if ok:
            self.do_update_btn.config(state=tk.DISABLED)
        else:
            self.do_update_btn.config(state=tk.NORMAL)

    # ─────────────────────────────────────────────────────────
    # Очередь
    # ─────────────────────────────────────────────────────────

    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        ok, err = core.validate_url_syntax(url)
        if not ok:
            messagebox.showerror("Некорректная ссылка", err)
            return

        save_path = self.path_entry.get().strip()
        if not save_path:
            messagebox.showerror("Ошибка", "Сначала укажите папку для сохранения")
            return

        if any(ch in save_path for ch in '<>"|?*') and os.name == "nt":
            messagebox.showerror("Ошибка", "Путь содержит недопустимые символы")
            return

        host_ok, host_name, host_warn = core.check_host_supported(url)
        if host_warn:
            if not messagebox.askyesno(
                "Сайт может не поддерживаться",
                f"{host_warn}.\n\nВсё равно добавить в очередь?"
            ):
                return

        mode = self.mode_var.get()
        quality = self.quality_var.get()
        container = self.container_var.get()
        is_playlist = self.playlist_var.get()

        if save_path != self._config.get("last_save_path"):
            self._config["last_save_path"] = save_path
            cfg_mod.save_config(self._config)

        item = qm.make_item(url, mode, quality, save_path, container, is_playlist, title=self._pending_title or "")
        self.queue_items[item["id"]] = item
        self.item_order.append(item["id"])

        self._render_queue_row(item)

        self.url_entry.delete(0, tk.END)
        self._clear_preview()
        self._hide_settings_panel()
        self._update_queue_count()
        self._update_disk_space_label(save_path)

    def _render_queue_row(self, item: dict):
        c = self.colors
        row = tk.Frame(self.queue_list_inner, bg=c["card"], bd=1, relief=tk.SOLID)
        row.pack(fill=tk.X, pady=2, padx=1)

        top = tk.Frame(row, bg=c["card"])
        top.pack(fill=tk.X, padx=6, pady=(4, 0))

        display_title = item.get("title") or item["url"]
        short_title = display_title if len(display_title) <= 50 else display_title[:47] + "…"
        playlist_tag = " [плейлист]" if item.get("playlist") else ""
        url_lbl = tk.Label(top, text=short_title + playlist_tag, font=("Segoe UI", 8, "bold"),
                           bg=c["card"], fg=c["text"], anchor="w")
        url_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        action_frame = tk.Frame(top, bg=c["card"])
        action_frame.pack(side=tk.RIGHT)

        open_btn = tk.Button(action_frame, text="📁", font=("Segoe UI", 8), relief=tk.FLAT,
                             bg=c["card"], cursor="hand2", state=tk.DISABLED,
                             command=lambda: self._open_item_folder(item["id"]))
        open_btn.pack(side=tk.LEFT, padx=(0, 2))

        cancel_btn = tk.Button(action_frame, text="⏹", font=("Segoe UI", 8), relief=tk.FLAT,
                               bg=c["card"], fg="#e6a817", cursor="hand2", state=tk.DISABLED,
                               command=lambda: self._cancel_item(item["id"]))
        cancel_btn.pack(side=tk.LEFT, padx=(0, 2))

        del_btn = tk.Button(action_frame, text="✕", font=("Segoe UI", 8), relief=tk.FLAT,
                            bg=c["card"], fg="#e74c3c", cursor="hand2",
                            command=lambda: self._remove_item(item["id"]))
        del_btn.pack(side=tk.LEFT)

        bottom = tk.Frame(row, bg=c["card"])
        bottom.pack(fill=tk.X, padx=6, pady=(0, 2))

        info_text = (f"{qm.MODE_LABELS[item['mode']]}  •  {item['quality']}  •  "
                    f"{os.path.basename(os.path.normpath(item['save_path'])) or item['save_path']}")
        tk.Label(bottom, text=info_text, font=("Segoe UI", 7),
                fg=c["text_dim"], bg=c["card"], anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        status_lbl = tk.Label(bottom, text=qm.STATUS_LABELS["pending"], font=("Segoe UI", 7, "bold"),
                              fg=qm.STATUS_COLORS["pending"], bg=c["card"])
        status_lbl.pack(side=tk.RIGHT)

        pbar_frame = tk.Frame(row, bg=c["card"])
        pbar_frame.pack(fill=tk.X, padx=6, pady=(0, 4))

        item_style_name = f"item{item['id']}.Horizontal.TProgressbar"
        self.style.configure(item_style_name, troughcolor=c["panel"],
                            background=theme_mod.GREEN, thickness=6)
        item_progress = ttk.Progressbar(pbar_frame, mode="determinate", style=item_style_name)
        item_progress.pack(fill=tk.X)

        item["_row"] = row
        item["_status_lbl"] = status_lbl
        item["_del_btn"] = del_btn
        item["_cancel_btn"] = cancel_btn
        item["_open_btn"] = open_btn
        item["_progress_bar"] = item_progress

    def _open_item_folder(self, item_id: str):
        item = self.queue_items.get(item_id)
        if not item:
            return
        final_path = item.get("final_path")
        folder = final_path if (final_path and os.path.isdir(final_path)) else item["save_path"]
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror(i18n.t("error"), i18n.t("open_folder_error", e))

    def _cancel_item(self, item_id: str):
        item = self.queue_items.get(item_id)
        if not item or item["status"] != qm.STATUS_DOWNLOADING:
            return
        item["_cancel_flag"]["cancelled"] = True
        item["_status_lbl"].config(text=i18n.t("cancelling"), fg="#e6a817")

    def _remove_item(self, item_id: str):
        item = self.queue_items.get(item_id)
        if not item:
            return
        if item["status"] == qm.STATUS_DOWNLOADING:
            messagebox.showwarning(i18n.t("error"),
                                  i18n.t("cannot_remove_downloading"))
            return

        # Если загрузка была отменена — предложить удалить частичный файл с диска
        partial = item.get("_partial_path")
        if partial and os.path.exists(partial):
            if messagebox.askyesno(
                i18n.t("remove_partial_title"),
                i18n.t("remove_partial", partial)
            ):
                try:
                    os.remove(partial)
                except OSError as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить файл:\n{e}")

        item["_row"].destroy()
        del self.queue_items[item_id]
        self.item_order.remove(item_id)
        self._update_queue_count()
        self._save_queue_to_config()

    def _clear_queue(self):
        if any(it["status"] == qm.STATUS_DOWNLOADING for it in self.queue_items.values()):
            messagebox.showwarning("Нельзя очистить",
                                  "Дождитесь окончания текущей загрузки (или отмените её)")
            return
        for item_id in list(self.item_order):
            item = self.queue_items.get(item_id)
            if item and item.get("_row"):
                try:
                    item["_row"].destroy()
                except Exception:
                    pass
            partial = (item or {}).get("_partial_path")
            if partial and os.path.exists(partial):
                try:
                    os.remove(partial)
                except OSError:
                    pass
        self.queue_items.clear()
        self.item_order.clear()
        self._update_queue_count()
        self._save_queue_to_config()

    def _update_queue_count(self):
        n = len(self.item_order)
        self.queue_count_lbl.config(text=f"Элементов в очереди: {n}")

    def _save_queue_to_config(self):
        to_save = []
        for item_id in self.item_order:
            item = self.queue_items[item_id]
            if item["status"] in (qm.STATUS_PENDING, qm.STATUS_ERROR,
                                  qm.STATUS_CANCELLED, qm.STATUS_DOWNLOADING):
                to_save.append(qm.item_to_dict_for_save(item))
        self._config["saved_queue"] = to_save
        cfg_mod.save_config(self._config)

    def _restore_queue_from_config(self):
        saved = self._config.get("saved_queue") or []
        for entry in saved:
            item = qm.item_from_saved_dict(entry)
            if item is None:
                continue
            self.queue_items[item["id"]] = item
            self.item_order.append(item["id"])
            self._render_queue_row(item)
        if saved:
            self._update_queue_count()

    # ─────────────────────────────────────────────────────────
    # Загрузка
    # ─────────────────────────────────────────────────────────

    def _make_progress_hook(self, item_id: str, cancel_flag: dict):
        def hook(d):
            if cancel_flag.get("cancelled"):
                raise yt_dlp.utils.DownloadCancelled("Отменено пользователем")

            if d["status"] == "downloading":
                # Запоминаем путь к частичному файлу — пригодится при
                # отмене + удалении элемента, чтобы убрать его с диска
                partial = d.get("tmpfilename") or d.get("filename")
                if partial:
                    item = self.queue_items.get(item_id)
                    if item is not None:
                        item["_partial_path"] = partial

                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0

                pct = (downloaded / total * 100) if total else 0
                speed_str = f"{speed / 1_048_576:.1f} МБ/с" if speed else "—"
                eta_str = f"{eta}с" if eta else "—"
                txt = f"{pct:.0f}%  •  {speed_str}  •  осталось {eta_str}"

                self._gui(lambda p=pct, t=txt: self._set_item_progress(item_id, p, t, "#1a6fc4"))

            elif d["status"] == "finished":
                self._gui(lambda: self._set_item_progress(item_id, 100, "Обработка файла…", "#e6a817"))

        return hook

    def _set_item_progress(self, item_id: str, pct: float, text: str, color: str):
        item = self.queue_items.get(item_id)
        if not item:
            return
        bar = item.get("_progress_bar")
        lbl = item.get("_status_lbl")
        if bar is not None:
            bar["value"] = pct
        if lbl is not None:
            lbl.config(text=text, fg=color)

    def _set_item_status(self, item_id: str, status: str, error: str = None):
        item = self.queue_items.get(item_id)
        if not item:
            return
        item["status"] = status
        item["error"] = error
        lbl = item["_status_lbl"]
        lbl.config(text=qm.STATUS_LABELS[status], fg=qm.STATUS_COLORS[status])

        is_downloading = status == qm.STATUS_DOWNLOADING
        item["_del_btn"].config(state=tk.DISABLED if is_downloading else tk.NORMAL)
        item["_cancel_btn"].config(state=tk.NORMAL if is_downloading else tk.DISABLED)
        item["_open_btn"].config(state=tk.NORMAL if status == qm.STATUS_DONE else tk.DISABLED)

        if status == qm.STATUS_DONE:
            item["_progress_bar"]["value"] = 100
        elif status in (qm.STATUS_ERROR, qm.STATUS_CANCELLED, qm.STATUS_PENDING):
            item["_progress_bar"]["value"] = 0

    def _download_one_with_disk_check(self, item: dict) -> tuple[bool, str, str]:
        """Перед скачиванием проверяет место на диске (best-effort оценка)."""
        try:
            fmt = core.build_format_string(item["mode"], item["quality"])
            size = core.estimate_download_size(item["url"], fmt)
            ok, err = core.check_disk_space(item["save_path"], size)
            if not ok:
                return False, err, ""
        except Exception:
            pass  # оценка размера не критична — продолжаем без неё

        hook = self._make_progress_hook(item["id"], item["_cancel_flag"])
        return core.download_one(item, hook)

    def _download_worker(self, item_ids: list[str], max_parallel: int):
        total = len(item_ids)
        success_count = 0
        fail_count = 0
        cancelled_count = 0
        lock = threading.Lock()

        def _run_one(item_id):
            nonlocal success_count, fail_count, cancelled_count
            item = self.queue_items.get(item_id)
            if not item:
                return

            self._gui(lambda i=item_id: self._set_item_status(i, qm.STATUS_DOWNLOADING))
            self._gui(lambda i=item_id: self._set_item_progress(i, 0, i18n.t("preparing"), "#1a6fc4"))

            ok, err, final_path = self._download_one_with_disk_check(item)

            with lock:
                if ok:
                    success_count += 1
                    item["final_path"] = final_path
                    self._gui(lambda i=item_id: self._set_item_status(i, qm.STATUS_DONE))
                elif err == "Отменено пользователем":
                    cancelled_count += 1
                    self._gui(lambda i=item_id: self._set_item_status(i, qm.STATUS_CANCELLED))
                else:
                    fail_count += 1
                    self._gui(lambda i=item_id, e=err: self._set_item_status(i, qm.STATUS_ERROR, e))

        self._gui(lambda: self.status_label.config(
            text=f"Загрузка {total} элементов (до {max_parallel} одновременно)…",
            fg="#1a6fc4"))

        with ThreadPoolExecutor(max_workers=max(1, max_parallel)) as executor:
            futures = [executor.submit(_run_one, i) for i in item_ids]
            for f in as_completed(futures):
                f.result()

        def _final_report():
            if fail_count == 0 and cancelled_count == 0 and success_count > 0:
                self.status_label.config(text=f"Готово: успешно скачано {success_count} из {total}", fg="#27ae60")
                self.tray.notify("Загрузка завершена", f"Скачано файлов: {success_count}")
                messagebox.showinfo("Готово", f"Успешно скачано: {success_count} из {total}")
            elif success_count == 0 and cancelled_count == 0:
                self.status_label.config(text=f"Ничего не скачано: {fail_count} ошибок", fg="#e74c3c")
                self.tray.notify("Ошибка загрузки", "Ни один файл не был скачан")
                errors = "\n".join(
                    f"- {self.queue_items[i]['url'][:60]}: {self.queue_items[i]['error']}"
                    for i in item_ids if self.queue_items.get(i) and self.queue_items[i]["status"] == qm.STATUS_ERROR
                )
                messagebox.showerror("Ничего не скачано", f"Не удалось скачать ни одного файла.\n\n{errors[:1500]}")
            else:
                parts = [f"успешно: {success_count}"]
                if fail_count:
                    parts.append(f"с ошибкой: {fail_count}")
                if cancelled_count:
                    parts.append(f"отменено: {cancelled_count}")
                self.status_label.config(text=i18n.t("completed", ", ".join(parts)), fg="#e6a817")
                self.tray.notify("Загрузка завершена", ", ".join(parts))
                messagebox.showinfo("Завершено", "Завершено — " + ", ".join(parts))

            self.download_btn.config(state=tk.NORMAL)
            self._save_queue_to_config()

        self._gui(_final_report)

    def _start_download(self):
        pending_ids = [i for i in self.item_order
                      if self.queue_items[i]["status"] in
                      (qm.STATUS_PENDING, qm.STATUS_ERROR, qm.STATUS_CANCELLED)]

        if not pending_ids:
            if not self.item_order:
                messagebox.showerror("Ошибка", "Очередь пуста. Добавьте хотя бы одну ссылку.")
            else:
                messagebox.showinfo("Нечего качать", "Все элементы уже скачаны. Удалите их или добавьте новые ссылки.")
            return

        for i in pending_ids:
            self.queue_items[i]["_cancel_flag"]["cancelled"] = False

        max_parallel = int(self._config.get("max_parallel", 2))

        self.download_btn.config(state=tk.DISABLED)
        self.status_label.config(text=i18n.t("preparing"), fg="#1a6fc4")

        threading.Thread(target=self._download_worker, args=(pending_ids, max_parallel), daemon=True).start()

    def run(self):
        self.root.mainloop()


def main():
    app = App()
    app.run()