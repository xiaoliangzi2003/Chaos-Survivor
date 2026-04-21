"""Weapon base classes and helpers."""

from __future__ import annotations

import math

from src.core.rng import rng
from src.systems.damage_numbers import damage_numbers


def nearest_enemy(px: float, py: float, enemies: list, max_range: float = float("inf")):
    best = None
    best_sq = max_range * max_range
    for enemy in enemies:
        if not enemy.alive:
            continue
        dx = enemy.x - px
        dy = enemy.y - py
        dist_sq = dx * dx + dy * dy
        if dist_sq < best_sq:
            best_sq = dist_sq
            best = enemy
    return best


def enemies_in_radius(px: float, py: float, enemies: list, radius: float) -> list:
    radius_sq = radius * radius
    hits = []
    for enemy in enemies:
        if not enemy.alive:
            continue
        dx = enemy.x - px
        dy = enemy.y - py
        if dx * dx + dy * dy <= radius_sq:
            hits.append(enemy)
    return hits


def apply_weapon_damage(
    enemy,
    damage: float,
    player,
    source_x: float,
    source_y: float,
    kb_force: float = 130.0,
) -> tuple[bool, float, bool]:
    is_crit = rng.chance(player.stats.crit_rate)
    actual = damage * player.stats.atk_mul
    if is_crit:
        actual *= player.stats.crit_mul

    angle = math.atan2(enemy.y - source_y, enemy.x - source_x)
    killed = enemy.take_damage(actual, angle, kb_force)
    damage_numbers.add(enemy.x, enemy.y - enemy.radius - 6, actual, is_crit=is_crit)
    player.total_damage_dealt += actual

    feedback = getattr(player, "combat_feedback", None)
    if feedback:
        feedback(
            "enemy_hit",
            x=enemy.x,
            y=enemy.y,
            amount=actual,
            is_crit=is_crit,
            killed=killed,
            color=getattr(enemy, "color", (255, 255, 255)),
        )
    return killed, actual, is_crit


class Weapon:
    NAME = "Weapon"
    DESCRIPTION = ""
    ICON_COLOR = (200, 200, 200)
    MAX_LEVEL = 8
    LEVEL_DATA: list[dict] = []

    def __init__(self) -> None:
        self.level = 1
        self._timer = 0.0
        self._player_ref = None
        self._apply_level()

    def update(self, dt: float, player, enemies: list, grid, proj_system) -> None:
        self._player_ref = player
        effective_cooldown = self._cooldown / max(0.1, player.stats.atk_speed_mul)
        self._timer -= dt
        if self._timer <= 0:
            self._timer = effective_cooldown
            self._fire(player, enemies, grid, proj_system)

    def draw(self, surface, cam) -> None:
        pass

    def level_up(self) -> bool:
        if self.level >= self.MAX_LEVEL:
            return False
        self.level += 1
        self._apply_level()
        return True

    def _apply_level(self) -> None:
        if not self.LEVEL_DATA:
            return
        for key, value in self.LEVEL_DATA[self.level - 1].items():
            setattr(self, key, value)

    def _fire(self, player, enemies: list, grid, proj_system) -> None:
        raise NotImplementedError

    @property
    def _cooldown(self) -> float:
        return getattr(self, "cooldown", 1.0)

    @property
    def _damage(self) -> float:
        return getattr(self, "damage", 10.0)

    def _eff_range(self, player) -> float:
        return getattr(self, "radius", 150.0) * player.stats.range_mul

    def _eff_proj_count(self, player) -> int:
        return getattr(self, "count", 1) + player.stats.proj_bonus
