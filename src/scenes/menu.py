"""主菜单场景（阶段 1 骨架，阶段 10 完整实现）。"""

import pygame
from src.core.scene  import Scene
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GOLD, GRAY
from src.ui.fonts    import get_font


class MenuScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self._font_title  = get_font(80, bold=True)
        self._font_item   = get_font(46)
        self._font_small  = get_font(28)

        self._menu_items  = ["开始游戏", "选择难度", "设置", "退出"]
        self._selected    = 0
        self._difficulty  = kwargs.get("difficulty", 1)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._menu_items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._menu_items)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate()

    def _activate(self) -> None:
        choice = self._menu_items[self._selected]
        if choice == "开始游戏":
            self.game.set_scene("battle", difficulty=self._difficulty)
        elif choice == "退出":
            self.game.running = False

    def update(self, dt: float) -> None:
        # 鼠标悬停高亮
        mx, my = pygame.mouse.get_pos()
        cx = SCREEN_WIDTH // 2
        for i, item in enumerate(self._menu_items):
            y = 320 + i * 60
            rect = pygame.Rect(cx - 150, y - 22, 300, 44)
            if rect.collidepoint(mx, my):
                self._selected = i

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((10, 10, 20))

        # 标题
        title = self._font_title.render("SURVIVOR 3.0", True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH//2, y=140))

        subtitle = self._font_small.render("几何幸存者 — Roguelike Bullet Heaven", True, GRAY)
        surface.blit(subtitle, subtitle.get_rect(centerx=SCREEN_WIDTH//2, y=230))

        # 菜单项
        cx = SCREEN_WIDTH // 2
        for i, item in enumerate(self._menu_items):
            y = 320 + i * 60
            color = GOLD if i == self._selected else WHITE
            text  = self._font_item.render(item, True, color)
            surface.blit(text, text.get_rect(centerx=cx, y=y))
            if i == self._selected:
                # 选中指示符
                pygame.draw.polygon(surface, GOLD, [
                    (cx - 160, y + 14),
                    (cx - 148, y + 8),
                    (cx - 148, y + 20),
                ])

        # 版本号
        ver = self._font_small.render("v0.1 — 阶段 1", True, (60, 60, 80))
        surface.blit(ver, (10, SCREEN_HEIGHT - 26))
