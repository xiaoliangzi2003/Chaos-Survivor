"""World pickups for XP gems and gold drops."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from src.core.camera import Camera
from src.core.config import XP_GEM_VALUES
from src.render import shapes
from src.render.particles import particles

_XP_ORDER = (
    ("large", XP_GEM_VALUES["large"]),
    ("medium", XP_GEM_VALUES["medium"]),
    ("small", XP_GEM_VALUES["small"]),
)

_PICKUP_STYLE = {
    "xp_small": {"color": (90, 185, 255), "radius": 7},
    "xp_medium": {"color": (110, 215, 255), "radius": 9},
    "xp_large": {"color": (150, 240, 255), "radius": 12},
    "gold": {"color": (255, 205, 70), "radius": 8},
}


@dataclass(slots=True)
class Pickup:
    kind: str
    value: int
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    alive: bool = True

    def update(self, dt: float, player) -> bool:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        attract_range = player.stats.pickup_radius * 2.2

        self.vx *= 0.92
        self.vy *= 0.92
        if dist < attract_range:
            pull = 180 + (attract_range - dist) * 5
            self.vx += dx / dist * pull * dt
            self.vy += dy / dist * pull * dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        if dist <= player.stats.pickup_radius + self.radius:
            self.collect(player)
            return True
        return False

    def collect(self, player) -> None:
        self.alive = False
        if self.kind.startswith("xp_"):
            player.gain_xp(self.value)
            particles.sparkle(self.x, self.y, (120, 220, 255), count=6, radius=16)
        else:
            player.gain_gold(self.value)
            particles.sparkle(self.x, self.y, (255, 220, 100), count=5, radius=14)

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.radius + 4):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        style = _PICKUP_STYLE[self.kind]
        color = style["color"]
        if self.kind.startswith("xp_"):
            shapes.glow_circle(surface, color, sx, sy, self.radius, layers=2, alpha_start=40)
            shapes.diamond(surface, color, sx, sy, self.radius, self.radius + 2)
            shapes.diamond(surface, (255, 255, 255), sx, sy, self.radius, self.radius + 2, width=1)
        else:
            shapes.glow_circle(surface, color, sx, sy, self.radius, layers=2, alpha_start=35)
            shapes.circle(surface, color, sx, sy, self.radius)
            shapes.circle(surface, (255, 245, 180), sx, sy, self.radius * 0.45)


class PickupSystem:
    def __init__(self) -> None:
        self._items: list[Pickup] = []

    def spawn_rewards(self, x: float, y: float, xp_value: int, gold_value: int) -> None:
        for kind, value in _split_xp_value(xp_value):
            self._items.append(self._make_pickup(kind, value, x, y))
        if gold_value > 0:
            self._items.append(self._make_pickup("gold", gold_value, x, y))

    def update(self, dt: float, player) -> None:
        keep: list[Pickup] = []
        for item in self._items:
            if item.update(dt, player):
                continue
            keep.append(item)
        self._items = keep

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        for item in self._items:
            item.draw(surface, cam)

    def clear(self) -> None:
        self._items.clear()

    def absorb_all(self, player, xp_ratio: float = 1.0, gold_ratio: float = 1.0) -> tuple[float, int]:
        total_xp = 0
        total_gold = 0
        for item in self._items:
            if not item.alive:
                continue
            if item.kind.startswith("xp_"):
                total_xp += item.value
            else:
                total_gold += item.value

        gained_xp = total_xp * max(0.0, xp_ratio)
        gained_gold = int(total_gold * max(0.0, gold_ratio))
        if gained_xp > 0:
            player.gain_xp(gained_xp)
            particles.sparkle(player.x, player.y, (120, 220, 255), count=10, radius=26)
        if gained_gold > 0:
            player.gain_gold(gained_gold)
            particles.sparkle(player.x, player.y, (255, 220, 100), count=8, radius=22)

        self.clear()
        return gained_xp, gained_gold

    @property
    def count(self) -> int:
        return len(self._items)

    def _make_pickup(self, kind: str, value: int, x: float, y: float) -> Pickup:
        style = _PICKUP_STYLE[kind]
        angle = (len(self._items) * 1.73) % (math.pi * 2)
        speed = 35 + (len(self._items) % 4) * 15
        return Pickup(
            kind=kind,
            value=value,
            x=x,
            y=y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed - 30,
            radius=style["radius"],
        )


def _split_xp_value(total_value: int) -> list[tuple[str, int]]:
    if total_value <= 0:
        return []

    remaining = total_value
    result: list[tuple[str, int]] = []
    for size_name, size_value in _XP_ORDER:
        while remaining >= size_value:
            result.append((f"xp_{size_name}", size_value))
            remaining -= size_value
    return result
