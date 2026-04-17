"""武器基类 + 公用工具函数。"""

import math
import pygame
from src.core.rng              import rng
from src.systems.damage_numbers import damage_numbers


# ─────────────────────────────────────────────────────
#  公用工具
# ─────────────────────────────────────────────────────

def nearest_enemy(px: float, py: float,
                  enemies: list,
                  max_range: float = float("inf")):
    """返回距 (px,py) 最近的存活敌人，超出 max_range 返回 None。"""
    best      = None
    best_sq   = max_range * max_range
    for e in enemies:
        if not e.alive:
            continue
        dx = e.x - px;  dy = e.y - py
        d2 = dx*dx + dy*dy
        if d2 < best_sq:
            best_sq = d2
            best    = e
    return best


def enemies_in_radius(px: float, py: float,
                      enemies: list,
                      radius: float) -> list:
    """返回以 (px,py) 为中心、radius 半径内所有存活敌人。"""
    r2 = radius * radius
    out = []
    for e in enemies:
        if not e.alive:
            continue
        dx = e.x - px;  dy = e.y - py
        if dx*dx + dy*dy <= r2:
            out.append(e)
    return out


def apply_weapon_damage(enemy, damage: float, player,
                        source_x: float, source_y: float,
                        kb_force: float = 130.0) -> tuple[bool, float, bool]:
    """
    对敌人造成武器伤害（含暴击判定）。
    返回 (killed, actual_damage, is_crit)。
    """
    is_crit = rng.chance(player.stats.crit_rate)
    actual  = damage * player.stats.atk_mul
    if is_crit:
        actual *= player.stats.crit_mul
    angle  = math.atan2(enemy.y - source_y, enemy.x - source_x)
    killed = enemy.take_damage(actual, angle, kb_force)
    damage_numbers.add(enemy.x, enemy.y - enemy.radius - 6,
                       actual, is_crit=is_crit)
    player.total_damage_dealt += actual
    return killed, actual, is_crit


# ─────────────────────────────────────────────────────
#  武器基类
# ─────────────────────────────────────────────────────

class Weapon:
    """
    所有武器继承此类。
    update() 每帧由 BattleScene 调用，传入战场上下文。
    draw()   渲染持久视觉效果（闪电弧、新星环等）。
    """

    NAME        = "武器"
    DESCRIPTION = ""
    ICON_COLOR  = (200, 200, 200)
    MAX_LEVEL   = 8

    # 子类需定义 8 级数据列表，每项为 dict
    LEVEL_DATA: list[dict] = []

    def __init__(self) -> None:
        self.level:  int   = 1
        self._timer: float = 0.0   # 冷却计时（倒数到 0 触发）
        self._player_ref = None     # 每帧 update() 时刷新
        self._apply_level()

    # ── 对外接口 ──────────────────────────────────────
    def update(self, dt: float, player, enemies: list,
               grid, proj_system) -> None:
        self._player_ref = player
        eff_cd = self._cooldown / max(0.1, player.stats.atk_speed_mul)
        self._timer -= dt
        if self._timer <= 0:
            self._timer = eff_cd
            self._fire(player, enemies, grid, proj_system)

    def draw(self, surface: pygame.Surface, cam) -> None:
        pass

    def level_up(self) -> bool:
        """升级，返回 True 表示升级成功（未满级）。"""
        if self.level >= self.MAX_LEVEL:
            return False
        self.level += 1
        self._apply_level()
        return True

    # ── 子类重写 ──────────────────────────────────────
    def _apply_level(self) -> None:
        """从 LEVEL_DATA 读取当前级别数据并赋值到属性。"""
        if self.LEVEL_DATA:
            data = self.LEVEL_DATA[self.level - 1]
            for k, v in data.items():
                setattr(self, k, v)

    def _fire(self, player, enemies: list, grid, proj_system) -> None:
        pass

    # ── 武器属性缩写（子类用） ────────────────────────
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
