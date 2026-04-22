"""帮助界面：显示按键操作说明。"""

from __future__ import annotations

import pygame

from src.core.config import GOLD, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font

_SECTIONS = [
    ("移动", [
        ("WASD / 方向键", "控制角色移动"),
    ]),
    ("战斗", [
        ("自动", "武器自动攻击周围敌人，无需手动操作"),
    ]),
    ("升级 / 商店", [
        ("1 / 2 / 3（/ 4）", "选择对应的升级强化或商店物品"),
        ("← → / A D", "切换高亮选项"),
        ("回车 / 空格", "确认当前选项"),
        ("R", "在商店中刷新商品（消耗金币）"),
        ("Esc / 空格", "关闭商店，继续战斗"),
    ]),
    ("界面", [
        ("Esc / P", "暂停游戏"),
        ("B", "在主菜单打开图鉴"),
        ("F11", "切换全屏 / 窗口模式"),
    ]),
]


class HelpScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._title_font = get_font(48, bold=True)
        self._section_font = get_font(24, bold=True)
        self._body_font = get_font(21)
        self._hint_font = get_font(18)
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 215))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.game.pop_scene()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))

        title = self._title_font.render("帮助", True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=44))

        left_x = SCREEN_WIDTH // 2 - 320
        right_x = SCREEN_WIDTH // 2 + 20
        y = 130

        for section_name, entries in _SECTIONS:
            sec = self._section_font.render(section_name, True, (255, 210, 70))
            surface.blit(sec, (left_x, y))
            y += 36
            for key, desc in entries:
                key_surf = self._body_font.render(key, True, (140, 195, 255))
                surface.blit(key_surf, (left_x + 12, y))
                desc_surf = self._body_font.render(desc, True, (220, 220, 230))
                surface.blit(desc_surf, (right_x, y))
                y += 30
            y += 14

        hint = self._hint_font.render("按任意键或点击关闭", True, (140, 155, 185))
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 48))
