"""Enemy bestiary scene."""

from __future__ import annotations

import pygame

from src.core.bestiary import build_enemy_snapshot, list_bestiary_entries, render_enemy_portrait
from src.core.config import SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font, wrap_text

_CATEGORY_COLORS = {
    "小怪": (106, 198, 255),
    "精英": (255, 178, 82),
    "Boss": (255, 104, 138),
}


class BestiaryScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._entries = list_bestiary_entries()
        self._selected = 0
        self._scroll = 0
        self._visible_rows = 11

        self._title_font = get_font(50, bold=True)
        self._name_font = get_font(34, bold=True)
        self._row_font = get_font(20, bold=True)
        self._body_font = get_font(18)
        self._small_font = get_font(17)
        self._hint_font = get_font(16)

        self._portrait_cache: dict[str, pygame.Surface] = {}
        self._snapshot_cache: dict[str, object] = {}

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_selection(1)
            elif event.key == pygame.K_PAGEUP:
                self._move_selection(-self._visible_rows)
            elif event.key == pygame.K_PAGEDOWN:
                self._move_selection(self._visible_rows)
            elif event.key == pygame.K_HOME:
                self._selected = 0
                self._ensure_visible()
            elif event.key == pygame.K_END:
                self._selected = len(self._entries) - 1
                self._ensure_visible()
            elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_BACKSPACE):
                self.game.pop_scene()
        elif event.type == pygame.MOUSEWHEEL:
            self._move_selection(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.game.get_mouse_pos()
            if self._back_button().collidepoint(mx, my):
                self.game.pop_scene()
                return
            for index, rect in self._visible_row_rects():
                if rect.collidepoint(mx, my):
                    self._selected = index
                    self._ensure_visible()
                    return

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        for index, rect in self._visible_row_rects():
            if rect.collidepoint(mx, my):
                self._selected = index
                self._ensure_visible()
                break

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((8, 11, 23))
        self._draw_backdrop(surface)

        title = self._title_font.render("敌人图鉴", True, (255, 226, 118))
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=20))

        subtitle = self._body_font.render("查看所有小怪、精英与 Boss 的基础资料与程序绘制预览。", True, WHITE)
        surface.blit(subtitle, subtitle.get_rect(centerx=SCREEN_WIDTH // 2, y=74))

        self._draw_action_button(surface, self._back_button(), "返回菜单", (255, 214, 96))

        list_panel = pygame.Rect(40, 124, 328, 556)
        detail_panel = pygame.Rect(388, 124, 852, 556)
        pygame.draw.rect(surface, (22, 28, 46), list_panel, border_radius=18)
        pygame.draw.rect(surface, (86, 102, 142), list_panel, 2, border_radius=18)
        pygame.draw.rect(surface, (22, 28, 46), detail_panel, border_radius=18)
        pygame.draw.rect(surface, (92, 112, 158), detail_panel, 2, border_radius=18)

        total_label = self._small_font.render(f"已收录 {len(self._entries)} 种敌人", True, (190, 206, 235))
        surface.blit(total_label, (list_panel.x + 18, list_panel.y + 14))

        for index, rect in self._visible_row_rects():
            entry = self._entries[index]
            active = index == self._selected
            fill = (40, 50, 82) if active else (28, 34, 56)
            border = (255, 216, 98) if active else (72, 86, 124)
            pygame.draw.rect(surface, fill, rect, border_radius=12)
            pygame.draw.rect(surface, border, rect, 2, border_radius=12)

            name = self._row_font.render(entry.name, True, WHITE)
            surface.blit(name, name.get_rect(midleft=(rect.x + 12, rect.centery)))

            badge_color = _CATEGORY_COLORS[entry.category]
            badge = pygame.Rect(rect.right - 72, rect.y + 8, 56, 22)
            pygame.draw.rect(surface, (32, 40, 62), badge, border_radius=11)
            pygame.draw.rect(surface, badge_color, badge, 2, border_radius=11)
            badge_text = self._hint_font.render(entry.category, True, badge_color)
            surface.blit(badge_text, badge_text.get_rect(center=badge.center))

        self._draw_detail(surface, detail_panel)

        hint = self._hint_font.render("上下翻阅，PageUp/PageDown 快速翻页，点击条目查看详情。", True, (164, 178, 212))
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=696))

    def _draw_detail(self, surface: pygame.Surface, panel: pygame.Rect) -> None:
        entry = self._entries[self._selected]
        snapshot = self._snapshot(entry.enemy_id)

        portrait_rect = pygame.Rect(panel.x + 22, panel.y + 22, 334, 236)
        info_rect = pygame.Rect(panel.x + 378, panel.y + 24, 446, 226)
        stats_y = panel.y + 278
        left_desc = pygame.Rect(panel.x + 22, panel.y + 382, 392, 140)
        right_desc = pygame.Rect(panel.x + 438, panel.y + 382, 392, 140)

        pygame.draw.rect(surface, (30, 38, 62), portrait_rect, border_radius=16)
        pygame.draw.rect(surface, (90, 106, 150), portrait_rect, 2, border_radius=16)
        portrait = self._portrait(entry.enemy_id)
        surface.blit(portrait, portrait.get_rect(center=portrait_rect.center))

        tag_color = _CATEGORY_COLORS[entry.category]
        name = self._name_font.render(entry.name, True, WHITE)
        surface.blit(name, (info_rect.x, info_rect.y))

        badge = pygame.Rect(info_rect.x, info_rect.y + 46, 84, 28)
        pygame.draw.rect(surface, (32, 40, 62), badge, border_radius=14)
        pygame.draw.rect(surface, tag_color, badge, 2, border_radius=14)
        badge_text = self._small_font.render(entry.category, True, tag_color)
        surface.blit(badge_text, badge_text.get_rect(center=badge.center))

        style_title = self._small_font.render("作战风格", True, (190, 206, 236))
        style_text = self._body_font.render(entry.style, True, (255, 228, 126))
        surface.blit(style_title, (info_rect.x, info_rect.y + 96))
        surface.blit(style_text, (info_rect.x, info_rect.y + 120))

        note = self._hint_font.render("数值基于普通难度与当前配置。", True, (155, 170, 206))
        surface.blit(note, (info_rect.x, info_rect.y + 166))

        stat_titles = ("生命", "速度", "伤害", "经验", "金币")
        stat_values = (snapshot.hp, snapshot.speed, snapshot.damage, snapshot.xp_drop, snapshot.gold_drop)
        stat_w = 152
        stat_gap = 8
        for idx, (title, value) in enumerate(zip(stat_titles, stat_values)):
            rect = pygame.Rect(panel.x + 22 + idx * (stat_w + stat_gap), stats_y, stat_w, 78)
            pygame.draw.rect(surface, (32, 40, 64), rect, border_radius=14)
            pygame.draw.rect(surface, (92, 112, 156), rect, 2, border_radius=14)
            title_text = self._small_font.render(title, True, (180, 196, 230))
            value_text = self._row_font.render(str(value), True, WHITE)
            surface.blit(title_text, title_text.get_rect(centerx=rect.centerx, y=rect.y + 12))
            surface.blit(value_text, value_text.get_rect(centerx=rect.centerx, y=rect.y + 38))

        self._draw_text_box(surface, left_desc, "敌人特征", entry.description)
        self._draw_text_box(surface, right_desc, "应对建议", entry.tips)

    def _draw_text_box(self, surface: pygame.Surface, rect: pygame.Rect, title: str, text: str) -> None:
        pygame.draw.rect(surface, (30, 38, 62), rect, border_radius=16)
        pygame.draw.rect(surface, (92, 112, 156), rect, 2, border_radius=16)
        title_text = self._small_font.render(title, True, (180, 198, 234))
        surface.blit(title_text, (rect.x + 16, rect.y + 14))

        current_y = rect.y + 40
        for line in wrap_text(self._body_font, text, rect.w - 32, max_lines=4):
            body = self._body_font.render(line, True, WHITE)
            surface.blit(body, (rect.x + 16, current_y))
            current_y += 22

    def _draw_action_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, border_color: tuple[int, int, int]) -> None:
        pygame.draw.rect(surface, (30, 38, 62), rect, border_radius=12)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=12)
        text = self._body_font.render(label, True, WHITE)
        surface.blit(text, text.get_rect(center=rect.center))

    def _move_selection(self, delta: int) -> None:
        self._selected = max(0, min(len(self._entries) - 1, self._selected + delta))
        self._ensure_visible()

    def _ensure_visible(self) -> None:
        if self._selected < self._scroll:
            self._scroll = self._selected
        elif self._selected >= self._scroll + self._visible_rows:
            self._scroll = self._selected - self._visible_rows + 1

    def _portrait(self, enemy_id: str) -> pygame.Surface:
        if enemy_id not in self._portrait_cache:
            self._portrait_cache[enemy_id] = render_enemy_portrait(enemy_id)
        return self._portrait_cache[enemy_id]

    def _snapshot(self, enemy_id: str):
        if enemy_id not in self._snapshot_cache:
            self._snapshot_cache[enemy_id] = build_enemy_snapshot(enemy_id)
        return self._snapshot_cache[enemy_id]

    def _visible_row_rects(self) -> list[tuple[int, pygame.Rect]]:
        start = self._scroll
        end = min(len(self._entries), start + self._visible_rows)
        rects: list[tuple[int, pygame.Rect]] = []
        for local_idx, index in enumerate(range(start, end)):
            rects.append((index, pygame.Rect(54, 168 + local_idx * 44, 300, 38)))
        return rects

    def _back_button(self) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH - 176, 30, 136, 38)

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        for idx in range(6):
            radius = 80 + idx * 44
            glow = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (86, 124, 220, 28 - idx * 3), (glow.get_width() // 2, glow.get_height() // 2), radius, 2)
            surface.blit(glow, (SCREEN_WIDTH - 240 - radius, 22 - idx * 12))

        bloom = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(bloom, (255, 180, 82, 18), (180, 240), 138)
        pygame.draw.circle(bloom, (110, 180, 255, 16), (248, 180), 122)
        surface.blit(bloom, (18, 342))
