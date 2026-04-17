"""玩家实体：属性、移动、受伤、经验、金币、死亡系统。"""

import math
import pygame

from src.core.config  import (PLAYER_DEFAULT, xp_to_next_level,
                               COLOR_HP_BAR, COLOR_HP_BG,
                               COLOR_XP_BAR, COLOR_XP_BG,
                               SCREEN_WIDTH, SCREEN_HEIGHT)
from src.core.input   import input_mgr
from src.core.camera  import Camera
from src.core.rng     import rng
from src.entities.entity  import Entity
from src.render       import shapes
from src.render.particles import particles


# ── 玩家外观常量 ──────────────────────────────────────
_RADIUS       = 16
_COLOR_BODY   = (80,  160, 255)
_COLOR_RING   = (150, 210, 255)
_COLOR_CORE   = (220, 240, 255)
_COLOR_ARROW  = (255, 255, 255)
_COLOR_LOW_HP = (255, 60,  60)
_IFRAMES_DUR  = 0.7    # 受伤无敌帧时长（秒）
_LOW_HP_RATIO = 0.35   # HP 低于此比例触发警示


class PlayerStats:
    """可在运行时动态修改的玩家属性容器。"""

    def __init__(self) -> None:
        d = PLAYER_DEFAULT
        self.max_hp:        float = d["max_hp"]
        self.hp_regen:      float = d["hp_regen"]
        self.speed:         float = d["speed"]
        self.pickup_radius: float = d["pickup_radius"]
        self.crit_rate:     float = d["crit_rate"]
        self.crit_mul:      float = d["crit_mul"]
        self.dodge_rate:    float = d["dodge_rate"]
        self.atk_mul:       float = d["atk_mul"]
        self.atk_speed_mul: float = d["atk_speed_mul"]
        self.proj_bonus:    int   = d["proj_bonus"]
        self.range_mul:     float = d["range_mul"]
        self.xp_mul:        float = d["xp_mul"]
        self.gold_mul:      float = d["gold_mul"]
        self.armor:         float = d["armor"]

    def copy(self) -> "PlayerStats":
        ps = PlayerStats.__new__(PlayerStats)
        ps.__dict__.update(self.__dict__)
        return ps


class Player(Entity):

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        super().__init__(x, y, _RADIUS)

        # ── 属性 ──────────────────────────────────────
        self.stats = PlayerStats()
        self.hp:   float = self.stats.max_hp
        self.xp:   float = 0.0
        self.level: int  = 1
        self.gold: int   = 0
        self.xp_to_next: int = xp_to_next_level(1)

        # ── 运动 ──────────────────────────────────────
        self.vx: float = 0.0
        self.vy: float = 0.0
        self._facing: float = 0.0   # 朝向角度（弧度），0 = 右

        # ── 武器 / 被动槽（后续阶段填充） ────────────
        self.weapons:  list = []
        self.passives: list = []

        # ── 受伤状态 ──────────────────────────────────
        self._iframes:       float = 0.0   # 剩余无敌时间
        self._hit_flash:     float = 0.0   # 白闪计时（视觉）
        self._hit_flash_max: float = 0.12
        self.screen_flash:   float = 0.0   # 屏幕红边强度（0–1，由 battle 读取）
        self.just_leveled:   bool  = False  # 本帧升级标志
        self.dead_timer:     float = 0.0   # 死亡动画计时

        # ── 统计 ──────────────────────────────────────
        self.kills:               int   = 0
        self.total_damage_dealt:  float = 0.0
        self.total_damage_taken:  float = 0.0
        self.survive_time:        float = 0.0

        # ── 视觉辅助 ──────────────────────────────────
        self._pulse: float = 0.0     # 用于 HP 低时脉冲动画

    # ── 每帧逻辑 ──────────────────────────────────────

    def update(self, dt: float) -> None:
        if not self.alive:
            self._update_death(dt)
            return

        self.survive_time += dt
        self._pulse        = (self._pulse + dt * 4) % (math.pi * 2)

        # 移动
        dx, dy = input_mgr.move_vector
        spd = self.stats.speed
        self.vx = dx * spd
        self.vy = dy * spd
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 朝向（有移动时才更新）
        if dx != 0 or dy != 0:
            self._facing = math.atan2(dy, dx)

        # HP 自然回复
        if self.stats.hp_regen > 0:
            self.hp = min(self.stats.max_hp,
                          self.hp + self.stats.hp_regen * dt)

        # 无敌帧倒计时
        if self._iframes > 0:
            self._iframes -= dt
        if self._hit_flash > 0:
            self._hit_flash -= dt

        # 屏幕红边衰减
        if self.screen_flash > 0:
            self.screen_flash = max(0.0, self.screen_flash - dt * 2.5)

        # 升级标志清除
        self.just_leveled = False

        # 武器更新（阶段 5 填充）
        for w in self.weapons:
            w.update(dt, self)

    def _update_death(self, dt: float) -> None:
        self.dead_timer += dt

    # ── 受伤 / 治疗 ───────────────────────────────────

    def take_damage(self, raw_dmg: float,
                    source_x: float | None = None,
                    source_y: float | None = None) -> float:
        """
        受伤入口。返回实际扣除血量（0 表示闪避或无敌）。
        source_x/y 用于击退粒子方向。
        """
        if not self.alive:
            return 0.0
        if self._iframes > 0:
            return 0.0

        # 闪避判定
        if rng.chance(self.stats.dodge_rate):
            self._spawn_dodge_effect()
            return 0.0

        # 护甲减伤（最低 1 点）
        actual = max(1.0, raw_dmg - self.stats.armor)
        self.hp -= actual
        self.total_damage_taken += actual

        # 受伤反馈
        self._iframes   = _IFRAMES_DUR
        self._hit_flash = self._hit_flash_max
        self.screen_flash = min(1.0, self.screen_flash + 0.6)

        # 受击粒子
        sx = source_x if source_x is not None else self.x
        sy = source_y if source_y is not None else self.y
        angle = math.atan2(self.y - sy, self.x - sx)
        particles.directional(self.x, self.y, angle, math.pi * 0.6,
                               (255, 100, 100), count=8, speed=90, life=0.35)

        if self.hp <= 0:
            self.hp = 0
            self._die()

        return actual

    def heal(self, amount: float) -> float:
        """治疗，返回实际回复量。"""
        before = self.hp
        self.hp = min(self.stats.max_hp, self.hp + amount)
        healed = self.hp - before
        if healed > 0:
            particles.sparkle(self.x, self.y, (80, 255, 120),
                               count=6, radius=20)
        return healed

    # ── 经验 / 金币 ───────────────────────────────────

    def gain_xp(self, amount: float) -> bool:
        """
        获取经验值。
        返回 True 表示本次调用发生了升级。
        """
        self.xp += amount * self.stats.xp_mul
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp          -= self.xp_to_next
            self.level        += 1
            self.xp_to_next   = xp_to_next_level(self.level)
            leveled            = True
            self.just_leveled  = True
            self._on_level_up()
        return leveled

    def gain_gold(self, amount: int) -> None:
        self.gold += max(1, int(amount * self.stats.gold_mul))

    def _on_level_up(self) -> None:
        # 升级光效
        particles.burst(self.x, self.y, (255, 220, 50),
                        count=20, speed=100, life=0.7, size=5)
        particles.sparkle(self.x, self.y, (255, 255, 120),
                          count=12, radius=30)

    # ── 死亡 ──────────────────────────────────────────

    def _die(self) -> None:
        self.alive = False
        particles.burst(self.x, self.y, _COLOR_BODY,
                        count=30, speed=120, life=1.0, size=6, gravity=80)
        particles.burst(self.x, self.y, (255, 255, 255),
                        count=15, speed=60,  life=0.6, size=3)

    def _spawn_dodge_effect(self) -> None:
        particles.sparkle(self.x, self.y, (200, 200, 255),
                          count=5, radius=22)

    # ── 绘制 ──────────────────────────────────────────

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        sx, sy = cam.world_to_screen(self.x, self.y)

        # 离屏剔除
        if not cam.is_visible(self.x, self.y, self.radius + 10):
            return

        if not self.alive:
            self._draw_death(surface, sx, sy)
            return

        # 无敌帧闪烁：奇数帧半透明
        is_iframes = self._iframes > 0
        if is_iframes and (int(self._iframes * 12) % 2 == 0):
            return

        # 白闪遮罩（受击瞬间）
        flash = self._hit_flash > 0

        # ── 拾取范围虚线圈（低透明度） ────────────────
        pr = self.stats.pickup_radius
        _draw_dashed_circle(surface, (80, 130, 200, 60), sx, sy, pr, 16)

        # ── 低 HP 警示脉冲圈 ──────────────────────────
        if self.hp / self.stats.max_hp < _LOW_HP_RATIO:
            pulse_r = self.radius + 6 + math.sin(self._pulse) * 4
            shapes.ring(surface, _COLOR_LOW_HP, sx, sy, pulse_r, 2)

        # ── 外发光圈（移动时更亮） ────────────────────
        moving = abs(self.vx) > 5 or abs(self.vy) > 5
        glow_a = 80 if moving else 40
        shapes.glow_circle(surface, _COLOR_RING, sx, sy,
                            self.radius, layers=2, alpha_start=glow_a)

        # ── 主体圆 ────────────────────────────────────
        body_color = (255, 255, 255) if flash else _COLOR_BODY
        shapes.circle(surface, body_color, sx, sy, self.radius)

        # ── 内圈高光 ──────────────────────────────────
        if not flash:
            shapes.circle(surface, _COLOR_RING, sx, sy, self.radius, width=2)
            shapes.circle(surface, _COLOR_CORE, sx, sy, self.radius * 0.45)

        # ── 朝向箭头 ──────────────────────────────────
        if not flash:
            _draw_direction_arrow(surface, sx, sy, self._facing,
                                   self.radius, _COLOR_ARROW)

    def _draw_death(self, surface: pygame.Surface,
                    sx: float, sy: float) -> None:
        """死亡后玩家原地缩小消失。"""
        progress = min(1.0, self.dead_timer / 0.5)
        r = int(self.radius * (1 - progress))
        if r > 1:
            alpha = int(255 * (1 - progress))
            col   = (min(255, _COLOR_BODY[0] + 100),
                     _COLOR_BODY[1], _COLOR_BODY[2])
            shapes.circle(surface, col, sx, sy, r)


# ── 绘制辅助函数 ──────────────────────────────────────

def _draw_direction_arrow(surface: pygame.Surface,
                           sx: float, sy: float,
                           angle: float, radius: float,
                           color: tuple) -> None:
    """在玩家圆边缘绘制朝向小三角。"""
    tip_r  = radius + 8
    base_r = radius - 2
    tip_x  = sx + math.cos(angle) * tip_r
    tip_y  = sy + math.sin(angle) * tip_r
    perp   = angle + math.pi / 2
    hw     = 5
    b1x = sx + math.cos(angle) * base_r + math.cos(perp) * hw
    b1y = sy + math.sin(angle) * base_r + math.sin(perp) * hw
    b2x = sx + math.cos(angle) * base_r - math.cos(perp) * hw
    b2y = sy + math.sin(angle) * base_r - math.sin(perp) * hw
    shapes.polygon(surface, color, [(tip_x, tip_y), (b1x, b1y), (b2x, b2y)])


def _draw_dashed_circle(surface: pygame.Surface,
                         color: tuple, cx: float, cy: float,
                         radius: float, segments: int) -> None:
    """绘制虚线圆（拾取范围指示）。"""
    r, g, b = color[0], color[1], color[2]
    a = color[3] if len(color) > 3 else 255
    if a <= 0 or radius <= 0:
        return
    step = math.pi * 2 / segments
    for i in range(0, segments, 2):
        a1 = i * step
        a2 = a1 + step * 0.6
        x1 = cx + math.cos(a1) * radius
        y1 = cy + math.sin(a1) * radius
        x2 = cx + math.cos(a2) * radius
        y2 = cy + math.sin(a2) * radius
        pygame.draw.line(surface, (r, g, b), (int(x1), int(y1)), (int(x2), int(y2)), 1)
