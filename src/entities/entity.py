"""实体基类：所有游戏对象（玩家、敌人、投射物）的公共接口。"""

import pygame
from src.core.camera import Camera


class Entity:
    """
    最小公共接口。子类按需重写 update / draw。
    碰撞均用圆形，radius 为碰撞半径。
    """

    def __init__(self, x: float, y: float, radius: float) -> None:
        self.x:      float = x
        self.y:      float = y
        self.radius: float = radius
        self.alive:  bool  = True

    # ── 碰撞工具 ──────────────────────────────────────
    def dist_sq_to(self, other: "Entity") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def collides_with(self, other: "Entity") -> bool:
        min_dist = self.radius + other.radius
        return self.dist_sq_to(other) < min_dist * min_dist

    def collides_point(self, px: float, py: float) -> bool:
        dx = self.x - px
        dy = self.y - py
        return dx * dx + dy * dy < self.radius * self.radius

    # ── 帧接口 ────────────────────────────────────────
    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        pass
