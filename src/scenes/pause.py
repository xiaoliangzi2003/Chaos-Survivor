"""暂停场景（覆盖层）。"""

import pygame
from src.core.scene  import Scene
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GOLD, GRAY, COLOR_UI_BG
from src.ui.fonts    import get_font


class PauseScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self._font_title = get_font(64, bold=True)
        self._font_item  = get_font(42)
        self._items      = ["继续游戏", "返回主菜单", "退出"]
        self._selected   = 0

        # 半透明遮罩 surface
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
        if choice == "继续游戏":
            self.game.pop_scene()
        elif choice == "返回主菜单":
            self.game.set_scene("menu")
        elif choice == "退出":
            self.game.running = False

    def update(self, dt: float) -> None:
        mx, my = pygame.mouse.get_pos()
        cx = SCREEN_WIDTH // 2
        for i in range(len(self._items)):
            y = 340 + i * 60
            rect = pygame.Rect(cx - 140, y - 20, 280, 40)
            if rect.collidepoint(mx, my):
                self._selected = i

    def draw(self, surface: pygame.Surface) -> None:
        # 覆盖层（下层场景已经画好）
        surface.blit(self._overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        title = self._font_title.render("暂  停", True, GOLD)
        surface.blit(title, title.get_rect(centerx=cx, y=240))

        for i, item in enumerate(self._items):
            y = 340 + i * 60
            color = GOLD if i == self._selected else WHITE
            text  = self._font_item.render(item, True, color)
            surface.blit(text, text.get_rect(centerx=cx, y=y))
