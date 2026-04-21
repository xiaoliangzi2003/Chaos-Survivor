"""Map renderer with richer geometric tiles and landmark details."""

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

_DECO_THRESHOLD = 34
_LANDMARK_THRESHOLD = 18


def _tile_hash(tx: int, ty: int, salt: int = 0) -> int:
    h = (tx * 374761393 + ty * 668265263 + salt * 1000003) & 0xFFFF_FFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFF_FFFF
    return h ^ (h >> 16)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    ratio = max(0.0, min(1.0, ratio))
    return tuple(int(a[idx] + (b[idx] - a[idx]) * ratio) for idx in range(3))


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
        tiles: list[pygame.Surface] = []
        for color_index, base_color in enumerate((self._theme["tile1"], self._theme["tile2"])):
            for variant in range(4):
                surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                surf.fill(base_color)
                dark = _mix(base_color, (0, 0, 0), 0.24)
                mid = _mix(base_color, self._theme["deco"], 0.45)
                light = _mix(base_color, (255, 255, 255), 0.12)
                accent = _mix(base_color, (255, 255, 255), 0.22)

                pygame.draw.line(surf, dark, (0, 0), (TILE_SIZE - 1, 0))
                pygame.draw.line(surf, dark, (0, 0), (0, TILE_SIZE - 1))
                pygame.draw.line(surf, light, (TILE_SIZE - 1, 0), (TILE_SIZE - 1, TILE_SIZE - 1))
                pygame.draw.line(surf, light, (0, TILE_SIZE - 1), (TILE_SIZE - 1, TILE_SIZE - 1))

                for idx in range(8):
                    h = _tile_hash(idx * 11 + color_index * 7, variant * 13 + idx * 3, self._seed + color_index * 97)
                    px = 6 + ((h >> 3) & 0x2F)
                    py = 6 + ((h >> 10) & 0x2F)
                    pr = 1 + ((h >> 16) & 0x2)
                    dot_color = accent if idx % 2 == 0 else mid
                    pygame.draw.circle(surf, dot_color, (px, py), pr)

                if variant == 0:
                    pygame.draw.line(surf, mid, (8, TILE_SIZE - 12), (TILE_SIZE - 10, 10), 2)
                    pygame.draw.line(surf, accent, (10, TILE_SIZE - 10), (TILE_SIZE - 16, 16), 1)
                elif variant == 1:
                    pygame.draw.rect(surf, (*light, 70), pygame.Rect(10, 10, TILE_SIZE - 20, TILE_SIZE - 20), 1, border_radius=6)
                    shapes.diamond(surf, accent, TILE_SIZE / 2, TILE_SIZE / 2, 8, 12)
                    shapes.diamond(surf, dark, TILE_SIZE / 2, TILE_SIZE / 2, 8, 12, width=1)
                elif variant == 2:
                    pygame.draw.line(surf, dark, (12, 18), (TILE_SIZE - 12, 18), 2)
                    pygame.draw.line(surf, dark, (18, 12), (18, TILE_SIZE - 12), 2)
                    pygame.draw.line(surf, light, (12, TILE_SIZE - 18), (TILE_SIZE - 16, TILE_SIZE - 18), 1)
                    pygame.draw.line(surf, light, (TILE_SIZE - 18, 12), (TILE_SIZE - 18, TILE_SIZE - 16), 1)
                else:
                    crack = [(12, 14), (20, 22), (30, 18), (42, 30), (54, 22)]
                    pygame.draw.lines(surf, dark, False, crack, 2)
                    pygame.draw.lines(surf, accent, False, [(x, y + 8) for x, y in crack[:-1]], 1)

                tiles.append(surf)
        return tiles

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        surface.fill(self._theme["bg"])

        left, top, right, bottom = self.world_bounds
        margin = self.MARGIN
        left_tile = max(int(math.floor((cam.x - SCREEN_WIDTH / 2) / TILE_SIZE)) - margin, int(left // TILE_SIZE))
        top_tile = max(int(math.floor((cam.y - SCREEN_HEIGHT / 2) / TILE_SIZE)) - margin, int(top // TILE_SIZE))
        right_tile = min(left_tile + SCREEN_WIDTH // TILE_SIZE + margin * 2 + 2, int(right // TILE_SIZE))
        bottom_tile = min(top_tile + SCREEN_HEIGHT // TILE_SIZE + margin * 2 + 2, int(bottom // TILE_SIZE))

        self._draw_backdrop(surface, cam, left_tile, top_tile, right_tile, bottom_tile)

        tile_count = len(self._tiles)
        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                sx, sy = cam.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                tile = self._tiles[_tile_hash(tx, ty, self._seed) % tile_count]
                surface.blit(tile, (int(sx), int(sy)))

        self._draw_landmarks(surface, cam, left_tile, top_tile, right_tile, bottom_tile)
        self._draw_decorations(surface, cam, left_tile, top_tile, right_tile, bottom_tile)
        self._draw_border(surface, cam)

    def _draw_backdrop(self, surface: pygame.Surface, cam: Camera, lx: int, ty: int, rx: int, by: int) -> None:
        shade = _mix(self._theme["bg"], self._theme["deco"], 0.38)
        glow = _mix(self._theme["tile1"], (255, 255, 255), 0.18)
        for gy in range(ty // 6 - 1, by // 6 + 2):
            for gx in range(lx // 6 - 1, rx // 6 + 2):
                h = _tile_hash(gx, gy, self._seed + 701)
                if (h & 0x1F) > 3:
                    continue
                wx = gx * TILE_SIZE * 6 + ((h >> 8) & 0xFF) - 128
                wy = gy * TILE_SIZE * 6 + ((h >> 16) & 0xFF) - 128
                sx, sy = cam.world_to_screen(wx, wy)
                radius = 80 + ((h >> 24) & 0x3F)
                blob = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
                center = (blob.get_width() // 2, blob.get_height() // 2)
                pygame.draw.circle(blob, (*shade, 18), center, radius)
                pygame.draw.circle(blob, (*glow, 10), center, int(radius * 0.55))
                surface.blit(blob, (int(sx - blob.get_width() / 2), int(sy - blob.get_height() / 2)))

    def _draw_landmarks(self, surface: pygame.Surface, cam: Camera, lx: int, ty: int, rx: int, by: int) -> None:
        deco = self._theme["deco"]
        accent = _mix(deco, (255, 255, 255), 0.16)
        for gy in range(ty // 4 - 1, by // 4 + 2):
            for gx in range(lx // 4 - 1, rx // 4 + 2):
                h = _tile_hash(gx, gy, self._seed + 411)
                if (h & 0xFF) > _LANDMARK_THRESHOLD:
                    continue
                wx = gx * TILE_SIZE * 4 + ((h >> 10) & 0x7F) - 64
                wy = gy * TILE_SIZE * 4 + ((h >> 17) & 0x7F) - 64
                sx, sy = cam.world_to_screen(wx, wy)
                pattern = (h >> 24) & 0x3
                if pattern == 0:
                    shapes.ring(surface, accent, sx, sy, 22 + (h & 0xF), 2)
                    shapes.ring(surface, deco, sx, sy, 10 + ((h >> 4) & 0x7), 1)
                elif pattern == 1:
                    shapes.regular_polygon(surface, deco, sx, sy, 16 + (h & 0x7), 6, 0.2, width=2)
                    shapes.circle(surface, accent, sx, sy, 4)
                elif pattern == 2:
                    shapes.line(surface, deco, sx - 20, sy, sx + 20, sy, 2)
                    shapes.line(surface, deco, sx, sy - 20, sx, sy + 20, 2)
                    shapes.diamond(surface, accent, sx, sy, 5, 8)
                else:
                    pygame.draw.arc(surface, accent, pygame.Rect(int(sx - 20), int(sy - 14), 40, 28), 0.2, math.pi - 0.2, 2)
                    pygame.draw.arc(surface, deco, pygame.Rect(int(sx - 28), int(sy - 22), 56, 44), math.pi + 0.15, math.tau - 0.15, 2)

    def _draw_decorations(self, surface: pygame.Surface, cam: Camera, lx: int, ty: int, rx: int, by: int) -> None:
        deco_color = self._theme["deco"]
        for ty_i in range(ty, by + 1):
            for tx_i in range(lx, rx + 1):
                h = _tile_hash(tx_i + 31, ty_i + 17, self._seed + 99)
                if (h & 0xFF) > _DECO_THRESHOLD:
                    continue

                offset_x = ((h >> 8) & 0x3F) - 32
                offset_y = ((h >> 14) & 0x3F) - 32
                wx = tx_i * TILE_SIZE + TILE_SIZE // 2 + offset_x
                wy = ty_i * TILE_SIZE + TILE_SIZE // 2 + offset_y
                if not (WORLD_LEFT <= wx <= WORLD_RIGHT and WORLD_TOP <= wy <= WORLD_BOTTOM):
                    continue
                sx, sy = cam.world_to_screen(wx, wy)

                deco_type = (h >> 20) % 5
                if deco_type == 0:
                    self._draw_rock(surface, sx, sy, deco_color, h)
                elif deco_type == 1:
                    self._draw_grass_tuft(surface, sx, sy, deco_color, h)
                elif deco_type == 2:
                    self._draw_pebbles(surface, sx, sy, deco_color, h)
                elif deco_type == 3:
                    self._draw_cracks(surface, sx, sy, deco_color, h)
                else:
                    self._draw_ruin(surface, sx, sy, deco_color, h)

    def _draw_border(self, surface: pygame.Surface, cam: Camera) -> None:
        left, top = cam.world_to_screen(WORLD_LEFT, WORLD_TOP)
        right, bottom = cam.world_to_screen(WORLD_RIGHT, WORLD_BOTTOM)
        border_rect = pygame.Rect(int(left), int(top), int(right - left), int(bottom - top))
        if border_rect.width <= 0 or border_rect.height <= 0:
            return

        outer = (26, 18, 18)
        mid = (96, 58, 58)
        accent = (160, 92, 92)
        pygame.draw.rect(surface, outer, border_rect, 10, border_radius=12)
        pygame.draw.rect(surface, mid, border_rect.inflate(-8, -8), 3, border_radius=10)
        pygame.draw.rect(surface, accent, border_rect.inflate(-18, -18), 1, border_radius=8)

        corners = (
            border_rect.topleft,
            border_rect.topright,
            border_rect.bottomleft,
            border_rect.bottomright,
        )
        for cx, cy in corners:
            shapes.diamond(surface, accent, cx, cy, 9, 14)
            shapes.diamond(surface, mid, cx, cy, 5, 8)

    def _draw_rock(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        base_r = 5 + (h & 0x7)
        sides = 5 + ((h >> 3) & 0x3)
        dark = _mix(color, (0, 0, 0), 0.25)
        shapes.irregular_polygon(surface, dark, sx, sy, base_r, sides, 0.35, h)
        shapes.irregular_polygon(surface, color, sx, sy, base_r, sides, 0.35, h, width=1)

    def _draw_grass_tuft(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        lighter = _mix(color, (255, 255, 255), 0.18)
        blade_count = 3 + (h & 0x3)
        for idx in range(blade_count):
            spread = ((h >> (idx * 6 + 4)) & 0x1F) - 16
            height = 6 + ((h >> (idx * 3 + 2)) & 0x7)
            bx = sx + spread * 0.5
            col = lighter if idx % 2 == 0 else color
            shapes.line(surface, col, bx, sy, bx + spread * 0.3, sy - height, 1)

    def _draw_pebbles(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        tint = _mix(color, (255, 255, 255), 0.1)
        count = 2 + (h & 0x3)
        for idx in range(count):
            px = sx + (((h >> (idx * 7 + 2)) & 0x1F) - 16)
            py = sy + (((h >> (idx * 5 + 1)) & 0x1F) - 16)
            pr = 2 + ((h >> (idx * 3)) & 0x3)
            shapes.circle(surface, tint, px, py, pr)

    def _draw_cracks(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        dark = _mix(color, (0, 0, 0), 0.3)
        points = [(sx - 12, sy + 4), (sx - 4, sy - 5), (sx + 6, sy + 2), (sx + 14, sy - 8)]
        jittered = []
        for idx, (px, py) in enumerate(points):
            jittered.append((px + (((h >> (idx * 4)) & 0x7) - 3), py + (((h >> (idx * 5 + 2)) & 0x7) - 3)))
        pygame.draw.lines(surface, dark, False, [(int(px), int(py)) for px, py in jittered], 2)
        pygame.draw.lines(surface, color, False, [(int(px + 1), int(py + 1)) for px, py in jittered[1:]], 1)

    def _draw_ruin(self, surface: pygame.Surface, sx: float, sy: float, color: tuple[int, int, int], h: int) -> None:
        accent = _mix(color, (255, 255, 255), 0.16)
        width = 12 + (h & 0x7)
        height = 8 + ((h >> 3) & 0x7)
        rect = pygame.Rect(int(sx - width / 2), int(sy - height / 2), width, height)
        pygame.draw.rect(surface, color, rect, 1, border_radius=3)
        shapes.line(surface, accent, rect.left + 2, rect.centery, rect.right - 2, rect.centery, 1)
        shapes.line(surface, accent, rect.centerx, rect.top + 2, rect.centerx, rect.bottom - 2, 1)
