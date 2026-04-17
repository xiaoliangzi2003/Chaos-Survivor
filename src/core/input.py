"""输入管理器：统一处理键盘和鼠标状态，避免各处直接调用 pygame.key.get_pressed。"""

import pygame
from typing import Tuple


class InputManager:
    """每帧调用 update() 后，可通过属性查询当前帧输入状态。"""

    def __init__(self) -> None:
        self._keys_held:    frozenset[int] = frozenset()
        self._keys_down:    frozenset[int] = frozenset()   # 本帧刚按下
        self._keys_up:      frozenset[int] = frozenset()   # 本帧刚抬起
        self._mouse_pos:    Tuple[int, int] = (0, 0)
        self._mouse_held:   tuple[bool, ...] = (False, False, False)
        self._mouse_down:   set[int] = set()
        self._mouse_up:     set[int] = set()

    # ── 每帧调用 ──────────────────────────────────────
    def update(self, events: list[pygame.event.Event]) -> None:
        pressed = pygame.key.get_pressed()
        new_held: set[int] = {k for k in range(len(pressed)) if pressed[k]}

        self._keys_down = frozenset(new_held - self._keys_held)
        self._keys_up   = frozenset(self._keys_held - new_held)
        self._keys_held = frozenset(new_held)

        self._mouse_pos  = pygame.mouse.get_pos()
        self._mouse_held = pygame.mouse.get_pressed()
        self._mouse_down.clear()
        self._mouse_up.clear()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_down.add(event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._mouse_up.add(event.button)

    # ── 键盘查询 ──────────────────────────────────────
    def held(self, key: int) -> bool:
        """持续按住。"""
        return key in self._keys_held

    def just_pressed(self, key: int) -> bool:
        """本帧刚按下。"""
        return key in self._keys_down

    def just_released(self, key: int) -> bool:
        """本帧刚抬起。"""
        return key in self._keys_up

    # ── 方向向量（归一化） ────────────────────────────
    @property
    def move_vector(self) -> Tuple[float, float]:
        dx = dy = 0
        if self.held(pygame.K_a) or self.held(pygame.K_LEFT):  dx -= 1
        if self.held(pygame.K_d) or self.held(pygame.K_RIGHT): dx += 1
        if self.held(pygame.K_w) or self.held(pygame.K_UP):    dy -= 1
        if self.held(pygame.K_s) or self.held(pygame.K_DOWN):  dy += 1
        length = (dx*dx + dy*dy) ** 0.5
        if length > 0:
            dx /= length
            dy /= length
        return (dx, dy)

    # ── 鼠标查询 ──────────────────────────────────────
    @property
    def mouse_pos(self) -> Tuple[int, int]:
        return self._mouse_pos

    def mouse_held(self, button: int = 1) -> bool:
        """button: 1=左键, 2=中键, 3=右键"""
        idx = button - 1
        return self._mouse_held[idx] if idx < len(self._mouse_held) else False

    def mouse_just_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_down

    def mouse_just_released(self, button: int = 1) -> bool:
        return button in self._mouse_up


# 全局单例
input_mgr = InputManager()
