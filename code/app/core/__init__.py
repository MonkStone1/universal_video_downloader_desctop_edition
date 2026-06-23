"""
Ядро загрузчика: работа с yt-dlp, форматы, проверки.
"""

from app.core.formats import QUALITY_HEIGHTS, build_format_string
from app.core.download import download_one, get_ydl_options
from app.core.metadata import (
    validate_url_syntax,
    check_host_supported,
    get_free_space,
    estimate_download_size,
    check_disk_space,
)

__all__ = [
    "QUALITY_HEIGHTS",
    "build_format_string",
    "download_one",
    "get_ydl_options",
    "validate_url_syntax",
    "check_host_supported",
    "get_free_space",
    "estimate_download_size",
    "check_disk_space",
]
