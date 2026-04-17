"""地图渲染器：程序化瓦片地图，支持 3 种主题，无限滚动，含装饰物。"""

import math
import pygame
from src.core.config  import TILE_SIZE, MAP_THEMES, SCREEN_WIDTH, SCREEN_HEIGHT
from src.core.camera  import Camera
from src.render       import shapes


# ── 装饰物出现概率（0–255，值越大越多）────────────────
_DECO_THRESHOLD = 20   # ≈ 8%


def _tile_hash(tx: int, ty: int, salt: int = 0) -> int:
    """基于瓦片坐标的确定性哈希（同坐标每次相同结果）。"""
    h = (tx * 374761393 + ty * 668265263 + salt * 1000003) & 0xFFFF_FFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFF_FFFF
    return h ^ (h >> 16)


class MapRenderer:
    """
    无限世界地图。
    按摄像机可见区动态绘制瓦片，不维护世界范围。
    """

    MARGIN = 2   # 屏幕外额外渲染的瓦片行/列

    def __init__(self, theme_name: str, seed: int = 0) -> None:
        self.theme_name = theme_name
        self._theme     = MAP_THEMES[theme_name]
        self._seed      = seed
        self._tiles     = self._bake_tiles()

    # ── 瓦片预渲染 ────────────────────────────────────

    def _bake_tiles(self) -> list[pygame.Surface]:
        """预渲染 2 种瓦片变体，后续直接 blit（比每帧 fill+draw 快很多）。"""
        t = self._theme
        tiles = []
        for base_color in (t["tile1"], t["tile2"]):
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
            surf.fill(base_color)
            # 微妙的内边框，增加砖块感
            r, g, b = base_color
            dark  = (max(0, r - 18), max(0, g - 18), max(0, b - 18))
            light = (min(255, r + 12), min(255, g + 12), min(255, b + 12))
            pygame.draw.line(surf, dark,  (0, 0), (TILE_SIZE - 1, 0))
            pygame.draw.line(surf, dark,  (0, 0), (0, TILE_SIZE - 1))
            pygame.draw.line(surf, light, (TILE_SIZE - 1, 0), (TILE_SIZE - 1, TILE_SIZE - 1))
            pygame.draw.line(surf, light, (0, TILE_SIZE - 1), (TILE_SIZE - 1, TILE_SIZE - 1))
            tiles.append(surf)
        return tiles

    # ── 主绘制入口 ────────────────────────────────────

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        m = self.MARGIN
        left_tile  = int(math.floor((cam.x - SCREEN_WIDTH  / 2) / TILE_SIZE)) - m
        top_tile   = int(math.floor((cam.y - SCREEN_HEIGHT / 2) / TILE_SIZE)) - m
        right_tile  = left_tile  + SCREEN_WIDTH  // TILE_SIZE + m * 2 + 2
        bottom_tile = top_tile   + SCREEN_HEIGHT // TILE_SIZE + m * 2 + 2

        # ── 瓦片层 ────────────────────────────────────
        for ty in range(top_tile, bottom_tile + 1):
            for tx in range(left_tile, right_tile + 1):
                sx, sy = cam.world_to_screen(tx * TILE_SIZE, ty * TILE_SIZE)
                h      = _tile_hash(tx, ty, self._seed)
                tile   = self._tiles[h & 1]
                surface.blit(tile, (int(sx), int(sy)))

        # ── 装饰物层 ──────────────────────────────────
        self._draw_decorations(surface, cam,
                               left_tile, top_tile, right_tile, bottom_tile)

    # ── 装饰物绘制 ────────────────────────────────────

    def _draw_decorations(self, surface: pygame.Surface, cam: Camera,
                          lx: int, ty: int, rx: int, by: int) -> None:
        deco_color = self._theme["deco"]

        for ty_i in range(ty, by + 1):
            for tx_i in range(lx, rx + 1):
                h = _tile_hash(tx_i + 31, ty_i + 17, self._seed + 99)
                if (h & 0xFF) > _DECO_THRESHOLD:
                    continue

                # 在瓦片内偏移，避免总在中心
                offset_x = (h >> 8  & 0x3F) - 32   # -32 ~ +31
                offset_y = (h >> 14 & 0x3F) - 32
                wx = tx_i * TILE_SIZE + TILE_SIZE // 2 + offset_x
                wy = ty_i * TILE_SIZE + TILE_SIZE // 2 + offset_y
                sx, sy = cam.world_to_screen(wx, wy)

                deco_type = (h >> 20) % 3
                if deco_type == 0:
                    self._draw_rock(surface, sx, sy, deco_color, h)
                elif deco_type == 1:
                    self._draw_grass_tuft(surface, sx, sy, deco_color, h)
                else:
                    self._draw_pebbles(surface, sx, sy, deco_color, h)

    # ── 各类装饰 ──────────────────────────────────────

    def _draw_rock(self, surface: pygame.Surface,
                   sx: float, sy: float,
                   color: tuple, h: int) -> None:
        base_r = 5 + (h & 0x7)           # 5–12 px
        sides  = 5 + (h >> 3 & 0x3)      # 5–8 sides
        angle  = (h >> 5 & 0x3F) * 0.1
        r, g, b = color
        dark   = (max(0, r - 20), max(0, g - 20), max(0, b - 20))
        # 填充
        shapes.irregular_polygon(surface, dark, sx, sy, base_r, sides, 0.35, h)
        # 描边
        shapes.irregular_polygon(surface, color, sx, sy, base_r, sides, 0.35, h, width=1)

    def _draw_grass_tuft(self, surface: pygame.Surface,
                         sx: float, sy: float,
                         color: tuple, h: int) -> None:
        r, g, b = color
        lighter = (min(255, r + 30), min(255, g + 40), min(255, b + 10))
        blade_count = 3 + (h & 0x3)
        for i in range(blade_count):
            spread  = (h >> (i * 6 + 4) & 0x1F) - 16    # -16 ~ +15
            height  = 6 + (h >> (i * 3 + 2) & 0x7)
            bx      = sx + spread * 0.5
            col     = lighter if i % 2 == 0 else color
            shapes.line(surface, col, bx, sy, bx + spread * 0.3, sy - height, 1)

    def _draw_pebbles(self, surface: pygame.Surface,
                      sx: float, sy: float,
                      color: tuple, h: int) -> None:
        count = 2 + (h & 0x3)
        r, g, b = color
        for i in range(count):
            px = sx + ((h >> (i * 7 + 2)) & 0x1F) - 16
            py = sy + ((h >> (i * 5 + 1)) & 0x1F) - 16
            pr = 2 + (h >> (i * 3) & 0x3)
            tint = (min(255, r + 15), min(255, g + 15), min(255, b + 15))
            shapes.circle(surface, tint, px, py, pr)
