"""Gameplay settings scene."""

from __future__ import annotations

import pygame

from src.core.config import SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.gameplay_settings import SETTING_DEFINITIONS, adjust_setting, get_settings, reset_settings
from src.core.scene import Scene
from src.ui.fonts import get_font, wrap_text


class SettingsScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._title_font = get_font(52, bold=True)
        self._row_font = get_font(21, bold=True)
        self._body_font = get_font(18)
        self._small_font = get_font(17)
        self._hint_font = get_font(16)
        self._settings = get_settings()
        self._selected = 0
        self._message = "设置会自动保存，新开的一局会立即按当前配置生效。"

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(SETTING_DEFINITIONS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(SETTING_DEFINITIONS)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._change_selected(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._change_selected(1)
            elif event.key == pygame.K_r:
                self._settings = reset_settings()
                self._message = "已恢复默认配置。"
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.game.pop_scene()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = self.game.get_mouse_pos()
            if event.button == 1:
                if self._back_button().collidepoint(mx, my):
                    self.game.pop_scene()
                    return
                if self._reset_button().collidepoint(mx, my):
                    self._settings = reset_settings()
                    self._message = "已恢复默认配置。"
                    return
                for idx, rect in enumerate(self._row_rects()):
                    if rect.collidepoint(mx, my):
                        self._selected = idx
                        minus_rect, plus_rect = self._adjust_buttons(rect)
                        if minus_rect.collidepoint(mx, my):
                            self._change_selected(-1)
                        elif plus_rect.collidepoint(mx, my):
                            self._change_selected(1)
                        return
            elif event.button == 4:
                self._change_selected(1)
            elif event.button == 5:
                self._change_selected(-1)

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        for idx, rect in enumerate(self._row_rects()):
            if rect.collidepoint(mx, my):
                self._selected = idx
                break

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((8, 10, 22))
        self._draw_backdrop(surface)

        title = self._title_font.render("战斗配置", True, (255, 226, 110))
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=22))

        subtitle = self._body_font.render("调整数值倍率，打造你想要的刷怪节奏与成长曲线。", True, WHITE)
        surface.blit(subtitle, subtitle.get_rect(centerx=SCREEN_WIDTH // 2, y=78))

        selected = SETTING_DEFINITIONS[self._selected]
        detail = f"{selected.description} 默认值 {selected.default:.2f}x"
        for line_idx, line in enumerate(wrap_text(self._small_font, detail, 1060, max_lines=2)):
            text = self._small_font.render(line, True, (175, 192, 225))
            surface.blit(text, text.get_rect(centerx=SCREEN_WIDTH // 2, y=108 + line_idx * 20))

        message = self._small_font.render(self._message, True, (220, 230, 255))
        surface.blit(message, message.get_rect(centerx=SCREEN_WIDTH // 2, y=148))

        panel = pygame.Rect(118, 168, 1044, 474)
        pygame.draw.rect(surface, (18, 24, 40), panel, border_radius=20)
        pygame.draw.rect(surface, (82, 96, 138), panel, 2, border_radius=20)

        for idx, (meta, rect) in enumerate(zip(SETTING_DEFINITIONS, self._row_rects())):
            selected_row = idx == self._selected
            fill = (44, 54, 88) if selected_row else (24, 30, 48)
            border = (255, 214, 90) if selected_row else (90, 108, 156)
            pygame.draw.rect(surface, fill, rect, border_radius=12)
            pygame.draw.rect(surface, border, rect, 2, border_radius=12)

            label = self._row_font.render(meta.label, True, WHITE)
            surface.blit(label, label.get_rect(midleft=(rect.x + 18, rect.centery)))

            value = getattr(self._settings, meta.key)
            value_text = self._row_font.render(f"{value:.2f}x", True, (255, 232, 132))
            surface.blit(value_text, value_text.get_rect(center=(rect.right - 154, rect.centery)))

            minus_rect, plus_rect = self._adjust_buttons(rect)
            self._draw_adjust_button(surface, minus_rect, "-", selected_row)
            self._draw_adjust_button(surface, plus_rect, "+", selected_row)

        self._draw_action_button(surface, self._reset_button(), "恢复默认 (R)", (80, 185, 255))
        self._draw_action_button(surface, self._back_button(), "返回菜单", (255, 200, 100))

        footer = self._hint_font.render("上下选择，左右调整，鼠标也可点击加减按钮。", True, (170, 180, 210))
        surface.blit(footer, footer.get_rect(centerx=SCREEN_WIDTH // 2, y=700))

    def _change_selected(self, direction: int) -> None:
        meta = SETTING_DEFINITIONS[self._selected]
        value = adjust_setting(meta.key, direction)
        self._message = f"{meta.label} 已调整为 {value:.2f}x。"

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        for idx in range(6):
            radius = 110 + idx * 46
            alpha = max(18, 54 - idx * 6)
            ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (60, 120, 220, alpha), (ring.get_width() // 2, ring.get_height() // 2), radius, 2)
            surface.blit(ring, (SCREEN_WIDTH - radius * 2 - 80, -radius * 0.35))

        glow = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 180, 70, 24), (210, 210), 180)
        pygame.draw.circle(glow, (80, 150, 255, 20), (260, 240), 150)
        surface.blit(glow, (42, 320))

    def _draw_adjust_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, selected_row: bool) -> None:
        fill = (76, 94, 138) if selected_row else (48, 58, 90)
        border = (255, 214, 90) if selected_row else (120, 136, 180)
        pygame.draw.rect(surface, fill, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)
        text = self._row_font.render(label, True, WHITE)
        surface.blit(text, text.get_rect(center=rect.center))

    def _draw_action_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, border_color: tuple[int, int, int]) -> None:
        pygame.draw.rect(surface, (28, 36, 60), rect, border_radius=12)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=12)
        text = self._body_font.render(label, True, WHITE)
        surface.blit(text, text.get_rect(center=rect.center))

    def _row_rects(self) -> list[pygame.Rect]:
        start_y = 182
        row_h = 36
        gap = 6
        return [pygame.Rect(132, start_y + idx * (row_h + gap), 1016, row_h) for idx in range(len(SETTING_DEFINITIONS))]

    def _adjust_buttons(self, rect: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
        minus_rect = pygame.Rect(rect.right - 84, rect.y + 4, 28, 28)
        plus_rect = pygame.Rect(rect.right - 42, rect.y + 4, 28, 28)
        return minus_rect, plus_rect

    def _reset_button(self) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH // 2 - 212, 652, 180, 40)

    def _back_button(self) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH // 2 + 32, 652, 180, 40)
