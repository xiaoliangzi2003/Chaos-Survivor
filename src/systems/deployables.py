"""Deployable item effects: mines, turrets, poison mushrooms, campfires."""

from __future__ import annotations

import math

import pygame

from src.core.rng import rng
from src.render import shapes
from src.render.particles import particles
from src.systems.damage_numbers import damage_numbers


# ── Mine ────────────────────────────────────────────────────────────────────

class Mine:
    TRIGGER_RADIUS = 46
    BLAST_RADIUS = 170
    BASE_DAMAGE = 65

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.age = 0.0
        self.alive = True

    def update(self, dt: float, player, enemies: list) -> None:
        if not self.alive:
            return
        self.age += dt
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            if dx * dx + dy * dy <= self.TRIGGER_RADIUS ** 2:
                self._explode(player, enemies)
                return

    def _explode(self, player, enemies: list) -> None:
        self.alive = False
        damage = self.BASE_DAMAGE * player.stats.atk_mul
        particles.burst(self.x, self.y, (255, 180, 40), count=28, speed=180, life=0.55, size=6)
        particles.burst(self.x, self.y, (255, 100, 20), count=14, speed=100, life=0.35, size=4)
        r2 = self.BLAST_RADIUS ** 2
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            if dx * dx + dy * dy <= r2:
                angle = math.atan2(dy, dx)
                enemy.take_damage(damage, angle, 120.0)

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, 20):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        pulse = 1.0 + math.sin(self.age * 5.0) * 0.15
        r = int(10 * pulse)
        shapes.glow_circle(surface, (255, 200, 40), sx, sy, 18, layers=2, alpha_start=35)
        shapes.diamond(surface, (255, 200, 40), sx, sy, r, r + 2)
        shapes.diamond(surface, (255, 255, 180), sx, sy, r // 2, r // 2 + 1)


# ── Turret ──────────────────────────────────────────────────────────────────

class Turret:
    RANGE = 300
    COOLDOWN = 1.2
    BASE_DAMAGE = 22
    SIZE = 14

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.age = 0.0
        self.alive = True
        self._timer = 0.3
        self._barrel_angle = 0.0

    def update(self, dt: float, player, enemies: list) -> None:
        if not self.alive:
            return
        self.age += dt
        self._timer -= dt

        target = self._find_target(enemies)
        if target is not None:
            self._barrel_angle = math.atan2(target.y - self.y, target.x - self.x)
            if self._timer <= 0:
                self._timer = self.COOLDOWN / max(0.5, player.stats.atk_speed_mul)
                damage = self.BASE_DAMAGE * player.stats.atk_mul
                angle = self._barrel_angle
                target.take_damage(damage, angle, 0.0)
                actual = getattr(target, "last_damage_taken", damage)
                if actual > 0:
                    damage_numbers.add(target.x, target.y - target.radius - 6, actual)
                    particles.burst(target.x, target.y, (255, 220, 80), count=4, speed=70, life=0.25, size=3)
        elif self._timer <= 0:
            self._timer = self.COOLDOWN

    def _find_target(self, enemies: list):
        best = None
        best_sq = self.RANGE ** 2
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_sq:
                best_sq = dist_sq
                best = enemy
        return best

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.SIZE + 8):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)

        shapes.glow_circle(surface, (80, 180, 255), sx, sy, self.RANGE, layers=1, alpha_start=8)
        shapes.ring(surface, (60, 140, 200), sx, sy, self.RANGE, 1)

        body_rect = pygame.Rect(sx - self.SIZE, sy - self.SIZE, self.SIZE * 2, self.SIZE * 2)
        pygame.draw.rect(surface, (60, 90, 140), body_rect, border_radius=4)
        pygame.draw.rect(surface, (100, 160, 220), body_rect, 2, border_radius=4)

        # Barrel
        bx = sx + math.cos(self._barrel_angle) * (self.SIZE + 10)
        by = sy + math.sin(self._barrel_angle) * (self.SIZE + 10)
        pygame.draw.line(surface, (160, 210, 255), (int(sx), int(sy)), (int(bx), int(by)), 4)


# ── Poison Mushroom ─────────────────────────────────────────────────────────

_POISON_TICKS = 5
_POISON_DPS = 5.0
_MUSHROOM_ATTRACTION_RADIUS = 240
_MUSHROOM_BITE_RADIUS = 42
_MUSHROOM_MAX_BITES = 10


class PoisonMushroom:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.age = 0.0
        self.alive = True
        self._bites_left = _MUSHROOM_MAX_BITES
        self._bitten_ids: set[int] = set()

    def update(self, dt: float, enemies: list, poison_targets: list) -> None:
        if not self.alive:
            return
        self.age += dt

        attract_r2 = _MUSHROOM_ATTRACTION_RADIUS ** 2
        bite_r2 = _MUSHROOM_BITE_RADIUS ** 2

        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - self.x
            dy = enemy.y - self.y
            dist_sq = dx * dx + dy * dy

            if dist_sq <= attract_r2:
                dist = math.sqrt(dist_sq) or 0.001
                strength = 60.0 * (1.0 - dist / _MUSHROOM_ATTRACTION_RADIUS)
                if hasattr(enemy, "vx"):
                    enemy.vx += (-dx / dist) * strength * dt
                    enemy.vy += (-dy / dist) * strength * dt

            if dist_sq <= bite_r2 and id(enemy) not in self._bitten_ids and self._bites_left > 0:
                self._bitten_ids.add(id(enemy))
                self._bites_left -= 1
                poison_targets.append([enemy, _POISON_TICKS, 0.0])
                particles.burst(enemy.x, enemy.y, (120, 200, 80), count=6, speed=60, life=0.35, size=3)
                if self._bites_left <= 0:
                    self._expire()
                    return

        # Ambient spore particles
        if int(self.age * 4) % 2 == 0:
            particles.sparkle(self.x, self.y, (140, 220, 100), count=1, radius=_MUSHROOM_ATTRACTION_RADIUS * 0.5)

    def _expire(self) -> None:
        self.alive = False
        particles.burst(self.x, self.y, (120, 200, 80), count=18, speed=80, life=0.5, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, _MUSHROOM_ATTRACTION_RADIUS + 10):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)

        shapes.glow_circle(surface, (100, 200, 80), sx, sy, _MUSHROOM_ATTRACTION_RADIUS, layers=1, alpha_start=10)
        shapes.ring(surface, (80, 160, 60), sx, sy, _MUSHROOM_ATTRACTION_RADIUS, 1)

        # Stem
        pygame.draw.rect(surface, (180, 150, 100), pygame.Rect(sx - 4, sy - 2, 8, 14), border_radius=2)
        # Cap
        pulse = 1.0 + math.sin(self.age * 2.0) * 0.06
        cap_r = int(18 * pulse)
        shapes.glow_circle(surface, (100, 210, 80), sx, sy - 8, cap_r, layers=2, alpha_start=40)
        shapes.circle(surface, (80, 170, 60), sx, sy - 8, cap_r)
        shapes.circle(surface, (140, 240, 110), sx, sy - 8, cap_r // 2)

        bites_pct = self._bites_left / _MUSHROOM_MAX_BITES
        bar_w = 36
        bar_x = sx - bar_w // 2
        bar_y = sy - 36
        pygame.draw.rect(surface, (40, 40, 40), pygame.Rect(bar_x - 1, bar_y - 1, bar_w + 2, 7), border_radius=2)
        pygame.draw.rect(surface, (80, 200, 60), pygame.Rect(bar_x, bar_y, int(bar_w * bites_pct), 5), border_radius=2)


# ── Campfire ────────────────────────────────────────────────────────────────

class Campfire:
    REGEN_RADIUS = 185
    REGEN_PER_SEC = 1.0

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.age = 0.0
        self.alive = True
        self._regen_timer = 0.0

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return
        self.age += dt
        dx = player.x - self.x
        dy = player.y - self.y
        if dx * dx + dy * dy <= self.REGEN_RADIUS ** 2:
            player.heal(self.REGEN_PER_SEC * dt)
        # Particle flames
        if int(self.age * 10) % 3 == 0:
            particles.sparkle(self.x, self.y, (255, 160, 50), count=1, radius=20)

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not self.alive or not cam.is_visible(self.x, self.y, self.REGEN_RADIUS + 10):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)

        shapes.glow_circle(surface, (255, 140, 40), sx, sy, self.REGEN_RADIUS, layers=2, alpha_start=14)
        shapes.ring(surface, (200, 120, 40), sx, sy, self.REGEN_RADIUS, 1)

        pulse = 1.0 + math.sin(self.age * 7.0) * 0.12
        shapes.glow_circle(surface, (255, 180, 60), sx, sy, int(24 * pulse), layers=3, alpha_start=60)
        shapes.circle(surface, (255, 110, 30), sx, sy, int(16 * pulse))
        shapes.circle(surface, (255, 220, 120), sx, sy, int(8 * pulse))


# ── DeployableSystem ─────────────────────────────────────────────────────────

class DeployableSystem:
    _MINE_INTERVAL = 12.0
    _TURRET_INTERVAL = 12.0
    _MUSHROOM_INTERVAL = 30.0

    def __init__(self) -> None:
        self._mines: list[Mine] = []
        self._turrets: list[Turret] = []
        self._mushrooms: list[PoisonMushroom] = []
        self._campfires: list[Campfire] = []
        self._poison_targets: list[list] = []

        self._mine_timer: float = self._MINE_INTERVAL
        self._turret_timer: float = self._TURRET_INTERVAL
        self._mushroom_timer: float = self._MUSHROOM_INTERVAL

    def update(self, dt: float, player, enemies: list) -> None:
        self._handle_spawn_timers(dt, player)
        self._update_mines(dt, player, enemies)
        self._update_turrets(dt, player, enemies)
        self._update_mushrooms(dt, enemies)
        self._update_campfires(dt, player)
        self._update_poison(dt)

    def spawn_campfire(self, x: float, y: float) -> None:
        self._campfires.append(Campfire(x, y))

    def draw(self, surface: pygame.Surface, cam) -> None:
        for obj in self._campfires:
            obj.draw(surface, cam)
        for obj in self._mushrooms:
            obj.draw(surface, cam)
        for obj in self._mines:
            obj.draw(surface, cam)
        for obj in self._turrets:
            obj.draw(surface, cam)

    # ── internal ──────────────────────────────────────────────────────────────

    def _handle_spawn_timers(self, dt: float, player) -> None:
        if player.stats.mine_item:
            self._mine_timer -= dt
            if self._mine_timer <= 0:
                self._mine_timer = self._MINE_INTERVAL
                self._mines.append(Mine(player.x, player.y))
                particles.burst(player.x, player.y, (255, 200, 40), count=8, speed=60, life=0.3, size=3)

        if player.stats.turret_item:
            self._turret_timer -= dt
            if self._turret_timer <= 0:
                self._turret_timer = self._TURRET_INTERVAL
                angle = rng.uniform(0, math.tau)
                tx = player.x + math.cos(angle) * 80
                ty = player.y + math.sin(angle) * 80
                self._turrets.append(Turret(tx, ty))
                particles.burst(tx, ty, (80, 180, 255), count=10, speed=70, life=0.35, size=3)

        if player.stats.mushroom_item:
            self._mushroom_timer -= dt
            if self._mushroom_timer <= 0:
                self._mushroom_timer = self._MUSHROOM_INTERVAL
                self._mushrooms.append(PoisonMushroom(player.x, player.y))
                particles.burst(player.x, player.y, (120, 200, 80), count=10, speed=60, life=0.35, size=3)

    def _update_mines(self, dt: float, player, enemies: list) -> None:
        alive_mines = []
        for mine in self._mines:
            mine.update(dt, player, enemies)
            if mine.alive:
                alive_mines.append(mine)
        self._mines = alive_mines

    def _update_turrets(self, dt: float, player, enemies: list) -> None:
        for turret in self._turrets:
            turret.update(dt, player, enemies)

    def _update_mushrooms(self, dt: float, enemies: list) -> None:
        alive = []
        for mushroom in self._mushrooms:
            mushroom.update(dt, enemies, self._poison_targets)
            if mushroom.alive:
                alive.append(mushroom)
        self._mushrooms = alive

    def _update_campfires(self, dt: float, player) -> None:
        for campfire in self._campfires:
            campfire.update(dt, player)

    def _update_poison(self, dt: float) -> None:
        alive_poison = []
        for state in self._poison_targets:
            enemy, ticks_left, tick_timer = state[0], state[1], state[2]
            if not enemy.alive or ticks_left <= 0:
                continue
            state[2] += dt
            while state[2] >= 1.0 and state[1] > 0:
                state[2] -= 1.0
                state[1] -= 1
                enemy.take_damage(_POISON_DPS, 0.0, 0.0)
                particles.sparkle(enemy.x, enemy.y, (100, 220, 80), count=2, radius=14)
            if state[1] > 0 and enemy.alive:
                alive_poison.append(state)
        self._poison_targets = alive_poison

    @property
    def count(self) -> int:
        return len(self._mines) + len(self._turrets) + len(self._mushrooms) + len(self._campfires)
