"""场地危险物系统，目前包含黑洞。"""

from __future__ import annotations

import math

import pygame

from src.render import shapes
from src.render.particles import particles


class BlackHole:
    def __init__(self) -> None:
        self.alive = False

    def init(
        self,
        x: float,
        y: float,
        life: float,
        pull_radius: float,
        damage_radius: float,
        pull_strength: float,
        dps: float,
        color: tuple[int, int, int] = (90, 50, 170),
    ) -> None:
        self.x = x
        self.y = y
        self.life = life
        self.pull_radius = pull_radius
        self.damage_radius = damage_radius
        self.pull_strength = pull_strength
        self.dps = dps
        self.color = color
        self.age = 0.0
        self._damage_tick = 0.0
        self.alive = True

    def update(self, dt: float, player) -> tuple[float, float]:
        if not self.alive:
            return (0.0, 0.0)

        self.life -= dt
        self.age += dt
        if self.life <= 0:
            self.alive = False
            particles.burst(self.x, self.y, self.color, count=18, speed=80, life=0.35, size=5)
            return (0.0, 0.0)

        dx = self.x - player.x
        dy = self.y - player.y
        dist = math.hypot(dx, dy) or 0.001
        force_x = 0.0
        force_y = 0.0
        if dist < self.pull_radius:
            strength = self.pull_strength * (1.0 - dist / self.pull_radius)
            force_x = dx / dist * strength
            force_y = dy / dist * strength
        if dist < self.damage_radius:
            self._damage_tick += dt
            if self._damage_tick >= 0.25:
                self._damage_tick -= 0.25
                player.take_damage(self.dps * 0.25, self.x, self.y)
                particles.sparkle(player.x, player.y, (120, 80, 210), count=2, radius=18)
        return (force_x, force_y)

    def draw(self, surface: pygame.Surface, cam, low_detail: bool = False) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.pull_radius + 16):
            return

        sx, sy = cam.world_to_screen(self.x, self.y)
        phase = self.age * 2.6
        glow_layers = 2 if low_detail else 3
        ring_count = 1 if low_detail else 3
        shapes.glow_circle(surface, self.color, sx, sy, self.damage_radius, layers=glow_layers, alpha_start=44)
        for idx in range(ring_count):
            ring_r = self.damage_radius + 10 + idx * 18 + math.sin(phase + idx) * 4
            shapes.ring(surface, self.color, sx, sy, ring_r, 2)
        shapes.circle(surface, (20, 12, 35), sx, sy, self.damage_radius * 0.95)
        shapes.circle(surface, (255, 255, 255), sx, sy, self.damage_radius * 0.18)


class HazardSystem:
    def __init__(self, pool_size: int = 64, max_total_pull: float = 185.0) -> None:
        self._pool = [BlackHole() for _ in range(pool_size)]
        self._active: list[BlackHole] = []
        self._ptr = 0
        self._max_total_pull = max_total_pull
        self._low_detail = False

    def spawn_black_hole(self, **kwargs):
        size = len(self._pool)
        for _ in range(size):
            hazard = self._pool[self._ptr % size]
            self._ptr = (self._ptr + 1) % size
            if not hazard.alive:
                hazard.init(**kwargs)
                self._active.append(hazard)
                return hazard
        return None

    def update(self, dt: float, player) -> tuple[float, float]:
        total_x = 0.0
        total_y = 0.0
        keep: list[BlackHole] = []
        for hazard in self._active:
            fx, fy = hazard.update(dt, player)
            total_x += fx
            total_y += fy
            if hazard.alive:
                keep.append(hazard)
        self._active = keep
        total_force = math.hypot(total_x, total_y)
        if total_force > self._max_total_pull > 0:
            scale = self._max_total_pull / total_force
            total_x *= scale
            total_y *= scale
        return (total_x, total_y)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for hazard in self._active:
            hazard.draw(surface, cam, self._low_detail)

    def clear(self) -> None:
        for hazard in self._active:
            hazard.alive = False
        self._active.clear()

    def set_low_detail(self, enabled: bool) -> None:
        self._low_detail = enabled

    @property
    def count(self) -> int:
        return len(self._active)
