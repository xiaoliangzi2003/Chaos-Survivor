"""结算场景（阶段 10 完整实现，此处为骨架）。"""

import pygame
from src.core.scene  import Scene
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GOLD, RED
from src.ui.fonts    import get_font


class ResultScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self._font       = get_font(72, bold=True)
        self._font_body  = get_font(36)
        self._font_small = get_font(28)
        self.victory     = kwargs.get("victory", False)
        self.stats       = kwargs.get("stats", {})

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.set_scene("battle")
            elif event.key == pygame.K_ESCAPE:
                self.game.set_scene("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.game.set_scene("menu")

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((10, 5, 20))

        cx = SCREEN_WIDTH // 2
        label = "胜利！" if self.victory else "阵亡"
        color = GOLD    if self.victory else RED
        title = self._font.render(label, True, color)
        surface.blit(title, title.get_rect(centerx=cx, y=180))

        hint = self._font_small.render("按 R 再来一局 / ESC 返回主菜单", True, (160, 160, 160))
        surface.blit(hint, hint.get_rect(centerx=cx, y=SCREEN_HEIGHT - 60))
