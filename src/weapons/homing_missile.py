"""追踪导弹：锁定最近敌人，命中爆炸造成范围伤害。"""

import math
from src.weapons.weapon_base import Weapon, nearest_enemy
from src.render.particles    import particles


class HomingMissile(Weapon):
    NAME        = "追踪导弹"
    DESCRIPTION = "发射追踪弹，命中后爆炸造成范围伤害"
    ICON_COLOR  = (255, 80, 60)

    LEVEL_DATA = [
        {"damage": 45,  "cooldown": 3.5, "explode_dmg": 20,  "explode_r": 80,  "_speed": 260, "_turn": 2.5},
        {"damage": 55,  "cooldown": 3.2, "explode_dmg": 25,  "explode_r": 90,  "_speed": 270, "_turn": 2.8},
        {"damage": 67,  "cooldown": 2.8, "explode_dmg": 32,  "explode_r": 100, "_speed": 280, "_turn": 3.0},
        {"damage": 80,  "cooldown": 2.4, "explode_dmg": 40,  "explode_r": 110, "_speed": 290, "_turn": 3.2},
        {"damage": 96,  "cooldown": 2.0, "explode_dmg": 50,  "explode_r": 120, "_speed": 300, "_turn": 3.5},
        {"damage": 115, "cooldown": 1.7, "explode_dmg": 60,  "explode_r": 135, "_speed": 315, "_turn": 3.8},
        {"damage": 138, "cooldown": 1.4, "explode_dmg": 72,  "explode_r": 150, "_speed": 330, "_turn": 4.0},
        {"damage": 165, "cooldown": 1.2, "explode_dmg": 90,  "explode_r": 165, "_speed": 345, "_turn": 4.5},
    ]

    def _fire(self, player, enemies, grid, proj_system) -> None:
        target = nearest_enemy(player.x, player.y, enemies)
        angle  = (math.atan2(target.y - player.y, target.x - player.x)
                  if target else player._facing)
        count  = self._eff_proj_count(player)
        eff_r  = self.explode_r * player.stats.range_mul

        for i in range(count):
            spread_a = angle + (i - count // 2) * 0.25
            vx = math.cos(spread_a) * self._speed
            vy = math.sin(spread_a) * self._speed
            p  = proj_system.spawn(
                x=player.x, y=player.y,
                vx=vx, vy=vy,
                damage=self.damage,
                player=player,
                pierce=1,
                life=4.0,
                radius=7, size=7,
                color=(255, 100, 40),
                shape="missile",
                tracking=True,
                turn_speed=self._turn,
                explode_radius=eff_r,
                explode_damage=self.explode_dmg,
                trail_max=12,
                trail_color=(255, 60, 20),
                kb_force=180,
            )
            if p and target:
                p._target = target
        particles.directional(player.x, player.y, angle, 0.4,
                               (255, 100, 30), count=5, speed=50, life=0.25)
