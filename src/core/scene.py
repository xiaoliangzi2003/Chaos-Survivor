"""场景基类：所有游戏场景（菜单、战斗、结算等）继承此类。"""

import pygame
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.game import Game


class Scene:
    """
    每个场景实现三个方法：
      handle_event(event)  — 处理单个 pygame 事件
      update(dt)           — 逻辑更新，dt 为帧时间（秒）
      draw(surface)        — 渲染到 surface
    场景切换通过 self.game.set_scene(name, **kwargs) 实现。
    """

    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_enter(self, **kwargs) -> None:
        """场景激活时调用（携带来自上一场景的参数）。"""
        pass

    def on_exit(self) -> None:
        """场景失活时调用。"""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        pass
