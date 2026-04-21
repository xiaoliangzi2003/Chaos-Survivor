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


class Enemy(Entity):
    HIT_FLASH = 0.08

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
        if self._slow_timer > 0:
            shapes.ring(surface, (100, 170, 255), sx, sy, self.radius + 4, 2)
        self._draw_hp_bar(surface, sx, sy)

    def _draw_shadow(self, surface: pygame.Surface, sx: float, sy: float) -> None:
        shadow = pygame.Surface((int(self.radius * 4), int(self.radius * 2.2)), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 65), shadow.get_rect())
        surface.blit(shadow, (int(sx - shadow.get_width() / 2), int(sy + self.radius * 0.6)))

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
        "large": {"hp": 68, "speed": 52, "damage": 12, "radius": 26, "xp": 7, "gold": 3, "children": ("medium", 3)},
        "medium": {"hp": 30, "speed": 72, "damage": 8, "radius": 18, "xp": 4, "gold": 1, "children": ("small", 3)},
        "small": {"hp": 12, "speed": 102, "damage": 5, "radius": 11, "xp": 2, "gold": 0, "children": None},
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
    _CAST_CD = 5.0

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
            self.pending_hazards.append(
                {
                    "kind": "black_hole",
                    "x": player.x + rng.uniform(-90, 90),
                    "y": player.y + rng.uniform(-90, 90),
                    "life": 4.8,
                    "pull_radius": 220,
                    "damage_radius": 36,
                    "pull_strength": 220,
                    "dps": self.damage * 1.6,
                    "color": (110, 90, 220),
                }
            )
            particles.burst(self.x, self.y, (140, 110, 255), count=10, speed=60, life=0.3, size=4)

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


class StormTyrantBoss(Enemy):
    _BASE = dict(max_hp=1600, speed=78, damage=20, radius=38, color=(255, 95, 165), xp_drop=90, gold_drop=28, knockback_resist=0.9)
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
    _BASE = dict(max_hp=1850, speed=62, damage=24, radius=44, color=(90, 120, 255), xp_drop=110, gold_drop=34, knockback_resist=0.92)
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
                self.pending_spawns.append(("zombie", sx, sy))
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
    "tank": TankEnemy,
    "wizard": WizardEnemy,
    "exploder": ExploderEnemy,
    "gunner": GunnerEnemy,
    "artillery": ArtilleryEnemy,
    "storm_tyrant": StormTyrantBoss,
    "void_colossus": VoidColossusBoss,
}

_ELITE_MAP: dict[str, type] = {
    "elite_summoner": EliteSummoner,
    "elite_berserker": EliteBerserker,
    "elite_assassin": EliteAssassin,
    "elite_sentinel": EliteSentinel,
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
