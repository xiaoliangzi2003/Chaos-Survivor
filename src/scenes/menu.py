"""主菜单场景。"""

from __future__ import annotations

import pygame

from src.core.config import DIFFICULTY_NAMES, GOLD, GRAY, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font


class MenuScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._font_title = get_font(80, bold=True)
        self._font_item = get_font(42)
        self._font_small = get_font(28)
        self._items = ["开始游戏", "难度", "显示模式", "退出游戏"]
        self._selected = 0
        self._difficulty = kwargs.get("difficulty", getattr(self, "_difficulty", 1))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._items)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_selected(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_selected(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate()

    def _adjust_selected(self, delta: int) -> None:
        item = self._items[self._selected]
        if item == "难度":
            self._difficulty = (self._difficulty + delta) % len(DIFFICULTY_NAMES)
        elif item == "显示模式":
            self.game.toggle_fullscreen(delta > 0 if delta != 0 else None)

    def _activate(self) -> None:
        choice = self._items[self._selected]
        if choice == "开始游戏":
            self.game.set_scene("battle", difficulty=self._difficulty)
        elif choice == "难度":
            self._difficulty = (self._difficulty + 1) % len(DIFFICULTY_NAMES)
        elif choice == "显示模式":
            self.game.toggle_fullscreen()
        else:
            self.game.running = False

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        center_x = SCREEN_WIDTH // 2
        for idx, _ in enumerate(self._items):
            y = 320 + idx * 68
            rect = pygame.Rect(center_x - 220, y - 24, 440, 48)
            if rect.collidepoint(mx, my):
                self._selected = idx

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((10, 10, 20))

        title = self._font_title.render("幸存者 3.0", True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=130))

        subtitle = self._font_small.render("单局闭环试玩版", True, GRAY)
        surface.blit(subtitle, subtitle.get_rect(centerx=SCREEN_WIDTH // 2, y=220))

        for idx, item in enumerate(self._items):
            y = 320 + idx * 68
            color = GOLD if idx == self._selected else WHITE
            label = item
            if item == "难度":
                label = f"难度：{DIFFICULTY_NAMES[self._difficulty]}"
            elif item == "显示模式":
                label = f"显示模式：{self.game.display_mode_label()}"
            text = self._font_item.render(label, True, color)
            surface.blit(text, text.get_rect(centerx=SCREEN_WIDTH // 2, y=y))
            if idx == self._selected:
                pygame.draw.polygon(
                    surface,
                    GOLD,
                    [
                        (SCREEN_WIDTH // 2 - 250, y + 14),
                        (SCREEN_WIDTH // 2 - 235, y + 7),
                        (SCREEN_WIDTH // 2 - 235, y + 21),
                    ],
                )

        hint = self._font_small.render("方向键或 WASD 选择，回车确认，F11 也可切换全屏", True, (110, 110, 140))
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 56))
