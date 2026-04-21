"""暂停场景。"""

from __future__ import annotations

import pygame

from src.core.config import GOLD, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font


class PauseScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._font_title = get_font(64, bold=True)
        self._font_item = get_font(42)
        self._items = ["继续战斗", "返回主菜单", "退出游戏"]
        self._selected = 0
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 160))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.pop_scene()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate()

    def _activate(self) -> None:
        choice = self._items[self._selected]
        if choice == "继续战斗":
            self.game.pop_scene()
        elif choice == "返回主菜单":
            self.game.set_scene("menu")
        else:
            self.game.running = False

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        cx = SCREEN_WIDTH // 2
        for idx in range(len(self._items)):
            y = 340 + idx * 60
            rect = pygame.Rect(cx - 160, y - 20, 320, 40)
            if rect.collidepoint(mx, my):
                self._selected = idx

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        title = self._font_title.render("已暂停", True, GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=240))

        for idx, item in enumerate(self._items):
            y = 340 + idx * 60
            color = GOLD if idx == self._selected else WHITE
            text = self._font_item.render(item, True, color)
            surface.blit(text, text.get_rect(centerx=cx, y=y))
