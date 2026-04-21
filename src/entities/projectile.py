"""投射物实体与投射物对象池系统。"""

from __future__ import annotations

import math

import pygame

from src.entities.entity import Entity
from src.render import shapes
from src.render.particles import particles
from src.weapons.weapon_base import apply_weapon_damage, nearest_enemy

_POOL_SIZE = 600


class Projectile(Entity):
    def __init__(self) -> None:
        super().__init__(0.0, 0.0, 5.0)
        self.alive = False

    def init(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: float,
        player,
        pierce: int = 1,
        life: float = 3.0,
        radius: float = 6.0,
        color: tuple[int, int, int] = (255, 240, 120),
        size: float = 5.0,
        shape: str = "ball",
        tracking: bool = False,
        turn_speed: float = 3.0,
        explode_radius: float = 0.0,
        explode_damage: float = 0.0,
        slow_mul: float = 1.0,
        slow_dur: float = 0.0,
        trail_max: int = 10,
        trail_color: tuple[int, int, int] | None = None,
        kb_force: float = 130.0,
        returning: bool = False,
        return_after: float = 0.35,
        return_speed: float = 1.0,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self._speed = math.hypot(vx, vy)
        self.damage = damage
        self._player = player
        self.pierce = pierce
        self._hits_left = pierce
        self._hit_ids: set[int] = set()
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color
        self.size = size
        self.shape = shape
        self.tracking = tracking
        self._target = None
        self.turn_speed = turn_speed
        self.explode_radius = explode_radius
        self.explode_damage = explode_damage
        self.slow_mul = slow_mul
        self.slow_dur = slow_dur
        self.kb_force = kb_force
        self.returning = returning
        self.return_after = return_after
        self.return_speed = return_speed
        self._return_timer = 0.0
        self._trail: list[tuple[float, float]] = []
        self._trail_max = trail_max
        self._trail_color = trail_color or color
        self.alive = True

    def update(self, dt: float, enemies: list, grid) -> None:
        if not self.alive:
            return

        if self.tracking:
            self._update_tracking(dt, enemies)
        elif self.returning:
            self._update_returning(dt)

        self.x += self.vx * dt
        self.y += self.vy * dt

        if len(self._trail) >= self._trail_max:
            self._trail.pop(0)
        self._trail.append((self.x, self.y))

        self.life -= dt
        if self.life <= 0:
            self._expire()
            return

        nearby = grid.query_radius(self.x, self.y, self.radius + 30)
        for enemy in nearby:
            if not enemy.alive or id(enemy) in self._hit_ids:
                continue
            if self.collides_with(enemy):
                self._on_hit(enemy, enemies)
                if not self.alive:
                    return

    def _update_tracking(self, dt: float, enemies: list) -> None:
        if self._target is None or not self._target.alive:
            self._target = nearest_enemy(self.x, self.y, enemies)
        if self._target is None:
            return
        dx = self._target.x - self.x
        dy = self._target.y - self.y
        self._turn_toward(math.atan2(dy, dx), dt, self.turn_speed, self._speed)

    def _update_returning(self, dt: float) -> None:
        self._return_timer += dt
        if self._return_timer < self.return_after or self._player is None:
            return
        dx = self._player.x - self.x
        dy = self._player.y - self.y
        self._turn_toward(math.atan2(dy, dx), dt, self.return_speed * 4.0, self._speed * max(1.0, self.return_speed))

    def _turn_toward(self, target_angle: float, dt: float, turn_speed: float, speed: float) -> None:
        cur_angle = math.atan2(self.vy, self.vx)
        diff = target_angle - cur_angle
        while diff > math.pi:
            diff -= math.pi * 2
        while diff < -math.pi:
            diff += math.pi * 2
        new_angle = cur_angle + diff * min(1.0, turn_speed * dt)
        self.vx = math.cos(new_angle) * speed
        self.vy = math.sin(new_angle) * speed

    def _on_hit(self, enemy, enemies: list) -> None:
        apply_weapon_damage(enemy, self.damage, self._player, self.x, self.y, self.kb_force)
        self._hit_ids.add(id(enemy))
        if self.slow_dur > 0:
            enemy.apply_slow(self.slow_mul, self.slow_dur)
        self._hits_left -= 1
        if self._hits_left <= 0:
            if self.explode_radius > 0:
                self._explode(enemies)
            else:
                self.alive = False

    def _expire(self) -> None:
        if self.explode_radius > 0:
            self._explode([])
        self.alive = False

    def _explode(self, enemies: list) -> None:
        particles.burst(self.x, self.y, self.color, count=16, speed=120, life=0.5, size=6, gravity=40)
        if self.explode_radius <= 0 or self._player is None:
            self.alive = False
            return
        r2 = self.explode_radius * self.explode_radius
        for enemy in enemies:
            if not enemy.alive or id(enemy) in self._hit_ids:
                continue
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            if dx * dx + dy * dy <= r2:
                factor = 1.0 - math.hypot(dx, dy) / self.explode_radius
                apply_weapon_damage(enemy, self.explode_damage * factor, self._player, self.x, self.y, 80)
        self.alive = False

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive:
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        if sx < -40 or sx > surface.get_width() + 40 or sy < -40 or sy > surface.get_height() + 40:
            return

        for idx, (tx, ty) in enumerate(self._trail):
            tsx, tsy = cam.world_to_screen(tx, ty)
            ratio = (idx + 1) / max(1, len(self._trail))
            tr = max(1, int(self.size * 0.4 * ratio))
            alpha = int(160 * ratio)
            pygame.draw.circle(surface, (*self._trail_color[:3], alpha), (int(tsx), int(tsy)), tr)

        angle = math.atan2(self.vy, self.vx)
        if self.shape == "dagger":
            _draw_dagger(surface, sx, sy, angle, self.size, self.color)
        elif self.shape == "ice":
            _draw_ice(surface, sx, sy, angle, self.size, self.color)
        elif self.shape == "missile":
            _draw_missile(surface, sx, sy, angle, self.size, self.color)
        elif self.shape == "boomerang":
            _draw_boomerang(surface, sx, sy, angle, self.size, self.color)
        else:
            shapes.circle(surface, self.color, sx, sy, int(self.size))
            shapes.circle(surface, (255, 255, 255), sx, sy, max(1, int(self.size * 0.4)))


def _draw_dagger(surface, sx, sy, angle, size, color):
    l = size * 2.8
    w = size * 0.55
    ca = math.cos(angle)
    sa = math.sin(angle)
    pa = angle + math.pi / 2
    cp = math.cos(pa)
    sp = math.sin(pa)
    pts = [
        (sx + ca * l, sy + sa * l),
        (sx + cp * w, sy + sp * w),
        (sx - ca * l * 0.35, sy - sa * l * 0.35),
        (sx - cp * w, sy - sp * w),
    ]
    shapes.polygon(surface, color, pts)
    shapes.polygon(surface, (255, 255, 255), pts, width=1)


def _draw_ice(surface, sx, sy, angle, size, color):
    l = size * 2.4
    w = size * 0.85
    ca = math.cos(angle)
    sa = math.sin(angle)
    pa = angle + math.pi / 2
    cp = math.cos(pa)
    sp = math.sin(pa)
    pts = [
        (sx + ca * l, sy + sa * l),
        (sx + cp * w, sy + sp * w),
        (sx - ca * l * 0.4, sy - sa * l * 0.4),
        (sx - cp * w, sy - sp * w),
    ]
    shapes.polygon(surface, color, pts)
    light = tuple(min(255, c + 80) for c in color)
    shapes.polygon(surface, light, pts, width=1)


def _draw_missile(surface, sx, sy, angle, size, color):
    l = size * 2.5
    w = size * 0.9
    ca = math.cos(angle)
    sa = math.sin(angle)
    pa = angle + math.pi / 2
    cp = math.cos(pa)
    sp = math.sin(pa)
    pts = [
        (sx + ca * l, sy + sa * l),
        (sx + cp * w, sy + sp * w),
        (sx - ca * l * 0.3, sy - sa * l * 0.3),
        (sx - cp * w, sy - sp * w),
    ]
    shapes.polygon(surface, color, pts)
    tail_x = sx - ca * size * 2
    tail_y = sy - sa * size * 2
    shapes.circle(surface, (255, 160, 30), tail_x, tail_y, max(1, int(size * 0.7)))


def _draw_boomerang(surface, sx, sy, angle, size, color):
    points = []
    for idx in range(4):
        a = angle + math.pi / 2 * idx
        inner = size * 0.45 if idx % 2 else size * 1.6
        points.append((sx + math.cos(a) * inner, sy + math.sin(a) * inner))
    shapes.polygon(surface, color, points)
    shapes.polygon(surface, (255, 255, 255), points, width=1)


class ProjectileSystem:
    def __init__(self, pool_size: int = _POOL_SIZE) -> None:
        self._pool: list[Projectile] = [Projectile() for _ in range(pool_size)]
        self._active: list[Projectile] = []
        self._ptr = 0

    def spawn(self, **kwargs) -> Projectile | None:
        size = len(self._pool)
        for _ in range(size):
            proj = self._pool[self._ptr % size]
            self._ptr = (self._ptr + 1) % size
            if not proj.alive:
                proj.init(**kwargs)
                self._active.append(proj)
                return proj
        return None

    def update(self, dt: float, enemies: list, grid) -> None:
        keep = []
        for proj in self._active:
            proj.update(dt, enemies, grid)
            if proj.alive:
                keep.append(proj)
        self._active = keep

    def draw(self, surface: pygame.Surface, cam) -> None:
        for proj in self._active:
            proj.draw(surface, cam)

    def clear(self) -> None:
        for proj in self._active:
            proj.alive = False
        self._active.clear()

    @property
    def count(self) -> int:
        return len(self._active)
