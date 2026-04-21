"""字体与中文文本换行工具。"""

from __future__ import annotations

from typing import Optional

import pygame

_FONT_CANDIDATES = [
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "SimHei",
    "DengXian",
    "SimSun",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
    "Arial Unicode MS",
]

_resolved_font_path: Optional[str] = None
_cache: dict[tuple[int, bool], pygame.font.Font] = {}


def _resolve_font_path() -> Optional[str]:
    global _resolved_font_path
    if _resolved_font_path is not None:
        return _resolved_font_path

    for name in _FONT_CANDIDATES:
        path = pygame.font.match_font(name)
        if path:
            _resolved_font_path = path
            return path
    return None


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    font_path = _resolve_font_path()
    if font_path:
        font = pygame.font.Font(font_path, size)
        font.set_bold(bold)
    else:
        font = pygame.font.SysFont(None, size, bold=bold)

    _cache[key] = font
    return font


def wrap_text(font: pygame.font.Font, text: str, max_width: int, max_lines: int = 4) -> list[str]:
    if not text:
        return [""]

    if " " in text:
        tokens = text.split(" ")
        joiner = " "
    else:
        tokens = list(text)
        joiner = ""

    lines: list[str] = []
    current = tokens[0]
    for token in tokens[1:]:
        trial = f"{current}{joiner}{token}" if joiner else f"{current}{token}"
        if font.size(trial)[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = token
            if len(lines) >= max_lines - 1:
                break
    lines.append(current)
    return lines[:max_lines]


def clear_cache() -> None:
    _cache.clear()
    global _resolved_font_path
    _resolved_font_path = None
