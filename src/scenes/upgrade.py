"""升级选择场景（阶段 9 完整实现，此处为骨架）。"""

import pygame
from src.core.scene  import Scene
from src.core.config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GOLD
from src.ui.fonts    import get_font


class UpgradeScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self._font  = get_font(48)
        self._small = get_font(28)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.pop_scene()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        msg = self._font.render("升级选择 — 待实现（阶段 9）", True, GOLD)
        surface.blit(msg, msg.get_rect(centerx=SCREEN_WIDTH//2, centery=SCREEN_HEIGHT//2))
