"""陨星术：在敌人附近生成延迟坠落的陨星。"""

from __future__ import annotations

import math

import pygame

from src.render import shapes
from src.render.particles import particles
from src.weapons.weapon_base import Weapon, apply_weapon_damage, nearest_enemy


class MeteorCall(Weapon):
    NAME = "陨星术"
    DESCRIPTION = "召唤短暂延迟后坠落的陨石，对范围内敌人造成爆发伤害。"
    ICON_COLOR = (255, 90, 70)

    LEVEL_DATA = [
        {"damage": 38, "cooldown": 3.8, "count": 1, "radius": 90, "_delay": 0.65},
        {"damage": 48, "cooldown": 3.4, "count": 1, "radius": 96, "_delay": 0.60},
        {"damage": 58, "cooldown": 3.0, "count": 2, "radius": 102, "_delay": 0.58},
        {"damage": 72, "cooldown": 2.7, "count": 2, "radius": 110, "_delay": 0.56},
        {"damage": 88, "cooldown": 2.4, "count": 3, "radius": 118, "_delay": 0.54},
        {"damage": 104, "cooldown": 2.1, "count": 3, "radius": 126, "_delay": 0.50},
        {"damage": 122, "cooldown": 1.8, "count": 4, "radius": 134, "_delay": 0.47},
        {"damage": 145, "cooldown": 1.5, "count": 4, "radius": 144, "_delay": 0.44},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._markers: list[dict] = []

    def update(self, dt: float, player, enemies, grid, proj_system) -> None:
        self._player_ref = player
        super().update(dt, player, enemies, grid, proj_system)

        keep: list[dict] = []
        for marker in self._markers:
            marker["time"] -= dt
            if marker["time"] <= 0:
                self._explode_marker(marker, enemies, player)
            else:
                keep.append(marker)
        self._markers = keep

    def _fire(self, player, enemies, grid, proj_system) -> None:
        count = self._eff_proj_count(player)
        chosen: list = []
        for _ in range(count):
            target = nearest_enemy(player.x, player.y, [enemy for enemy in enemies if enemy not in chosen], max_range=560)
            if target is None:
                angle = player._facing + (_ * 0.7)
                tx = player.x + math.cos(angle) * 150
                ty = player.y + math.sin(angle) * 150
            else:
                chosen.append(target)
                tx = target.x + math.cos(self._timer + len(chosen)) * 10
                ty = target.y + math.sin(self._timer + len(chosen)) * 10
            self._markers.append({"x": tx, "y": ty, "time": self._delay, "radius": self.radius * player.stats.range_mul})
        particles.sparkle(player.x, player.y, (255, 140, 100), count=8, radius=18)

    def _explode_marker(self, marker: dict, enemies: list, player) -> None:
        x = marker["x"]
        y = marker["y"]
        radius = marker["radius"]
        particles.burst(x, y, (255, 120, 60), count=18, speed=130, life=0.4, size=6)
        particles.burst(x, y, (255, 220, 180), count=10, speed=70, life=0.25, size=4)
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - x
            dy = enemy.y - y
            dist = math.hypot(dx, dy)
            if dist <= radius + enemy.radius:
                factor = max(0.55, 1.0 - dist / max(1.0, radius))
                apply_weapon_damage(enemy, self.damage * factor, player, x, y, 130)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for marker in self._markers:
            sx, sy = cam.world_to_screen(marker["x"], marker["y"])
            ratio = marker["time"] / max(0.001, self._delay)
            radius = marker["radius"] * (0.25 + (1.0 - ratio) * 0.75)
            shapes.ring(surface, (255, 110, 70), sx, sy, radius, 2)
            shapes.ring(surface, (255, 220, 180), sx, sy, max(12, radius * 0.55), 1)
            tip_y = sy - 180 * ratio
            pygame.draw.line(surface, (255, 180, 120), (int(sx), int(tip_y)), (int(sx), int(sy - 12)), 3)
