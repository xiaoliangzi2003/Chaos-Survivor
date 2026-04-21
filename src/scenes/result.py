"""结算场景。"""

from __future__ import annotations

import pygame

from src.core.config import DIFFICULTY_NAMES, GOLD, RED, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font


class ResultScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._title_font = get_font(72, bold=True)
        self._body_font = get_font(32)
        self._small_font = get_font(24)
        self.victory = kwargs.get("victory", False)
        self.stats = kwargs.get("stats", {})
        self.restart_kwargs = kwargs.get("restart_kwargs", {})

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.game.set_scene("battle", **self.restart_kwargs)
            elif event.key == pygame.K_ESCAPE:
                self.game.set_scene("menu", difficulty=self.restart_kwargs.get("difficulty", 1))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.game.set_scene("menu", difficulty=self.restart_kwargs.get("difficulty", 1))

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((10, 5, 20))

        center_x = SCREEN_WIDTH // 2
        label = "胜利" if self.victory else "失败"
        color = GOLD if self.victory else RED
        title = self._title_font.render(label, True, color)
        surface.blit(title, title.get_rect(centerx=center_x, y=100))

        stats_rect = pygame.Rect(center_x - 280, 220, 560, 320)
        pygame.draw.rect(surface, (25, 25, 38), stats_rect, border_radius=16)
        pygame.draw.rect(surface, color, stats_rect, 3, border_radius=16)

        for idx, (key, value) in enumerate(self._rows()):
            y = stats_rect.y + 26 + idx * 42
            key_surf = self._body_font.render(key, True, (190, 190, 210))
            value_surf = self._body_font.render(value, True, WHITE)
            surface.blit(key_surf, (stats_rect.x + 26, y))
            surface.blit(value_surf, value_surf.get_rect(right=stats_rect.right - 26, y=y))

        hint = self._small_font.render("按 R 重新开始，按 ESC 返回主菜单", True, (170, 170, 190))
        surface.blit(hint, hint.get_rect(centerx=center_x, y=SCREEN_HEIGHT - 70))

    def _rows(self) -> list[tuple[str, str]]:
        total_time = self.stats.get("time", 0)
        minutes = int(total_time) // 60
        seconds = int(total_time) % 60
        difficulty = DIFFICULTY_NAMES[self.stats.get("difficulty", 1)]
        return [
            ("波次", str(self.stats.get("wave", 0))),
            ("生存时间", f"{minutes:02d}:{seconds:02d}"),
            ("击杀数", str(self.stats.get("kills", 0))),
            ("造成伤害", str(int(self.stats.get("damage_dealt", 0)))),
            ("受到伤害", str(int(self.stats.get("damage_taken", 0)))),
            ("最终等级", str(self.stats.get("level", 1))),
            ("金币", str(self.stats.get("gold", 0))),
            ("难度", difficulty),
        ]
