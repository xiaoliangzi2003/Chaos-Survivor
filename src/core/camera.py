"""摄像机：世界坐标 ↔ 屏幕坐标转换，支持震屏。"""

import math
import random
import pygame
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    def __init__(self) -> None:
        # 摄像机在世界坐标中心目标
        self.x: float = 0.0
        self.y: float = 0.0

        # 震屏状态
        self._shake_timer:     float = 0.0    # 剩余震屏时间（秒）
        self._shake_intensity: float = 0.0    # 震屏强度（px）
        self._shake_offset:    tuple[float, float] = (0.0, 0.0)

        # 半屏偏移（常量，避免重复计算）
        self._hw = SCREEN_WIDTH  / 2
        self._hh = SCREEN_HEIGHT / 2

    # ── 每帧更新 ──────────────────────────────────────
    def update(self, target_x: float, target_y: float, dt: float) -> None:
        """将摄像机中心对准目标点（通常是玩家）。"""
        self.x = target_x
        self.y = target_y

        # 震屏更新
        if self._shake_timer > 0:
            self._shake_timer -= dt
            decay = max(0.0, self._shake_timer / max(self._shake_timer + dt, 0.001))
            strength = self._shake_intensity * decay
            self._shake_offset = (
                random.uniform(-strength, strength),
                random.uniform(-strength, strength),
            )
        else:
            self._shake_offset = (0.0, 0.0)

    # ── 坐标转换 ──────────────────────────────────────
    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """世界坐标 → 屏幕坐标。"""
        sx = (wx - self.x) + self._hw + self._shake_offset[0]
        sy = (wy - self.y) + self._hh + self._shake_offset[1]
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """屏幕坐标 → 世界坐标。"""
        wx = (sx - self._hw - self._shake_offset[0]) + self.x
        wy = (sy - self._hh - self._shake_offset[1]) + self.y
        return wx, wy

    # ── 可见性裁剪 ────────────────────────────────────
    def is_visible(self, wx: float, wy: float, radius: float = 0) -> bool:
        """粗略判断世界坐标点是否在屏幕可见区域内（含 margin）。"""
        sx, sy = self.world_to_screen(wx, wy)
        margin = radius + 64
        return (-margin <= sx <= SCREEN_WIDTH  + margin and
                -margin <= sy <= SCREEN_HEIGHT + margin)

    # ── 震屏触发 ──────────────────────────────────────
    def shake(self, duration_ms: int, intensity: float) -> None:
        """触发震屏。duration_ms 毫秒，intensity 像素幅度。"""
        duration_s = duration_ms / 1000.0
        # 取最强的那次，不叠加
        if intensity >= self._shake_intensity or self._shake_timer <= 0:
            self._shake_timer     = duration_s
            self._shake_intensity = intensity


# 全局单例
camera = Camera()
