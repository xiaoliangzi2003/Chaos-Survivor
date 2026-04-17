"""寒冰飞镖：散射多枚飞镖，命中减速敌人。"""

import math
from src.weapons.weapon_base import Weapon, nearest_enemy
from src.render.particles    import particles


class IceDart(Weapon):
    NAME        = "寒冰飞镖"
    DESCRIPTION = "散射冰镖，命中使敌人大幅减速"
    ICON_COLOR  = (100, 200, 255)

    LEVEL_DATA = [
        {"damage": 12, "cooldown": 1.3, "count": 2, "slow_mul": 0.50, "slow_dur": 2.0, "_speed": 360},
        {"damage": 15, "cooldown": 1.2, "count": 3, "slow_mul": 0.50, "slow_dur": 2.2, "_speed": 370},
        {"damage": 18, "cooldown": 1.1, "count": 3, "slow_mul": 0.40, "slow_dur": 2.5, "_speed": 380},
        {"damage": 22, "cooldown": 1.0, "count": 4, "slow_mul": 0.40, "slow_dur": 2.8, "_speed": 390},
        {"damage": 27, "cooldown": 0.9, "count": 5, "slow_mul": 0.35, "slow_dur": 3.0, "_speed": 400},
        {"damage": 32, "cooldown": 0.8, "count": 5, "slow_mul": 0.30, "slow_dur": 3.2, "_speed": 415},
        {"damage": 38, "cooldown": 0.7, "count": 6, "slow_mul": 0.25, "slow_dur": 3.5, "_speed": 430},
        {"damage": 46, "cooldown": 0.6, "count": 8, "slow_mul": 0.20, "slow_dur": 4.0, "_speed": 450},
    ]

    def _fire(self, player, enemies, grid, proj_system) -> None:
        target = nearest_enemy(player.x, player.y, enemies)
        base_angle = (math.atan2(target.y - player.y, target.x - player.x)
                      if target else 0.0)
        count  = self._eff_proj_count(player)
        spread = math.radians(20) * (count - 1) / max(1, count)

        for i in range(count):
            offset = -spread / 2 + spread * i / max(1, count - 1)
            angle  = base_angle + offset
            vx     = math.cos(angle) * self._speed
            vy     = math.sin(angle) * self._speed
            proj_system.spawn(
                x=player.x, y=player.y,
                vx=vx, vy=vy,
                damage=self.damage,
                player=player,
                pierce=1,
                life=2.2,
                radius=6, size=7,
                color=(120, 210, 255),
                shape="ice",
                slow_mul=self.slow_mul,
                slow_dur=self.slow_dur,
                trail_max=8,
                trail_color=(80, 170, 255),
                kb_force=80,
            )
        particles.burst(player.x, player.y, (140, 210, 255),
                        count=4, speed=30, life=0.2, size=3)
