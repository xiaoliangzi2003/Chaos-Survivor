"""火焰新星：以玩家为中心释放扩散圆环，命中范围内所有敌人。"""

import math
import pygame
from src.weapons.weapon_base import Weapon, apply_weapon_damage
from src.render.particles    import particles


class FireNova(Weapon):
    NAME        = "火焰新星"
    DESCRIPTION = "向四周释放火焰扩散圆，命中范围内所有敌人"
    ICON_COLOR  = (255, 120, 30)

    LEVEL_DATA = [
        {"damage": 30,  "cooldown": 4.5, "radius": 150, "_expand_spd": 200},
        {"damage": 38,  "cooldown": 4.0, "radius": 165, "_expand_spd": 210},
        {"damage": 47,  "cooldown": 3.5, "radius": 180, "_expand_spd": 220},
        {"damage": 58,  "cooldown": 3.0, "radius": 195, "_expand_spd": 230},
        {"damage": 70,  "cooldown": 2.5, "radius": 210, "_expand_spd": 240},
        {"damage": 85,  "cooldown": 2.2, "radius": 225, "_expand_spd": 250},
        {"damage": 100, "cooldown": 1.8, "radius": 240, "_expand_spd": 260},
        {"damage": 120, "cooldown": 1.5, "radius": 260, "_expand_spd": 270},
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rings: list[_NovaRing] = []

    def _fire(self, player, enemies, grid, proj_system) -> None:
        eff_r = self.radius * player.stats.range_mul
        self._rings.append(_NovaRing(
            player.x, player.y, eff_r,
            self._expand_spd, self.damage, player))
        particles.burst(player.x, player.y, (255, 120, 30),
                        count=12, speed=60, life=0.4, size=5)

    def update(self, dt: float, player, enemies, grid, proj_system) -> None:
        self._player_ref = player
        super().update(dt, player, enemies, grid, proj_system)
        self._rings = [r for r in self._rings if r.alive]
        for ring in self._rings:
            ring.update(dt, enemies)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for ring in self._rings:
            ring.draw(surface, cam)


class _NovaRing:
    """单个扩散火焰环。"""
    def __init__(self, cx, cy, max_r, speed, damage, player) -> None:
        self.cx, self.cy = cx, cy
        self.max_r  = max_r
        self.speed  = speed
        self.damage = damage
        self.player = player
        self.r      = 10.0
        self.alive  = True
        self._hit_ids: set[int] = set()
        self.life = max_r / speed

    def update(self, dt: float, enemies: list) -> None:
        self.r     += self.speed * dt
        self.life  -= dt
        if self.life <= 0 or self.r > self.max_r:
            self.alive = False
            return
        # 命中检测：在环边缘附近的敌人
        for e in enemies:
            if not e.alive or id(e) in self._hit_ids:
                continue
            dx = e.x - self.cx;  dy = e.y - self.cy
            dist = math.hypot(dx, dy)
            if abs(dist - self.r) < e.radius + 12:
                apply_weapon_damage(e, self.damage, self.player,
                                    self.cx, self.cy, 100)
                self._hit_ids.add(id(e))
                particles.burst(e.x, e.y, (255, 150, 30),
                                count=5, speed=55, life=0.3, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        sx, sy = cam.world_to_screen(self.cx, self.cy)
        ratio  = 1.0 - self.r / self.max_r
        alpha  = int(200 * ratio)
        width  = max(1, int(4 * ratio + 1))
        col    = (255, int(80 + 120 * ratio), 20)
        r_int  = max(1, int(self.r))
        pygame.draw.circle(surface, col, (int(sx), int(sy)), r_int, width)
        # 内层淡环
        if r_int > 6:
            inner_col = (255, int(160 + 80 * ratio), 60)
            pygame.draw.circle(surface, inner_col,
                               (int(sx), int(sy)), max(1, r_int - 4), 1)
