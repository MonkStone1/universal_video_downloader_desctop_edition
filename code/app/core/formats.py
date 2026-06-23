"""
Построение строки формата для yt-dlp и проверка места на диске.
"""

QUALITY_HEIGHTS = {
    "Лучшее": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

DISK_SPACE_SAFETY_MARGIN = 1.3


def build_format_string(mode: str, quality: str) -> str:
    """
    Построить строку format для yt-dlp.

    ВАЖНО про YouTube и качество:
    720p и выше YouTube отдаёт ТОЛЬКО раздельными потоками
    (видео без звука + аудио без видео) — требует FFmpeg для слияния.
    480p и ниже есть прогрессивные форматы (video+audio в одном файле).
    Поэтому `best[height<=720]` вернёт максимум 480p, игнорируя раздельные
    потоки — это и был баг. Правильно: всегда предпочитать bestvideo+bestaudio
    с фильтром высоты, а как запасной вариант брать любой доступный формат
    с нужной высотой (в т.ч. прогрессивный), и только в крайнем случае
    падать на лучшее из доступного.

    Используем \"/\" (или-цепочки) для совместимости с сайтами, которые не
    поддерживают раздельные потоки и/или не имеют FFmpeg.
    """
    # Determine height: if quality ends with 'p' and the prefix is integer, use it;
    # otherwise lookup in QUALITY_HEIGHTS (for "Лучшее" etc.)
    height = None
    if quality.endswith('p'):
        try:
            height = int(quality[:-1])
        except ValueError:
            pass
    if height is None:
        height = QUALITY_HEIGHTS.get(quality)

    if mode == "audio":
        return "bestaudio/best"

    if height is None:
        # "Лучшее" — без ограничений по высоте
        if mode == "video_only":
            return "bestvideo[vcodec!=none]/bestvideo/best"
        return "bestvideo+bestaudio/best"

    # Конкретная высота — фильтруем оба потока по высоте
    if mode == "video_only":
        return (
            f"bestvideo[height<={height}][vcodec!=none]"
            f"/bestvideo[height<={height}]"
            f"/bestvideo[vcodec!=none]"
            f"/best[height<={height}]"
            f"/best"
        )

    return (
        f"bestvideo[height<={height}]+bestaudio"
        f"/bestvideo[height<={height}]+bestaudio[abr<=128]"
        f"/best[height<={height}]"
        f"/bestvideo+bestaudio"
        f"/best"
    )