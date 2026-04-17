"""
敌人实体：5 种普通 + 3 种精英，含 AI、受击反馈、击退、死亡粒子。

普通敌人
  ZombieEnemy   — 绿色圆形，直线追击
  SpeederEnemy  — 黄色三角，高速冲刺
  TankEnemy     — 钢蓝方块，缓慢高 HP
  WizardEnemy   — 紫色菱形，保持距离 / 占位射击
  ExploderEnemy — 红色圆，靠近引爆

精英敌人（4× HP / 2× 伤害 / 3× 奖励）
  EliteSummoner  — 超级僵尸，每 5s 召唤 3 只小僵尸
  EliteBerserker — 超级重甲，HP<50% 进入暴怒
  EliteAssassin  — 超级速行者，每 4s 瞬移至玩家身后
"""

import math
import pygame

from src.core.config      import DIFFICULTY_SETTINGS
from src.core.rng         import rng
from src.entities.entity  import Entity
from src.render           import shapes
from src.render.particles import particles

# ── 精英倍率 ──────────────────────────────────────────
_E_HP   = 4.0
_E_DMG  = 2.0
_E_RWD  = 3.0    # 经验 / 金币倍率
_E_RAD  = 1.35   # 半径倍率

# ── 击退衰减 ──────────────────────────────────────────
_KB_DECAY = 9.0  # 每秒衰减系数（越大越快停下）


# ═════════════════════════════════════════════════════
#  基类
# ═════════════════════════════════════════════════════

class Enemy(Entity):
    """所有敌人共用逻辑：移动、受伤、白闪、击退、死亡。"""

    COLOR     = (180, 180, 180)
    HIT_FLASH = 0.08    # 受击白闪时长（秒）

    def __init__(self, x: float, y: float,
                 max_hp: float, speed: float, damage: float,
                 radius: float, color: tuple,
                 xp_drop: int, gold_drop: int,
                 knockback_resist: float = 0.0) -> None:
        super().__init__(x, y, radius)
        self.max_hp           = max_hp
        self.hp               = max_hp
        self.speed            = speed
        self.damage           = damage
        self.color            = color
        self.xp_drop          = xp_drop
        self.gold_drop        = gold_drop
        self.knockback_resist = knockback_resist

        self.vx: float = 0.0
        self.vy: float = 0.0
        self.kb_vx: float = 0.0
        self.kb_vy: float = 0.0

        self._flash_timer: float = 0.0
        self.pending_spawns: list[tuple[str, float, float]] = []

    # ── 受伤 ──────────────────────────────────────────
    def take_damage(self, amount: float,
                    angle: float = 0.0,
                    kb_force: float = 150.0) -> bool:
        """
        返回 True = 本次击杀。
        angle: 击退方向（弧度，从伤害来源指向敌人）。
        """
        self.hp -= amount
        self._flash_timer = self.HIT_FLASH

        # 击退
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
        particles.burst(self.x, self.y, self.color,
                        count=14, speed=90, life=0.55, size=5, gravity=40)

    # ── 每帧更新 ──────────────────────────────────────
    def update(self, dt: float, player) -> None:
        if not self.alive:
            return
        self.pending_spawns.clear()

        # 击退衰减
        decay = max(0.0, 1.0 - _KB_DECAY * dt)
        self.kb_vx *= decay
        self.kb_vy *= decay

        # 白闪倒计时
        if self._flash_timer > 0:
            self._flash_timer = max(0.0, self._flash_timer - dt)

        # AI（子类重写）
        self._ai(dt, player)

        # 位移
        self.x += (self.vx + self.kb_vx) * dt
        self.y += (self.vy + self.kb_vy) * dt

    def _ai(self, dt: float, player) -> None:
        """默认 AI：直线追玩家。"""
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.vx = dx / dist * self.speed
            self.vy = dy / dist * self.speed

    # ── 绘制 ──────────────────────────────────────────
    def draw(self, surface: pygame.Surface, cam) -> None:
        if not cam.is_visible(self.x, self.y, self.radius + 4):
            return
        sx, sy = cam.world_to_screen(self.x, self.y)
        flash = self._flash_timer > 0
        self._draw_shape(surface, sx, sy, flash)
        self._draw_hp_bar(surface, sx, sy)

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        col = (255, 255, 255) if flash else self.color
        shapes.circle(surface, col, sx, sy, self.radius)

    def _draw_hp_bar(self, surface: pygame.Surface,
                     sx: float, sy: float) -> None:
        if self.hp >= self.max_hp:
            return
        bw = self.radius * 2
        bh = 4
        bx = sx - self.radius
        by = sy - self.radius - 8
        shapes.bar(surface, bx, by, bw, bh,
                   self.hp, self.max_hp,
                   (220, 60, 60), (60, 20, 20))

    # ── 工具 ──────────────────────────────────────────
    def dir_to_player(self, player) -> tuple[float, float]:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        return (dx / dist, dy / dist) if dist > 0 else (0.0, 0.0)


# ═════════════════════════════════════════════════════
#  普通敌人
# ═════════════════════════════════════════════════════

class ZombieEnemy(Enemy):
    """绿色圆形僵尸：直线追击，基础单位。"""
    _BASE = dict(max_hp=30,  speed=80,  damage=8,
                 radius=14,  color=(55, 185, 55),
                 xp_drop=2,  gold_drop=1,  knockback_resist=0.0)

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d  = DIFFICULTY_SETTINGS[difficulty]
        b  = self._BASE
        super().__init__(x, y,
            max_hp=b["max_hp"] * d["hp_mul"],
            speed=b["speed"],
            damage=b["damage"] * d["dmg_mul"],
            radius=b["radius"],
            color=b["color"],
            xp_drop=max(1, int(b["xp_drop"] * d["reward_mul"])),
            gold_drop=b["gold_drop"],
            knockback_resist=b["knockback_resist"])

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        col  = (255, 255, 255) if flash else self.color
        dark = (20, 80, 20)   if not flash else (200, 200, 200)
        shapes.circle(surface, col, sx, sy, self.radius)
        shapes.circle(surface, col, sx, sy, self.radius, width=2)
        # 眼睛
        eo = self.radius * 0.35
        er = max(2, int(self.radius * 0.18))
        shapes.circle(surface, dark, sx - eo, sy - eo * 0.3, er)
        shapes.circle(surface, dark, sx + eo, sy - eo * 0.3, er)
        # 顶部锯齿（3 根刺）
        for i in range(-1, 2):
            bx = sx + i * self.radius * 0.35
            shapes.line(surface, dark,
                        bx, sy - self.radius,
                        bx, sy - self.radius - 5, 2)


class SpeederEnemy(Enemy):
    """黄色三角速行者：平时慢走，每 3s 发动冲刺。"""
    _BASE = dict(max_hp=18,  speed=85,  damage=6,
                 radius=11,  color=(220, 210, 35),
                 xp_drop=3,  gold_drop=1,  knockback_resist=0.0)

    _CHARGE_SPEED    = 340.0
    _CHARGE_INTERVAL = 3.0
    _CHARGE_DUR      = 0.55

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y,
            max_hp=b["max_hp"] * d["hp_mul"],
            speed=b["speed"],
            damage=b["damage"] * d["dmg_mul"],
            radius=b["radius"], color=b["color"],
            xp_drop=max(1, int(b["xp_drop"] * d["reward_mul"])),
            gold_drop=b["gold_drop"],
            knockback_resist=b["knockback_resist"])
        self._charge_cd   = self._CHARGE_INTERVAL * 0.5
        self._charge_timer = 0.0
        self._charging     = False
        self._cdx = self._cdy = 0.0

    def _ai(self, dt: float, player) -> None:
        self._charge_cd -= dt
        px, py = player.x, player.y
        dx = px - self.x;  dy = py - self.y
        dist = math.hypot(dx, dy)

        if self._charging:
            self._charge_timer += dt
            if self._charge_timer >= self._CHARGE_DUR:
                self._charging = False
                self._charge_cd = self._CHARGE_INTERVAL
            self.vx = self._cdx * self._CHARGE_SPEED
            self.vy = self._cdy * self._CHARGE_SPEED
        else:
            if self._charge_cd <= 0 and dist < 350 and dist > 0:
                self._charging = True
                self._charge_timer = 0.0
                self._cdx = dx / dist
                self._cdy = dy / dist
            elif dist > 0:
                self.vx = dx / dist * self.speed
                self.vy = dy / dist * self.speed

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        angle = math.atan2(self.vy or self.kb_vy, self.vx or self.kb_vx)
        r = self.radius
        col = (255, 255, 255) if flash else self.color
        # 朝运动方向的三角形
        pts = [
            (sx + math.cos(angle) * r * 1.2,
             sy + math.sin(angle) * r * 1.2),
            (sx + math.cos(angle + 2.4) * r,
             sy + math.sin(angle + 2.4) * r),
            (sx + math.cos(angle - 2.4) * r,
             sy + math.sin(angle - 2.4) * r),
        ]
        shapes.polygon(surface, col, pts)
        # 冲刺时画速度线
        if self._charging and not flash:
            for i in range(1, 4):
                tx = sx - math.cos(angle) * r * i * 0.55
                ty = sy - math.sin(angle) * r * i * 0.55
                a  = max(30, 100 - i * 30)
                pygame.draw.circle(surface, (*self.color, a),
                                   (int(tx), int(ty)), max(1, r - i * 2))


class TankEnemy(Enemy):
    """钢蓝方块：缓慢但高 HP 高伤害，强力击退抗性。"""
    _BASE = dict(max_hp=120, speed=45, damage=22,
                 radius=20,  color=(90, 115, 155),
                 xp_drop=8,  gold_drop=3,  knockback_resist=0.6)

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y,
            max_hp=b["max_hp"] * d["hp_mul"],
            speed=b["speed"],
            damage=b["damage"] * d["dmg_mul"],
            radius=b["radius"], color=b["color"],
            xp_drop=max(1, int(b["xp_drop"] * d["reward_mul"])),
            gold_drop=b["gold_drop"],
            knockback_resist=b["knockback_resist"])
        self._angle = 0.0

    def update(self, dt: float, player) -> None:
        self._angle += dt * 0.8
        super().update(dt, player)

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        col  = (255, 255, 255) if flash else self.color
        dark = (50, 65, 90)   if not flash else (200, 200, 200)
        r = self.radius
        a = self._angle
        # 外方块（旋转）
        shapes.regular_polygon(surface, col,  sx, sy, r,     4, a)
        shapes.regular_polygon(surface, dark, sx, sy, r,     4, a,    width=2)
        shapes.regular_polygon(surface, dark, sx, sy, r*0.5, 4, a + math.pi/4)


class WizardEnemy(Enemy):
    """紫色菱形巫师：保持距离绕行，预留远程射击接口。"""
    _BASE = dict(max_hp=40,  speed=60,  damage=12,
                 radius=13,  color=(165, 55, 225),
                 xp_drop=5,  gold_drop=2,  knockback_resist=0.0)

    _IDEAL_DIST  = 210.0
    _SHOOT_CD    = 2.5

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y,
            max_hp=b["max_hp"] * d["hp_mul"],
            speed=b["speed"],
            damage=b["damage"] * d["dmg_mul"],
            radius=b["radius"], color=b["color"],
            xp_drop=max(1, int(b["xp_drop"] * d["reward_mul"])),
            gold_drop=b["gold_drop"],
            knockback_resist=b["knockback_resist"])
        self._shoot_timer = self._SHOOT_CD * 0.4
        self._orb_angle   = 0.0
        # 阶段 5 填充：射击回调 / 返回投射物请求

    def update(self, dt: float, player) -> None:
        self._orb_angle = (self._orb_angle + dt * 2.5) % (math.pi * 2)
        super().update(dt, player)

    def _ai(self, dt: float, player) -> None:
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        ideal = self._IDEAL_DIST

        if dist < ideal * 0.75 and dist > 0:          # 太近：后退
            self.vx = -dx / dist * self.speed
            self.vy = -dy / dist * self.speed
        elif dist > ideal * 1.4 and dist > 0:          # 太远：靠近
            self.vx =  dx / dist * self.speed * 0.6
            self.vy =  dy / dist * self.speed * 0.6
        elif dist > 0:                                  # 绕行
            perp = math.atan2(dy, dx) + math.pi / 2
            self.vx = math.cos(perp) * self.speed * 0.45
            self.vy = math.sin(perp) * self.speed * 0.45

        # 射击计时（占位，阶段 5 补充实际投射物）
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self._SHOOT_CD
            # 视觉反馈
            particles.directional(self.x, self.y,
                math.atan2(player.y - self.y, player.x - self.x),
                0.25, (200, 90, 255), count=4, speed=25, life=0.2, size=4)

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        r   = self.radius
        col = (255, 255, 255) if flash else self.color
        lit = (210, 130, 255) if not flash else (255, 255, 255)
        # 菱形主体
        shapes.diamond(surface, col, sx, sy, r, r * 1.25)
        shapes.diamond(surface, lit, sx, sy, r, r * 1.25, width=2)
        # 内圆
        shapes.circle(surface, lit, sx, sy, r * 0.38)
        # 环绕小球（阶段 5 将由武器系统接管）
        if not flash:
            for i in range(3):
                a  = self._orb_angle + i * math.pi * 2 / 3
                ox = sx + math.cos(a) * r * 1.45
                oy = sy + math.sin(a) * r * 1.45
                shapes.circle(surface, lit, ox, oy, 3)


class ExploderEnemy(Enemy):
    """红色自爆体：靠近玩家后引爆，范围伤害。"""
    _BASE = dict(max_hp=25,  speed=95,  damage=45,
                 radius=15,  color=(225, 55, 55),
                 xp_drop=4,  gold_drop=2,  knockback_resist=0.0)

    _ARM_DIST    = 85.0     # 开始倒计时的距离
    _FUSE_TIME   = 1.4      # 引爆倒计时（秒）
    _BLAST_RANGE = 130.0    # 爆炸范围

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        d = DIFFICULTY_SETTINGS[difficulty]
        b = self._BASE
        super().__init__(x, y,
            max_hp=b["max_hp"] * d["hp_mul"],
            speed=b["speed"],
            damage=b["damage"] * d["dmg_mul"],
            radius=b["radius"], color=b["color"],
            xp_drop=max(1, int(b["xp_drop"] * d["reward_mul"])),
            gold_drop=b["gold_drop"],
            knockback_resist=b["knockback_resist"])
        self._fuse  = 0.0
        self._armed = False
        self._pulse = 0.0
        self._player_ref = None   # 爆炸时需要引用

    def _ai(self, dt: float, player) -> None:
        self._player_ref = player
        self._pulse = (self._pulse + dt * (6 if self._armed else 2)) % (math.pi * 2)
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)

        if dist < self._ARM_DIST:
            self._armed = True
            self.vx = self.vy = 0.0
            self._fuse += dt
            if self._fuse >= self._FUSE_TIME:
                self._explode(player)
        else:
            self._armed = False
            self._fuse  = 0.0
            if dist > 0:
                self.vx = dx / dist * self.speed
                self.vy = dy / dist * self.speed

    def _explode(self, player) -> None:
        dx  = player.x - self.x
        dy  = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self._BLAST_RANGE:
            factor = 1.0 - dist / self._BLAST_RANGE
            player.take_damage(self.damage * factor, self.x, self.y)
        particles.burst(self.x, self.y, (255, 120, 30),
                        count=28, speed=160, life=0.75, size=8, gravity=50)
        particles.burst(self.x, self.y, (255, 50, 50),
                        count=18, speed=220, life=0.5,  size=5)
        self.alive = False

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        r   = self.radius
        col = (255, 255, 255) if flash else self.color
        shapes.circle(surface, col, sx, sy, r)
        if not flash:
            # 脉冲扩散圈
            rings = 3 if self._armed else 2
            for i in range(rings):
                phase   = (self._pulse + i * math.pi * 2 / rings) % (math.pi * 2)
                ring_r  = r + 6 + math.sin(phase) * (10 if self._armed else 5)
                alpha_i = int(180 * (1 - math.sin(phase) * 0.5))
                if self._armed:
                    ring_col = (255, 80, 30)
                else:
                    ring_col = self.color
                shapes.ring(surface, ring_col, sx, sy, ring_r, 2)
            # 倒计时弧
            if self._armed and self._FUSE_TIME > 0:
                progress = self._fuse / self._FUSE_TIME
                end_angle = int(-90 + 360 * progress)
                pygame.draw.arc(surface, (255, 255, 80),
                                pygame.Rect(int(sx)-r, int(sy)-r, r*2, r*2),
                                math.radians(-90), math.radians(end_angle), 3)


# ═════════════════════════════════════════════════════
#  精英敌人
# ═════════════════════════════════════════════════════

class EliteSummoner(ZombieEnemy):
    """超级僵尸：每 5 秒召唤 3 只小僵尸。"""

    _SUMMON_CD    = 5.0
    _SUMMON_COUNT = 3

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp    *= _E_HP;   self.hp = self.max_hp
        self.damage    *= _E_DMG
        self.radius     = int(self.radius * _E_RAD)
        self.xp_drop    = int(self.xp_drop  * _E_RWD)
        self.gold_drop  = int(self.gold_drop * _E_RWD)
        self.speed     *= 0.8
        self.color      = (20, 150, 30)
        self._summon_cd = self._SUMMON_CD * 0.5
        self._anim      = 0.0

    def update(self, dt: float, player) -> None:
        self._anim = (self._anim + dt * 2) % (math.pi * 2)
        super().update(dt, player)

    def _ai(self, dt: float, player) -> None:
        super()._ai(dt, player)
        self._summon_cd -= dt
        if self._summon_cd <= 0:
            self._summon_cd = self._SUMMON_CD
            for i in range(self._SUMMON_COUNT):
                a  = math.pi * 2 * i / self._SUMMON_COUNT
                sx = self.x + math.cos(a) * self.radius * 3
                sy = self.y + math.sin(a) * self.radius * 3
                self.pending_spawns.append(("zombie", sx, sy))
            particles.burst(self.x, self.y, self.color,
                            count=10, speed=45, life=0.5, size=4)

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        super()._draw_shape(surface, sx, sy, flash)
        if not flash:
            # 皇冠光圈
            shapes.ring(surface, (80, 255, 100),
                        sx, sy - self.radius - 6,
                        self.radius * 0.7, 2)
            for i in range(3):
                a  = self._anim + i * math.pi * 2 / 3
                cx = sx + math.cos(a) * self.radius * 0.7
                cy = sy - self.radius - 6 + math.sin(a) * self.radius * 0.5
                shapes.circle(surface, (80, 255, 100), cx, cy, 3)


class EliteBerserker(TankEnemy):
    """超级重甲：HP < 50% 进入暴怒，速度翻倍，颜色变红。"""

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp   *= _E_HP;   self.hp = self.max_hp
        self.damage   *= _E_DMG
        self.radius    = int(self.radius * _E_RAD)
        self.xp_drop   = int(self.xp_drop  * _E_RWD)
        self.gold_drop = int(self.gold_drop * _E_RWD)
        self.knockback_resist = 0.85
        self.color     = (70, 90, 130)
        self._base_speed = self.speed
        self._rage_timer = 0.0

    @property
    def enraged(self) -> bool:
        return self.hp / self.max_hp < 0.5

    def update(self, dt: float, player) -> None:
        if self.enraged:
            self.speed = self._base_speed * 2.0
            self._rage_timer = (self._rage_timer + dt * 5) % (math.pi * 2)
            # 偶发怒焰粒子
            if rng.chance(dt * 3):
                particles.sparkle(self.x, self.y,
                                   (255, 50, 20), count=2, radius=self.radius)
        else:
            self.speed = self._base_speed
        super().update(dt, player)

    def _draw_shape(self, surface: pygame.Surface,
                    sx: float, sy: float, flash: bool) -> None:
        col = (255, 255, 255) if flash else (
            (200, 50, 30) if self.enraged else self.color)
        dark = (50, 65, 90) if not self.enraged else (140, 20, 10)
        r = self.radius
        a = self._angle
        shapes.regular_polygon(surface, col,  sx, sy, r,     4, a)
        shapes.regular_polygon(surface, dark, sx, sy, r,     4, a, width=2)
        shapes.regular_polygon(surface, dark, sx, sy, r*0.5, 4, a + math.pi/4)
        # 暴怒时画尖刺
        if self.enraged and not flash:
            for i in range(4):
                sa = a + i * math.pi / 2
                tip_x = sx + math.cos(sa) * r * 1.55
                tip_y = sy + math.sin(sa) * r * 1.55
                shapes.line(surface, (255, 80, 20),
                            sx + math.cos(sa) * r,
                            sy + math.sin(sa) * r,
                            tip_x, tip_y, 3)


class EliteAssassin(SpeederEnemy):
    """超级速行者：每 4s 瞬移至玩家背后，留下残影。"""

    _TELEPORT_CD   = 4.0
    _BEHIND_DIST   = 55.0

    def __init__(self, x: float, y: float, difficulty: int = 1) -> None:
        super().__init__(x, y, difficulty)
        self.max_hp   *= _E_HP;   self.hp = self.max_hp
        self.damage   *= _E_DMG
        self.radius    = int(self.radius * _E_RAD)
        self.xp_drop   = int(self.xp_drop  * _E_RWD)
        self.gold_drop = int(self.gold_drop * _E_RWD)
        self.speed    *= 1.3
        self.color     = (120, 30, 200)
        self._tp_cd    = self._TELEPORT_CD * 0.3
        self._ghosts: list[tuple[float, float, float]] = []   # (x, y, alpha)

    def update(self, dt: float, player) -> None:
        self._tp_cd -= dt
        # 残影衰减
        self._ghosts = [(gx, gy, a - dt * 300)
                        for gx, gy, a in self._ghosts if a > 20]
        if self._tp_cd <= 0:
            self._teleport(player)
            self._tp_cd = self._TELEPORT_CD
        super().update(dt, player)
        # 高速时留下残影
        spd = math.hypot(self.vx, self.vy)
        if spd > 200 and rng.chance(dt * 10):
            self._ghosts.append((self.x, self.y, 180))

    def _teleport(self, player) -> None:
        behind = player._facing + math.pi
        tx = player.x + math.cos(behind) * self._BEHIND_DIST
        ty = player.y + math.sin(behind) * self._BEHIND_DIST
        self._ghosts.append((self.x, self.y, 200))
        self.x, self.y = tx, ty
        self.kb_vx = self.kb_vy = 0
        particles.burst(tx, ty, self.color,
                        count=8, speed=55, life=0.3, size=4)

    def draw(self, surface: pygame.Surface, cam) -> None:
        # 先画残影
        for gx, gy, ga in self._ghosts:
            if not cam.is_visible(gx, gy, self.radius):
                continue
            gsx, gsy = cam.world_to_screen(gx, gy)
            ghost_surf = pygame.Surface(
                (self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(ghost_surf, (*self.color, int(ga)),
                               (self.radius * 2, self.radius * 2), self.radius)
            surface.blit(ghost_surf,
                         (int(gsx) - self.radius * 2, int(gsy) - self.radius * 2))
        super().draw(surface, cam)


# ═════════════════════════════════════════════════════
#  工厂函数
# ═════════════════════════════════════════════════════

_NORMAL_MAP: dict[str, type] = {
    "zombie":   ZombieEnemy,
    "speeder":  SpeederEnemy,
    "tank":     TankEnemy,
    "wizard":   WizardEnemy,
    "exploder": ExploderEnemy,
}

_ELITE_MAP: dict[str, type] = {
    "elite_summoner":  EliteSummoner,
    "elite_berserker": EliteBerserker,
    "elite_assassin":  EliteAssassin,
}

ALL_ENEMY_TYPES  = list(_NORMAL_MAP.keys())
ALL_ELITE_TYPES  = list(_ELITE_MAP.keys())


def create_enemy(etype: str, x: float, y: float,
                 difficulty: int = 1) -> Enemy:
    """工厂函数：按类型名创建敌人。"""
    cls = _NORMAL_MAP.get(etype) or _ELITE_MAP.get(etype)
    if cls is None:
        raise ValueError(f"未知敌人类型: {etype}")
    return cls(x, y, difficulty)
