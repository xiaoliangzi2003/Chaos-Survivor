"""粒子系统：带对象池，支持多种效果类型。"""

import math
import random
import pygame
from src.core.config import MAX_PARTICLES
from src.core.camera import Camera


class Particle:
    """单个粒子（直接操作字段，避免 dataclass 开销）。"""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "r", "g", "b", "size", "gravity", "drag", "alive")

    def __init__(self) -> None:
        self.alive = False

    def init(self, x: float, y: float, vx: float, vy: float,
             life: float, color: tuple[int, int, int], size: float,
             gravity: float = 0.0, drag: float = 0.96) -> None:
        self.x, self.y   = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.r, self.g, self.b = color[0], color[1], color[2]
        self.size    = size
        self.gravity = gravity
        self.drag    = drag
        self.alive   = True


class ParticleSystem:
    """
    全局粒子系统单例。
    使用固定大小对象池（避免 GC 压力）。
    """

    def __init__(self, max_particles: int = MAX_PARTICLES) -> None:
        self._pool:  list[Particle] = [Particle() for _ in range(max_particles)]
        self._active: list[Particle] = []
        self._free_idx: int = 0          # 轮询式分配

    # ── 发射接口 ──────────────────────────────────────

    def emit(self, x: float, y: float,
             vx: float, vy: float,
             life: float,
             color: tuple[int, int, int],
             size: float = 4.0,
             gravity: float = 0.0,
             drag: float = 0.96) -> None:
        """发射单个粒子。"""
        if len(self._active) >= len(self._pool):
            return  # 池已满，丢弃

        # 找到一个空闲粒子
        p = self._pool[self._free_idx % len(self._pool)]
        self._free_idx += 1
        if p.alive:
            return  # 当前槽还活着，放弃（极低概率）

        p.init(x, y, vx, vy, life, color, size, gravity, drag)
        self._active.append(p)

    def burst(self, x: float, y: float,
              color: tuple[int, int, int],
              count: int = 12,
              speed: float = 80.0,
              life: float = 0.5,
              size: float = 4.0,
              gravity: float = 60.0,
              spread: float = math.pi * 2) -> None:
        """向四周爆发发射粒子（受击/死亡特效）。"""
        for i in range(count):
            angle = random.uniform(0, spread)
            spd   = random.uniform(speed * 0.5, speed)
            self.emit(
                x, y,
                math.cos(angle) * spd,
                math.sin(angle) * spd,
                life * random.uniform(0.6, 1.4),
                color,
                random.uniform(size * 0.5, size),
                gravity,
            )

    def directional(self, x: float, y: float,
                    angle: float, spread: float,
                    color: tuple[int, int, int],
                    count: int = 6,
                    speed: float = 60.0,
                    life: float = 0.35,
                    size: float = 3.0) -> None:
        """定向发射（击退方向、枪口焰等）。"""
        for _ in range(count):
            a   = angle + random.uniform(-spread / 2, spread / 2)
            spd = random.uniform(speed * 0.4, speed)
            self.emit(x, y, math.cos(a) * spd, math.sin(a) * spd,
                      life, color, size)

    def sparkle(self, x: float, y: float,
                color: tuple[int, int, int],
                count: int = 5,
                radius: float = 12.0) -> None:
        """升级/拾取光点。"""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            r     = random.uniform(0, radius)
            self.emit(
                x + math.cos(angle) * r,
                y + math.sin(angle) * r,
                random.uniform(-15, 15),
                random.uniform(-40, -10),
                random.uniform(0.4, 0.8),
                color, random.uniform(2, 5),
            )

    # ── 更新 & 绘制 ───────────────────────────────────

    def update(self, dt: float) -> None:
        keep: list[Particle] = []
        for p in self._active:
            p.life -= dt
            if p.life <= 0:
                p.alive = False
                continue
            p.vx *= p.drag
            p.vy *= p.drag
            p.vy += p.gravity * dt
            p.x  += p.vx * dt
            p.y  += p.vy * dt
            keep.append(p)
        self._active = keep

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        for p in self._active:
            sx, sy = cam.world_to_screen(p.x, p.y)
            # 离屏剔除
            if sx < -20 or sx > surface.get_width() + 20:
                continue
            if sy < -20 or sy > surface.get_height() + 20:
                continue
            # 按生命衰减透明度和大小
            ratio = p.life / p.max_life
            alpha = int(255 * ratio)
            size  = max(1, int(p.size * ratio))
            # 直接画实心圆（最快）
            pygame.draw.circle(
                surface,
                (p.r, p.g, p.b, alpha) if alpha < 255 else (p.r, p.g, p.b),
                (int(sx), int(sy)),
                size,
            )

    def clear(self) -> None:
        for p in self._active:
            p.alive = False
        self._active.clear()

    @property
    def count(self) -> int:
        return len(self._active)


# 全局单例
particles = ParticleSystem()
