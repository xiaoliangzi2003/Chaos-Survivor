"""战斗场景（阶段 3：玩家实体 + 受伤/死亡/经验；阶段 4+ 继续填充）。"""

import pygame

from src.core.scene          import Scene
from src.core.config         import (SCREEN_WIDTH, SCREEN_HEIGHT,
                                     WHITE, GOLD, GRAY, RED,
                                     MAP_THEMES,
                                     COLOR_HP_BAR, COLOR_HP_BG,
                                     COLOR_XP_BAR, COLOR_XP_BG,
                                     DIFFICULTY_NAMES)
from src.core.camera         import camera
from src.core.input          import input_mgr
from src.core.rng            import rng
from src.render.map_renderer import MapRenderer
from src.render.particles    import particles
from src.render              import shapes
from src.entities.player     import Player
from src.ui.fonts            import get_font

_THEME_NAMES = list(MAP_THEMES.keys())


class BattleScene(Scene):

    # ── 初始化 ────────────────────────────────────────
    def on_enter(self, **kwargs) -> None:
        self.difficulty = kwargs.get("difficulty", 1)

        # 字体
        self._font_hud    = get_font(22)
        self._font_medium = get_font(32)
        self._font_large  = get_font(52, bold=True)

        # 随机地图
        seed        = rng.seed()
        theme       = rng.choice(_THEME_NAMES)
        self._map   = MapRenderer(theme, seed=seed)

        # 玩家
        self._player = Player(0.0, 0.0)

        # 粒子系统清空
        particles.clear()

        # 红边遮罩 surface（预分配，避免每帧创建）
        self._red_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                            pygame.SRCALPHA)

        # 死亡过渡计时
        self._death_delay: float = 0.0

        camera.update(0, 0, 0)

    # ── 事件 ──────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.push_scene("pause")

            # ── 阶段 3 调试快捷键 ──────────────────────
            elif event.key == pygame.K_f:
                # 模拟受伤（来自右边）
                self._player.take_damage(15,
                    source_x=self._player.x + 100,
                    source_y=self._player.y)

            elif event.key == pygame.K_h:
                # 治疗 20 HP
                self._player.heal(20)

            elif event.key == pygame.K_x:
                # 获取经验（测试升级）
                leveled = self._player.gain_xp(self._player.xp_to_next * 0.6)

            elif event.key == pygame.K_g:
                # 获取 50 金币
                self._player.gain_gold(50)

            elif event.key == pygame.K_k:
                # 立即杀死玩家（测试死亡动画）
                self._player.take_damage(9999)

            elif event.key == pygame.K_t:
                # 切换地图主题
                seed  = rng.seed()
                theme = rng.choice(_THEME_NAMES)
                self._map = MapRenderer(theme, seed=seed)

    # ── 逻辑更新 ──────────────────────────────────────
    def update(self, dt: float) -> None:
        p = self._player

        # 玩家更新
        p.update(dt)

        # 摄像机跟随玩家
        camera.update(p.x, p.y, dt)

        # 粒子
        particles.update(dt)

        # 死亡后延迟跳转结算
        if not p.alive:
            self._death_delay += dt
            if self._death_delay >= 2.0:
                self.game.set_scene("result",
                                    victory=False,
                                    stats=self._build_stats())

    # ── 绘制 ──────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        # 1. 地图
        self._map.draw(surface, camera)

        # 2. 粒子（世界层）
        particles.draw(surface, camera)

        # 3. 玩家
        self._player.draw(surface, camera)

        # 4. 屏幕红边（受伤反馈）
        self._draw_screen_flash(surface)

        # 5. HUD
        self._draw_hud(surface)

        # 6. 死亡遮罩
        if not self._player.alive:
            self._draw_death_overlay(surface)

    # ── 屏幕红边 ──────────────────────────────────────
    def _draw_screen_flash(self, surface: pygame.Surface) -> None:
        flash = self._player.screen_flash
        if flash <= 0:
            return
        alpha = int(flash * 160)
        self._red_overlay.fill((0, 0, 0, 0))
        border = 60
        # 四条红色渐变边
        for i in range(border):
            a = int(alpha * (1 - i / border))
            if a <= 0:
                continue
            col = (200, 20, 20, a)
            pygame.draw.rect(self._red_overlay, col,
                             pygame.Rect(i, i,
                                         SCREEN_WIDTH  - i * 2,
                                         SCREEN_HEIGHT - i * 2),
                             1)
        surface.blit(self._red_overlay, (0, 0))

    # ── 死亡遮罩 ──────────────────────────────────────
    def _draw_death_overlay(self, surface: pygame.Surface) -> None:
        progress = min(1.0, self._death_delay / 2.0)
        alpha    = int(progress * 160)
        overlay  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))
        if progress > 0.3:
            txt_alpha = int((progress - 0.3) / 0.7 * 255)
            txt = self._font_large.render("已阵亡", True, RED)
            txt.set_alpha(txt_alpha)
            surface.blit(txt, txt.get_rect(
                centerx=SCREEN_WIDTH // 2,
                centery=SCREEN_HEIGHT // 2 - 20))

    # ── HUD ───────────────────────────────────────────
    def _draw_hud(self, surface: pygame.Surface) -> None:
        p   = self._player
        fnt = self._font_hud

        # ── HP 条 ──────────────────────────────────────
        shapes.bar(surface, 14, 14, 220, 18,
                   p.hp, p.stats.max_hp,
                   COLOR_HP_BAR, COLOR_HP_BG,
                   border_color=(200, 80, 80), border_radius=4)
        hp_txt = fnt.render(
            f"HP  {int(p.hp)} / {int(p.stats.max_hp)}", True, WHITE)
        surface.blit(hp_txt, (14, 36))

        # ── XP 条 ──────────────────────────────────────
        shapes.bar(surface, 14, 60, 220, 14,
                   p.xp, p.xp_to_next,
                   COLOR_XP_BAR, COLOR_XP_BG,
                   border_color=(40, 100, 180), border_radius=3)
        xp_txt = fnt.render(f"Lv.{p.level}  {int(p.xp)}/{p.xp_to_next}", True, (160, 210, 255))
        surface.blit(xp_txt, (14, 78))

        # ── 金币 ───────────────────────────────────────
        gold_txt = fnt.render(f"金币: {p.gold}", True, GOLD)
        surface.blit(gold_txt, (14, 100))

        # ── 右上：击杀 / 存活时间 ──────────────────────
        minutes = int(p.survive_time) // 60
        seconds = int(p.survive_time) % 60
        time_txt = fnt.render(f"{minutes:02d}:{seconds:02d}", True, WHITE)
        surface.blit(time_txt, (SCREEN_WIDTH - 90, 14))

        kill_txt = fnt.render(f"击杀: {p.kills}", True, (220, 180, 180))
        surface.blit(kill_txt, (SCREEN_WIDTH - 120, 38))

        diff_txt = fnt.render(
            f"难度: {DIFFICULTY_NAMES[self.difficulty]}", True, GOLD)
        surface.blit(diff_txt, (SCREEN_WIDTH - 140, 62))

        # ── 调试提示（屏幕下方） ──────────────────────
        hint = fnt.render(
            "F=受伤  H=治疗  X=+经验  G=+金币  K=死亡  T=换地图  ESC=暂停",
            True, (100, 100, 100))
        surface.blit(hint, hint.get_rect(
            centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 28))

    # ── 结算数据 ──────────────────────────────────────
    def _build_stats(self) -> dict:
        p = self._player
        return {
            "wave":         0,
            "time":         p.survive_time,
            "kills":        p.kills,
            "damage_dealt": p.total_damage_dealt,
            "damage_taken": p.total_damage_taken,
            "gold":         p.gold,
            "level":        p.level,
            "difficulty":   self.difficulty,
        }
