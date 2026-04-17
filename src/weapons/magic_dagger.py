"""魔法飞刀：朝最近敌人直线投射，可穿透多个目标。"""

import math
from src.weapons.weapon_base import Weapon, nearest_enemy
from src.render.particles    import particles


class MagicDagger(Weapon):
    NAME        = "魔法飞刀"
    DESCRIPTION = "向最近敌人投出魔法飞刀，可穿透目标"
    ICON_COLOR  = (255, 220, 80)

    LEVEL_DATA = [
        {"damage": 15, "cooldown": 0.65, "pierce": 1, "_speed": 420},
        {"damage": 18, "cooldown": 0.60, "pierce": 1, "_speed": 440},
        {"damage": 22, "cooldown": 0.55, "pierce": 2, "_speed": 460},
        {"damage": 26, "cooldown": 0.50, "pierce": 2, "_speed": 480},
        {"damage": 32, "cooldown": 0.45, "pierce": 3, "_speed": 500},
        {"damage": 38, "cooldown": 0.40, "pierce": 3, "_speed": 520},
        {"damage": 45, "cooldown": 0.35, "pierce": 4, "_speed": 540},
        {"damage": 55, "cooldown": 0.30, "pierce": 5, "_speed": 560},
    ]

    def _fire(self, player, enemies, grid, proj_system) -> None:
        target = nearest_enemy(player.x, player.y, enemies)
        if target is None:
            return
        count = self._eff_proj_count(player)
        base_angle = math.atan2(target.y - player.y,
                                target.x - player.x)
        spread = 0.18 * (count - 1)
        for i in range(count):
            if count > 1:
                angle = base_angle - spread / 2 + spread * i / (count - 1)
            else:
                angle = base_angle
            vx = math.cos(angle) * self._speed
            vy = math.sin(angle) * self._speed
            proj_system.spawn(
                x=player.x, y=player.y,
                vx=vx, vy=vy,
                damage=self.damage,
                player=player,
                pierce=self.pierce,
                life=2.5,
                radius=7, size=6,
                color=(255, 220, 80),
                shape="dagger",
                trail_max=10,
                trail_color=(255, 180, 30),
                kb_force=110,
            )
        # 发射粒子
        particles.directional(player.x, player.y, base_angle, 0.3,
                               (255, 230, 100), count=3, speed=40, life=0.2)
