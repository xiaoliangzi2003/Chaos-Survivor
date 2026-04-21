"""World hazards such as black holes and burning craters."""

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


class FirePit:
    def __init__(self) -> None:
        self.alive = False

    def init(
        self,
        x: float,
        y: float,
        life: float,
        damage_radius: float,
        dps: float,
        color: tuple[int, int, int] = (255, 120, 60),
    ) -> None:
        self.x = x
        self.y = y
        self.life = life
        self.damage_radius = damage_radius
        self.dps = dps
        self.color = color
        self.age = 0.0
        self._damage_tick = 0.0
        self.alive = True

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return

        self.life -= dt
        self.age += dt
        if self.life <= 0:
            self.alive = False
            particles.burst(self.x, self.y, self.color, count=10, speed=55, life=0.24, size=4)
            return

        dx = self.x - player.x
        dy = self.y - player.y
        dist = math.hypot(dx, dy) or 0.001
        if dist < self.damage_radius:
            self._damage_tick += dt
            if self._damage_tick >= 0.25:
                self._damage_tick -= 0.25
                player.take_damage(self.dps * 0.25, self.x, self.y)
                particles.sparkle(player.x, player.y, (255, 150, 80), count=2, radius=14)

        if int(self.age * 12) % 3 == 0:
            particles.sparkle(self.x, self.y, self.color, count=1, radius=self.damage_radius * 0.7)

    def draw(self, surface: pygame.Surface, cam, low_detail: bool = False) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.damage_radius + 16):
            return

        sx, sy = cam.world_to_screen(self.x, self.y)
        pulse = 1.0 + math.sin(self.age * 6.0) * 0.08
        outer = self.damage_radius * pulse
        shapes.glow_circle(surface, self.color, sx, sy, outer, layers=2 if low_detail else 3, alpha_start=38)
        shapes.circle(surface, (95, 26, 10), sx, sy, self.damage_radius * 0.95)
        shapes.circle(surface, (220, 70, 35), sx, sy, self.damage_radius * 0.72)
        shapes.circle(surface, (255, 175, 80), sx, sy, self.damage_radius * 0.36)
        if not low_detail:
            shapes.ring(surface, (255, 220, 140), sx, sy, self.damage_radius * 0.9, 2)


class HazardSystem:
    def __init__(self, pool_size: int = 64, max_total_pull: float = 185.0) -> None:
        self._black_hole_pool = [BlackHole() for _ in range(pool_size)]
        self._fire_pit_pool = [FirePit() for _ in range(pool_size)]
        self._active_black_holes: list[BlackHole] = []
        self._active_fire_pits: list[FirePit] = []
        self._bh_ptr = 0
        self._fp_ptr = 0
        self._max_total_pull = max_total_pull
        self._low_detail = False

    def spawn_black_hole(self, **kwargs):
        size = len(self._black_hole_pool)
        for _ in range(size):
            hazard = self._black_hole_pool[self._bh_ptr % size]
            self._bh_ptr = (self._bh_ptr + 1) % size
            if not hazard.alive:
                hazard.init(**kwargs)
                self._active_black_holes.append(hazard)
                return hazard
        return None

    def spawn_fire_pit(self, **kwargs):
        size = len(self._fire_pit_pool)
        for _ in range(size):
            hazard = self._fire_pit_pool[self._fp_ptr % size]
            self._fp_ptr = (self._fp_ptr + 1) % size
            if not hazard.alive:
                hazard.init(**kwargs)
                self._active_fire_pits.append(hazard)
                return hazard
        return None

    def update(self, dt: float, player) -> tuple[float, float]:
        total_x = 0.0
        total_y = 0.0

        keep_holes: list[BlackHole] = []
        for hazard in self._active_black_holes:
            fx, fy = hazard.update(dt, player)
            total_x += fx
            total_y += fy
            if hazard.alive:
                keep_holes.append(hazard)
        self._active_black_holes = keep_holes

        keep_fire: list[FirePit] = []
        for hazard in self._active_fire_pits:
            hazard.update(dt, player)
            if hazard.alive:
                keep_fire.append(hazard)
        self._active_fire_pits = keep_fire

        total_force = math.hypot(total_x, total_y)
        if total_force > self._max_total_pull > 0:
            scale = self._max_total_pull / total_force
            total_x *= scale
            total_y *= scale
        return (total_x, total_y)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for hazard in self._active_fire_pits:
            hazard.draw(surface, cam, self._low_detail)
        for hazard in self._active_black_holes:
            hazard.draw(surface, cam, self._low_detail)

    def clear(self) -> None:
        for hazard in self._active_black_holes:
            hazard.alive = False
        for hazard in self._active_fire_pits:
            hazard.alive = False
        self._active_black_holes.clear()
        self._active_fire_pits.clear()

    def set_low_detail(self, enabled: bool) -> None:
        self._low_detail = enabled

    @property
    def count(self) -> int:
        return len(self._active_black_holes) + len(self._active_fire_pits)
