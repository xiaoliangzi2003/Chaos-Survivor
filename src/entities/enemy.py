"""全部由几何图形绘制的敌人实体。"""

from __future__ import annotations

import math

import pygame

from src.core.config import DIFFICULTY_SETTINGS
from src.core.rng import rng
from src.entities.entity import Entity
from src.render import shapes
from src.render.particles import particles

_ELITE_HP = 4.0
_ELITE_DMG = 2.0
_ELITE_RWD = 3.0
_ELITE_RAD = 1.35
_KB_DECAY = 9.0


def _angle_diff(target: float, current: float) -> float:
    diff = target - current
    while diff > math.pi:
        diff -= math.tau
    while diff < -math.pi:
        diff += math.tau
    return diff


def _turn_towards(current: float, target: float, max_step: float) -> float:
    diff = _angle_diff(target, current)
    if abs(diff) <= max_step:
        return target
    return current + max_step * (1 if diff > 0 else -1)


def _blend_angles(source: float, target: float, ratio: float) -> float:
    return source + _angle_diff(target, source) * max(0.0, min(1.0, ratio))


class Enemy(Entity):
    HIT_FLASH = 0.08
    _shadow_cache: dict[int, pygame.Surface] = {}

    def __init__(
        self,
        x: float,
        y: float,
        max_hp: float,
        speed: float,
        damage: float,
        radius: float,
        color: tuple[int, int, int],
        xp_drop: int,
        gold_drop: int,
        knockback_resist: float = 0.0,
    ) -> None:
        super().__init__(x, y, radius)
        self.max_hp = max_hp
        self.hp = max_hp
        self.speed = speed
        self.damage = damage
        self.color = color
        self.xp_drop = xp_drop
        self.gold_drop = gold_drop
        self.knockback_resist = knockback_resist
        self.is_boss = False
        self.boss_name = ""
        self.attack_label = ""
        self.contact_damage = True
        self.ignore_world_clamp = False
        self.invulnerable = False
        self.damage_taken_mul = 1.0
        self.shielded = False
        self.last_damage_taken = 0.0

        self.vx = 0.0
        self.vy = 0.0
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self._flash_timer = 0.0
        self._slow_timer = 0.0
        self._slow_mul = 1.0
        self._anim_t = rng.uniform(0, math.pi * 2)
        self._hit_burst = 0.0

        self.pending_spawns: list[tuple[str, float, float]] = []
        self.pending_projectiles: list[dict] = []
        self.pending_hazards: list[dict] = []

    def take_damage(self, amount: float, angle: float = 0.0, kb_force: float = 150.0) -> bool:
        if self.invulnerable:
            self.last_damage_taken = 0.0
            return False
        amount *= self.damage_taken_mul
        self.last_damage_taken = min(self.hp, max(0.0, amount))
        self.hp -= amount
        self._flash_timer = self.HIT_FLASH
        self._hit_burst = 1.0

        actual_kb = kb_force * (1.0 - self.knockback_resist)
        self.kb_vx += math.cos(angle) * actual_kb
        self.kb_vy += math.sin(angle) * actual_kb

        if self.hp <= 0:
            self.hp = 0
            self._on_death()
            return True
        return False

    def collision_nodes(self) -> list[tuple[float, float, float, float]]:
        if not self.alive or not self.contact_damage:
            return []
        return [(self.x, self.y, self.radius, self.damage)]

    def _on_death(self) -> None:
        self.alive = False
        burst = 34 if self.is_boss else 18
        speed = 160 if self.is_boss else 110
        size = 8 if self.is_boss else 5
        particles.burst(self.x, self.y, self.color, count=burst, speed=speed, life=0.7, size=size, gravity=60)

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return

        self.pending_spawns.clear()
        self.pending_projectiles.clear()
        self.pending_hazards.clear()
        self._anim_t = (self._anim_t + dt * (2.0 + self.speed / 140.0)) % (math.pi * 2)
        self._hit_burst = max(0.0, self._hit_burst - dt * 6.0)

        decay = max(0.0, 1.0 - _KB_DECAY * dt)
        self.kb_vx *= decay
        self.kb_vy *= decay

        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)

        self._ai(dt, player)

        if self._slow_timer > 0:
            self._slow_timer -= dt
            if self._slow_timer <= 0:
                self._slow_mul = 1.0
            else:
                self.vx *= self._slow_mul
                self.vy *= self._slow_mul

        self.x += (self.vx + self.kb_vx) * dt
        self.y += (self.vy + self.kb_vy) * dt

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.vx = dx / dist * self.speed
            self.vy = dy / dist * self.speed

    def draw(self, surface: pygame.Surface, cam) -> None:
        if not cam.is_visible(self.x, self.y, self.radius + 18):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        flash = self._flash_timer > 0
        self._draw_shadow(surface, sx, sy)
        self._draw_shape(surface, sx, sy, flash)
        if self.shielded:
            shield_color = (120, 200, 255)
            shapes.ring(surface, shield_color, sx, sy, self.radius + 7, 2)
            shapes.ring(surface, shield_color, sx, sy, self.radius + 11, 1)
        if self._slow_timer > 0:
            shapes.ring(surface, (100, 170, 255), sx, sy, self.radius + 4, 2)
        self._draw_hp_bar(surface, sx, sy)

    def _draw_shadow(self, surface: pygame.Surface, sx: float, sy: float) -> None:
        shadow = self._get_shadow_surface()
        surface.blit(shadow, (int(sx - shadow.get_width() / 2), int(sy + self.radius * 0.6)))

    def _get_shadow_surface(self) -> pygame.Surface:
        key = max(4, int(self.radius * 10))
        shadow = self._shadow_cache.get(key)
        if shadow is None:
            width = max(8, int(self.radius * 4))
            height = max(6, int(self.radius * 2.2))
            shadow = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 65), shadow.get_rect())
            self._shadow_cache[key] = shadow
        return shadow

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        color = (255, 255, 255) if flash else self.color
        shapes.circle(surface, color, sx, sy, self.radius)

    def _draw_hp_bar(self, surface: pygame.Surface, sx: float, sy: float) -> None:
        if self.hp >= self.max_hp or self.is_boss:
            return
        bw = self.radius * 2.2
        bh = 4
        shapes.bar(surface, sx - bw / 2, sy - self.radius - 10, bw, bh, self.hp, self.max_hp, (230, 70, 80), (60, 20, 20))

    def apply_slow(self, mul: float, duration: float) -> None:
        if mul < self._slow_mul:
            self._slow_mul = mul
        self._slow_timer = max(self._slow_timer, duration)

    def _shoot_at_player(
        self,
        player,
        speed: float,
        damage: float,
        color,
        spread: float = 0.0,
        count: int = 1,
        shape: str = "orb",
        radius: float = 7.0,
        life: float = 4.0,
    ) -> None:
        base = math.atan2(player.y - self.y, player.x - self.x)
        for idx in range(count):
            offset = 0.0 if count == 1 else -spread / 2 + spread * idx / (count - 1)
            angle = base + offset
            self.pending_projectiles.append(
                {
                    "x": self.x,
                    "y": self.y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "damage": damage,
                    "life": life,
                    "radius": radius,
                    "color": color,
                    "shape": shape,
                }
            )

    def _shoot_ring(
        self,
        speed: float,
        damage: float,
        color,
        count: int,
        shape: str = "orb",
        radius: float = 7.0,
        life: float = 4.0,
    ) -> None:
        for idx in range(count):
            angle = math.tau * idx / count
            self.pending_projectiles.append(
                {
                    "x": self.x,
                    "y": self.y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "damage": damage,
                    "life": life,
                    "radius": radius,
                    "color": color,
                    "shape": shape,
                }
            )


class ZombieEnemy(Enemy):
    _BASE = dict(max_hp=34, speed=78, damage=8, radius=15, color=(55, 185, 90), xp_drop=2, gold_drop=1, knockback_resist=0.0)

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        bob = math.sin(self._anim_t * 1.4) * 2
        stretch = 1.0 + math.sin(self._anim_t) * 0.08 + self._hit_burst * 0.18
        radius = self.radius * stretch
        color = (255, 255, 255) if flash else self.color
        dark = (25, 88, 45)
        shapes.glow_circle(surface, color, sx, sy + bob, radius * 0.9, layers=2, alpha_start=45)
        shapes.circle(surface, color, sx, sy + bob, radius)
        shapes.circle(surface, dark, sx, sy + bob, radius, width=2)
        eye_offset = radius * 0.35
        shapes.circle(surface, dark, sx - eye_offset, sy - radius * 0.15 + bob, max(2, radius * 0.16))
        shapes.circle(surface, dark, sx + eye_offset, sy - radius * 0.15 + bob, max(2, radius * 0.16))
        for idx in (-1, 0, 1):
            bx = sx + idx * radius * 0.42
            shapes.line(surface, dark, bx, sy - radius + bob, bx, sy - radius - 6 + bob, 2)


class SpeederEnemy(Enemy):
    _BASE = dict(max_hp=20, speed=88, damage=7, radius=12, color=(235, 220, 70), xp_drop=3, gold_drop=1, knockback_resist=0.0)
    _CHARGE_SPEED = 360.0
    _CHARGE_INTERVAL = 3.0
    _CHARGE_DUR = 0.55

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._charge_cd = self._CHARGE_INTERVAL * 0.5
        self._charge_timer = 0.0
        self._charging = False
        self._cdx = 0.0
        self._cdy = 0.0

    def _ai(self, dt: float, player) -> None:
        self._charge_cd -= dt
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if self._charging:
            self._charge_timer += dt
            if self._charge_timer >= self._CHARGE_DUR:
                self._charging = False
                self._charge_cd = self._CHARGE_INTERVAL
            self.vx = self._cdx * self._CHARGE_SPEED
            self.vy = self._cdy * self._CHARGE_SPEED
        else:
            if self._charge_cd <= 0 and 0 < dist < 350:
                self._charging = True
                self._charge_timer = 0.0
                self._cdx = dx / dist
                self._cdy = dy / dist
            elif dist > 0:
                self.vx = dx / dist * self.speed
                self.vy = dy / dist * self.speed

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = math.atan2(self.vy or self.kb_vy or 0.01, self.vx or self.kb_vx or 0.01)
        r = self.radius * (1.0 + self._hit_burst * 0.16)
        color = (255, 255, 255) if flash else self.color
        tip = (sx + math.cos(angle) * r * 1.35, sy + math.sin(angle) * r * 1.35)
        pts = [
            tip,
            (sx + math.cos(angle + 2.5) * r, sy + math.sin(angle + 2.5) * r),
            (sx + math.cos(angle + math.pi) * r * 0.35, sy + math.sin(angle + math.pi) * r * 0.35),
            (sx + math.cos(angle - 2.5) * r, sy + math.sin(angle - 2.5) * r),
        ]
        if self._charging and not flash:
            for idx in range(1, 4):
                tx = sx - math.cos(angle) * r * idx * 0.8
                ty = sy - math.sin(angle) * r * idx * 0.8
                shapes.circle(surface, color, tx, ty, max(1, r - idx * 2))
        shapes.glow_circle(surface, color, sx, sy, r * 0.9, layers=2, alpha_start=40)
        shapes.polygon(surface, color, pts)
        shapes.polygon(surface, (255, 255, 255), pts, width=1)


class LancerEnemy(Enemy):
    _BASE = dict(max_hp=28, speed=76, damage=10, radius=11, color=(255, 160, 80), xp_drop=3, gold_drop=1, knockback_resist=0.05)
    _LUNGE_CD = 2.2
    _LUNGE_DUR = 0.38
    _LUNGE_SPEED = 420

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._lunge_cd = self._LUNGE_CD * 0.6
        self._lunge_timer = 0.0
        self._lunging = False
        self._dir = 0.0

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        self._lunge_cd -= dt

        if self._lunging:
            self._lunge_timer += dt
            if self._lunge_timer >= self._LUNGE_DUR:
                self._lunging = False
                self._lunge_cd = self._LUNGE_CD
            self.vx = math.cos(self._dir) * self._LUNGE_SPEED
            self.vy = math.sin(self._dir) * self._LUNGE_SPEED
            return

        if self._lunge_cd <= 0 and dist < 260:
            self._lunging = True
            self._lunge_timer = 0.0
            self._dir = math.atan2(dy, dx)
            return

        strafe = math.atan2(dy, dx) + math.pi / 2
        self.vx = math.cos(strafe) * self.speed * 0.55 + dx / dist * self.speed * 0.45
        self.vy = math.sin(strafe) * self.speed * 0.55 + dy / dist * self.speed * 0.45

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = self._dir if self._lunging else math.atan2(self.vy or 0.01, self.vx or 0.01)
        r = self.radius * (1.0 + self._hit_burst * 0.18)
        color = (255, 255, 255) if flash else self.color
        tail = (sx - math.cos(angle) * r * 1.4, sy - math.sin(angle) * r * 1.4)
        left = (sx + math.cos(angle + 2.65) * r, sy + math.sin(angle + 2.65) * r)
        right = (sx + math.cos(angle - 2.65) * r, sy + math.sin(angle - 2.65) * r)
        shapes.glow_circle(surface, color, sx, sy, r * 0.9, layers=2, alpha_start=30)
        shapes.polygon(surface, color, [(sx + math.cos(angle) * r * 1.65, sy + math.sin(angle) * r * 1.65), left, tail, right])
        shapes.line(surface, (255, 250, 220), tail[0], tail[1], sx + math.cos(angle) * r * 1.9, sy + math.sin(angle) * r * 1.9, 2)


class WispEnemy(Enemy):
    _BASE = dict(max_hp=24, speed=74, damage=9, radius=10, color=(100, 240, 255), xp_drop=4, gold_drop=1, knockback_resist=0.0)
    _IDEAL_DIST = 180.0
    _SHOOT_CD = 1.8

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._shoot_timer = self._SHOOT_CD * 0.5

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist > self._IDEAL_DIST * 1.2:
            self.vx = dx / dist * self.speed * 0.8
            self.vy = dy / dist * self.speed * 0.8
        elif dist < self._IDEAL_DIST * 0.75:
            self.vx = -dx / dist * self.speed * 0.7
            self.vy = -dy / dist * self.speed * 0.7
        else:
            self.vx = math.cos(orbit) * self.speed
            self.vy = math.sin(orbit) * self.speed

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self._SHOOT_CD
            self._shoot_at_player(player, 260, self.damage, (145, 250, 255), spread=0.22, count=2, shape="orb", radius=5.5, life=3.8)
            particles.sparkle(self.x, self.y, (145, 250, 255), count=5, radius=15)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + math.sin(self._anim_t * 1.6) * 0.08 + self._hit_burst * 0.18)
        color = (255, 255, 255) if flash else self.color
        shapes.glow_circle(surface, color, sx, sy, r * 1.15, layers=3, alpha_start=55)
        shapes.diamond(surface, color, sx, sy, r * 0.75, r * 1.1)
        shapes.circle(surface, (255, 255, 255), sx, sy, r * 0.3)
        tail_y = sy + r * 1.3
        shapes.line(surface, color, sx, sy + r * 0.55, sx, tail_y, 2)


class SlimeEnemy(Enemy):
    _SIZE_DATA = {
        "large": {"hp": 68, "speed": 86, "damage": 12, "radius": 26, "xp": 7, "gold": 3, "children": ("medium", 3)},
        "medium": {"hp": 30, "speed": 124, "damage": 8, "radius": 18, "xp": 4, "gold": 1, "children": ("small", 3)},
        "small": {"hp": 12, "speed": 178, "damage": 5, "radius": 11, "xp": 2, "gold": 0, "children": None},
    }
    _COLOR_POOL = (
        (120, 230, 120),
        (120, 170, 255),
        (255, 170, 120),
        (225, 130, 255),
    )

    def __init__(self, x: float, y: float, difficulty: int = 1, size: str = "large", color: tuple[int, int, int] | None = None) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        data = self._SIZE_DATA[size]
        body_color = color or rng.choice(self._COLOR_POOL)
        super().__init__(
            x,
            y,
            data["hp"] * d["hp_mul"],
            data["speed"],
            data["damage"] * d["dmg_mul"],
            data["radius"],
            body_color,
            max(1, int(data["xp"] * d["reward_mul"])),
            max(0, int(data["gold"] * d["reward_mul"])),
            0.05,
        )
        self.slime_size = size

    def _on_death(self) -> None:
        children = self._SIZE_DATA[self.slime_size]["children"]
        if children is not None:
            child_size, child_count = children
            for idx in range(child_count):
                angle = math.tau * idx / child_count + rng.uniform(-0.25, 0.25)
                dist = self.radius * 1.1
                self.pending_spawns.append(
                    {
                        "etype": f"slime_{child_size}",
                        "x": self.x + math.cos(angle) * dist,
                        "y": self.y + math.sin(angle) * dist,
                        "color": self.color,
                    }
                )
        super()._on_death()

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        wobble_x = math.sin(self._anim_t * 1.5) * self.radius * 0.08
        wobble_y = math.cos(self._anim_t * 1.3) * self.radius * 0.12
        scale = 1.0 + self._hit_burst * 0.15
        rx = self.radius * 1.15 * scale
        ry = self.radius * 0.88 * scale
        color = (255, 255, 255) if flash else self.color
        glow = tuple(min(255, c + 35) for c in color)
        blob = pygame.Surface((int(rx * 3), int(ry * 3)), pygame.SRCALPHA)
        rect = pygame.Rect(int(rx * 0.35), int(ry * 0.45), int(rx * 2), int(ry * 1.6))
        pygame.draw.ellipse(blob, (*glow, 70), rect.inflate(10, 8))
        pygame.draw.ellipse(blob, color, rect)
        pygame.draw.ellipse(blob, (255, 255, 255), pygame.Rect(rect.x + rect.w * 0.18, rect.y + rect.h * 0.15, rect.w * 0.38, rect.h * 0.32))
        surface.blit(blob, (int(sx - blob.get_width() / 2 + wobble_x), int(sy - blob.get_height() / 2 + wobble_y)))


class BlackHoleMage(Enemy):
    _BASE = dict(max_hp=76, speed=54, damage=12, radius=18, color=(88, 72, 170), xp_drop=8, gold_drop=3, knockback_resist=0.1)
    _IDEAL_DIST = 250.0
    _CAST_CD = 8.2

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(
            x,
            y,
            b["max_hp"] * d["hp_mul"],
            b["speed"],
            b["damage"] * d["dmg_mul"],
            b["radius"],
            b["color"],
            max(1, int(b["xp_drop"] * d["reward_mul"])),
            b["gold_drop"],
            b["knockback_resist"],
        )
        self._cast_timer = self._CAST_CD * 0.5

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist < self._IDEAL_DIST * 0.8:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.2:
            self.vx = dx / dist * self.speed * 0.7
            self.vy = dy / dist * self.speed * 0.7
        else:
            self.vx = math.cos(orbit) * self.speed * 0.55
            self.vy = math.sin(orbit) * self.speed * 0.55

        self._cast_timer -= dt
        if self._cast_timer <= 0:
            self._cast_timer = self._CAST_CD
            angle = rng.uniform(0.0, math.tau)
            dist = rng.uniform(150.0, 230.0)
            self.pending_hazards.append(
                {
                    "kind": "black_hole",
                    "x": player.x + math.cos(angle) * dist,
                    "y": player.y + math.sin(angle) * dist,
                    "life": 3.2,
                    "pull_radius": 150,
                    "damage_radius": 28,
                    "pull_strength": 92,
                    "dps": self.damage * 0.85,
                    "color": (110, 90, 220),
                }
            )
            particles.burst(self.x, self.y, (140, 110, 255), count=7, speed=60, life=0.3, size=4)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.15)
        color = (255, 255, 255) if flash else self.color
        glow = (165, 145, 255)
        angle = self._anim_t * 0.9
        shapes.glow_circle(surface, color, sx, sy, r, layers=3, alpha_start=34)
        shapes.regular_polygon(surface, color, sx, sy, r, 6, angle)
        shapes.circle(surface, (20, 12, 35), sx, sy, r * 0.42)
        for idx in range(3):
            oa = angle + math.tau * idx / 3
            ox = sx + math.cos(oa) * r * 1.25
            oy = sy + math.sin(oa) * r * 1.25
            shapes.circle(surface, glow, ox, oy, 3)


class LineRaiderEnemy(Enemy):
    _BASE = dict(max_hp=86, speed=0, damage=20, radius=18, color=(255, 85, 85), xp_drop=9, gold_drop=3, knockback_resist=0.35)
    _TELEGRAPH_TIME = 1.0
    _WARN_HALF_WIDTH = 34.0
    _DASH_SPEED = 1880.0
    _SPAWN_MARGIN = 140.0

    def __init__(
        self,
        x: float,
        y: float,
        difficulty: int = 1,
        world_bounds: tuple[float, float, float, float] | None = None,
        target_x: float | None = None,
        target_y: float | None = None,
    ) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(
            x,
            y,
            b["max_hp"] * d["hp_mul"],
            b["speed"],
            b["damage"] * d["dmg_mul"],
            b["radius"],
            b["color"],
            max(1, int(b["xp_drop"] * d["reward_mul"])),
            b["gold_drop"],
            b["knockback_resist"],
        )
        self.contact_damage = False
        self.ignore_world_clamp = True
        self.invulnerable = True
        self._world_bounds = world_bounds or (-1800.0, -1200.0, 1800.0, 1200.0)
        self._state = "warning"
        self._state_timer = 0.0
        self._warn_half_width = self._WARN_HALF_WIDTH
        self._hit_done = False
        self._prev_x = self.x
        self._prev_y = self.y
        self._phase_flash = 0.0
        self._axis = rng.choice(("horizontal", "vertical"))
        self._direction = rng.choice((-1, 1))

        left, top, right, bottom = self._world_bounds
        lock_x = target_x if target_x is not None else x
        lock_y = target_y if target_y is not None else y
        lane_jitter = rng.uniform(-24.0, 24.0)

        if self._axis == "horizontal":
            self.y = max(top + self.radius, min(bottom - self.radius, lock_y + lane_jitter))
            self.x = left - self._SPAWN_MARGIN if self._direction > 0 else right + self._SPAWN_MARGIN
            self._exit_pos = right + self._SPAWN_MARGIN if self._direction > 0 else left - self._SPAWN_MARGIN
        else:
            self.x = max(left + self.radius, min(right - self.radius, lock_x + lane_jitter))
            self.y = top - self._SPAWN_MARGIN if self._direction > 0 else bottom + self._SPAWN_MARGIN
            self._exit_pos = bottom + self._SPAWN_MARGIN if self._direction > 0 else top - self._SPAWN_MARGIN

    def update(self, dt: float, player) -> None:
        if not self.alive:
            return

        self.pending_spawns.clear()
        self.pending_projectiles.clear()
        self.pending_hazards.clear()
        self._anim_t = (self._anim_t + dt * 6.5) % math.tau
        self._hit_burst = max(0.0, self._hit_burst - dt * 6.0)
        self._phase_flash = max(0.0, self._phase_flash - dt * 2.6)

        decay = max(0.0, 1.0 - _KB_DECAY * dt)
        self.kb_vx *= decay
        self.kb_vy *= decay
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)

        self._state_timer += dt
        self._prev_x = self.x
        self._prev_y = self.y

        if self._state == "warning":
            self.vx = 0.0
            self.vy = 0.0
            if self._state_timer >= self._TELEGRAPH_TIME:
                self._state = "dash"
                self._state_timer = 0.0
                self._phase_flash = 1.0
                particles.directional(self.x, self.y, self._travel_angle, 0.18, self.color, count=8, speed=90, life=0.24)
            return

        speed = self._DASH_SPEED
        if self._axis == "horizontal":
            self.vx = speed * self._direction + self.kb_vx
            self.vy = self.kb_vy
            self.x += self.vx * dt
            self.y += self.vy * dt
            self._check_dash_hit(player, horizontal=True)
            if (self._direction > 0 and self.x >= self._exit_pos) or (self._direction < 0 and self.x <= self._exit_pos):
                self.alive = False
        else:
            self.vx = self.kb_vx
            self.vy = speed * self._direction + self.kb_vy
            self.x += self.vx * dt
            self.y += self.vy * dt
            self._check_dash_hit(player, horizontal=False)
            if (self._direction > 0 and self.y >= self._exit_pos) or (self._direction < 0 and self.y <= self._exit_pos):
                self.alive = False

    @property
    def _travel_angle(self) -> float:
        if self._axis == "horizontal":
            return 0.0 if self._direction > 0 else math.pi
        return math.pi / 2 if self._direction > 0 else -math.pi / 2

    def _check_dash_hit(self, player, horizontal: bool) -> None:
        if self._hit_done:
            return
        if horizontal:
            if abs(player.y - self.y) > self._warn_half_width + player.radius:
                return
            min_pos = min(self._prev_x, self.x) - player.radius
            max_pos = max(self._prev_x, self.x) + player.radius
            crossed = min_pos <= player.x <= max_pos
        else:
            if abs(player.x - self.x) > self._warn_half_width + player.radius:
                return
            min_pos = min(self._prev_y, self.y) - player.radius
            max_pos = max(self._prev_y, self.y) + player.radius
            crossed = min_pos <= player.y <= max_pos
        if crossed:
            actual = player.take_damage(self.damage, self.x, self.y)
            if actual > 0:
                particles.burst(player.x, player.y, self.color, count=12, speed=120, life=0.28, size=4)
            self._hit_done = True

    def draw(self, surface: pygame.Surface, cam) -> None:
        self._draw_warning(surface, cam)
        if not cam.is_visible(self.x, self.y, self.radius + 48):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        flash = self._flash_timer > 0 or self._phase_flash > 0.4
        self._draw_shadow(surface, sx, sy)
        self._draw_shape(surface, sx, sy, flash)
        self._draw_hp_bar(surface, sx, sy)

    def _draw_warning(self, surface: pygame.Surface, cam) -> None:
        left, top, right, bottom = self._world_bounds
        pulse = 0.55 + 0.45 * math.sin(self._anim_t * 6.0)
        alpha = 54 if self._state == "dash" else int(75 + pulse * 65)
        line_alpha = 150 if self._state == "dash" else int(175 + pulse * 50)

        if self._axis == "horizontal":
            x1, y1 = cam.world_to_screen(left, self.y - self._warn_half_width)
            x2, y2 = cam.world_to_screen(right, self.y + self._warn_half_width)
        else:
            x1, y1 = cam.world_to_screen(self.x - self._warn_half_width, top)
            x2, y2 = cam.world_to_screen(self.x + self._warn_half_width, bottom)

        rect = pygame.Rect(min(x1, x2), min(y1, y2), max(2, abs(x2 - x1)), max(2, abs(y2 - y1)))
        if rect.right < 0 or rect.left > surface.get_width() or rect.bottom < 0 or rect.top > surface.get_height():
            return
        warning = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        warning.fill((255, 80, 80, alpha))
        surface.blit(warning, rect.topleft)
        pygame.draw.rect(surface, (255, 235, 235, line_alpha), rect, 3)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        color = (255, 255, 255) if flash else self.color
        glow = (255, 180, 180)
        angle = self._travel_angle
        head = (sx + math.cos(angle) * self.radius * 1.75, sy + math.sin(angle) * self.radius * 1.75)
        left = (sx + math.cos(angle + 2.55) * self.radius, sy + math.sin(angle + 2.55) * self.radius)
        right = (sx + math.cos(angle - 2.55) * self.radius, sy + math.sin(angle - 2.55) * self.radius)
        tail = (sx - math.cos(angle) * self.radius * 1.2, sy - math.sin(angle) * self.radius * 1.2)
        shapes.glow_circle(surface, color, sx, sy, self.radius * 0.9, layers=2, alpha_start=38)
        shapes.polygon(surface, color, [head, left, tail, right])
        shapes.polygon(surface, glow, [head, left, tail, right], width=2)
        shapes.line(surface, glow, tail[0], tail[1], head[0], head[1], 2)


class ShieldCasterEnemy(Enemy):
    _BASE = dict(max_hp=58, speed=68, damage=0, radius=16, color=(110, 205, 255), xp_drop=7, gold_drop=2, knockback_resist=0.08)
    _IDEAL_DIST = 250.0
    _AURA_RADIUS = 260.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self.contact_damage = False
        self.shield_aura_radius = self._AURA_RADIUS

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist < self._IDEAL_DIST * 0.72:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.25:
            self.vx = dx / dist * self.speed * 0.65
            self.vy = dy / dist * self.speed * 0.65
        else:
            self.vx = math.cos(orbit) * self.speed * 0.7
            self.vy = math.sin(orbit) * self.speed * 0.7

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + math.sin(self._anim_t * 1.5) * 0.06 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        glow = (190, 235, 255)
        shapes.glow_circle(surface, color, sx, sy, r * 1.05, layers=3, alpha_start=36)
        shapes.circle(surface, color, sx, sy, r * 0.9)
        shapes.circle(surface, (30, 70, 110), sx, sy, r * 0.42)
        for idx in range(3):
            angle = self._anim_t * 1.7 + idx * math.tau / 3
            ox = sx + math.cos(angle) * r * 1.25
            oy = sy + math.sin(angle) * r * 1.25
            shapes.diamond(surface, glow, ox, oy, 4.5, 7.0)
        pulse = 0.55 + math.sin(self._anim_t * 1.2) * 0.04
        shapes.ring(surface, glow, sx, sy, self.shield_aura_radius * pulse, 2)


class EliteMissileSniper(Enemy):
    _BASE = dict(max_hp=165, speed=58, damage=18, radius=20, color=(255, 120, 70), xp_drop=18, gold_drop=7, knockback_resist=0.3)
    _IDEAL_DIST = 360.0
    _CHARGE_TIME = 1.0
    _SHOT_CD = 4.8

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(
            x,
            y,
            b["max_hp"] * d["hp_mul"],
            b["speed"],
            b["damage"] * d["dmg_mul"],
            b["radius"],
            b["color"],
            max(1, int(b["xp_drop"] * d["reward_mul"])),
            int(b["gold_drop"] * d["reward_mul"]),
            b["knockback_resist"],
        )
        self.max_hp *= _ELITE_HP * 0.9
        self.hp = self.max_hp
        self.damage *= _ELITE_DMG * 0.95
        self.radius = int(self.radius * _ELITE_RAD)
        self.xp_drop = int(self.xp_drop * _ELITE_RWD * 0.8)
        self.gold_drop = int(self.gold_drop * _ELITE_RWD * 0.8)
        self._shot_timer = self._SHOT_CD * 0.55
        self._charge_timer = 0.0
        self._charging = False

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        angle_to_player = math.atan2(dy, dx)

        if self._charging:
            self.vx = math.cos(angle_to_player + math.pi / 2) * self.speed * 0.2
            self.vy = math.sin(angle_to_player + math.pi / 2) * self.speed * 0.2
            self._charge_timer += dt
            if self._charge_timer >= self._CHARGE_TIME:
                self._charging = False
                self._shot_timer = self._SHOT_CD
                self._fire_missile(player)
            return

        if dist < self._IDEAL_DIST * 0.7:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.15:
            self.vx = dx / dist * self.speed * 0.65
            self.vy = dy / dist * self.speed * 0.65
        else:
            orbit = angle_to_player + math.pi / 2
            self.vx = math.cos(orbit) * self.speed * 0.55
            self.vy = math.sin(orbit) * self.speed * 0.55

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._charging = True
            self._charge_timer = 0.0

    def _fire_missile(self, player) -> None:
        angle = math.atan2(player.y - self.y, player.x - self.x)
        self.pending_projectiles.append(
            {
                "x": self.x,
                "y": self.y,
                "vx": math.cos(angle) * 175.0,
                "vy": math.sin(angle) * 175.0,
                "damage": self.damage,
                "life": 5.2,
                "radius": 9.0,
                "color": (255, 145, 80),
                "shape": "missile",
                "tracking": True,
                "turn_speed": 1.45,
                "explode_fire": {
                    "life": 4.6,
                    "damage_radius": 44,
                    "dps": self.damage * 0.95,
                    "color": (255, 115, 55),
                },
                "burst_count": 14,
            }
        )
        particles.directional(self.x, self.y, angle, 0.25, (255, 170, 90), count=8, speed=75, life=0.24)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        dark = (120, 45, 20)
        angle = math.atan2(self.vy or 0.01, self.vx or 0.01)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=34)
        shapes.regular_polygon(surface, color, sx, sy, r, 6, self._anim_t * 0.35)
        shapes.regular_polygon(surface, dark, sx, sy, r, 6, self._anim_t * 0.35, width=2)
        barrel_len = r * (2.1 if not self._charging else 2.6)
        bx = sx + math.cos(angle) * barrel_len
        by = sy + math.sin(angle) * barrel_len
        shapes.line(surface, dark, sx, sy, bx, by, 4)
        if self._charging:
            shapes.glow_circle(surface, (255, 220, 140), bx, by, r * 0.6, layers=2, alpha_start=44)
            shapes.circle(surface, (255, 220, 140), bx, by, r * 0.34)


class TankEnemy(Enemy):
    _BASE = dict(max_hp=130, speed=46, damage=22, radius=22, color=(95, 130, 175), xp_drop=8, gold_drop=3, knockback_resist=0.6)

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = self._anim_t * 0.3
        r = self.radius * (1.0 + self._hit_burst * 0.12)
        color = (255, 255, 255) if flash else self.color
        dark = (45, 70, 105)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=30)
        shapes.regular_polygon(surface, color, sx, sy, r, 6, angle)
        shapes.regular_polygon(surface, dark, sx, sy, r, 6, angle, width=2)
        shapes.regular_polygon(surface, dark, sx, sy, r * 0.52, 4, angle + math.pi / 4)
        for idx in range(6):
            a = angle + math.pi * 2 * idx / 6
            bx = sx + math.cos(a) * r * 0.75
            by = sy + math.sin(a) * r * 0.75
            shapes.circle(surface, dark, bx, by, 2)


class WizardEnemy(Enemy):
    _BASE = dict(max_hp=44, speed=64, damage=12, radius=14, color=(165, 60, 230), xp_drop=5, gold_drop=2, knockback_resist=0.0)
    _IDEAL_DIST = 210.0
    _SHOOT_CD = 2.25

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._shoot_timer = self._SHOOT_CD * 0.4

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        ideal = self._IDEAL_DIST

        if dist < ideal * 0.75:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > ideal * 1.4:
            self.vx = dx / dist * self.speed * 0.6
            self.vy = dy / dist * self.speed * 0.6
        else:
            perp = math.atan2(dy, dx) + math.pi / 2
            self.vx = math.cos(perp) * self.speed * 0.45
            self.vy = math.sin(perp) * self.speed * 0.45

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self._SHOOT_CD
            self._shoot_at_player(player, 240, self.damage, (210, 120, 255), shape="orb", radius=7.5, life=4.5)
            particles.sparkle(self.x, self.y, (220, 140, 255), count=6, radius=18)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        glow = (215, 145, 255)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=50)
        shapes.diamond(surface, color, sx, sy, r, r * 1.25)
        shapes.diamond(surface, glow, sx, sy, r, r * 1.25, width=2)
        shapes.circle(surface, glow, sx, sy, r * 0.38)
        for idx in range(3):
            angle = self._anim_t * 1.4 + idx * math.tau / 3
            ox = sx + math.cos(angle) * r * 1.45
            oy = sy + math.sin(angle) * r * 1.45
            shapes.circle(surface, glow, ox, oy, 3)


class ExploderEnemy(Enemy):
    _BASE = dict(max_hp=27, speed=96, damage=45, radius=16, color=(235, 65, 65), xp_drop=4, gold_drop=2, knockback_resist=0.0)
    _ARM_DIST = 90.0
    _FUSE_TIME = 1.35
    _BLAST_RANGE = 130.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._fuse = 0.0
        self._armed = False

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self._ARM_DIST:
            self._armed = True
            self.vx = 0.0
            self.vy = 0.0
            self._fuse += dt
            if self._fuse >= self._FUSE_TIME:
                self._explode(player)
        else:
            self._armed = False
            self._fuse = 0.0
            if dist > 0:
                self.vx = dx / dist * self.speed
                self.vy = dy / dist * self.speed

    def _explode(self, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self._BLAST_RANGE:
            factor = 1.0 - dist / self._BLAST_RANGE
            player.take_damage(self.damage * factor, self.x, self.y)
        particles.burst(self.x, self.y, (255, 120, 30), count=32, speed=170, life=0.75, size=8, gravity=50)
        particles.burst(self.x, self.y, (255, 70, 60), count=22, speed=230, life=0.5, size=5)
        self.alive = False

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.18)
        color = (255, 255, 255) if flash else self.color
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=45)
        shapes.circle(surface, color, sx, sy, r)
        if not flash:
            ring_count = 3 if self._armed else 2
            for idx in range(ring_count):
                phase = self._anim_t + idx * math.tau / ring_count
                ring_r = r + 6 + math.sin(phase) * (10 if self._armed else 5)
                ring_col = (255, 120, 40) if self._armed else self.color
                shapes.ring(surface, ring_col, sx, sy, ring_r, 2)


class GunnerEnemy(Enemy):
    _BASE = dict(max_hp=62, speed=58, damage=14, radius=17, color=(235, 150, 70), xp_drop=7, gold_drop=3, knockback_resist=0.15)
    _IDEAL_DIST = 280.0
    _BURST_CD = 2.6

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._burst_timer = self._BURST_CD * 0.5

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        if dist < self._IDEAL_DIST * 0.7:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST:
            self.vx = dx / dist * self.speed * 0.7
            self.vy = dy / dist * self.speed * 0.7
        else:
            angle = math.atan2(dy, dx) + math.pi / 2
            self.vx = math.cos(angle) * self.speed * 0.55
            self.vy = math.sin(angle) * self.speed * 0.55

        self._burst_timer -= dt
        if self._burst_timer <= 0:
            self._burst_timer = self._BURST_CD
            self._shoot_at_player(player, 300, self.damage, (255, 185, 95), spread=0.28, count=3, shape="spike", radius=6, life=3.5)
            particles.directional(self.x, self.y, math.atan2(dy, dx), 0.35, (255, 190, 120), count=6, speed=40, life=0.2)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = self._anim_t * 0.5
        r = self.radius * (1.0 + self._hit_burst * 0.16)
        color = (255, 255, 255) if flash else self.color
        dark = (120, 70, 35)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=35)
        shapes.regular_polygon(surface, color, sx, sy, r, 6, angle)
        shapes.regular_polygon(surface, dark, sx, sy, r, 6, angle, width=2)
        barrel_a = math.atan2(self.vy or 0.01, self.vx or 0.01)
        bx = sx + math.cos(barrel_a) * r * 0.9
        by = sy + math.sin(barrel_a) * r * 0.9
        shapes.line(surface, dark, sx, sy, bx, by, 4)
        shapes.circle(surface, dark, sx, sy, r * 0.28)


class ArtilleryEnemy(Enemy):
    _BASE = dict(max_hp=95, speed=42, damage=20, radius=20, color=(120, 95, 230), xp_drop=10, gold_drop=4, knockback_resist=0.25)
    _SHOOT_CD = 3.4
    _IDEAL_DIST = 340.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._shoot_timer = self._SHOOT_CD * 0.35

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        if dist < self._IDEAL_DIST * 0.7:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST:
            self.vx = dx / dist * self.speed * 0.6
            self.vy = dy / dist * self.speed * 0.6
        else:
            self.vx *= 0.85
            self.vy *= 0.85

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self._SHOOT_CD
            self._shoot_at_player(player, 250, self.damage, (165, 140, 255), spread=0.55, count=5, shape="bolt", radius=7, life=4.0)
            particles.burst(self.x, self.y, (165, 140, 255), count=8, speed=45, life=0.25, size=4)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.16)
        color = (255, 255, 255) if flash else self.color
        glow = (190, 170, 255)
        angle = self._anim_t * 0.4
        shapes.glow_circle(surface, color, sx, sy, r * 1.05, layers=2, alpha_start=40)
        shapes.regular_polygon(surface, color, sx, sy, r, 8, angle)
        shapes.regular_polygon(surface, glow, sx, sy, r, 8, angle, width=2)
        shapes.regular_polygon(surface, glow, sx, sy, r * 0.52, 4, angle + math.pi / 4)
        for idx in range(4):
            a = angle + math.tau * idx / 4
            ox = sx + math.cos(a) * r * 0.62
            oy = sy + math.sin(a) * r * 0.62
            shapes.circle(surface, glow, ox, oy, 2.5)


class BlinkSkirmisherEnemy(Enemy):
    _BASE = dict(max_hp=48, speed=82, damage=14, radius=14, color=(70, 230, 210), xp_drop=6, gold_drop=2, knockback_resist=0.08)
    _IDEAL_DIST = 190.0
    _TELEPORT_CD = 4.6

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._teleport_timer = self._TELEPORT_CD * 0.5
        self._ghosts: list[tuple[float, float, float]] = []

    def update(self, dt: float, player) -> None:
        self._ghosts = [(gx, gy, alpha - dt * 240) for gx, gy, alpha in self._ghosts if alpha > 16]
        super().update(dt, player)

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist < self._IDEAL_DIST * 0.72:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.2:
            self.vx = dx / dist * self.speed * 0.78
            self.vy = dy / dist * self.speed * 0.78
        else:
            self.vx = math.cos(orbit) * self.speed * 0.75
            self.vy = math.sin(orbit) * self.speed * 0.75

        self._teleport_timer -= dt
        if self._teleport_timer <= 0:
            self._teleport_timer = self._TELEPORT_CD
            self._teleport_and_burst(player)

    def _teleport_and_burst(self, player) -> None:
        self._ghosts.append((self.x, self.y, 185))
        base = player._facing if math.hypot(player.vx, player.vy) > 20 else math.atan2(player.y - self.y, player.x - self.x)
        flank = base + rng.choice((-1, 1)) * rng.uniform(1.75, 2.3)
        tx = player.x + math.cos(flank) * rng.uniform(86.0, 116.0)
        ty = player.y + math.sin(flank) * rng.uniform(86.0, 116.0)
        self.x = tx
        self.y = ty
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self._ghosts.append((self.x, self.y, 220))
        self._shoot_at_player(player, 310, self.damage * 0.92, (120, 255, 235), spread=0.58, count=3, shape="bolt", radius=6.0, life=3.5)
        particles.burst(self.x, self.y, self.color, count=10, speed=65, life=0.28, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for gx, gy, alpha in self._ghosts:
            if not cam.is_visible(gx, gy, self.radius):
                continue
            gsx, gsy = cam.world_to_screen(gx, gy)
            ghost = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*self.color, int(alpha)), (self.radius * 2, self.radius * 2), self.radius)
            surface.blit(ghost, (int(gsx) - self.radius * 2, int(gsy) - self.radius * 2))
        super().draw(surface, cam)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = math.atan2(self.vy or 0.01, self.vx or 0.01)
        r = self.radius * (1.0 + self._hit_burst * 0.17)
        color = (255, 255, 255) if flash else self.color
        glow = (165, 255, 245)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=3, alpha_start=34)
        pts = [
            (sx + math.cos(angle) * r * 1.5, sy + math.sin(angle) * r * 1.5),
            (sx + math.cos(angle + 2.3) * r, sy + math.sin(angle + 2.3) * r),
            (sx + math.cos(angle + math.pi) * r * 0.45, sy + math.sin(angle + math.pi) * r * 0.45),
            (sx + math.cos(angle - 2.3) * r, sy + math.sin(angle - 2.3) * r),
        ]
        shapes.polygon(surface, color, pts)
        shapes.polygon(surface, glow, pts, width=2)
        shapes.circle(surface, glow, sx, sy, r * 0.28)


class EmbermineEnemy(Enemy):
    _BASE = dict(max_hp=72, speed=56, damage=11, radius=18, color=(240, 120, 78), xp_drop=8, gold_drop=3, knockback_resist=0.16)
    _IDEAL_DIST = 245.0
    _MINE_CD = 2.3
    _SHOT_CD = 4.4

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._mine_timer = self._MINE_CD * 0.5
        self._shot_timer = self._SHOT_CD * 0.65

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist < self._IDEAL_DIST * 0.78:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.18:
            self.vx = dx / dist * self.speed * 0.7
            self.vy = dy / dist * self.speed * 0.7
        else:
            self.vx = math.cos(orbit) * self.speed * 0.55
            self.vy = math.sin(orbit) * self.speed * 0.55

        self._mine_timer -= dt
        if self._mine_timer <= 0:
            self._mine_timer = self._MINE_CD
            back = math.atan2(-(self.vy or dy), -(self.vx or dx))
            mx = self.x + math.cos(back) * 20.0
            my = self.y + math.sin(back) * 20.0
            self.pending_hazards.append(
                {
                    "kind": "fire_pool",
                    "x": mx,
                    "y": my,
                    "life": 4.4,
                    "damage_radius": 34,
                    "dps": self.damage * 1.0,
                    "color": (255, 105, 60),
                }
            )
            particles.burst(mx, my, (255, 150, 90), count=8, speed=45, life=0.22, size=3)

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = self._SHOT_CD
            angle = math.atan2(player.y - self.y, player.x - self.x)
            self.pending_projectiles.append(
                {
                    "x": self.x,
                    "y": self.y,
                    "vx": math.cos(angle) * 215.0,
                    "vy": math.sin(angle) * 215.0,
                    "damage": self.damage * 0.88,
                    "life": 3.6,
                    "radius": 10.5,
                    "color": (255, 135, 70),
                    "shape": "fireball",
                    "trail": 6,
                    "explode_fire": {
                        "life": 3.2,
                        "damage_radius": 28,
                        "dps": self.damage * 0.8,
                        "color": (255, 100, 55),
                    },
                    "burst_count": 11,
                }
            )
            particles.directional(self.x, self.y, angle, 0.25, (255, 165, 90), count=8, speed=55, life=0.22, size=3)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        dark = (120, 45, 18)
        shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=30)
        shapes.regular_polygon(surface, color, sx, sy, r, 8, self._anim_t * 0.4)
        shapes.regular_polygon(surface, dark, sx, sy, r, 8, self._anim_t * 0.4, width=2)
        for idx in range(3):
            oa = self._anim_t * 1.2 + idx * math.tau / 3
            ox = sx + math.cos(oa) * r * 0.65
            oy = sy + math.sin(oa) * r * 0.65
            shapes.circle(surface, (255, 210, 120), ox, oy, 3)


class SiegePylonEnemy(Enemy):
    _BASE = dict(max_hp=96, speed=34, damage=18, radius=20, color=(95, 205, 255), xp_drop=10, gold_drop=4, knockback_resist=0.28)
    _IDEAL_DIST = 310.0
    _CHARGE_CD = 3.9
    _CHARGE_TIME = 0.75

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self.contact_damage = False
        self._charge_cd = self._CHARGE_CD * 0.45
        self._charge_t = 0.0
        self._charging = False

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001

        if self._charging:
            self.vx *= 0.45
            self.vy *= 0.45
            self._charge_t += dt
            if self._charge_t >= self._CHARGE_TIME:
                self._charging = False
                self._charge_cd = self._CHARGE_CD
                self._fire_pattern(player)
            return

        if dist > self._IDEAL_DIST * 1.12:
            self.vx = dx / dist * self.speed * 0.75
            self.vy = dy / dist * self.speed * 0.75
        elif dist < self._IDEAL_DIST * 0.72:
            self.vx = -dx / dist * self.speed * 0.85
            self.vy = -dy / dist * self.speed * 0.85
        else:
            self.vx *= 0.78
            self.vy *= 0.78

        self._charge_cd -= dt
        if self._charge_cd <= 0:
            self._charging = True
            self._charge_t = 0.0
            particles.sparkle(self.x, self.y, (155, 225, 255), count=8, radius=22)

    def _fire_pattern(self, player) -> None:
        self._shoot_ring(225, self.damage * 0.46, (145, 220, 255), count=8, shape="orb", radius=6.5, life=3.8)
        self._shoot_at_player(player, 340, self.damage * 0.95, (195, 240, 255), count=1, shape="bolt", radius=8, life=4.4)
        particles.burst(self.x, self.y, (165, 230, 255), count=16, speed=58, life=0.28, size=4)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        dark = (28, 80, 110)
        shapes.glow_circle(surface, color, sx, sy, r * 1.02, layers=2, alpha_start=34)
        shapes.regular_polygon(surface, color, sx, sy, r, 4, math.pi / 4)
        shapes.regular_polygon(surface, dark, sx, sy, r, 4, math.pi / 4, width=2)
        if self._charging and not flash:
            charge_r = r + 8 + math.sin(self._anim_t * 4.0) * 3
            shapes.ring(surface, (190, 245, 255), sx, sy, charge_r, 2)
        shapes.circle(surface, (225, 250, 255), sx, sy, r * 0.22)


class RazorbatEnemy(Enemy):
    _BASE = dict(max_hp=24, speed=108, damage=8, radius=10, color=(255, 115, 185), xp_drop=5, gold_drop=1, knockback_resist=0.02)
    _PERCH_DIST = 220.0
    _SWOOP_CD = 2.7
    _SWOOP_DUR = 0.62
    _SWOOP_SPEED = 430.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self._swoop_cd = self._SWOOP_CD * 0.45
        self._swoop_t = 0.0
        self._swooping = False
        self._swoop_dir = 0.0

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if self._swooping:
            self._swoop_t += dt
            if self._swoop_t >= self._SWOOP_DUR:
                self._swooping = False
                self._swoop_cd = self._SWOOP_CD
            self.vx = math.cos(self._swoop_dir) * self._SWOOP_SPEED
            self.vy = math.sin(self._swoop_dir) * self._SWOOP_SPEED
            return

        if dist < self._PERCH_DIST * 0.72:
            self.vx = -dx / dist * self.speed * 0.72
            self.vy = -dy / dist * self.speed * 0.72
        elif dist > self._PERCH_DIST * 1.18:
            self.vx = dx / dist * self.speed * 0.86
            self.vy = dy / dist * self.speed * 0.86
        else:
            self.vx = math.cos(orbit) * self.speed
            self.vy = math.sin(orbit) * self.speed

        self._swoop_cd -= dt
        if self._swoop_cd <= 0 and dist < 330:
            self._swooping = True
            self._swoop_t = 0.0
            tx = player.x + player.vx * 0.28
            ty = player.y + player.vy * 0.28
            self._swoop_dir = math.atan2(ty - self.y, tx - self.x)
            particles.directional(self.x, self.y, self._swoop_dir, 0.45, (255, 150, 205), count=9, speed=70, life=0.2, size=3)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        angle = self._swoop_dir if self._swooping else math.atan2(self.vy or 0.01, self.vx or 0.01)
        r = self.radius * (1.0 + math.sin(self._anim_t * 7.0) * 0.06 + self._hit_burst * 0.16)
        color = (255, 255, 255) if flash else self.color
        wing_a = angle + math.pi / 2
        wing_b = angle - math.pi / 2
        tips = [
            (sx + math.cos(angle) * r * 1.45, sy + math.sin(angle) * r * 1.45),
            (sx + math.cos(wing_a) * r * 1.35, sy + math.sin(wing_a) * r * 0.85),
            (sx - math.cos(angle) * r * 0.2, sy - math.sin(angle) * r * 0.2),
            (sx + math.cos(wing_b) * r * 1.35, sy + math.sin(wing_b) * r * 0.85),
        ]
        if self._swooping and not flash:
            shapes.glow_circle(surface, color, sx, sy, r * 0.95, layers=2, alpha_start=24)
        shapes.polygon(surface, color, tips)
        shapes.line(surface, (255, 215, 240), sx, sy, sx - math.cos(angle) * r * 0.9, sy - math.sin(angle) * r * 0.9, 2)


class BroodSeederEnemy(Enemy):
    _BASE = dict(max_hp=58, speed=52, damage=8, radius=16, color=(145, 205, 90), xp_drop=7, gold_drop=2, knockback_resist=0.08)
    _IDEAL_DIST = 265.0
    _SUMMON_CD = 6.7
    _SHOT_CD = 2.8

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), b["gold_drop"], b["knockback_resist"])
        self.contact_damage = False
        self._summon_timer = self._SUMMON_CD * 0.45
        self._shot_timer = self._SHOT_CD * 0.55

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2

        if dist < self._IDEAL_DIST * 0.74:
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > self._IDEAL_DIST * 1.16:
            self.vx = dx / dist * self.speed * 0.7
            self.vy = dy / dist * self.speed * 0.7
        else:
            self.vx = math.cos(orbit) * self.speed * 0.65
            self.vy = math.sin(orbit) * self.speed * 0.65

        self._summon_timer -= dt
        if self._summon_timer <= 0:
            self._summon_timer = self._SUMMON_CD
            summons = ("razorbat", "blink_skirmisher")
            for idx, etype in enumerate(summons):
                angle = self._anim_t + math.tau * idx / len(summons)
                self.pending_spawns.append(
                    {
                        "etype": etype,
                        "x": self.x + math.cos(angle) * 58.0,
                        "y": self.y + math.sin(angle) * 58.0,
                    }
                )
            particles.burst(self.x, self.y, (180, 235, 120), count=12, speed=55, life=0.3, size=4)

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = self._SHOT_CD
            self._shoot_at_player(player, 255, self.damage * 0.82, (185, 240, 130), spread=0.24, count=2, shape="orb", radius=5.5, life=3.4)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + self._hit_burst * 0.15)
        color = (255, 255, 255) if flash else self.color
        glow = (205, 245, 155)
        shapes.glow_circle(surface, color, sx, sy, r, layers=2, alpha_start=36)
        shapes.circle(surface, color, sx, sy, r * 0.9)
        shapes.circle(surface, (60, 95, 32), sx, sy, r * 0.38)
        for idx in range(4):
            a = self._anim_t * 0.9 + math.tau * idx / 4
            ox = sx + math.cos(a) * r * 1.2
            oy = sy + math.sin(a) * r * 1.2
            shapes.diamond(surface, glow, ox, oy, 4.0, 6.0)


class GeometricDevourerBoss(Enemy):
    _BASE = dict(max_hp=7350, speed=132, damage=26, radius=32, color=(255, 125, 85), xp_drop=135, gold_drop=40, knockback_resist=0.94)
    _CRUISE_DURATION = 5.4
    _ASSAULT_DURATION = 2.7
    _PORTAL_HIDE_TIME = 0.55
    _PORTAL_EXIT_TIME = 0.48
    _PORTAL_COOLDOWN = 8.5
    _CRUISE_TURN = 2.0
    _ASSAULT_TURN = 3.25
    _SEGMENT_SPACING = 24.0
    _SEGMENT_COUNT = 24
    _SEGMENT_FIRE_CD = 1.05
    _GODFIRE_CD = 4.1

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(
            x,
            y,
            b["max_hp"] * d["hp_mul"],
            b["speed"],
            b["damage"] * d["dmg_mul"],
            b["radius"],
            b["color"],
            max(1, int(b["xp_drop"] * d["reward_mul"])),
            int(b["gold_drop"] * d["reward_mul"]),
            b["knockback_resist"],
        )
        self.is_boss = True
        self.boss_name = "\u51e0\u4f55\u541e\u566c\u8005"
        self.attack_label = "\u5de1\u822a\u5f39\u5e55"
        self.contact_damage = False

        self._facing = 0.0
        self._state = "cruise"
        self._mode_timer = self._CRUISE_DURATION
        self._phase_two = False
        self._segment_fire_timer = self._SEGMENT_FIRE_CD * 0.75
        self._godfire_timer = self._GODFIRE_CD * 1.1
        self._portal_cd = self._PORTAL_COOLDOWN
        self._portal_stage = ""
        self._portal_timer = 0.0
        self._portal_entry: tuple[float, float] | None = None
        self._portal_exit: tuple[float, float] | None = None
        self._dash_dir = 0.0
        self._turn_echo = 0.0
        self._player_angle = 0.0
        self._last_player_angle = 0.0
        self._segments: list[tuple[float, float]] = []
        self._segment_cache: list[tuple[float, float, float]] = []
        self._reset_segments()

    def update(self, dt: float, player) -> None:
        move_angle = player._facing
        if math.hypot(player.vx, player.vy) > 25:
            move_angle = math.atan2(player.vy, player.vx)
        if abs(_angle_diff(move_angle, self._last_player_angle)) > 0.55:
            self._turn_echo = 0.45
        self._last_player_angle = move_angle
        self._player_angle = move_angle

        if not self._phase_two and self.hp / self.max_hp <= 0.5:
            self._phase_two = True
            self._portal_cd = 3.2
            self._godfire_timer = 1.2
            particles.burst(self.x, self.y, (255, 180, 120), count=22, speed=95, life=0.45, size=5)

        super().update(dt, player)
        self._turn_echo = max(0.0, self._turn_echo - dt)
        if self._state == "portal":
            self._collapse_segments(dt)
        else:
            self._update_segments(dt)

    def _ai(self, dt: float, player) -> None:
        self._mode_timer -= dt
        self.vx = 0.0
        self.vy = 0.0

        if self._phase_two and self._state != "portal":
            self._portal_cd -= dt
            if self._portal_cd <= 0:
                self._begin_portal()

        if self._state == "portal":
            self.attack_label = "\u4f20\u9001\u95e8\u7a81\u523a"
            self._portal_logic(dt, player)
            return

        self.invulnerable = False
        if self._state == "cruise":
            self.attack_label = "\u5de1\u822a\u5f39\u5e55"
            self.contact_damage = False
            self._state_cruise(dt, player)
            if self._mode_timer <= 0:
                self._start_assault(player)
        else:
            self.attack_label = "\u7a81\u51fb\u51b2\u950b"
            self.contact_damage = True
            self._state_assault(dt, player)
            if self._mode_timer <= 0:
                self._start_cruise()

        if self._state == "cruise":
            self._segment_fire_timer -= dt
            if self._segment_fire_timer <= 0:
                self._segment_fire_timer = 0.82 if self._phase_two else self._SEGMENT_FIRE_CD
                self._fire_segment_barrage(player)

        if self._phase_two:
            self._godfire_timer -= dt
            if self._godfire_timer <= 0:
                self._godfire_timer = 3.2 if self._state == "assault" else self._GODFIRE_CD
                self._fire_godfire(player)

    def _state_cruise(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        desired = math.atan2(dy, dx)
        desired = _blend_angles(desired, self._player_angle, 0.22)
        turn_speed = self._CRUISE_TURN + self._turn_echo * 1.4
        self._facing = _turn_towards(self._facing, desired, turn_speed * dt)
        speed = self.speed + min(100.0, dist * 0.11)
        if dist < 165:
            speed *= 0.78
        self.vx = math.cos(self._facing) * speed
        self.vy = math.sin(self._facing) * speed

    def _state_assault(self, dt: float, player) -> None:
        desired = math.atan2(player.y - self.y, player.x - self.x)
        desired = _blend_angles(desired, self._player_angle, 0.14)
        self._dash_dir = _turn_towards(self._dash_dir, desired, self._ASSAULT_TURN * dt)
        self._facing = _turn_towards(self._facing, self._dash_dir, (self._ASSAULT_TURN + 0.9) * dt)
        speed = 420.0 if not self._phase_two else 495.0
        if self._mode_timer > self._ASSAULT_DURATION - 0.22:
            speed *= 0.72
        self.vx = math.cos(self._dash_dir) * speed
        self.vy = math.sin(self._dash_dir) * speed
        if rng.chance(dt * 10):
            particles.directional(self.x, self.y, self._dash_dir + math.pi, 0.45, (255, 165, 120), count=4, speed=60, life=0.18, size=3)

    def _start_cruise(self) -> None:
        self._state = "cruise"
        self._mode_timer = self._CRUISE_DURATION
        self.contact_damage = False
        particles.burst(self.x, self.y, self.color, count=10, speed=55, life=0.24, size=3)

    def _start_assault(self, player) -> None:
        self._state = "assault"
        self._mode_timer = self._ASSAULT_DURATION
        self._dash_dir = math.atan2(player.y - self.y, player.x - self.x)
        self.contact_damage = True
        particles.directional(self.x, self.y, self._dash_dir, 0.4, (255, 165, 110), count=10, speed=85, life=0.22, size=4)

    def _begin_portal(self) -> None:
        self._state = "portal"
        self._mode_timer = self._PORTAL_HIDE_TIME
        self._portal_stage = "entry"
        self._portal_timer = self._PORTAL_HIDE_TIME
        self._portal_entry = (self.x, self.y)
        self._portal_exit = None
        self.contact_damage = False
        self.invulnerable = True
        self.vx = 0.0
        self.vy = 0.0
        particles.burst(self.x, self.y, (255, 145, 95), count=12, speed=70, life=0.32, size=4)

    def _portal_logic(self, dt: float, player) -> None:
        self.vx = 0.0
        self.vy = 0.0
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        self._portal_timer -= dt
        if self._portal_stage == "entry" and self._portal_timer <= 0:
            self._portal_stage = "exit"
            self._portal_timer = self._PORTAL_EXIT_TIME
            self._portal_exit = self._pick_portal_exit(player)
            self.x, self.y = self._portal_exit
            self._dash_dir = math.atan2(player.y - self.y, player.x - self.x)
            self._facing = self._dash_dir
            self._reset_segments()
            particles.burst(self.x, self.y, (255, 205, 135), count=14, speed=82, life=0.34, size=4)
            return
        if self._portal_stage == "exit" and self._portal_timer <= 0:
            self._portal_cd = self._PORTAL_COOLDOWN
            self._portal_stage = ""
            self.invulnerable = False
            self._start_assault(player)

    def _pick_portal_exit(self, player) -> tuple[float, float]:
        angle = rng.uniform(0.0, math.tau)
        dist = rng.uniform(210.0, 320.0)
        return player.x + math.cos(angle) * dist, player.y + math.sin(angle) * dist

    def _reset_segments(self) -> None:
        self._segments = []
        for idx in range(self._SEGMENT_COUNT):
            dist = (idx + 1) * self._SEGMENT_SPACING
            self._segments.append(
                (
                    self.x - math.cos(self._facing) * dist,
                    self.y - math.sin(self._facing) * dist,
                )
            )

    def _update_segments(self, dt: float) -> None:
        updated: list[tuple[float, float]] = []
        prev_x, prev_y = self.x, self.y
        for idx, (sx, sy) in enumerate(self._segments):
            dx = prev_x - sx
            dy = prev_y - sy
            dist = math.hypot(dx, dy)
            if dist <= 0.001:
                tx = prev_x - math.cos(self._facing) * self._SEGMENT_SPACING
                ty = prev_y - math.sin(self._facing) * self._SEGMENT_SPACING
            else:
                tx = prev_x - dx / dist * self._SEGMENT_SPACING
                ty = prev_y - dy / dist * self._SEGMENT_SPACING
            follow = min(1.0, dt * (12.0 - min(idx, 8) * 0.55))
            sx += (tx - sx) * follow
            sy += (ty - sy) * follow
            updated.append((sx, sy))
            prev_x, prev_y = sx, sy
        self._segments = updated

    def _segment_radius(self, idx: int) -> float:
        if self._SEGMENT_COUNT <= 1:
            return self.radius * 0.8
        t = idx / (self._SEGMENT_COUNT - 1)
        return self.radius * max(0.24, 0.88 - 0.56 * t)

    def _collapse_segments(self, dt: float) -> None:
        updated: list[tuple[float, float]] = []
        anchor_x, anchor_y = self.x, self.y
        for idx, (sx, sy) in enumerate(self._segments):
            pull = min(1.0, dt * (7.5 + idx * 0.5))
            sx += (anchor_x - sx) * pull
            sy += (anchor_y - sy) * pull
            updated.append((sx, sy))
        self._segments = updated

    def _fire_segment_barrage(self, player) -> None:
        segment_step = 1 if self._phase_two else 2
        for idx, (sx, sy) in enumerate(self._segments):
            if idx % segment_step != 0:
                continue
            angle = math.atan2(player.y - sy, player.x - sx)
            angle += (idx - len(self._segments) / 2) * 0.035
            speed = 270 + idx * 10 + (20 if self._phase_two else 0)
            self.pending_projectiles.append(
                {
                    "x": sx,
                    "y": sy,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "damage": self.damage * 0.5,
                    "life": 4.2,
                    "radius": 6.5,
                    "color": (255, 175, 115),
                    "shape": "bolt",
                    "trail": 4,
                    "burst_count": 7,
                }
            )
        particles.sparkle(self.x, self.y, (255, 185, 135), count=7, radius=self.radius + 22)

    def _fire_godfire(self, player) -> None:
        angle = math.atan2(player.y - self.y, player.x - self.x)
        if self._state == "assault":
            angle = self._dash_dir
        color = (255, 120, 70)
        self.pending_projectiles.append(
            {
                "x": self.x + math.cos(angle) * self.radius * 1.25,
                "y": self.y + math.sin(angle) * self.radius * 1.25,
                "vx": math.cos(angle) * 290.0,
                "vy": math.sin(angle) * 290.0,
                "damage": self.damage * 1.9,
                "life": 3.5,
                "radius": 15.0,
                "color": color,
                "shape": "fireball",
                "trail": 8,
                "burst_count": 14,
                "explode_spawn_on_hit": False,
                "explode_spawn": {
                    "count": 10,
                    "speed": 225.0,
                    "arc": math.tau,
                    "angle_offset": rng.uniform(0.0, math.tau),
                    "damage": self.damage * 0.58,
                    "life": 2.8,
                    "radius": 6.0,
                    "color": (255, 175, 95),
                    "shape": "orb",
                    "trail": 3,
                    "burst_count": 6,
                },
            }
        )
        particles.directional(self.x, self.y, angle, 0.26, color, count=14, speed=80, life=0.26, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        if self._state == "portal":
            if self._portal_entry is not None:
                self._draw_portal(surface, cam, self._portal_entry[0], self._portal_entry[1], (255, 125, 85), 1.0)
            if self._portal_exit is not None:
                self._draw_portal(surface, cam, self._portal_exit[0], self._portal_exit[1], (255, 210, 140), 0.85)
            return

        visible = cam.is_visible(self.x, self.y, self.radius + 48)
        if not visible:
            for sx, sy in self._segments:
                if cam.is_visible(sx, sy, self.radius):
                    visible = True
                    break
        if not visible:
            return

        self._segment_cache = []
        shadow_color = (0, 0, 0, 80)
        for idx in range(len(self._segments) - 1, -1, -1):
            sx, sy = self._segments[idx]
            seg_r = self._segment_radius(idx)
            self._segment_cache.append((sx, sy, seg_r))
            dsx, dsy = cam.world_to_screen(sx, sy)
            shadow = pygame.Surface((int(seg_r * 4), int(seg_r * 2.2)), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, shadow_color, shadow.get_rect())
            surface.blit(shadow, (int(dsx - shadow.get_width() / 2), int(dsy + seg_r * 0.55)))
            body = tuple(max(30, int(c * (0.8 - idx * 0.03))) for c in self.color)
            accent = tuple(min(255, c + 35) for c in body)
            shapes.glow_circle(surface, body, dsx, dsy, seg_r * 0.9, layers=2, alpha_start=34)
            shapes.regular_polygon(surface, body, dsx, dsy, seg_r, 6, self._anim_t * 0.25 + idx * 0.22)
            shapes.regular_polygon(surface, accent, dsx, dsy, seg_r, 6, self._anim_t * 0.25 + idx * 0.22, width=2)
            core_x = dsx + math.cos(self._anim_t * 1.1 + idx * 0.4) * seg_r * 0.15
            core_y = dsy + math.sin(self._anim_t * 1.1 + idx * 0.4) * seg_r * 0.15
            shapes.circle(surface, accent, core_x, core_y, max(2.0, seg_r * 0.18))

        head_sx, head_sy = cam.world_to_screen(self.x, self.y)
        head_r = self.radius * (1.0 + math.sin(self._anim_t * 1.5) * 0.04 + self._hit_burst * 0.14)
        head_color = (255, 255, 255) if self._flash_timer > 0 else self.color
        outline = (255, 220, 180)
        shadow = pygame.Surface((int(head_r * 4.6), int(head_r * 2.4)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, shadow_color, shadow.get_rect())
        surface.blit(shadow, (int(head_sx - shadow.get_width() / 2), int(head_sy + head_r * 0.58)))
        shapes.glow_circle(surface, head_color, head_sx, head_sy, head_r * 1.05, layers=4, alpha_start=42)
        head_angle = self._facing
        pts = [
            (head_sx + math.cos(head_angle) * head_r * 1.55, head_sy + math.sin(head_angle) * head_r * 1.55),
            (head_sx + math.cos(head_angle + 2.42) * head_r, head_sy + math.sin(head_angle + 2.42) * head_r),
            (head_sx + math.cos(head_angle + math.pi) * head_r * 0.48, head_sy + math.sin(head_angle + math.pi) * head_r * 0.48),
            (head_sx + math.cos(head_angle - 2.42) * head_r, head_sy + math.sin(head_angle - 2.42) * head_r),
        ]
        shapes.polygon(surface, head_color, pts)
        shapes.polygon(surface, outline, pts, width=2)
        jaw_a = head_angle + 0.45
        jaw_b = head_angle - 0.45
        shapes.line(surface, outline, head_sx, head_sy, head_sx + math.cos(jaw_a) * head_r * 1.25, head_sy + math.sin(jaw_a) * head_r * 1.25, 2)
        shapes.line(surface, outline, head_sx, head_sy, head_sx + math.cos(jaw_b) * head_r * 1.25, head_sy + math.sin(jaw_b) * head_r * 1.25, 2)
        eye_off = head_angle + math.pi / 2
        ex = head_sx + math.cos(head_angle) * head_r * 0.35 + math.cos(eye_off) * head_r * 0.22
        ey = head_sy + math.sin(head_angle) * head_r * 0.35 + math.sin(eye_off) * head_r * 0.22
        shapes.circle(surface, (255, 245, 200), ex, ey, 3)
        ex = head_sx + math.cos(head_angle) * head_r * 0.35 - math.cos(eye_off) * head_r * 0.22
        ey = head_sy + math.sin(head_angle) * head_r * 0.35 - math.sin(eye_off) * head_r * 0.22
        shapes.circle(surface, (255, 245, 200), ex, ey, 3)

        if self._phase_two:
            aura_r = head_r + 10 + math.sin(self._anim_t * 2.2) * 3
            shapes.ring(surface, (255, 170, 110), head_sx, head_sy, aura_r, 2)

    def collision_nodes(self) -> list[tuple[float, float, float, float]]:
        if not self.alive or self._state == "portal":
            return []
        nodes: list[tuple[float, float, float, float]] = []
        if self.contact_damage:
            nodes.append((self.x, self.y, self.radius * 0.95, self.damage))
        body_damage = self.damage * (0.6 if self._state == "cruise" else 0.9)
        for idx, (sx, sy) in enumerate(self._segments):
            seg_r = self._segment_radius(idx) * 0.78
            if seg_r <= 3:
                continue
            nodes.append((sx, sy, seg_r, body_damage))
        return nodes

    def _draw_portal(self, surface: pygame.Surface, cam, x: float, y: float, color, alpha_scale: float) -> None:
        if not cam.is_visible(x, y, self.radius + 40):
            return
        sx, sy = cam.world_to_screen(x, y)
        radius = self.radius + 12 + math.sin(self._anim_t * 3.0) * 3
        portal = pygame.Surface((int(radius * 3), int(radius * 3)), pygame.SRCALPHA)
        pr = portal.get_rect()
        center = (pr.width // 2, pr.height // 2)
        pygame.draw.circle(portal, (*color, int(34 * alpha_scale)), center, int(radius * 1.35))
        pygame.draw.circle(portal, (*color, int(85 * alpha_scale)), center, int(radius), 3)
        pygame.draw.circle(portal, (20, 10, 10, int(200 * alpha_scale)), center, int(radius * 0.74))
        surface.blit(portal, (int(sx - portal.get_width() / 2), int(sy - portal.get_height() / 2)))
        for idx in range(6):
            angle = self._anim_t * 1.6 + math.tau * idx / 6
            ox = sx + math.cos(angle) * radius * 1.08
            oy = sy + math.sin(angle) * radius * 1.08
            shapes.circle(surface, color, ox, oy, 2.5)


class StormTyrantBoss(Enemy):
    _BASE = dict(max_hp=4800, speed=78, damage=20, radius=38, color=(255, 95, 165), xp_drop=90, gold_drop=28, knockback_resist=0.9)
    _STATE_ORDER = ("散射压制", "环阵轰击", "冲锋追猎")
    _STATE_DURATIONS = {"散射压制": 4.2, "环阵轰击": 4.0, "冲锋追猎": 3.6}

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y, b["max_hp"] * d["hp_mul"], b["speed"], b["damage"] * d["dmg_mul"], b["radius"], b["color"], max(1, int(b["xp_drop"] * d["reward_mul"])), int(b["gold_drop"] * d["reward_mul"]), b["knockback_resist"])
        self.is_boss = True
        self.boss_name = "猩红风暴主宰"
        self.attack_label = self._STATE_ORDER[0]
        self._state_index = 0
        self._state_timer = 0.0
        self._shot_timer = 0.0
        self._dash_angle = 0.0
        self._summon_timer = 2.8

    def update(self, dt: float, player) -> None:
        if self.hp / self.max_hp < 0.45:
            self.speed = 94
        super().update(dt, player)

    def _ai(self, dt: float, player) -> None:
        self._state_timer += dt
        state = self._STATE_ORDER[self._state_index]
        self.attack_label = state
        if self._state_timer >= self._STATE_DURATIONS[state]:
            self._state_index = (self._state_index + 1) % len(self._STATE_ORDER)
            self._state_timer = 0.0
            self._shot_timer = 0.0
            particles.burst(self.x, self.y, self.color, count=14, speed=70, life=0.35, size=5)
            state = self._STATE_ORDER[self._state_index]
            self.attack_label = state

        if state == "散射压制":
            self._state_spread(dt, player)
        elif state == "环阵轰击":
            self._state_ring(dt, player)
        else:
            self._state_dash(dt, player)
        self._handle_summons(dt)

    def _handle_summons(self, dt: float) -> None:
        self._summon_timer -= dt
        if self._summon_timer > 0:
            return
        self._summon_timer = 6.0
        minions = ("wisp", "lancer", "slime_medium")
        for idx, etype in enumerate(minions):
            angle = self._anim_t + math.tau * idx / len(minions)
            self.pending_spawns.append(
                {
                    "etype": etype,
                    "x": self.x + math.cos(angle) * 110,
                    "y": self.y + math.sin(angle) * 110,
                    "color": self.color if "slime" in etype else None,
                }
            )
        particles.burst(self.x, self.y, (255, 170, 210), count=12, speed=80, life=0.35, size=4)

    def _state_spread(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2
        self.vx = math.cos(orbit) * self.speed * 0.75 + dx / dist * self.speed * 0.25
        self.vy = math.sin(orbit) * self.speed * 0.75 + dy / dist * self.speed * 0.25

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = 0.55
            self._shoot_at_player(player, 305, self.damage * 0.8, (255, 130, 185), spread=0.85, count=7, shape="spike", radius=7, life=4.4)
            particles.directional(self.x, self.y, math.atan2(dy, dx), 0.4, (255, 150, 195), count=10, speed=70, life=0.22)

    def _state_ring(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        self.vx = -dx / dist * self.speed * 0.25
        self.vy = -dy / dist * self.speed * 0.25

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = 0.95
            self._shoot_ring(235, self.damage * 0.65, (255, 175, 215), count=14, shape="orb", radius=8, life=4.0)
            self._shoot_at_player(player, 340, self.damage * 0.95, (255, 220, 240), count=1, shape="bolt", radius=8, life=4.8)
            particles.burst(self.x, self.y, (255, 190, 220), count=18, speed=65, life=0.3, size=4)

    def _state_dash(self, dt: float, player) -> None:
        if self._shot_timer <= 0:
            self._dash_angle = math.atan2(player.y - self.y, player.x - self.x)
        self._shot_timer -= dt

        if self._shot_timer <= -0.8:
            self._shot_timer = 1.1
            self._dash_angle = math.atan2(player.y - self.y, player.x - self.x)
            self._shoot_ring(200, self.damage * 0.45, (255, 120, 170), count=8, shape="bolt", radius=6, life=2.8)
            particles.burst(self.x, self.y, (255, 110, 170), count=12, speed=80, life=0.28, size=4)

        dash_speed = 420 if self._shot_timer < 0.25 else 110
        self.vx = math.cos(self._dash_angle) * dash_speed
        self.vy = math.sin(self._dash_angle) * dash_speed

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + math.sin(self._anim_t * 1.2) * 0.05 + self._hit_burst * 0.14)
        color = (255, 255, 255) if flash else self.color
        glow = (255, 180, 215)
        angle = self._anim_t * 0.55
        shapes.glow_circle(surface, color, sx, sy, r * 1.2, layers=4, alpha_start=46)
        shapes.regular_polygon(surface, color, sx, sy, r, 10, angle)
        shapes.regular_polygon(surface, (120, 20, 55), sx, sy, r, 10, angle, width=3)
        shapes.regular_polygon(surface, glow, sx, sy, r * 0.62, 5, -angle)
        shapes.circle(surface, (255, 245, 250), sx, sy, r * 0.22)
        for idx in range(4):
            oa = angle + math.tau * idx / 4
            ox = sx + math.cos(oa) * r * 1.18
            oy = sy + math.sin(oa) * r * 1.18
            shapes.circle(surface, glow, ox, oy, 4)


class VoidColossusBoss(Enemy):
    _BASE = dict(max_hp=5550, speed=62, damage=24, radius=44, color=(90, 120, 255), xp_drop=110, gold_drop=34, knockback_resist=0.92)
    _STATE_ORDER = ("重压震荡", "虚空喷射", "引力坍塌")
    _STATE_DURATIONS = {"重压震荡": 4.5, "虚空喷射": 4.2, "引力坍塌": 4.8}

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(
            x,
            y,
            b["max_hp"] * d["hp_mul"],
            b["speed"],
            b["damage"] * d["dmg_mul"],
            b["radius"],
            b["color"],
            max(1, int(b["xp_drop"] * d["reward_mul"])),
            int(b["gold_drop"] * d["reward_mul"]),
            b["knockback_resist"],
        )
        self.is_boss = True
        self.boss_name = "虚空巨像"
        self.attack_label = self._STATE_ORDER[0]
        self._state_index = 0
        self._state_timer = 0.0
        self._shot_timer = 0.0
        self._summon_timer = 3.2

    def update(self, dt: float, player) -> None:
        if self.hp / self.max_hp < 0.5:
            self.speed = 78
        super().update(dt, player)

    def _ai(self, dt: float, player) -> None:
        self._state_timer += dt
        state = self._STATE_ORDER[self._state_index]
        self.attack_label = state
        if self._state_timer >= self._STATE_DURATIONS[state]:
            self._state_index = (self._state_index + 1) % len(self._STATE_ORDER)
            self._state_timer = 0.0
            self._shot_timer = 0.0
            particles.burst(self.x, self.y, self.color, count=16, speed=75, life=0.35, size=5)
            state = self._STATE_ORDER[self._state_index]
            self.attack_label = state

        if state == "重压震荡":
            self._state_barrage(dt, player)
        elif state == "虚空喷射":
            self._state_beam(dt, player)
        else:
            self._state_gravity(dt, player)
        self._handle_summons(dt)

    def _state_barrage(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        self.vx = dx / dist * self.speed * 0.45
        self.vy = dy / dist * self.speed * 0.45

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = 0.85
            self._shoot_ring(210, self.damage * 0.55, (130, 165, 255), count=10, shape="orb", radius=8, life=4.0)
            particles.burst(self.x, self.y, (130, 165, 255), count=12, speed=60, life=0.28, size=4)

    def _state_beam(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        orbit = math.atan2(dy, dx) + math.pi / 2
        self.vx = math.cos(orbit) * self.speed * 0.6
        self.vy = math.sin(orbit) * self.speed * 0.6

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = 0.48
            self._shoot_at_player(player, 330, self.damage * 0.85, (180, 210, 255), spread=0.22, count=3, shape="bolt", radius=8, life=4.6)
            particles.directional(self.x, self.y, math.atan2(dy, dx), 0.3, (180, 210, 255), count=8, speed=70, life=0.18)

    def _state_gravity(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.001
        self.vx = -dx / dist * self.speed * 0.25
        self.vy = -dy / dist * self.speed * 0.25

        self._shot_timer -= dt
        if self._shot_timer <= 0:
            self._shot_timer = 1.25
            self.pending_hazards.append(
                {
                    "kind": "black_hole",
                    "x": player.x + rng.uniform(-70, 70),
                    "y": player.y + rng.uniform(-70, 70),
                    "life": 4.2,
                    "pull_radius": 240,
                    "damage_radius": 44,
                    "pull_strength": 260,
                    "dps": self.damage * 1.8,
                    "color": (105, 130, 255),
                }
            )
            self._shoot_at_player(player, 270, self.damage * 0.5, (120, 145, 255), spread=0.65, count=5, shape="orb", radius=7, life=3.8)

    def _handle_summons(self, dt: float) -> None:
        self._summon_timer -= dt
        if self._summon_timer > 0:
            return
        self._summon_timer = 7.0
        minions = ("slime_large", "blackhole_mage")
        for idx, etype in enumerate(minions):
            angle = self._anim_t + math.tau * idx / len(minions)
            self.pending_spawns.append(
                {
                    "etype": etype,
                    "x": self.x + math.cos(angle) * 135,
                    "y": self.y + math.sin(angle) * 135,
                    "color": self.color if "slime" in etype else None,
                }
            )
        particles.burst(self.x, self.y, (160, 190, 255), count=14, speed=85, life=0.35, size=4)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        r = self.radius * (1.0 + math.sin(self._anim_t) * 0.04 + self._hit_burst * 0.12)
        color = (255, 255, 255) if flash else self.color
        glow = (175, 200, 255)
        angle = self._anim_t * 0.35
        shapes.glow_circle(surface, color, sx, sy, r * 1.15, layers=4, alpha_start=42)
        shapes.regular_polygon(surface, color, sx, sy, r, 12, angle)
        shapes.regular_polygon(surface, (20, 35, 90), sx, sy, r, 12, angle, width=3)
        shapes.regular_polygon(surface, glow, sx, sy, r * 0.68, 6, -angle)
        shapes.circle(surface, (235, 245, 255), sx, sy, r * 0.18)
        for idx in range(6):
            oa = angle + math.tau * idx / 6
            ox = sx + math.cos(oa) * r * 1.05
            oy = sy + math.sin(oa) * r * 1.05
            shapes.circle(surface, glow, ox, oy, 3)


class EliteSummoner(ZombieEnemy):
    _SUMMON_CD = 5.0
    _SUMMON_COUNT = 3

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp *= _ELITE_HP
        self.hp = self.max_hp
        self.damage *= _ELITE_DMG
        self.radius = int(self.radius * _ELITE_RAD)
        self.xp_drop = int(self.xp_drop * _ELITE_RWD)
        self.gold_drop = int(self.gold_drop * _ELITE_RWD)
        self.speed *= 0.8
        self.color = (30, 165, 50)
        self._summon_cd = self._SUMMON_CD * 0.5

    def _ai(self, dt: float, player) -> None:
        super()._ai(dt, player)
        self._summon_cd -= dt
        if self._summon_cd <= 0:
            self._summon_cd = self._SUMMON_CD
            for idx in range(self._SUMMON_COUNT):
                angle = math.tau * idx / self._SUMMON_COUNT
                sx = self.x + math.cos(angle) * self.radius * 3
                sy = self.y + math.sin(angle) * self.radius * 3
                self.pending_spawns.append({"etype": "zombie", "x": sx, "y": sy})
            particles.burst(self.x, self.y, self.color, count=12, speed=50, life=0.5, size=4)


class EliteBerserker(TankEnemy):
    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp *= _ELITE_HP
        self.hp = self.max_hp
        self.damage *= _ELITE_DMG
        self.radius = int(self.radius * _ELITE_RAD)
        self.xp_drop = int(self.xp_drop * _ELITE_RWD)
        self.gold_drop = int(self.gold_drop * _ELITE_RWD)
        self.knockback_resist = 0.85
        self.color = (70, 90, 130)
        self._base_speed = self.speed

    @property
    def enraged(self) -> bool:
        return self.hp / self.max_hp < 0.5

    def update(self, dt: float, player) -> None:
        if self.enraged:
            self.speed = self._base_speed * 2.0
            if rng.chance(dt * 3):
                particles.sparkle(self.x, self.y, (255, 60, 30), count=2, radius=self.radius)
        else:
            self.speed = self._base_speed
        super().update(dt, player)

    def _draw_shape(self, surface: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
        if self.enraged and not flash:
            self.color = (200, 70, 55)
        super()._draw_shape(surface, sx, sy, flash)


class EliteAssassin(SpeederEnemy):
    _TELEPORT_CD = 4.0
    _BEHIND_DIST = 55.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp *= _ELITE_HP
        self.hp = self.max_hp
        self.damage *= _ELITE_DMG
        self.radius = int(self.radius * _ELITE_RAD)
        self.xp_drop = int(self.xp_drop * _ELITE_RWD)
        self.gold_drop = int(self.gold_drop * _ELITE_RWD)
        self.speed *= 1.3
        self.color = (135, 40, 215)
        self._tp_cd = self._TELEPORT_CD * 0.3
        self._ghosts: list[tuple[float, float, float]] = []

    def update(self, dt: float, player) -> None:
        self._tp_cd -= dt
        self._ghosts = [(gx, gy, alpha - dt * 300) for gx, gy, alpha in self._ghosts if alpha > 20]
        if self._tp_cd <= 0:
            self._teleport(player)
            self._tp_cd = self._TELEPORT_CD
        super().update(dt, player)
        if math.hypot(self.vx, self.vy) > 200 and rng.chance(dt * 10):
            self._ghosts.append((self.x, self.y, 180))

    def _teleport(self, player) -> None:
        behind = player._facing + math.pi
        tx = player.x + math.cos(behind) * self._BEHIND_DIST
        ty = player.y + math.sin(behind) * self._BEHIND_DIST
        self._ghosts.append((self.x, self.y, 200))
        self.x, self.y = tx, ty
        self.kb_vx = 0.0
        self.kb_vy = 0.0
        particles.burst(tx, ty, self.color, count=10, speed=60, life=0.3, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        for gx, gy, alpha in self._ghosts:
            if not cam.is_visible(gx, gy, self.radius):
                continue
            gsx, gsy = cam.world_to_screen(gx, gy)
            ghost = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*self.color, int(alpha)), (self.radius * 2, self.radius * 2), self.radius)
            surface.blit(ghost, (int(gsx) - self.radius * 2, int(gsy) - self.radius * 2))
        super().draw(surface, cam)


class EliteSentinel(ArtilleryEnemy):
    _BARRAGE_CD = 2.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp *= _ELITE_HP
        self.hp = self.max_hp
        self.damage *= _ELITE_DMG
        self.radius = int(self.radius * _ELITE_RAD)
        self.xp_drop = int(self.xp_drop * _ELITE_RWD)
        self.gold_drop = int(self.gold_drop * _ELITE_RWD)
        self.color = (210, 100, 255)
        self._shoot_timer = self._BARRAGE_CD * 0.5

    def _ai(self, dt: float, player) -> None:
        super()._ai(dt, player)
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self._BARRAGE_CD
            self._shoot_at_player(player, 285, self.damage * 0.85, (230, 140, 255), spread=0.8, count=7, shape="bolt", radius=7.5, life=4.2)
            particles.burst(self.x, self.y, (220, 150, 255), count=12, speed=50, life=0.3, size=4)


_NORMAL_MAP: dict[str, type] = {
    "zombie": ZombieEnemy,
    "speeder": SpeederEnemy,
    "lancer": LancerEnemy,
    "wisp": WispEnemy,
    "slime_large": SlimeEnemy,
    "slime_medium": SlimeEnemy,
    "slime_small": SlimeEnemy,
    "blackhole_mage": BlackHoleMage,
    "blink_skirmisher": BlinkSkirmisherEnemy,
    "embermine": EmbermineEnemy,
    "siege_pylon": SiegePylonEnemy,
    "razorbat": RazorbatEnemy,
    "brood_seeder": BroodSeederEnemy,
    "shield_caster": ShieldCasterEnemy,
    "line_raider": LineRaiderEnemy,
    "tank": TankEnemy,
    "wizard": WizardEnemy,
    "exploder": ExploderEnemy,
    "gunner": GunnerEnemy,
    "artillery": ArtilleryEnemy,
    "geometric_devourer": GeometricDevourerBoss,
    "storm_tyrant": StormTyrantBoss,
    "void_colossus": VoidColossusBoss,
}

_ELITE_MAP: dict[str, type] = {
    "elite_summoner": EliteSummoner,
    "elite_berserker": EliteBerserker,
    "elite_assassin": EliteAssassin,
    "elite_sentinel": EliteSentinel,
    "elite_missile_sniper": EliteMissileSniper,
}

ALL_ENEMY_TYPES = list(_NORMAL_MAP.keys())
ALL_ELITE_TYPES = list(_ELITE_MAP.keys())


def create_enemy(etype: str, x: float, y: float, difficulty: int = 1, **kwargs) -> Enemy:
    cls = _NORMAL_MAP.get(etype) or _ELITE_MAP.get(etype)
    if cls is None:
        raise ValueError(f"Unknown enemy type: {etype}")
    if cls is SlimeEnemy:
        if etype == "slime_large":
            kwargs.setdefault("size", "large")
        elif etype == "slime_medium":
            kwargs.setdefault("size", "medium")
        else:
            kwargs.setdefault("size", "small")
    clean_kwargs = {key: value for key, value in kwargs.items() if value is not None}
    return cls(x, y, difficulty, **clean_kwargs)
