"""Enemy projectile system with support for homing missiles and hazard spawning."""

from __future__ import annotations

import math

import pygame

from src.render import shapes
from src.render.particles import particles


class EnemyBullet:
    def __init__(self) -> None:
        self.alive = False

    def init(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        damage: float,
        life: float,
        radius: float,
        color: tuple[int, int, int],
        shape: str = "orb",
        trail: int = 8,
        tracking: bool = False,
        turn_speed: float = 2.0,
        explode_fire: dict | None = None,
        burst_count: int = 10,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self._speed = math.hypot(vx, vy)
        self.damage = damage
        self.life = life
        self.radius = radius
        self.color = color
        self.shape = shape
        self.trail: list[tuple[float, float]] = []
        self.trail_max = trail
        self.tracking = tracking
        self.turn_speed = turn_speed
        self.explode_fire = dict(explode_fire) if explode_fire else None
        self.burst_count = burst_count
        self.alive = True

    def update(self, dt: float, player, hazard_system=None) -> None:
        if not self.alive:
            return

        self.life -= dt
        if self.life <= 0:
            self._explode(hazard_system)
            return

        if self.tracking:
            self._update_tracking(dt, player)

        self.x += self.vx * dt
        self.y += self.vy * dt
        if len(self.trail) >= self.trail_max:
            self.trail.pop(0)
        self.trail.append((self.x, self.y))

        dx = player.x - self.x
        dy = player.y - self.y
        hit_r = self.radius + player.radius
        if dx * dx + dy * dy <= hit_r * hit_r:
            actual = player.take_damage(self.damage, self.x, self.y)
            if actual > 0:
                particles.burst(self.x, self.y, self.color, count=self.burst_count, speed=90, life=0.35, size=4)
            self._explode(hazard_system)

    def _update_tracking(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        target_angle = math.atan2(dy, dx)
        current_angle = math.atan2(self.vy, self.vx)
        diff = target_angle - current_angle
        while diff > math.pi:
            diff -= math.tau
        while diff < -math.pi:
            diff += math.tau
        new_angle = current_angle + diff * min(1.0, self.turn_speed * dt)
        self.vx = math.cos(new_angle) * self._speed
        self.vy = math.sin(new_angle) * self._speed

    def _explode(self, hazard_system=None) -> None:
        if not self.alive:
            return
        particles.burst(self.x, self.y, self.color, count=max(8, self.burst_count + 2), speed=105, life=0.38, size=5)
        if self.explode_fire and hazard_system is not None:
            payload = dict(self.explode_fire)
            payload.setdefault("x", self.x)
            payload.setdefault("y", self.y)
            hazard_system.spawn_fire_pit(**payload)
        self.alive = False

    def draw(self, surface: pygame.Surface, cam, low_detail: bool = False) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.radius + 12):
            return

        if not low_detail:
            for idx, (tx, ty) in enumerate(self.trail):
                tsx, tsy = cam.world_to_screen(tx, ty)
                ratio = (idx + 1) / max(1, len(self.trail))
                trail_r = max(1, int(self.radius * 0.55 * ratio))
                pygame.draw.circle(surface, self.color, (int(tsx), int(tsy)), trail_r)

        sx, sy = cam.world_to_screen(self.x, self.y)
        angle = math.atan2(self.vy, self.vx)
        if self.shape == "spike":
            _draw_spike(surface, sx, sy, angle, self.radius, self.color)
        elif self.shape == "bolt":
            _draw_bolt(surface, sx, sy, angle, self.radius, self.color)
        elif self.shape == "missile":
            _draw_missile(surface, sx, sy, angle, self.radius, self.color, low_detail)
        else:
            if not low_detail:
                shapes.glow_circle(surface, self.color, sx, sy, self.radius, layers=2, alpha_start=55)
            shapes.circle(surface, self.color, sx, sy, self.radius)
            if not low_detail:
                shapes.circle(surface, (255, 255, 255), sx, sy, self.radius * 0.35)


class EnemyBulletSystem:
    def __init__(self, pool_size: int = 240) -> None:
        self._pool = [EnemyBullet() for _ in range(pool_size)]
        self._active: list[EnemyBullet] = []
        self._ptr = 0
        self._low_detail = False

    def spawn(self, **kwargs) -> EnemyBullet | None:
        if self._low_detail:
            kwargs.setdefault("trail", 2)
        size = len(self._pool)
        for _ in range(size):
            bullet = self._pool[self._ptr % size]
            self._ptr = (self._ptr + 1) % size
            if not bullet.alive:
                bullet.init(**kwargs)
                self._active.append(bullet)
                return bullet
        return None

    def update(self, dt: float, player, hazard_system=None, bounds=None) -> None:
        keep = []
        left = top = right = bottom = None
        if bounds is not None:
            left, top, right, bottom = bounds
        margin = 260.0
        for bullet in self._active:
            bullet.update(dt, player, hazard_system)
            if bullet.alive and bounds is not None:
                if bullet.x < left - margin or bullet.x > right + margin or bullet.y < top - margin or bullet.y > bottom + margin:
                    bullet._explode(hazard_system)
            if bullet.alive:
                keep.append(bullet)
        self._active = keep

    def draw(self, surface: pygame.Surface, cam) -> None:
        for bullet in self._active:
            bullet.draw(surface, cam, self._low_detail)

    def clear(self) -> None:
        for bullet in self._active:
            bullet.alive = False
        self._active.clear()

    def set_low_detail(self, enabled: bool) -> None:
        self._low_detail = enabled

    @property
    def count(self) -> int:
        return len(self._active)


def _draw_spike(surface, sx, sy, angle, radius, color) -> None:
    length = radius * 2.5
    width = radius * 0.8
    ca = math.cos(angle)
    sa = math.sin(angle)
    pa = angle + math.pi / 2
    cp = math.cos(pa)
    sp = math.sin(pa)
    pts = [
        (sx + ca * length, sy + sa * length),
        (sx + cp * width, sy + sp * width),
        (sx - ca * radius * 0.7, sy - sa * radius * 0.7),
        (sx - cp * width, sy - sp * width),
    ]
    shapes.polygon(surface, color, pts)
    shapes.polygon(surface, (255, 255, 255), pts, width=1)


def _draw_bolt(surface, sx, sy, angle, radius, color) -> None:
    length = radius * 2.2
    width = radius * 0.65
    pts = [
        (sx + math.cos(angle) * length, sy + math.sin(angle) * length),
        (sx + math.cos(angle + 2.35) * width, sy + math.sin(angle + 2.35) * width),
        (sx + math.cos(angle + math.pi) * length * 0.45, sy + math.sin(angle + math.pi) * length * 0.45),
        (sx + math.cos(angle - 2.35) * width, sy + math.sin(angle - 2.35) * width),
    ]
    shapes.polygon(surface, color, pts)
    shapes.polygon(surface, (255, 255, 255), pts, width=1)


def _draw_missile(surface, sx, sy, angle, radius, color, low_detail: bool) -> None:
    length = radius * 2.7
    width = radius * 0.9
    pts = [
        (sx + math.cos(angle) * length, sy + math.sin(angle) * length),
        (sx + math.cos(angle + 2.45) * width, sy + math.sin(angle + 2.45) * width),
        (sx + math.cos(angle + math.pi) * radius * 0.8, sy + math.sin(angle + math.pi) * radius * 0.8),
        (sx + math.cos(angle - 2.45) * width, sy + math.sin(angle - 2.45) * width),
    ]
    if not low_detail:
        shapes.glow_circle(surface, color, sx, sy, radius * 1.05, layers=2, alpha_start=34)
    shapes.polygon(surface, color, pts)
    tail_x = sx - math.cos(angle) * radius * 1.4
    tail_y = sy - math.sin(angle) * radius * 1.4
    shapes.circle(surface, (255, 150, 40), tail_x, tail_y, max(2, int(radius * 0.55)))
