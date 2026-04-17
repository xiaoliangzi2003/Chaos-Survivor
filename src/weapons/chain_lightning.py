"""闪电链：击中最近敌人后跳跃至附近敌人。"""

import math
import random
import pygame
from src.weapons.weapon_base import Weapon, nearest_enemy, apply_weapon_damage
from src.render.particles    import particles


class ChainLightning(Weapon):
    NAME        = "闪电链"
    DESCRIPTION = "闪电击中最近敌人后向附近跳跃传导"
    ICON_COLOR  = (200, 220, 255)

    LEVEL_DATA = [
        {"damage": 25, "cooldown": 2.2, "chains": 2,  "chain_range": 120},
        {"damage": 30, "cooldown": 2.0, "chains": 3,  "chain_range": 130},
        {"damage": 36, "cooldown": 1.8, "chains": 4,  "chain_range": 140},
        {"damage": 43, "cooldown": 1.6, "chains": 5,  "chain_range": 150},
        {"damage": 52, "cooldown": 1.4, "chains": 6,  "chain_range": 160},
        {"damage": 62, "cooldown": 1.2, "chains": 7,  "chain_range": 175},
        {"damage": 74, "cooldown": 1.0, "chains": 8,  "chain_range": 190},
        {"damage": 90, "cooldown": 0.8, "chains": 10, "chain_range": 200},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._bolts: list[_Bolt] = []    # 持久化视觉弧

    def _fire(self, player, enemies, grid, proj_system) -> None:
        first = nearest_enemy(player.x, player.y, enemies)
        if first is None:
            return

        chain_range = self.chain_range * player.stats.range_mul
        hit_set: set[int] = set()
        current: object   = player          # 起跳点（用 .x .y 即可）
        to_hit  = first

        for _ in range(self.chains + player.stats.proj_bonus):
            if to_hit is None:
                break
            # 画弧
            self._bolts.append(_Bolt(current.x, current.y,
                                     to_hit.x, to_hit.y))
            # 伤害
            apply_weapon_damage(to_hit, self.damage, player,
                                current.x, current.y, 80)
            particles.burst(to_hit.x, to_hit.y, (180, 200, 255),
                            count=6, speed=60, life=0.25, size=4)
            hit_set.add(id(to_hit))
            current = to_hit

            # 寻找下一个未命中的最近敌人
            to_hit = None
            best_d2 = chain_range * chain_range
            for e in enemies:
                if not e.alive or id(e) in hit_set:
                    continue
                dx = e.x - current.x;  dy = e.y - current.y
                d2 = dx*dx + dy*dy
                if d2 < best_d2:
                    best_d2 = d2
                    to_hit  = e

    def update(self, dt: float, player, enemies, grid, proj_system) -> None:
        self._player_ref = player
        super().update(dt, player, enemies, grid, proj_system)
        self._bolts = [b for b in self._bolts if b.alive]
        for b in self._bolts:
            b.update(dt)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for b in self._bolts:
            b.draw(surface, cam)


class _Bolt:
    """单条闪电弧（锯齿线段 + 渐隐）。"""
    LIFE = 0.18

    def __init__(self, x1, y1, x2, y2) -> None:
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.life = self.LIFE
        self.alive = True
        # 预计算锯齿点
        self._pts = _zigzag(x1, y1, x2, y2, segs=8, amp=12)

    def update(self, dt: float) -> None:
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surface: pygame.Surface, cam) -> None:
        ratio = self.life / self.LIFE
        alpha = int(255 * ratio)
        if alpha <= 0:
            return
        scr_pts = [cam.world_to_screen(x, y) for x, y in self._pts]
        col = (int(180 + 75 * ratio), int(200 + 55 * ratio), 255)
        for i in range(len(scr_pts) - 1):
            x1, y1 = int(scr_pts[i][0]),   int(scr_pts[i][1])
            x2, y2 = int(scr_pts[i+1][0]), int(scr_pts[i+1][1])
            pygame.draw.line(surface, col, (x1, y1), (x2, y2), 2)
            # 外发光（更粗更透明）
            outer = (*col, max(0, alpha // 3))
            glow  = pygame.Surface((abs(x2-x1)+4, abs(y2-y1)+4), pygame.SRCALPHA)
            pygame.draw.line(glow, outer,
                             (1, 1), (abs(x2-x1)+1, abs(y2-y1)+1), 4)


def _zigzag(x1, y1, x2, y2, segs=8, amp=12) -> list[tuple]:
    pts = [(x1, y1)]
    for i in range(1, segs):
        t  = i / segs
        mx = x1 + (x2 - x1) * t
        my = y1 + (y2 - y1) * t
        # 垂直偏移
        dx = x2 - x1;  dy = y2 - y1
        length = math.hypot(dx, dy) or 1
        nx = -dy / length;  ny = dx / length
        offset = random.uniform(-amp, amp)
        pts.append((mx + nx * offset, my + ny * offset))
    pts.append((x2, y2))
    return pts
