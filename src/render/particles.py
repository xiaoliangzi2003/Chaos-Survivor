"""Particle system with pooling and adaptive load shedding."""

from __future__ import annotations

import math
import random

import pygame

from src.core.camera import Camera
from src.core.config import MAX_PARTICLES, MAX_PARTICLES_LO


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "r", "g", "b", "size", "gravity", "drag", "alive")

    def __init__(self) -> None:
        self.alive = False

    def init(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        color: tuple[int, int, int],
        size: float,
        gravity: float = 0.0,
        drag: float = 0.96,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.r, self.g, self.b = color
        self.size = size
        self.gravity = gravity
        self.drag = drag
        self.alive = True


class ParticleSystem:
    def __init__(self, max_particles: int = MAX_PARTICLES) -> None:
        self._pool: list[Particle] = [Particle() for _ in range(max_particles)]
        self._active: list[Particle] = []
        self._free_idx = 0
        self._spawn_scale = 1.0
        self._draw_limit = max_particles
        self._low_detail = False

    def emit(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: float,
        color: tuple[int, int, int],
        size: float = 4.0,
        gravity: float = 0.0,
        drag: float = 0.96,
    ) -> None:
        if len(self._active) >= len(self._pool):
            return

        particle = self._pool[self._free_idx % len(self._pool)]
        self._free_idx += 1
        if particle.alive:
            return
        particle.init(x, y, vx, vy, life, color, size, gravity, drag)
        self._active.append(particle)

    def burst(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 12,
        speed: float = 80.0,
        life: float = 0.5,
        size: float = 4.0,
        gravity: float = 60.0,
        spread: float = math.pi * 2,
    ) -> None:
        for _ in range(self._scaled_count(count)):
            angle = random.uniform(0.0, spread)
            particle_speed = random.uniform(speed * 0.5, speed)
            self.emit(
                x,
                y,
                math.cos(angle) * particle_speed,
                math.sin(angle) * particle_speed,
                life * random.uniform(0.6, 1.4),
                color,
                random.uniform(size * 0.5, size),
                gravity,
            )

    def directional(
        self,
        x: float,
        y: float,
        angle: float,
        spread: float,
        color: tuple[int, int, int],
        count: int = 6,
        speed: float = 60.0,
        life: float = 0.35,
        size: float = 3.0,
    ) -> None:
        for _ in range(self._scaled_count(count)):
            theta = angle + random.uniform(-spread / 2, spread / 2)
            particle_speed = random.uniform(speed * 0.4, speed)
            self.emit(x, y, math.cos(theta) * particle_speed, math.sin(theta) * particle_speed, life, color, size)

    def sparkle(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 5,
        radius: float = 12.0,
    ) -> None:
        for _ in range(self._scaled_count(count)):
            angle = random.uniform(0.0, math.tau)
            dist = random.uniform(0.0, radius)
            self.emit(
                x + math.cos(angle) * dist,
                y + math.sin(angle) * dist,
                random.uniform(-15, 15),
                random.uniform(-40, -10),
                random.uniform(0.4, 0.8),
                color,
                random.uniform(2, 5),
            )

    def update(self, dt: float) -> None:
        keep: list[Particle] = []
        for particle in self._active:
            particle.life -= dt
            if particle.life <= 0:
                particle.alive = False
                continue
            particle.vx *= particle.drag
            particle.vy *= particle.drag
            particle.vy += particle.gravity * dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            keep.append(particle)
        self._active = keep

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        if not self._active:
            return

        limit = max(1, min(self._draw_limit, len(self._active)))
        step = max(1, math.ceil(len(self._active) / limit))
        width = surface.get_width()
        height = surface.get_height()

        for idx, particle in enumerate(self._active):
            if idx % step:
                continue
            sx, sy = cam.world_to_screen(particle.x, particle.y)
            if sx < -20 or sx > width + 20 or sy < -20 or sy > height + 20:
                continue
            ratio = particle.life / particle.max_life
            alpha = 255 if self._low_detail else int(255 * ratio)
            size = max(1, int(particle.size * ratio))
            pygame.draw.circle(
                surface,
                (particle.r, particle.g, particle.b, alpha) if alpha < 255 else (particle.r, particle.g, particle.b),
                (int(sx), int(sy)),
                size,
            )

    def clear(self) -> None:
        for particle in self._active:
            particle.alive = False
        self._active.clear()

    def configure(self, spawn_scale: float = 1.0, draw_limit: int | None = None, low_detail: bool = False) -> None:
        self._spawn_scale = max(0.2, min(1.0, spawn_scale))
        self._draw_limit = max(32, draw_limit if draw_limit is not None else (MAX_PARTICLES_LO if low_detail else len(self._pool)))
        self._low_detail = low_detail

    def _scaled_count(self, count: int) -> int:
        count = max(1, int(round(count * self._spawn_scale)))
        if self._low_detail:
            count = max(1, int(round(count * 0.8)))
        return count

    @property
    def count(self) -> int:
        return len(self._active)


particles = ParticleSystem()
