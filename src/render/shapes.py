"""几何绘制工具：封装 pygame.draw，提供游戏常用图形。"""

import math
import pygame
from typing import Sequence

Color = tuple[int, ...]


# ── 基础图形 ──────────────────────────────────────────

def circle(surface: pygame.Surface, color: Color,
           cx: float, cy: float, radius: float, width: int = 0) -> None:
    pygame.draw.circle(surface, color, (int(cx), int(cy)), max(1, int(radius)), width)


def rect(surface: pygame.Surface, color: Color,
         x: float, y: float, w: float, h: float,
         width: int = 0, border_radius: int = 0) -> None:
    pygame.draw.rect(surface, color,
                     pygame.Rect(int(x), int(y), int(w), int(h)),
                     width, border_radius=border_radius)


def polygon(surface: pygame.Surface, color: Color,
            points: Sequence[tuple[float, float]], width: int = 0) -> None:
    pts = [(int(x), int(y)) for x, y in points]
    if len(pts) >= 3:
        pygame.draw.polygon(surface, color, pts, width)


def line(surface: pygame.Surface, color: Color,
         x1: float, y1: float, x2: float, y2: float, width: int = 1) -> None:
    pygame.draw.line(surface, color,
                     (int(x1), int(y1)), (int(x2), int(y2)), max(1, width))


def lines(surface: pygame.Surface, color: Color,
          closed: bool, points: Sequence[tuple[float, float]], width: int = 1) -> None:
    pts = [(int(x), int(y)) for x, y in points]
    if len(pts) >= 2:
        pygame.draw.lines(surface, color, closed, pts, max(1, width))


def ring(surface: pygame.Surface, color: Color,
         cx: float, cy: float, radius: float, thickness: int = 2) -> None:
    pygame.draw.circle(surface, color, (int(cx), int(cy)), max(1, int(radius)), thickness)


# ── 游戏专用图形 ──────────────────────────────────────

def diamond(surface: pygame.Surface, color: Color,
            cx: float, cy: float, hw: float, hh: float, width: int = 0) -> None:
    """菱形（经验宝石常用）。"""
    polygon(surface, color,
            [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)], width)


def triangle_up(surface: pygame.Surface, color: Color,
                cx: float, cy: float, size: float, width: int = 0) -> None:
    h = size * math.sqrt(3) / 2
    polygon(surface, color,
            [(cx, cy - h * 2/3), (cx + size/2, cy + h/3), (cx - size/2, cy + h/3)], width)


def triangle_down(surface: pygame.Surface, color: Color,
                  cx: float, cy: float, size: float, width: int = 0) -> None:
    h = size * math.sqrt(3) / 2
    polygon(surface, color,
            [(cx, cy + h * 2/3), (cx + size/2, cy - h/3), (cx - size/2, cy - h/3)], width)


def regular_polygon(surface: pygame.Surface, color: Color,
                    cx: float, cy: float, radius: float, sides: int,
                    angle_offset: float = 0.0, width: int = 0) -> None:
    """正多边形。angle_offset 为旋转偏移（弧度）。"""
    pts = []
    for i in range(sides):
        a = angle_offset + 2 * math.pi * i / sides
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    polygon(surface, color, pts, width)


def irregular_polygon(surface: pygame.Surface, color: Color,
                      cx: float, cy: float, base_r: float, sides: int,
                      variance: float, seed_hash: int, width: int = 0) -> None:
    """不规则多边形（石块、障碍物等）。variance 0–1 控制形变程度。"""
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        noise = 1.0 - variance + variance * ((seed_hash >> (i * 5) & 0x1F) / 31.0)
        r = base_r * noise
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    polygon(surface, color, pts, width)


# ── 进度条 ────────────────────────────────────────────

def bar(surface: pygame.Surface,
        x: float, y: float, w: float, h: float,
        value: float, max_value: float,
        fg_color: Color, bg_color: Color,
        border_color: Color | None = None,
        border_radius: int = 3) -> None:
    """通用进度条（HP/XP/Boss 血条）。"""
    bx, by, bw, bh = int(x), int(y), max(1, int(w)), max(1, int(h))
    pygame.draw.rect(surface, bg_color,
                     pygame.Rect(bx, by, bw, bh), border_radius=border_radius)
    if max_value > 0:
        fill_w = max(0, int(bw * min(value, max_value) / max_value))
        if fill_w > 0:
            pygame.draw.rect(surface, fg_color,
                             pygame.Rect(bx, by, fill_w, bh),
                             border_radius=border_radius)
    if border_color:
        pygame.draw.rect(surface, border_color,
                         pygame.Rect(bx, by, bw, bh), 1, border_radius=border_radius)


# ── 特效辅助 ──────────────────────────────────────────

def glow_circle(surface: pygame.Surface, color: Color,
                cx: float, cy: float, radius: float,
                layers: int = 3, alpha_start: int = 70) -> None:
    """发光圆（多层半透明叠加）。"""
    r, g, b = color[0], color[1], color[2]
    for i in range(layers, 0, -1):
        r_outer = int(radius * (1 + i * 0.5))
        alpha   = max(0, min(255, alpha_start // i))
        glow    = pygame.Surface((r_outer * 2 + 2, r_outer * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (r, g, b, alpha),
                           (r_outer + 1, r_outer + 1), r_outer)
        surface.blit(glow, (int(cx) - r_outer - 1, int(cy) - r_outer - 1),
                     special_flags=pygame.BLEND_RGBA_ADD)


def cross(surface: pygame.Surface, color: Color,
          cx: float, cy: float, size: float, width: int = 2) -> None:
    """十字形。"""
    h = size / 2
    line(surface, color, cx - h, cy, cx + h, cy, width)
    line(surface, color, cx, cy - h, cx, cy + h, width)
