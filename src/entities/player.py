"""Player entity."""

from __future__ import annotations

import math

import pygame

from src.core.camera import Camera
from src.core.config import PLAYER_DEFAULT, xp_to_next_level
from src.core.input import input_mgr
from src.core.rng import rng
from src.entities.entity import Entity
from src.render import shapes
from src.render.particles import particles

_RADIUS = 16
_BODY = (86, 185, 255)
_OUTLINE = (215, 240, 255)
_CORE = (255, 255, 255)
_LOW_HP = (255, 90, 90)
_IFRAMES_DUR = 0.7
_LOW_HP_RATIO = 0.35


class PlayerStats:
    def __init__(self) -> None:
        d = PLAYER_DEFAULT
        self.max_hp = d["max_hp"]
        self.hp_regen = d["hp_regen"]
        self.speed = d["speed"]
        self.pickup_radius = d["pickup_radius"]
        self.crit_rate = d["crit_rate"]
        self.crit_mul = d["crit_mul"]
        self.dodge_rate = d["dodge_rate"]
        self.atk_mul = d["atk_mul"]
        self.atk_speed_mul = d["atk_speed_mul"]
        self.proj_bonus = d["proj_bonus"]
        self.range_mul = d["range_mul"]
        self.xp_mul = d["xp_mul"]
        self.gold_mul = d["gold_mul"]
        self.armor = d["armor"]
        self.lucky = d["lucky"]
        self.vampire = d["vampire"]
        self.adrenaline = d["adrenaline"]
        self.berserker = d["berserker"]
        self.enemy_count_mul = d["enemy_count_mul"]
        self.range_bonus = d["range_bonus"]
        self.kb_bonus = d["kb_bonus"]
        self.coin_attack = d["coin_attack"]
        self.prism = d["prism"]
        self.mine_item = d["mine_item"]
        self.turret_item = d["turret_item"]
        self.mushroom_item = d["mushroom_item"]


class Player(Entity):
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        super().__init__(x, y, _RADIUS)
        self.stats = PlayerStats()
        self.hp = self.stats.max_hp
        self.xp = 0.0
        self.level = 1
        self.gold = 0
        self.xp_to_next = xp_to_next_level(1)

        self.vx = 0.0
        self.vy = 0.0
        self._facing = 0.0
        self._anim_t = 0.0
        self._hit_scale = 0.0

        self.weapons: list = []
        self.passives: list = []

        self._iframes = 0.0
        self._hit_flash = 0.0
        self._hit_flash_max = 0.12
        self.screen_flash = 0.0
        self._guardian_shields = 0
        self.vouchers = 0
        self.adrenaline_active = True
        self._timed_regen_buffs: list[list[float]] = []
        self.spawn_elite_count = 0
        self.on_gold_collect = None
        self.spawn_campfire_callback = None
        self.just_leveled = False
        self.pending_level_ups = 0
        self.dead_timer = 0.0
        self.combat_feedback = None

        self.kills = 0
        self.total_damage_dealt = 0.0
        self.total_damage_taken = 0.0
        self.survive_time = 0.0

    def update(
        self,
        dt: float,
        bounds: tuple[float, float, float, float] | None = None,
        external_force: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        if not self.alive:
            self.dead_timer += dt
            return

        self.survive_time += dt
        self._anim_t = (self._anim_t + dt * 5.5) % (math.pi * 2)

        dx, dy = input_mgr.move_vector
        target_vx = dx * self.stats.speed
        target_vy = dy * self.stats.speed
        moving = dx != 0 or dy != 0
        lerp_t = min(1.0, dt * (12.5 if moving else 20.0))
        self.vx += (target_vx - self.vx) * lerp_t
        self.vy += (target_vy - self.vy) * lerp_t
        pull_x, pull_y = external_force
        self.x += (self.vx + pull_x) * dt
        self.y += (self.vy + pull_y) * dt

        if bounds is not None:
            left, top, right, bottom = bounds
            self.x = max(left + self.radius, min(right - self.radius, self.x))
            self.y = max(top + self.radius, min(bottom - self.radius, self.y))

        if abs(self.vx) > 15 or abs(self.vy) > 15:
            self._facing = math.atan2(self.vy, self.vx)

        if self.stats.hp_regen > 0:
            self.hp = min(self.stats.max_hp, self.hp + self.stats.hp_regen * dt)

        active_buffs = []
        for buff in self._timed_regen_buffs:
            rate, remaining = buff[0], buff[1]
            elapsed = min(dt, remaining)
            self.hp = min(self.stats.max_hp, self.hp + rate * elapsed)
            buff[1] -= dt
            if buff[1] > 0:
                active_buffs.append(buff)
        self._timed_regen_buffs = active_buffs

        self._iframes = max(0.0, self._iframes - dt)
        self._hit_flash = max(0.0, self._hit_flash - dt)
        self._hit_scale = max(0.0, self._hit_scale - dt * 5.0)
        self.screen_flash = max(0.0, self.screen_flash - dt * 2.5)

    def take_damage(
        self,
        raw_dmg: float,
        source_x: float | None = None,
        source_y: float | None = None,
    ) -> float:
        if not self.alive or self._iframes > 0:
            return 0.0

        if self._guardian_shields > 0:
            self._guardian_shields -= 1
            self._iframes = _IFRAMES_DUR
            particles.sparkle(self.x, self.y, (255, 220, 80), count=16, radius=32)
            particles.burst(self.x, self.y, (255, 255, 180), count=8, speed=90, life=0.35, size=3)
            return 0.0

        if rng.chance(self.stats.dodge_rate):
            self._spawn_dodge_effect()
            return 0.0

        actual = max(1.0, raw_dmg - self.stats.armor)
        self.hp -= actual
        self.total_damage_taken += actual
        if self.stats.adrenaline:
            self.adrenaline_active = False

        self._iframes = _IFRAMES_DUR
        self._hit_flash = self._hit_flash_max
        self._hit_scale = 1.0
        self.screen_flash = min(1.0, self.screen_flash + 0.7)

        sx = self.x if source_x is None else source_x
        sy = self.y if source_y is None else source_y
        angle = math.atan2(self.y - sy, self.x - sx)
        particles.directional(
            self.x,
            self.y,
            angle,
            math.pi * 0.65,
            (255, 110, 110),
            count=10,
            speed=110,
            life=0.4,
            size=3.5,
        )

        if self.combat_feedback:
            self.combat_feedback("player_hit", x=self.x, y=self.y, amount=actual)

        if self.hp <= 0:
            self.hp = 0
            self._die()
        return actual

    def heal(self, amount: float) -> float:
        before = self.hp
        self.hp = min(self.stats.max_hp, self.hp + amount)
        healed = self.hp - before
        if healed > 0:
            particles.sparkle(self.x, self.y, (80, 255, 140), count=8, radius=20)
        return healed

    def gain_xp(self, amount: float) -> bool:
        self.xp += amount * self.stats.xp_mul
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = xp_to_next_level(self.level)
            self.just_leveled = True
            self.pending_level_ups += 1
            leveled = True
            self._on_level_up()
        return leveled

    def gain_gold(self, amount: int) -> None:
        self.gold += max(1, int(amount * self.stats.gold_mul))

    def get_weapon(self, weapon_id: str):
        for weapon in self.weapons:
            if getattr(weapon, "weapon_id", None) == weapon_id:
                return weapon
        return None

    def has_weapon(self, weapon_id: str) -> bool:
        return self.get_weapon(weapon_id) is not None

    def add_weapon(self, weapon) -> None:
        if not self.has_weapon(getattr(weapon, "weapon_id", "")):
            self.weapons.append(weapon)

    def on_wave_start(self) -> None:
        self.adrenaline_active = True

    def _on_level_up(self) -> None:
        particles.burst(self.x, self.y, (255, 220, 60), count=18, speed=110, life=0.7, size=5)
        particles.sparkle(self.x, self.y, (255, 255, 140), count=16, radius=32)

    def _die(self) -> None:
        self.alive = False
        particles.burst(self.x, self.y, _BODY, count=36, speed=140, life=1.0, size=6, gravity=80)
        particles.burst(self.x, self.y, (255, 255, 255), count=18, speed=70, life=0.7, size=3)

    def _spawn_dodge_effect(self) -> None:
        particles.sparkle(self.x, self.y, (215, 225, 255), count=6, radius=24)

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        sx, sy = cam.world_to_screen(self.x, self.y)
        if not cam.is_visible(self.x, self.y, self.radius + 12):
            return

        if not self.alive:
            self._draw_death(surface, sx, sy)
            return

        if self._iframes > 0 and int(self._iframes * 12) % 2 == 0:
            return

        pulse = 1.0 + math.sin(self._anim_t) * 0.04
        hit_pop = 1.0 + self._hit_scale * 0.22
        radius = self.radius * pulse * hit_pop
        flash = self._hit_flash > 0
        moving = abs(self.vx) > 5 or abs(self.vy) > 5

        shadow = pygame.Surface((60, 28), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        surface.blit(shadow, (int(sx - 30), int(sy + radius * 0.6)))

        pickup_r = self.stats.pickup_radius
        _draw_dashed_circle(surface, (90, 140, 210), sx, sy, pickup_r, 18)

        if self.hp / self.stats.max_hp < _LOW_HP_RATIO:
            alert_r = radius + 6 + math.sin(self._anim_t * 1.2) * 4
            shapes.ring(surface, _LOW_HP, sx, sy, alert_r, 2)

        glow_alpha = 95 if moving else 65
        shapes.glow_circle(surface, _BODY, sx, sy, radius * 0.95, layers=3, alpha_start=glow_alpha)

        body_color = (255, 255, 255) if flash else _BODY
        outline_color = (255, 255, 255) if flash else _OUTLINE
        core_size = radius * 0.55
        core_angle = self._facing + math.sin(self._anim_t) * 0.2

        shapes.regular_polygon(surface, body_color, sx, sy, radius * 1.04, 8, core_angle * 0.2)
        shapes.regular_polygon(surface, outline_color, sx, sy, radius * 1.04, 8, core_angle * 0.2, width=2)
        shapes.diamond(surface, outline_color, sx, sy, core_size * 0.9, core_size * 1.1, width=2)
        shapes.circle(surface, _CORE, sx, sy, radius * 0.28)

        orbit_r = radius + 5
        orbit_a = self._anim_t * 1.4
        for idx in range(2):
            oa = orbit_a + math.pi * idx
            ox = sx + math.cos(oa) * orbit_r
            oy = sy + math.sin(oa) * orbit_r * 0.4
            shapes.circle(surface, outline_color, ox, oy, 2.5)

        _draw_direction_arrow(surface, sx, sy, self._facing, radius, outline_color)

    def _draw_death(self, surface: pygame.Surface, sx: float, sy: float) -> None:
        progress = min(1.0, self.dead_timer / 0.6)
        radius = int(self.radius * (1 - progress))
        if radius > 1:
            shapes.regular_polygon(surface, (180, 220, 255), sx, sy, radius, 8)


def _draw_direction_arrow(surface: pygame.Surface, sx: float, sy: float, angle: float, radius: float, color) -> None:
    tip_r = radius + 10
    base_r = radius - 1
    perp = angle + math.pi / 2
    half_width = 5
    tip = (sx + math.cos(angle) * tip_r, sy + math.sin(angle) * tip_r)
    b1 = (
        sx + math.cos(angle) * base_r + math.cos(perp) * half_width,
        sy + math.sin(angle) * base_r + math.sin(perp) * half_width,
    )
    b2 = (
        sx + math.cos(angle) * base_r - math.cos(perp) * half_width,
        sy + math.sin(angle) * base_r - math.sin(perp) * half_width,
    )
    shapes.polygon(surface, color, [tip, b1, b2])


def _draw_dashed_circle(surface: pygame.Surface, color, cx: float, cy: float, radius: float, segments: int) -> None:
    if radius <= 0:
        return
    step = math.pi * 2 / segments
    for idx in range(0, segments, 2):
        a1 = idx * step
        a2 = a1 + step * 0.55
        x1 = cx + math.cos(a1) * radius
        y1 = cy + math.sin(a1) * radius
        x2 = cx + math.cos(a2) * radius
        y2 = cy + math.sin(a2) * radius
        pygame.draw.line(surface, color, (int(x1), int(y1)), (int(x2), int(y2)), 1)
