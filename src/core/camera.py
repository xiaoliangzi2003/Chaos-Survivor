"""摄像机：负责世界坐标到屏幕坐标转换，并支持边界限制与震屏。"""

from __future__ import annotations

import random

from src.core.config import SCREEN_HEIGHT, SCREEN_WIDTH


class Camera:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0

        self._shake_timer = 0.0
        self._shake_intensity = 0.0
        self._shake_offset = (0.0, 0.0)

        self._hw = SCREEN_WIDTH / 2
        self._hh = SCREEN_HEIGHT / 2

    def update(self, target_x: float, target_y: float, dt: float, bounds: tuple[float, float, float, float] | None = None) -> None:
        self.x = target_x
        self.y = target_y

        if bounds is not None:
            left, top, right, bottom = bounds
            self.x = _clamp(self.x, left + self._hw, right - self._hw)
            self.y = _clamp(self.y, top + self._hh, bottom - self._hh)

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

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        sx = (wx - self.x) + self._hw + self._shake_offset[0]
        sy = (wy - self.y) + self._hh + self._shake_offset[1]
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        wx = (sx - self._hw - self._shake_offset[0]) + self.x
        wy = (sy - self._hh - self._shake_offset[1]) + self.y
        return wx, wy

    def is_visible(self, wx: float, wy: float, radius: float = 0) -> bool:
        sx, sy = self.world_to_screen(wx, wy)
        margin = radius + 64
        return -margin <= sx <= SCREEN_WIDTH + margin and -margin <= sy <= SCREEN_HEIGHT + margin

    def shake(self, duration_ms: int, intensity: float) -> None:
        duration_s = duration_ms / 1000.0
        if intensity >= self._shake_intensity or self._shake_timer <= 0:
            self._shake_timer = duration_s
            self._shake_intensity = intensity


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        return (minimum + maximum) * 0.5
    return max(minimum, min(maximum, value))


camera = Camera()
