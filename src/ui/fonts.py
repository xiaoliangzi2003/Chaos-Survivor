"""字体管理器：统一加载支持中文的字体，全局缓存避免重复创建。"""

import pygame
from typing import Optional

# 中文字体候选列表（按优先级）
_CN_FONT_CANDIDATES = [
    "microsoftyahei",   # 微软雅黑
    "microsoftyaheui",
    "simhei",           # 黑体
    "dengxian",         # 等线
    "simsun",           # 宋体
    "fangsong",         # 仿宋
    "kaiti",            # 楷体
    "nsimsun",
]

_resolved_font_name: Optional[str] = None
_cache: dict[tuple[int, bool], pygame.font.Font] = {}


def _resolve() -> Optional[str]:
    """找到系统中第一个可用的中文字体名。"""
    global _resolved_font_name
    if _resolved_font_name is not None:
        return _resolved_font_name
    available = set(pygame.font.get_fonts())
    for name in _CN_FONT_CANDIDATES:
        if name in available:
            _resolved_font_name = name
            return name
    return None


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """
    获取指定大小的中文字体（带缓存）。
    找不到中文字体时回退到 pygame 默认字体（中文会显示为方块，但不崩溃）。
    """
    key = (size, bold)
    if key in _cache:
        return _cache[key]

    name = _resolve()
    if name:
        font = pygame.font.SysFont(name, size, bold=bold)
    else:
        font = pygame.font.SysFont(None, size, bold=bold)

    _cache[key] = font
    return font


def clear_cache() -> None:
    """重新初始化时清除缓存（一般不需要手动调用）。"""
    _cache.clear()
    global _resolved_font_name
    _resolved_font_name = None
