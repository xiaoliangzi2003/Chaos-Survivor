"""环绕法球：围绕玩家旋转的能量球，接触敌人造成伤害。"""

import math
import pygame
from src.weapons.weapon_base import Weapon, apply_weapon_damage
from src.render              import shapes
from src.render.particles    import particles


class OrbitOrb(Weapon):
    NAME        = "环绕法球"
    DESCRIPTION = "围绕玩家旋转的能量球，接触到敌人时造成伤害"
    ICON_COLOR  = (100, 200, 255)

    LEVEL_DATA = [
        {"damage": 12, "cooldown": 99, "count": 1, "orbit_radius": 80,  "hit_cd": 0.50, "_orb_size": 10},
        {"damage": 14, "cooldown": 99, "count": 2, "orbit_radius": 85,  "hit_cd": 0.45, "_orb_size": 10},
        {"damage": 17, "cooldown": 99, "count": 2, "orbit_radius": 90,  "hit_cd": 0.40, "_orb_size": 12},
        {"damage": 20, "cooldown": 99, "count": 3, "orbit_radius": 95,  "hit_cd": 0.35, "_orb_size": 12},
        {"damage": 24, "cooldown": 99, "count": 3, "orbit_radius": 100, "hit_cd": 0.30, "_orb_size": 14},
        {"damage": 28, "cooldown": 99, "count": 4, "orbit_radius": 108, "hit_cd": 0.25, "_orb_size": 14},
        {"damage": 33, "cooldown": 99, "count": 4, "orbit_radius": 115, "hit_cd": 0.22, "_orb_size": 16},
        {"damage": 40, "cooldown": 99, "count": 5, "orbit_radius": 120, "hit_cd": 0.20, "_orb_size": 16},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._angle     = 0.0
        self._hit_cds: dict[int, float] = {}    # enemy_id -> 剩余冷却

    def update(self, dt: float, player, enemies, grid, proj_system) -> None:
        self._player_ref = player
        eff_r   = self.orbit_radius * player.stats.range_mul
        rot_spd = 1.8 + self.level * 0.15       # 转速随级别提升

        self._angle = (self._angle + rot_spd * dt) % (math.pi * 2)

        # 命中冷却衰减
        for eid in list(self._hit_cds):
            self._hit_cds[eid] -= dt
            if self._hit_cds[eid] <= 0:
                del self._hit_cds[eid]

        # 碰撞检测
        orb_count = self.count + player.stats.proj_bonus
        for i in range(orb_count):
            a   = self._angle + math.pi * 2 * i / orb_count
            ox  = player.x + math.cos(a) * eff_r
            oy  = player.y + math.sin(a) * eff_r
            for e in grid.query_radius(ox, oy, self._orb_size + e_radius_est(enemies)):
                if not e.alive:
                    continue
                dx = e.x - ox;  dy = e.y - oy
                if dx*dx + dy*dy > (self._orb_size + e.radius) ** 2:
                    continue
                eid = id(e)
                if eid in self._hit_cds:
                    continue
                apply_weapon_damage(e, self.damage, player, ox, oy, 90)
                self._hit_cds[eid] = self.hit_cd
                particles.burst(ox, oy, (100, 200, 255),
                                count=4, speed=50, life=0.25, size=3)

    def draw(self, surface: pygame.Surface, cam) -> None:
        if self._player_ref is None:
            return
        player    = self._player_ref
        eff_r     = self.orbit_radius * player.stats.range_mul
        orb_count = self.count + player.stats.proj_bonus
        for i in range(orb_count):
            a  = self._angle + math.pi * 2 * i / orb_count
            ox = player.x + math.cos(a) * eff_r
            oy = player.y + math.sin(a) * eff_r
            sx, sy = cam.world_to_screen(ox, oy)
            shapes.glow_circle(surface, (100, 200, 255),
                               sx, sy, self._orb_size,
                               layers=2, alpha_start=60)
            shapes.circle(surface, (140, 220, 255), sx, sy, self._orb_size)
            shapes.circle(surface, (220, 240, 255), sx, sy,
                          max(2, int(self._orb_size * 0.45)))


def e_radius_est(enemies) -> float:
    return 20  # 估算最大敌人半径，用于网格预查询
