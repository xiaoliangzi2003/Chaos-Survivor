"""Main menu scene."""

from __future__ import annotations

import math
import random

import pygame

from src.core.bestiary import draw_bestiary_icon
from src.core.config import DIFFICULTY_NAMES, GOLD, GRAY, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.profile import clamp_difficulty, get_max_unlocked_difficulty
from src.core.scene import Scene
from src.ui.fonts import get_font

_VERSION = "alpha 0.1"


class MenuScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._font_title = get_font(72, bold=True)
        self._font_item = get_font(32)
        self._font_small = get_font(22)
        self._font_hint = get_font(17)
        self._font_icon = get_font(18, bold=True)
        self._items = ["开始游戏", "难度", "显示模式", "配置", "帮助", "退出游戏"]
        self._selected = 0
        self._unlocked_difficulty = get_max_unlocked_difficulty()
        preferred = kwargs.get("difficulty", getattr(self, "_difficulty", 0))
        self._difficulty = min(clamp_difficulty(preferred), self._unlocked_difficulty)
        self._bestiary_hover = False
        self._t = 0.0
        self._bg_orbs = [
            {
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(0, SCREEN_HEIGHT),
                "vx": random.uniform(-18, 18),
                "vy": random.uniform(-14, 14),
                "r": random.uniform(28, 72),
                "phase": random.uniform(0, math.pi * 2),
                "hue": random.choice([(80, 120, 230), (60, 180, 255), (180, 80, 255), (255, 160, 50)]),
            }
            for _ in range(10)
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._selected = (self._selected - 1) % len(self._items)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._selected = (self._selected + 1) % len(self._items)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._adjust_selected(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._adjust_selected(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate()
            elif event.key == pygame.K_b:
                self._open_bestiary()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = self.game.get_mouse_pos()
            if self._bestiary_rect().collidepoint(mx, my):
                self._open_bestiary()
                return
            for idx, rect in enumerate(self._item_rects()):
                if rect.collidepoint(mx, my):
                    self._selected = idx
                    self._activate()
                    break

    def _adjust_selected(self, delta: int) -> None:
        item = self._items[self._selected]
        if item == "难度":
            unlocked = self._unlocked_difficulty
            if unlocked <= 0:
                self._difficulty = 0
            else:
                self._difficulty = max(0, min(unlocked, self._difficulty + delta))
        elif item == "显示模式":
            self.game.toggle_fullscreen(delta > 0 if delta != 0 else None)

    def _activate(self) -> None:
        choice = self._items[self._selected]
        if choice == "开始游戏":
            self.game.set_scene("battle", difficulty=self._difficulty)
        elif choice == "难度":
            if self._difficulty >= self._unlocked_difficulty:
                self._difficulty = 0
            else:
                self._difficulty += 1
        elif choice == "显示模式":
            self.game.toggle_fullscreen()
        elif choice == "配置":
            self.game.push_scene("settings")
        elif choice == "帮助":
            self.game.push_scene("help")
        else:
            self.game.running = False

    def update(self, dt: float) -> None:
        self._t += dt
        for orb in self._bg_orbs:
            orb["x"] += orb["vx"] * dt
            orb["y"] += orb["vy"] * dt
            if orb["x"] < -120:
                orb["x"] = SCREEN_WIDTH + 120
            elif orb["x"] > SCREEN_WIDTH + 120:
                orb["x"] = -120
            if orb["y"] < -120:
                orb["y"] = SCREEN_HEIGHT + 120
            elif orb["y"] > SCREEN_HEIGHT + 120:
                orb["y"] = -120
        mx, my = self.game.get_mouse_pos()
        self._bestiary_hover = self._bestiary_rect().collidepoint(mx, my)
        for idx, rect in enumerate(self._item_rects()):
            if rect.collidepoint(mx, my):
                self._selected = idx
                break

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((10, 12, 24))
        self._draw_backdrop(surface)

        title = self._font_title.render("混乱幸存者", True, GOLD)
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=72))

        panel = pygame.Rect(356, 180, 568, 390)
        pygame.draw.rect(surface, (18, 24, 40), panel, border_radius=22)
        pygame.draw.rect(surface, (78, 90, 128), panel, 2, border_radius=22)

        for idx, (item, rect) in enumerate(zip(self._items, self._item_rects())):
            active = idx == self._selected
            fill = (38, 46, 74) if active else (24, 28, 42)
            border = GOLD if active else (78, 86, 118)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, border, rect, 2, border_radius=14)

            label = item
            if item == "难度":
                label = f"难度：{DIFFICULTY_NAMES[self._difficulty]}"
            elif item == "显示模式":
                label = f"显示模式：{self.game.display_mode_label()}"

            color = GOLD if active else WHITE
            text = self._font_item.render(label, True, color)
            surface.blit(text, text.get_rect(center=rect.center))

        unlocked_text = f"当前已解锁至：{DIFFICULTY_NAMES[self._unlocked_difficulty]}"
        unlocked = self._font_small.render(unlocked_text, True, (185, 210, 255))
        surface.blit(unlocked, unlocked.get_rect(centerx=SCREEN_WIDTH // 2, y=608))

        if self._unlocked_difficulty < len(DIFFICULTY_NAMES) - 1:
            next_name = DIFFICULTY_NAMES[self._unlocked_difficulty + 1]
            tip = f"通关当前最高难度后可解锁：{next_name}"
        else:
            tip = "所有难度均已解锁。"
        tip_text = self._font_hint.render(tip, True, (150, 170, 205))
        surface.blit(tip_text, tip_text.get_rect(centerx=SCREEN_WIDTH // 2, y=638))

        ver = self._font_hint.render(_VERSION, True, (120, 135, 165))
        surface.blit(ver, ver.get_rect(right=SCREEN_WIDTH - 16, y=SCREEN_HEIGHT - 28))

        icon_rect = self._bestiary_rect()
        draw_bestiary_icon(surface, icon_rect, active=self._bestiary_hover)
        label_color = GOLD if self._bestiary_hover else WHITE
        label = self._font_icon.render("图鉴", True, label_color)
        tip_icon = self._font_hint.render("B", True, label_color)
        surface.blit(label, (icon_rect.right + 12, icon_rect.y + 7))
        surface.blit(tip_icon, (icon_rect.right + 12, icon_rect.y + 30))

    def _open_bestiary(self) -> None:
        self.game.push_scene("bestiary")

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        t = self._t
        for orb in self._bg_orbs:
            pulse = math.sin(t * 0.9 + orb["phase"])
            r = max(4, int(orb["r"] + pulse * 12))
            alpha = int(14 + pulse * 7)
            h, s, v = orb["hue"]
            glow = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (h, s, v, alpha), (r + 2, r + 2), r)
            surface.blit(glow, (int(orb["x"]) - r - 2, int(orb["y"]) - r - 2))

        for idx in range(5):
            base_r = 90 + idx * 46
            radius = int(base_r + math.sin(t * 0.4 + idx * 0.9) * 6)
            alpha = int(18 + math.sin(t * 0.6 + idx * 0.7) * 8)
            ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(ring, (80, 120, 220, alpha), (ring.get_width() // 2, ring.get_height() // 2), radius, 2)
            surface.blit(ring, (70 - idx * 18, 70 - idx * 14))

        glow = pygame.Surface((420, 420), pygame.SRCALPHA)
        a1 = int(14 + math.sin(t * 0.5) * 6)
        a2 = int(14 + math.sin(t * 0.7 + 1.0) * 6)
        pygame.draw.circle(glow, (255, 185, 72, a1), (210, 210), 155)
        pygame.draw.circle(glow, (90, 170, 255, a2), (270, 240), 132)
        surface.blit(glow, (SCREEN_WIDTH - 470, 90))

    def _item_rects(self) -> list[pygame.Rect]:
        width = 504
        height = 50
        gap = 10
        start_y = 206
        x = SCREEN_WIDTH // 2 - width // 2
        return [pygame.Rect(x, start_y + idx * (height + gap), width, height) for idx in range(len(self._items))]

    def _bestiary_rect(self) -> pygame.Rect:
        return pygame.Rect(24, SCREEN_HEIGHT - 84, 56, 56)
