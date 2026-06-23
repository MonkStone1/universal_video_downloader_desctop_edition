# Video Downloader

Cross-platform video and audio downloader with a graphical interface built on Python + Tkinter.

## Features

- Download video and audio from YouTube and hundreds of other sites (via yt-dlp)
- Quality selection (360p – 1080p+) and container format (MP4, MKV, WebM)
- Download single videos or entire playlists
- Preview: thumbnail, title, duration, author
- Batch download queue with parallelism of 1–5 files simultaneously
- Free disk space check before downloading
- Localization: Russian and English languages
  - Automatic selection based on OS language
  - Language change in settings (applies on next launch)
- Dark/Light theme
- System tray (minimize to tray during download)
- yt-dlp version check and update
- Windows installer (Inno Setup) with language selection and optional VLC installation

## Screenshots

_Screenshots will be added later_

## Quick Start

### Requirements

- Python 3.9+
- pip

### Install Dependencies

```bash
pip install yt-dlp pillow pystray tkinterdnd2
```

> `pillow`, `pystray`, `tkinterdnd2` — optional. The application works without them, but without preview, system tray, and drag & drop respectively.

### Run from Source

```bash
python downloader.py
```

## Building .exe (Windows)

### 1. Build Executable

```bash
build.bat
```

Result: `downloader.exe`

### 2. Build Installer

```bash
build_installer_only.bat
```

Result: `installer\VideoDownloader-Setup.exe`

## Project Structure

```
.
├── downloader.py                 # Entry point
├── build (5).bat                 # Build .exe (Nuitka)
├── build_installer_only.bat      # Build installer (Inno Setup)
├── downloader-installer.iss      # Inno Setup script
├── icon.ico                      # Application icon
├── ffmpeg.exe                    # FFmpeg (video+audio muxing)
├── ffprobe.exe                   # FFprobe (stream inspection)
├── vlc-3.0.23-win64.exe          # VLC (optional, for HEVC)
└── app/
    ├── __init__.py
    ├── config.py                 # Settings (JSON, %APPDATA%)
    ├── gui/
    │   ├── __init__.py           # Re-exports App, main
    │   ├── app.py                # Main App class and entry point main()
    │   ├── builders.py           # UI widget construction
    │   ├── handlers.py           # Event handlers
    │   ├── preview.py            # Video preview
    │   ├── settings.py           # Settings window
    │   ├── queue.py              # Queue management
    │   └── download.py           # Download launching
    ├── core/
    │   ├── __init__.py           # Public core API
    │   ├── formats.py            # Format string building for yt-dlp
    │   ├── download.py           # Download logic
    │   └── metadata.py           # URL validation, host check, disk space
    ├── i18n.py                   # Localization (ru / en)
    ├── queue_model.py            # Queue item model
    ├── theme.py                  # Color schemes (light/dark)
    ├── tray.py                   # System tray
    └── updater.py                # yt-dlp update check
```

## Settings

The application stores settings in `%APPDATA%\VideoDownloader\config.json`:

```json
{
  "last_save_path": "C:\\Users\\...\\Videos",
  "container_format": "mp4",
  "dark_theme": false,
  "max_parallel": 2,
  "language": "ru",
  "saved_queue": []
}
```

## Building from Source

### Build Dependencies

- Nuitka
- Inno Setup 6
- FFmpeg / FFprobe
- yt-dlp (installed automatically before build)

### Process

1. `build.bat` compiles `downloader.py` into `downloader.exe` via Nuitka
2. `build_installer_only.bat` runs Inno Setup and packages `downloader.exe` + `ffmpeg.exe` + `ffprobe.exe` + `vlc` into `VideoDownloader-Setup.exe`

## License

MIT

# Видеозагрузчик

Кроссплатформенный загрузчик видео и аудио с графическим интерфейсом на Python + Tkinter.

## Возможности

- Скачивание видео и аудио с YouTube и сотен других сайтов (через yt-dlp)
- Выбор качества (360p – 1080p+) и контейнера (MP4, MKV, WebM)
- Скачивание отдельных видео или целых плейлистов
- Превью: миниатюра, название, длительность, автор
- Пакетная очередь загрузок с параллельностью 1–5 файлов одновременно
- Проверка свободного места на диске перед скачиванием
- Локализация: русский и английский языки
  - Автовыбор по языку ОС
  - Смена языка в настройках (событие применяется при следующем запуске)
- Темная/светлая тема
- Системный трей (сворачивание в трей во время загрузки)
- Проверка и обновление yt-dlp
- Установщик Windows (Inno Setup) с выбором языка и опциональной установкой VLC

## Скриншоты

_Скриншоты будут добавлены позже_

## Быстрый старт

### Требования

- Python 3.9+
- pip

### Установка зависимостей

```bash
pip install yt-dlp pillow pystray tkinterdnd2
```

> `pillow`, `pystray`, `tkinterdnd2` — опциональны. Без них приложение работает, но без превью, системного трея и drag & drop соответственно.

### Запуск из исходников

```bash
python downloader.py
```

## Сборка .exe (Windows)

### 1. Собрать исполняемый файл

```bash
build.bat
```

Результат: `downloader.exe`

### 2. Собрать установщик

```bash
build_installer_only.bat
```

Результат: `installer\VideoDownloader-Setup.exe`

## Структура проекта

```
.
├── downloader.py                 # Точка входа
├── build.bat                 # Сборка .exe (Nuitka)
├── build_installer_only.bat      # Сборка установщика (Inno Setup)
├── downloader-installer.iss      # Скрипт Inno Setup
├── icon.ico                      # Иконка приложения
├── ffmpeg.exe                    # FFmpeg (склеивание видео+аудио)
├── ffprobe.exe                   # FFprobe (проверка потоков)
├── vlc-3.0.23-win64.exe          # VLC (опционально, для HEVC)
└── app/
    ├── __init__.py
    ├── config.py                 # Настройки (JSON, %APPDATA%)
    ├── gui/
    │   ├── __init__.py           # Re-exports App, main
    │   ├── app.py                # Основной класс App и точка входа main()
    │   ├── builders.py           # Построение виджетов интерфейса
    │   ├── handlers.py           # Обработчики событий
    │   ├── preview.py            # Превью видео
    │   ├── settings.py           # Окно настроек
    │   ├── queue.py              # Управление очередью
    │   └── download.py           # Запуск загрузок
    ├── core/
    │   ├── __init__.py           # Публичный API ядра
    │   ├── formats.py            # Построение format‑строк для yt-dlp
    │   ├── download.py           # Логика скачивания
    │   └── metadata.py           # Валидация URL, проверка хоста, место на диске
    ├── i18n.py                   # Локализация (ru / en)
    ├── queue_model.py            # Модель элемента очереди
    ├── theme.py                  # Цветовые схемы (светлая/тёмная)
    ├── tray.py                   # Системный трей
    └── updater.py                # Проверка обновления yt-dlp
```

## Настройки

Приложение хранит настройки в `%APPDATA%\VideoDownloader\config.json`:

```json
{
  "last_save_path": "C:\\Users\\...\\Videos",
  "container_format": "mp4",
  "dark_theme": false,
  "max_parallel": 2,
  "language": "ru",
  "saved_queue": []
}
```

## Сборка из исходников

### Зависимости для сборки

- Nuitka
- Inno Setup 6
- FFmpeg / FFprobe
- yt-dlp (ставится автоматически перед сборкой)

### Процесс

1. `build.bat` компилирует `downloader.py` в `downloader.exe` через Nuitka
2. `build_installer_only.bat` запускает Inno Setup и упаковывает `downloader.exe` + `ffmpeg.exe` + `ffprobe.exe` + `vlc` в `VideoDownloader-Setup.exe`

## Лицензия

MIT
