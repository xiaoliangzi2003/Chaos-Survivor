"""战斗场景（阶段 1 骨架，后续阶段逐步填充）。"""

import pygame
from src.core.scene  import Scene
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GOLD, DARK_GRAY
from src.ui.fonts    import get_font


class BattleScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self.difficulty = kwargs.get("difficulty", 1)
        self._font      = get_font(40)
        self._small     = get_font(28)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.push_scene("pause")

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((20, 30, 20))   # 暂时深绿色占位

        msg = self._font.render("战斗场景 — 占位（阶段 3+ 实现）", True, WHITE)
        surface.blit(msg, msg.get_rect(centerx=SCREEN_WIDTH//2, centery=SCREEN_HEIGHT//2 - 30))

        hint = self._small.render("ESC = 暂停", True, GOLD)
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH//2, centery=SCREEN_HEIGHT//2 + 20))

        diff = self._small.render(f"难度: {self.difficulty}", True, (180, 180, 180))
        surface.blit(diff, (20, 20))
