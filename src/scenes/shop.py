"""Wave-break shop scene."""

from __future__ import annotations

import pygame

from src.core.config import SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.core.scene import Scene
from src.ui.fonts import get_font, wrap_text

_LOCK_COLOR = (255, 200, 60)
_LOCK_ACTIVE_BORDER = (255, 200, 60)


class ShopScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self._title_font = get_font(56, bold=True)
        self._card_font = get_font(26, bold=True)
        self._body_font = get_font(20)
        self._small_font = get_font(18)
        self._offers = kwargs.get("offers", [])
        self._player = kwargs.get("player")
        self._refresh_cost = kwargs.get("refresh_cost", 0)
        self._on_buy = kwargs.get("on_buy")
        self._on_refresh = kwargs.get("on_refresh")
        self._on_close = kwargs.get("on_close")
        self._wave = kwargs.get("wave", 1)
        self._selected = 0
        self._message = kwargs.get("message", "")
        self._overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 188))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._selected = (self._selected - 1) % max(1, len(self._offers))
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._selected = (self._selected + 1) % max(1, len(self._offers))
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self._buy(0)
            elif event.key in (pygame.K_2, pygame.K_KP2) and len(self._offers) > 1:
                self._buy(1)
            elif event.key in (pygame.K_3, pygame.K_KP3) and len(self._offers) > 2:
                self._buy(2)
            elif event.key in (pygame.K_4, pygame.K_KP4) and len(self._offers) > 3:
                self._buy(3)
            elif event.key == pygame.K_r:
                self._refresh()
            elif event.key == pygame.K_l:
                self._toggle_lock(self._selected)
            elif event.key == pygame.K_v:
                self._buy_with_voucher(self._selected)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self._close()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._buy(self._selected)
            elif event.button == 3:
                self._toggle_lock(self._selected)

    def update(self, dt: float) -> None:
        mx, my = self.game.get_mouse_pos()
        for idx, rect in enumerate(self._card_rects()):
            if rect.collidepoint(mx, my):
                self._selected = idx

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))

        title = self._title_font.render("商店", True, (255, 220, 80))
        surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=56))

        gold_str = f"金币 {self._player.gold}"
        voucher_count = getattr(self._player, "vouchers", 0)
        if voucher_count > 0:
            gold_str += f"  |  购物券 ×{voucher_count}"
        gold = self._body_font.render(gold_str, True, (255, 220, 120))
        surface.blit(gold, (64, 128))

        refresh = self._body_font.render(f"按 R 刷新（{self._refresh_cost} 金币）  已锁定物品不刷新", True, (210, 210, 220))
        surface.blit(refresh, (SCREEN_WIDTH - refresh.get_width() - 64, 128))

        for idx, (offer, rect) in enumerate(zip(self._offers, self._card_rects())):
            is_selected = idx == self._selected
            border = _LOCK_ACTIVE_BORDER if offer.locked else offer.color
            if offer.sold:
                fill = (48, 36, 36)
            elif offer.locked:
                fill = (50, 44, 20) if is_selected else (38, 34, 14)
            else:
                fill = (44, 44, 66) if is_selected else (30, 30, 44)
            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, border, rect, 3 if offer.locked else 2, border_radius=14)

            # Lock indicator
            if offer.locked:
                lock_surf = self._small_font.render("🔒 已锁定", True, _LOCK_COLOR)
                surface.blit(lock_surf, lock_surf.get_rect(right=rect.right - 10, y=rect.y + 52))
            else:
                rarity = self._small_font.render(offer.rarity_label, True, offer.color)
                surface.blit(rarity, (rect.x + 18, rect.y + 52))

            cost_label = "已售出" if offer.sold else f"{offer.cost} 金"
            cost_color = (255, 170, 170) if offer.sold else (255, 225, 110)
            cost = self._card_font.render(cost_label, True, cost_color)
            surface.blit(cost, cost.get_rect(right=rect.right - 16, y=rect.y + 16))

            name = self._card_font.render(offer.name, True, WHITE)
            surface.blit(name, (rect.x + 18, rect.y + 18))

            for line_idx, line in enumerate(wrap_text(self._body_font, offer.description, rect.width - 36, max_lines=4)):
                text = self._body_font.render(line, True, (220, 220, 230))
                surface.blit(text, (rect.x + 18, rect.y + 92 + line_idx * 24))

            hint = self._small_font.render(f"按 {idx + 1} 购买  |  右键/L 锁定", True, (170, 170, 195))
            surface.blit(hint, (rect.x + 18, rect.bottom - 30))

        voucher_hint = ""
        if getattr(self._player, "vouchers", 0) > 0:
            voucher_hint = "  |  按 V 使用购物券免费购买"
        footer = self._small_font.render(f"回车 / 空格 / Esc 继续战斗{voucher_hint}", True, (165, 165, 185))
        surface.blit(footer, footer.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 60))

        if self._message:
            msg = self._small_font.render(self._message, True, (220, 235, 255))
            surface.blit(msg, msg.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 34))

    def _close(self) -> None:
        if self._on_close is not None:
            self._on_close(self._offers)
        self.game.pop_scene()

    def _buy(self, index: int) -> None:
        if not (0 <= index < len(self._offers)) or self._on_buy is None:
            return
        offer = self._offers[index]
        if offer.sold:
            self._message = "这件商品已经买过了"
            return
        self._message = self._on_buy(offer, use_voucher=False)
        if self._message and self._message.endswith("已购买"):
            offer.sold = True

    def _buy_with_voucher(self, index: int) -> None:
        if not (0 <= index < len(self._offers)) or self._on_buy is None:
            return
        offer = self._offers[index]
        if offer.sold:
            self._message = "这件商品已经买过了"
            return
        if getattr(self._player, "vouchers", 0) <= 0:
            self._message = "没有购物券"
            return
        self._message = self._on_buy(offer, use_voucher=True)
        if self._message and self._message.endswith("已购买"):
            offer.sold = True

    def _toggle_lock(self, index: int) -> None:
        if not (0 <= index < len(self._offers)):
            return
        offer = self._offers[index]
        if offer.sold:
            return
        offer.locked = not offer.locked
        self._message = f"{offer.name} 已{'锁定' if offer.locked else '解锁'}"

    def _refresh(self) -> None:
        if self._on_refresh is None:
            return
        result = self._on_refresh(self._offers)
        if result is None:
            return
        self._offers, self._refresh_cost, self._message = result
        self._selected = 0

    def _card_rects(self) -> list[pygame.Rect]:
        card_w = 270
        card_h = 240
        gap = 18
        n = len(self._offers)
        total_w = card_w * n + gap * (n - 1)
        start_x = SCREEN_WIDTH // 2 - total_w // 2
        return [pygame.Rect(start_x + idx * (card_w + gap), 200, card_w, card_h) for idx in range(n)]
