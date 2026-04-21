"""升级选择场景。"""

from __future__ import annotations

import pygame

from src.core.config import SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font, wrap_text


class UpgradeScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._title_font = get_font(52, bold=True)
        self._card_font = get_font(28, bold=True)
        self._body_font = get_font(22)
        self._small_font = get_font(18)
        self._options = kwargs.get("options", [])
        self._on_select = kwargs.get("on_select")
        self._selected = 0
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 185))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._selected = (self._selected - 1) % len(self._options)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._selected = (self._selected + 1) % len(self._options)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self._pick(0)
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(self._options) > 1:
                self._pick(1)
            elif event.key in (pygame.K_3, pygame.K_KP3) and len(self._options) > 2:
                self._pick(2)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._pick(self._selected)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pick(self._selected)

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        for idx, rect in enumerate(self._card_rects()):
            if rect.collidepoint(mx, my):
                self._selected = idx

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))

        title = self._title_font.render("升级选择", True, (255, 220, 80))
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=90))

        subtitle = self._body_font.render("请选择一项强化", True, WHITE)
        surface.blit(subtitle, subtitle.get_rect(centerx=SCREEN_WIDTH // 2, y=150))

        for idx, (option, rect) in enumerate(zip(self._options, self._card_rects())):
            border = option.color
            fill = (28, 28, 40) if idx != self._selected else (42, 42, 60)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, border, rect, 3, border_radius=14)

            badge = self._small_font.render(option.rarity_label, True, border)
            surface.blit(badge, (rect.x + 18, rect.y + 16))

            title = self._card_font.render(option.title, True, WHITE)
            surface.blit(title, (rect.x + 18, rect.y + 50))

            desc = wrap_text(self._body_font, option.description, rect.width - 36, max_lines=4)
            for line_idx, line in enumerate(desc):
                text = self._body_font.render(line, True, (220, 220, 230))
                surface.blit(text, (rect.x + 18, rect.y + 100 + line_idx * 28))

            bottom = self._small_font.render(f"按 {idx + 1} 选择", True, (170, 170, 200))
            surface.blit(bottom, (rect.x + 18, rect.bottom - 34))

    def _pick(self, index: int) -> None:
        if not (0 <= index < len(self._options)):
            return
        if self._on_select:
            self._on_select(self._options[index])
        self.game.pop_scene()

    def _card_rects(self) -> list[pygame.Rect]:
        card_w = 320
        card_h = 250
        gap = 24
        total_w = card_w * len(self._options) + gap * (len(self._options) - 1)
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        rects = []
        for idx in range(len(self._options)):
            rects.append(pygame.Rect(start_x + idx * (card_w + gap), 230, card_w, card_h))
        return rects
