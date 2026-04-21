"""回旋刃：向前掷出后回到玩家身边。"""

from __future__ import annotations

import math

from src.render.particles import particles
from src.weapons.weapon_base import Weapon, nearest_enemy


class BoomerangScythe(Weapon):
    NAME = "回旋光刃"
    DESCRIPTION = "掷出回旋刃，飞出后折返，可多次擦伤敌人。"
    ICON_COLOR = (255, 170, 110)

    LEVEL_DATA = [
        {"damage": 14, "cooldown": 1.35, "count": 1, "_speed": 320, "pierce": 3, "return_after": 0.40},
        {"damage": 18, "cooldown": 1.20, "count": 1, "_speed": 340, "pierce": 4, "return_after": 0.38},
        {"damage": 22, "cooldown": 1.08, "count": 2, "_speed": 350, "pierce": 4, "return_after": 0.36},
        {"damage": 27, "cooldown": 0.96, "count": 2, "_speed": 365, "pierce": 5, "return_after": 0.35},
        {"damage": 32, "cooldown": 0.88, "count": 2, "_speed": 380, "pierce": 6, "return_after": 0.33},
        {"damage": 38, "cooldown": 0.80, "count": 3, "_speed": 395, "pierce": 6, "return_after": 0.32},
        {"damage": 45, "cooldown": 0.72, "count": 3, "_speed": 410, "pierce": 7, "return_after": 0.30},
        {"damage": 54, "cooldown": 0.64, "count": 4, "_speed": 430, "pierce": 8, "return_after": 0.28},
    ]

    def _fire(self, player, enemies, grid, proj_system) -> None:
        target = nearest_enemy(player.x, player.y, enemies, max_range=520)
        base_angle = player._facing if target is None else math.atan2(target.y - player.y, target.x - player.x)
        count = self._eff_proj_count(player)
        spread = 0.34 * max(0, count - 1)

        for idx in range(count):
            angle = base_angle if count == 1 else base_angle - spread / 2 + spread * idx / (count - 1)
            proj_system.spawn(
                x=player.x,
                y=player.y,
                vx=math.cos(angle) * self._speed,
                vy=math.sin(angle) * self._speed,
                damage=self.damage,
                player=player,
                pierce=self.pierce,
                life=1.8,
                radius=9,
                size=8,
                color=(255, 180, 120),
                shape="boomerang",
                trail_max=12,
                trail_color=(255, 120, 60),
                kb_force=105,
                returning=True,
                return_after=self.return_after,
                return_speed=1.45,
            )

        particles.directional(player.x, player.y, base_angle, 0.45, (255, 200, 140), count=5, speed=50, life=0.18)
