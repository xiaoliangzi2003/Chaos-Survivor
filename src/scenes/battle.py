"""战斗场景（阶段 4：敌人系统 + 空间网格 + 伤害浮字）。"""

import math
import pygame

from src.core.scene            import Scene
from src.core.config           import (SCREEN_WIDTH, SCREEN_HEIGHT,
                                       WHITE, GOLD, GRAY, RED,
                                       MAP_THEMES,
                                       COLOR_HP_BAR, COLOR_HP_BG,
                                       COLOR_XP_BAR, COLOR_XP_BG,
                                       DIFFICULTY_NAMES, MAX_ENEMIES)
from src.core.camera           import camera
from src.core.input            import input_mgr
from src.core.rng              import rng
from src.render.map_renderer   import MapRenderer
from src.render.particles      import particles
from src.render                import shapes
from src.entities.player       import Player
from src.entities.enemy        import (create_enemy,
                                       ALL_ENEMY_TYPES, ALL_ELITE_TYPES)
from src.systems.grid          import SpatialGrid
from src.systems.damage_numbers import damage_numbers
from src.ui.fonts              import get_font

_THEME_NAMES = list(MAP_THEMES.keys())

# ── 临时刷怪参数（阶段 7 由 WaveSystem 接管） ─────────
_SPAWN_INTERVAL  = 1.2    # 秒
_MAX_TEMP        = 60     # 临时敌人上限
_SPAWN_DIST_MIN  = 480
_SPAWN_DIST_MAX  = 680


class BattleScene(Scene):

    # ── 初始化 ────────────────────────────────────────
    def on_enter(self, **kwargs) -> None:
        self.difficulty = kwargs.get("difficulty", 1)

        self._font_hud    = get_font(22)
        self._font_medium = get_font(32)
        self._font_large  = get_font(52, bold=True)

        seed      = rng.seed()
        theme     = rng.choice(_THEME_NAMES)
        self._map = MapRenderer(theme, seed=seed)

        self._player  = Player(0.0, 0.0)
        self._enemies: list = []
        self._grid    = SpatialGrid()

        particles.clear()
        damage_numbers.clear()

        self._spawn_timer = 0.0
        self._death_delay = 0.0

        self._red_overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        camera.update(0, 0, 0)

    # ── 事件 ──────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        k = event.key

        if k in (pygame.K_ESCAPE, pygame.K_p):
            self.game.push_scene("pause")

        # ── 调试快捷键 ────────────────────────────────
        elif k == pygame.K_f:
            self._player.take_damage(15,
                source_x=self._player.x + 100,
                source_y=self._player.y)

        elif k == pygame.K_h:
            healed = self._player.heal(20)
            damage_numbers.add(self._player.x, self._player.y - 20,
                               healed, is_heal=True)

        elif k == pygame.K_x:
            self._player.gain_xp(self._player.xp_to_next * 0.6)

        elif k == pygame.K_g:
            self._player.gain_gold(50)

        elif k == pygame.K_k:
            self._player.take_damage(9999)

        elif k == pygame.K_t:
            seed  = rng.seed()
            theme = rng.choice(_THEME_NAMES)
            self._map = MapRenderer(theme, seed=seed)

        elif k == pygame.K_e:
            # 在玩家附近生成随机精英
            self._spawn_one(rng.choice(ALL_ELITE_TYPES), dist=200)

        elif k == pygame.K_BACKQUOTE:
            # 清空所有敌人
            self._enemies.clear()

    # ── 逻辑更新 ──────────────────────────────────────
    def update(self, dt: float) -> None:
        p = self._player
        p.update(dt)
        camera.update(p.x, p.y, dt)
        particles.update(dt)
        damage_numbers.update(dt)

        if p.alive:
            self._update_spawner(dt)
            self._update_enemies(dt, p)
            self._check_player_enemy_collision(p)
            self._collect_dead(p)

        else:
            self._death_delay += dt
            if self._death_delay >= 2.0:
                self.game.set_scene("result",
                                    victory=False,
                                    stats=self._build_stats())

    # ── 刷怪 ──────────────────────────────────────────
    def _update_spawner(self, dt: float) -> None:
        self._spawn_timer += dt
        if (self._spawn_timer >= _SPAWN_INTERVAL and
                len(self._enemies) < _MAX_TEMP):
            # 50% 普通，50% 加权随机
            etype = rng.choice(ALL_ENEMY_TYPES)
            self._spawn_one(etype)
            self._spawn_timer = 0.0

    def _spawn_one(self, etype: str, dist: float | None = None) -> None:
        p     = self._player
        angle = rng.uniform(0, math.pi * 2)
        d     = dist or rng.uniform(_SPAWN_DIST_MIN, _SPAWN_DIST_MAX)
        ex    = p.x + math.cos(angle) * d
        ey    = p.y + math.sin(angle) * d
        self._enemies.append(create_enemy(etype, ex, ey, self.difficulty))

    # ── 敌人更新 ──────────────────────────────────────
    def _update_enemies(self, dt: float, player: Player) -> None:
        # 重建空间网格
        self._grid.clear()
        for e in self._enemies:
            if e.alive:
                self._grid.insert(e)

        # 更新每个敌人
        for e in self._enemies:
            e.update(dt, player)
            # 处理精英召唤请求
            for (spawn_type, sx, sy) in e.pending_spawns:
                if len(self._enemies) < MAX_ENEMIES:
                    self._enemies.append(
                        create_enemy(spawn_type, sx, sy, self.difficulty))

    # ── 玩家-敌人碰撞 ─────────────────────────────────
    def _check_player_enemy_collision(self, player: Player) -> None:
        nearby = self._grid.query_radius(
            player.x, player.y, player.radius + 80)
        for e in nearby:
            if not e.alive:
                continue
            if not player.collides_with(e):
                continue
            actual = player.take_damage(e.damage, e.x, e.y)
            if actual > 0:
                damage_numbers.add(player.x, player.y - 28,
                                   actual, custom_color=(255, 80, 80))

    # ── 收集死亡敌人 ──────────────────────────────────
    def _collect_dead(self, player: Player) -> None:
        alive_list = []
        for e in self._enemies:
            if e.alive:
                alive_list.append(e)
            else:
                player.kills += 1
                player.gain_xp(e.xp_drop)
                if rng.chance(0.4):
                    player.gain_gold(e.gold_drop)
        self._enemies = alive_list

    # ── 绘制 ──────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        self._map.draw(surface, camera)

        # 敌人（按 y 轴排序，实现简单的深度感）
        for e in sorted(self._enemies, key=lambda e: e.y):
            e.draw(surface, camera)

        particles.draw(surface, camera)
        self._player.draw(surface, camera)
        damage_numbers.draw(surface, camera)

        self._draw_screen_flash(surface)
        self._draw_hud(surface)

        if not self._player.alive:
            self._draw_death_overlay(surface)

    # ── 屏幕红边 ──────────────────────────────────────
    def _draw_screen_flash(self, surface: pygame.Surface) -> None:
        flash = self._player.screen_flash
        if flash <= 0:
            return
        alpha  = int(flash * 160)
        border = 55
        self._red_overlay.fill((0, 0, 0, 0))
        for i in range(border):
            a = int(alpha * (1 - i / border))
            if a <= 0:
                continue
            pygame.draw.rect(self._red_overlay, (200, 20, 20, a),
                             pygame.Rect(i, i,
                                         SCREEN_WIDTH  - i * 2,
                                         SCREEN_HEIGHT - i * 2), 1)
        surface.blit(self._red_overlay, (0, 0))

    # ── 死亡遮罩 ──────────────────────────────────────
    def _draw_death_overlay(self, surface: pygame.Surface) -> None:
        progress = min(1.0, self._death_delay / 2.0)
        overlay  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(progress * 160)))
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

        # HP 条
        shapes.bar(surface, 14, 14, 220, 18,
                   p.hp, p.stats.max_hp,
                   COLOR_HP_BAR, COLOR_HP_BG,
                   border_color=(200, 80, 80), border_radius=4)
        surface.blit(fnt.render(
            f"HP  {int(p.hp)} / {int(p.stats.max_hp)}", True, WHITE),
            (14, 36))

        # XP 条
        shapes.bar(surface, 14, 60, 220, 14,
                   p.xp, p.xp_to_next,
                   COLOR_XP_BAR, COLOR_XP_BG,
                   border_color=(40, 100, 180), border_radius=3)
        surface.blit(fnt.render(
            f"Lv.{p.level}  {int(p.xp)}/{p.xp_to_next}", True, (160, 210, 255)),
            (14, 78))

        # 金币
        surface.blit(fnt.render(f"金币: {p.gold}", True, GOLD), (14, 100))

        # 右上：时间 / 击杀 / 难度 / 敌人数
        minutes = int(p.survive_time) // 60
        seconds = int(p.survive_time) % 60
        surface.blit(fnt.render(f"{minutes:02d}:{seconds:02d}", True, WHITE),
                     (SCREEN_WIDTH - 90, 14))
        surface.blit(fnt.render(f"击杀: {p.kills}", True, (220, 180, 180)),
                     (SCREEN_WIDTH - 120, 38))
        surface.blit(fnt.render(
            f"难度: {DIFFICULTY_NAMES[self.difficulty]}", True, GOLD),
            (SCREEN_WIDTH - 150, 62))
        surface.blit(fnt.render(
            f"敌人: {len(self._enemies)}", True, (200, 160, 160)),
            (SCREEN_WIDTH - 120, 86))

        # 调试提示
        surface.blit(fnt.render(
            "F=受伤 H=治疗 X=+经验 G=+金币 K=死亡 T=换图 E=精英 `=清敌",
            True, (90, 90, 90)),
            (0, 0), area=pygame.Rect(0, 0, SCREEN_WIDTH, 20))
        hint = fnt.render(
            "F=受伤  H=治疗  X=+经验  G=+金币  K=死亡  T=换图  E=精英  `=清空敌人",
            True, (90, 90, 90))
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
