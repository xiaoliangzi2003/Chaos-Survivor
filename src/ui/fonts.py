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

    has_spaces = " " in text
    words = text.split(" ") if has_spaces else [text]

    lines: list[str] = []
    line = ""

    for wi, word in enumerate(words):
        sep = " " if (has_spaces and line) else ""
        trial = line + sep + word
        if font.size(trial)[0] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
                if len(lines) >= max_lines:
                    return lines[:max_lines]
                line = ""
            if font.size(word)[0] <= max_width:
                line = word
            else:
                for ch in word:
                    trial_c = line + ch
                    if font.size(trial_c)[0] <= max_width:
                        line = trial_c
                    else:
                        if line:
                            lines.append(line)
                            if len(lines) >= max_lines:
                                return lines[:max_lines]
                        line = ch

    if line and len(lines) < max_lines:
        lines.append(line)
    return lines[:max_lines] if lines else [""]


def clear_cache() -> None:
    _cache.clear()
    global _resolved_font_path
    _resolved_font_path = None
