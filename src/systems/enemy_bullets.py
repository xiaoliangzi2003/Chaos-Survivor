"""Enemy projectile system."""

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
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.life = life
        self.radius = radius
        self.color = color
        self.shape = shape
        self.trail = []
        self.trail_max = trail
        self.alive = True

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return

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
                particles.burst(self.x, self.y, self.color, count=10, speed=90, life=0.35, size=4)
            self.alive = False

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.radius + 12):
            return

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
        else:
            shapes.glow_circle(surface, self.color, sx, sy, self.radius, layers=2, alpha_start=55)
            shapes.circle(surface, self.color, sx, sy, self.radius)
            shapes.circle(surface, (255, 255, 255), sx, sy, self.radius * 0.35)


class EnemyBulletSystem:
    def __init__(self, pool_size: int = 240) -> None:
        self._pool = [EnemyBullet() for _ in range(pool_size)]
        self._active: list[EnemyBullet] = []
        self._ptr = 0
        self._low_detail = False

    def spawn(self, **kwargs) -> EnemyBullet | None:
        if self._low_detail:
            kwargs.setdefault("trail", 3)
        size = len(self._pool)
        for _ in range(size):
            bullet = self._pool[self._ptr % size]
            self._ptr = (self._ptr + 1) % size
            if not bullet.alive:
                bullet.init(**kwargs)
                self._active.append(bullet)
                return bullet
        return None

    def update(self, dt: float, player, bounds=None) -> None:
        keep = []
        left = top = right = bottom = None
        if bounds is not None:
            left, top, right, bottom = bounds
        margin = 260.0
        for bullet in self._active:
            bullet.update(dt, player)
            if bullet.alive and bounds is not None:
                if bullet.x < left - margin or bullet.x > right + margin or bullet.y < top - margin or bullet.y > bottom + margin:
                    bullet.alive = False
            if bullet.alive:
                keep.append(bullet)
        self._active = keep

    def draw(self, surface: pygame.Surface, cam) -> None:
        for bullet in self._active:
            if self._low_detail and bullet.alive and cam.is_visible(bullet.x, bullet.y, bullet.radius + 12):
                sx, sy = cam.world_to_screen(bullet.x, bullet.y)
                angle = math.atan2(bullet.vy, bullet.vx)
                if bullet.shape == "spike":
                    _draw_spike(surface, sx, sy, angle, bullet.radius, bullet.color)
                elif bullet.shape == "bolt":
                    _draw_bolt(surface, sx, sy, angle, bullet.radius, bullet.color)
                else:
                    shapes.circle(surface, bullet.color, sx, sy, bullet.radius)
            else:
                bullet.draw(surface, cam)

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
