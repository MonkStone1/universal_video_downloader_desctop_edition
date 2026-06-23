"""Цветовые схемы для светлой/тёмной темы."""

GREEN = "#2ed573"
D_GREEN = "#20bf6b"
FONT = ("Segoe UI", 9)
FONT_B = ("Segoe UI", 10, "bold")

LIGHT_COLORS = {
    "bg": "#f0f2f5",
    "panel": "#e3e6eb",
    "card": "#ffffff",
    "text": "#1a1a1a",
    "text_dim": "#636e72",
}

DARK_COLORS = {
    "bg": "#1e1f22",
    "panel": "#2b2d31",
    "card": "#313338",
    "text": "#e3e5e8",
    "text_dim": "#9aa0a6",
}


def get_colors(dark: bool) -> dict:
    return dict(DARK_COLORS if dark else LIGHT_COLORS)
