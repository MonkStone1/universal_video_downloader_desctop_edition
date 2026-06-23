"""
Загрузчик видео/аудио — точка входа.

Зависимости:
  pip install yt-dlp pillow pystray tkinterdnd2

  (pillow, pystray, tkinterdnd2 опциональны - без них приложение
  работает, но без превью-картинок, системного трея и drag & drop
  соответственно)

Структура проекта:
  downloader.py           - точка входа (этот файл)
  app/config.py           - сохранение/загрузка настроек между запусками
  app/queue_model.py      - модель элемента очереди (данные, без GUI)
  app/core/             - логика yt-dlp: формат, скачивание, проверка
                             хоста, проверка места на диске
  app/updater.py          - проверка и обновление версии yt-dlp
  app/theme.py             - цветовые схемы (светлая/тёмная)
  app/tray.py              - системный трей
  app/gui.py                - построение интерфейса
"""

from app.gui import main

if __name__ == "__main__":
    main()
