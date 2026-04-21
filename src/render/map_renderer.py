"""地图渲染器：程序化绘制有限世界地图与边界。"""

from __future__ import annotations

import math

import pygame

from src.core.camera import Camera
from src.core.config import (
    MAP_THEMES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TILE_SIZE,
    WORLD_BOTTOM,
    WORLD_LEFT,
    WORLD_RIGHT,
    WORLD_TOP,
)
from src.render import shapes

_DECO_THRESHOLD = 20


def _tile_hash(tx: int, ty: int, salt: int = 0) -> int:
    h = (tx * 374761393 + ty * 668265263 + salt * 1000003) & 0xFFFF_FFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFF_FFFF
    return h ^ (h >> 16)


class MapRenderer:
    MARGIN = 2

    def __init__(self, theme_name: str, seed: int = 0) -> None:
        self.theme_name = theme_name
        self._theme = MAP_THEMES[theme_name]
        self._seed = seed
        self._tiles = self._bake_tiles()

    @property
    def world_bounds(self) -> tuple[float, float, float, float]:
        return (WORLD_LEFT, WORLD_TOP, WORLD_RIGHT, WORLD_BOTTOM)

    def _bake_tiles(self) -> list[pygame.Surface]:
        tiles = []
        for base_color in (self._theme["tile1"], self._theme["tile2"]):
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
            surf.fill(base_color)
            r, g, b = base_color
            dark = (max(0, r - 18), max(0, g - 18), max(0, b - 18))
            light = (min(255, r + 12), min(255, g + 12), min(255, b + 12))
            pygame.draw.line(surf, dark, (0, 0), (TILE_SIZE - 1, 0))
            pygame.draw.line(surf, dark, (0, 0), (0, TILE_SIZE - 1))
            pygame.draw.line(surf, light, (TILE_SIZE - 1, 0), (TILE_SIZE - 1, TILE_SIZE - 1))
            pygame.draw.line(surf, light, (0, TILE_SIZE - 1), (TILE_SIZE - 1, TILE_SIZE - 1))
            tiles.append(surf)
        return tiles

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        surface.fill(self._theme["bg"])

        left, top, right, bottom = self.world_bounds
        m = self.MARGIN
        left_tile = max(int(math.floor((cam.x - SCREEN_WIDTH / 2) / TILE_SIZE)) - m, int(left // TILE_SIZE))
        top_tile = max(int(math.floor((cam.y - SCREEN_HEIGHT / 2) / TILE_SIZE)) - m, int(top // TILE_SIZE))
        right_tile = min(left_tile + SCREEN_WIDTH // TILE_SIZE + m * 2 + 2, int(right // TILE_SIZE))
        bottom_tile = min(top_tile + SCREEN_HEIGHT // TILE_SIZE + m * 2 + 2, int(bottom // TILE_SIZE))

        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                sx, sy = cam.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                tile = self._tiles[_tile_hash(tx, ty, self._seed) & 1]
                surface.blit(tile, (int(sx), int(sy)))

        self._draw_decorations(surface, cam, left_tile, top_tile, right_tile, bottom_tile)
        self._draw_border(surface, cam)

    def _draw_decorations(self, surface: pygame.Surface, cam: Camera, lx: int, ty: int, rx: int, by: int) -> None:
        deco_color = self._theme["deco"]
        for ty_i in range(ty, by + 1):
            for tx_i in range(lx, rx + 1):
                h = _tile_hash(tx_i + 31, ty_i + 17, self._seed + 99)
                if (h & 0xFF) > _DECO_THRESHOLD:
                    continue

                offset_x = (h >> 8 & 0x3F) - 32
                offset_y = (h >> 14 & 0x3F) - 32
                wx = tx_i * TILE_SIZE + TILE_SIZE // 2 + offset_x
                wy = ty_i * TILE_SIZE + TILE_SIZE // 2 + offset_y
                if not (WORLD_LEFT <= wx <= WORLD_RIGHT and WORLD_TOP <= wy <= WORLD_BOTTOM):
                    continue
                sx, sy = cam.world_to_screen(wx, wy)

                deco_type = (h >> 20) % 3
                if deco_type == 0:
                    self._draw_rock(surface, sx, sy, deco_color, h)
                elif deco_type == 1:
                    self._draw_grass_tuft(surface, sx, sy, deco_color, h)
                else:
                    self._draw_pebbles(surface, sx, sy, deco_color, h)

    def _draw_border(self, surface: pygame.Surface, cam: Camera) -> None:
        left, top = cam.world_to_screen(WORLD_LEFT, WORLD_TOP)
        right, bottom = cam.world_to_screen(WORLD_RIGHT, WORLD_BOTTOM)
        border_rect = pygame.Rect(int(left), int(top), int(right - left), int(bottom - top))
        pygame.draw.rect(surface, (30, 20, 20), border_rect, 8, border_radius=10)
        pygame.draw.rect(surface, (120, 70, 70), border_rect, 3, border_radius=10)

    def _draw_rock(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        base_r = 5 + (h & 0x7)
        sides = 5 + (h >> 3 & 0x3)
        r, g, b = color
        dark = (max(0, r - 20), max(0, g - 20), max(0, b - 20))
        shapes.irregular_polygon(surface, dark, sx, sy, base_r, sides, 0.35, h)
        shapes.irregular_polygon(surface, color, sx, sy, base_r, sides, 0.35, h, width=1)

    def _draw_grass_tuft(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        r, g, b = color
        lighter = (min(255, r + 30), min(255, g + 40), min(255, b + 10))
        blade_count = 3 + (h & 0x3)
        for idx in range(blade_count):
            spread = (h >> (idx * 6 + 4) & 0x1F) - 16
            height = 6 + (h >> (idx * 3 + 2) & 0x7)
            bx = sx + spread * 0.5
            col = lighter if idx % 2 == 0 else color
            shapes.line(surface, col, bx, sy, bx + spread * 0.3, sy - height, 1)

    def _draw_pebbles(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        count = 2 + (h & 0x3)
        r, g, b = color
        for idx in range(count):
            px = sx + ((h >> (idx * 7 + 2)) & 0x1F) - 16
            py = sy + ((h >> (idx * 5 + 1)) & 0x1F) - 16
            pr = 2 + (h >> (idx * 3) & 0x3)
            tint = (min(255, r + 15), min(255, g + 15), min(255, b + 15))
            shapes.circle(surface, tint, px, py, pr)
