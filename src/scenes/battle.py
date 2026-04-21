"""战斗场景，负责边界、波次、首领战与战斗反馈。"""

from __future__ import annotations

import math

import pygame

from src.core.camera import camera
from src.core.config import (
    COLOR_HP_BAR,
    COLOR_HP_BG,
    COLOR_XP_BAR,
    COLOR_XP_BG,
    DIFFICULTY_NAMES,
    MAP_THEMES,
    MAX_ENEMIES,
    RED,
    SCREENSHAKE_BOSS_ENTER,
    SCREENSHAKE_PLAYER_HIT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WHITE,
)
from src.core.profile import clamp_difficulty
from src.core.rng import rng
from src.core.scene import Scene
from src.entities.enemy import create_enemy
from src.entities.player import Player
from src.entities.projectile import ProjectileSystem
from src.render import shapes
from src.render.map_renderer import MapRenderer
from src.render.particles import particles
from src.systems.damage_numbers import damage_numbers
from src.systems.enemy_bullets import EnemyBulletSystem
from src.systems.grid import SpatialGrid
from src.systems.hazards import HazardSystem
from src.systems.pickups import PickupSystem
from src.systems.progression import apply_upgrade, build_upgrade_options
from src.systems.shop_items import apply_shop_offer, build_shop_offers, refresh_cost
from src.systems.waves import WaveSystem
from src.ui.fonts import get_font
from src.weapons import STARTING_WEAPON_IDS, create_weapon

_THEME_NAMES = list(MAP_THEMES.keys())
_BOSS_NAMES = {
    "storm_tyrant": "猩红风暴主宰",
    "void_colossus": "虚空巨像",
    "elite_summoner": "裂群召魂者",
    "elite_berserker": "狂怒战躯",
    "elite_assassin": "影刃追猎者",
    "elite_sentinel": "棱镜炮台",
}
_BOSS_ATTACK_LABELS = {
    "elite_summoner": "召唤压制",
    "elite_berserker": "狂暴冲锋",
    "elite_assassin": "瞬影追猎",
    "elite_sentinel": "棱镜轰击",
}


class BattleScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.difficulty = clamp_difficulty(kwargs.get("difficulty", 0))

        self._font_hud = get_font(22)
        self._font_medium = get_font(30)
        self._font_large = get_font(52, bold=True)
        self._font_small = get_font(18)
        self._font_boss = get_font(24, bold=True)

        self._map = MapRenderer(rng.choice(_THEME_NAMES), seed=rng.seed())
        self._bounds = self._map.world_bounds
        self._player = Player(0.0, 0.0)
        self._player.combat_feedback = self._handle_combat_feedback
        for weapon_id in STARTING_WEAPON_IDS:
            self._player.add_weapon(create_weapon(weapon_id))

        self._enemies: list = []
        self._grid = SpatialGrid()
        self._projectiles = ProjectileSystem()
        self._enemy_bullets = EnemyBulletSystem()
        self._hazards = HazardSystem()
        self._pickups = PickupSystem()
        self._wave_system = WaveSystem(self.difficulty)

        particles.clear()
        damage_numbers.clear()

        self._death_delay = 0.0
        self._victory_delay = 0.0
        self._show_victory = False
        self._last_upgrade_text = ""
        self._hitstop_timer = 0.0
        self._shop_refresh_count = 0
        self._shop_message = ""
        self._boss_intro_timer = 0.0
        self._low_detail = False
        self._pending_shop_open = False

        self._red_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        camera.update(0, 0, 0, bounds=self._bounds)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.game.push_scene("pause")

    def update(self, dt: float) -> None:
        if self._hitstop_timer > 0:
            self._hitstop_timer = max(0.0, self._hitstop_timer - dt)
            particles.update(dt * 0.35)
            damage_numbers.update(dt * 0.35)
            return

        self._update_perf_profile()
        hazard_force = self._hazards.update(dt, self._player)
        self._player.update(dt, bounds=self._bounds, external_force=hazard_force)
        camera.update(self._player.x, self._player.y, dt, bounds=self._bounds)
        particles.update(dt)
        damage_numbers.update(dt)
        self._boss_intro_timer = max(0.0, self._boss_intro_timer - dt)

        if not self._player.alive:
            self._death_delay += dt
            if self._death_delay >= 2.0:
                self.game.set_scene("result", victory=False, stats=self._build_stats(), restart_kwargs={"difficulty": self.difficulty})
            return

        self._update_wave(dt)
        self._update_enemies(dt)
        self._update_grid()
        self._update_enemy_auras()
        self._update_weapons(dt)
        self._projectiles.update(dt, self._enemies, self._grid, self._bounds)
        self._enemy_bullets.update(dt, self._player, self._hazards, self._bounds)
        self._check_player_enemy_collision()
        self._collect_dead()
        self._pickups.update(dt, self._player)
        opened_overlay = self._handle_pending_level_up()
        if not opened_overlay:
            self._handle_overlay_queue()
        self._check_victory(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._map.draw(surface, camera)
        self._hazards.draw(surface, camera)
        self._pickups.draw(surface, camera)

        visible_enemies = [enemy for enemy in self._enemies if camera.is_visible(enemy.x, enemy.y, enemy.radius + 18)]
        for enemy in sorted(visible_enemies, key=lambda item: item.y):
            enemy.draw(surface, camera)

        for weapon in self._player.weapons:
            weapon.draw(surface, camera)
        self._projectiles.draw(surface, camera)
        self._enemy_bullets.draw(surface, camera)
        particles.draw(surface, camera)
        self._player.draw(surface, camera)
        damage_numbers.draw(surface, camera)

        self._draw_screen_flash(surface)
        self._draw_hud(surface)
        self._draw_boss_bar(surface)
        if not self._player.alive:
            self._draw_death_overlay(surface)

    def _update_wave(self, dt: float) -> None:
        step = self._wave_system.update(dt, len(self._enemies), boss_alive=self._active_boss() is not None)
        if step.entered_break:
            self._clear_wave_with_drops()
            self._pending_shop_open = True
        for spec in step.spawns:
            if len(self._enemies) >= MAX_ENEMIES:
                break
            self._spawn_one(spec)

    def _spawn_one(self, enemy_spec, dist: float | None = None) -> None:
        boss_rank = None
        if isinstance(enemy_spec, dict):
            etype = enemy_spec["etype"]
            ex = enemy_spec["x"] if "x" in enemy_spec else 0.0
            ey = enemy_spec["y"] if "y" in enemy_spec else 0.0
            if "x" not in enemy_spec or "y" not in enemy_spec:
                angle = rng.uniform(0, math.tau)
                distance = dist or rng.uniform(520, 720)
                ex = self._player.x + math.cos(angle) * distance
                ey = self._player.y + math.sin(angle) * distance
            kwargs = {key: value for key, value in enemy_spec.items() if key not in {"etype", "x", "y", "boss_rank"}}
            boss_rank = enemy_spec.get("boss_rank")
        elif isinstance(enemy_spec, (tuple, list)) and enemy_spec and isinstance(enemy_spec[0], str):
            etype = enemy_spec[0]
            if len(enemy_spec) >= 3:
                ex = float(enemy_spec[1])
                ey = float(enemy_spec[2])
            else:
                angle = rng.uniform(0, math.tau)
                distance = dist or rng.uniform(520, 720)
                ex = self._player.x + math.cos(angle) * distance
                ey = self._player.y + math.sin(angle) * distance
            kwargs = dict(enemy_spec[3]) if len(enemy_spec) >= 4 and isinstance(enemy_spec[3], dict) else {}
        else:
            etype = enemy_spec
            angle = rng.uniform(0, math.tau)
            distance = dist or rng.uniform(520, 720)
            ex = self._player.x + math.cos(angle) * distance
            ey = self._player.y + math.sin(angle) * distance
            kwargs = {}

        if etype == "line_raider":
            kwargs.setdefault("world_bounds", self._bounds)
            kwargs.setdefault("target_x", self._player.x)
            kwargs.setdefault("target_y", self._player.y)
            enemy = create_enemy(etype, ex, ey, self.difficulty, **kwargs)
        else:
            enemy = create_enemy(etype, *self._clamp_position(ex, ey, 18), self.difficulty, **kwargs)
        if boss_rank is not None:
            self._configure_boss(enemy, etype, boss_rank)
        self._enemies.append(enemy)

        if enemy.is_boss:
            self._boss_intro_timer = 2.2
            camera.shake(SCREENSHAKE_BOSS_ENTER, 7.0)
            particles.burst(enemy.x, enemy.y, enemy.color, count=24, speed=100, life=0.5, size=6)

    def _configure_boss(self, enemy, etype: str, boss_rank: int) -> None:
        enemy.is_boss = True
        enemy.boss_name = _BOSS_NAMES.get(etype, enemy.boss_name or "首领")
        if not enemy.attack_label:
            enemy.attack_label = _BOSS_ATTACK_LABELS.get(etype, "首领压制")

        scale = 1.0 + 0.18 * max(0, boss_rank - 1)
        enemy.max_hp *= scale
        enemy.hp = enemy.max_hp
        enemy.damage *= 1.0 + 0.14 * max(0, boss_rank - 1)
        enemy.speed *= 1.0 + 0.05 * max(0, boss_rank - 1)
        enemy.radius *= 1.0 + 0.04 * max(0, boss_rank - 1)
        enemy.xp_drop = int(enemy.xp_drop * scale)
        enemy.gold_drop = int(enemy.gold_drop * (1.0 + 0.12 * max(0, boss_rank - 1)))

    def _update_enemies(self, dt: float) -> None:
        for enemy in self._enemies:
            enemy.update(dt, self._player)
            if not getattr(enemy, "ignore_world_clamp", False):
                enemy.x, enemy.y = self._clamp_position(enemy.x, enemy.y, enemy.radius)
            for spawn in enemy.pending_spawns:
                if len(self._enemies) < MAX_ENEMIES:
                    self._spawn_one(spawn)
            for shot in enemy.pending_projectiles:
                self._enemy_bullets.spawn(**shot)
            for hazard in enemy.pending_hazards:
                if hazard.get("kind") == "black_hole":
                    payload = dict(hazard)
                    payload.pop("kind", None)
                    payload["x"], payload["y"] = self._clamp_position(payload["x"], payload["y"], payload["damage_radius"])
                    self._hazards.spawn_black_hole(**payload)
                elif hazard.get("kind") == "fire_pool":
                    payload = dict(hazard)
                    payload.pop("kind", None)
                    payload["x"], payload["y"] = self._clamp_position(payload["x"], payload["y"], payload["damage_radius"])
                    self._hazards.spawn_fire_pit(**payload)

    def _update_grid(self) -> None:
        self._grid.clear()
        for enemy in self._enemies:
            if enemy.alive:
                self._grid.insert(enemy)

    def _update_enemy_auras(self) -> None:
        for enemy in self._enemies:
            enemy.damage_taken_mul = 1.0
            enemy.shielded = False

        for enemy in self._enemies:
            radius = getattr(enemy, "shield_aura_radius", 0.0)
            if not enemy.alive or radius <= 0:
                continue
            for target in self._grid.query_radius(enemy.x, enemy.y, radius):
                if not target.alive or target is enemy:
                    continue
                dx = target.x - enemy.x
                dy = target.y - enemy.y
                if dx * dx + dy * dy <= radius * radius:
                    target.damage_taken_mul = min(target.damage_taken_mul, 0.1)
                    target.shielded = True

    def _update_weapons(self, dt: float) -> None:
        for weapon in self._player.weapons:
            weapon.update(dt, self._player, self._enemies, self._grid, self._projectiles)

    def _check_player_enemy_collision(self) -> None:
        px = self._player.x
        py = self._player.y
        for enemy in self._enemies:
            if not enemy.alive:
                continue
            for ex, ey, radius, damage in enemy.collision_nodes():
                hit_r = self._player.radius + radius
                dx = px - ex
                dy = py - ey
                if dx * dx + dy * dy > hit_r * hit_r:
                    continue
                actual = self._player.take_damage(damage, ex, ey)
                if actual > 0:
                    damage_numbers.add(self._player.x, self._player.y - 28, actual, custom_color=(255, 80, 80))
                    return

    def _collect_dead(self) -> None:
        keep = []
        for enemy in self._enemies:
            if enemy.alive:
                keep.append(enemy)
                continue
            for spawn in getattr(enemy, "pending_spawns", []):
                if len(keep) + len(self._enemies) < MAX_ENEMIES:
                    self._spawn_one(spawn)
            self._player.kills += 1
            self._pickups.spawn_rewards(enemy.x, enemy.y, enemy.xp_drop, enemy.gold_drop)
        self._enemies = [enemy for enemy in self._enemies if enemy.alive]

    def _clear_wave_with_drops(self) -> None:
        for enemy in self._enemies:
            self._player.kills += 1
            self._pickups.spawn_rewards(enemy.x, enemy.y, enemy.xp_drop, enemy.gold_drop)
        self._pickups.absorb_all(self._player, xp_ratio=0.25, gold_ratio=0.25)
        self._enemies.clear()
        self._enemy_bullets.clear()
        self._hazards.clear()
        particles.burst(self._player.x, self._player.y, (255, 220, 120), count=20, speed=80, life=0.45, size=5)

    def _handle_pending_level_up(self) -> bool:
        if self._player.pending_level_ups <= 0:
            return False
        self._player.pending_level_ups -= 1
        self._player.just_leveled = False
        options = build_upgrade_options(self._player, count=3)
        self.game.push_scene("upgrade", options=options, on_select=self._apply_upgrade)
        return True

    def _handle_overlay_queue(self) -> bool:
        if not self._pending_shop_open or self._player.pending_level_ups > 0:
            return False
        self._pending_shop_open = False
        self._open_shop()
        return True

    def _apply_upgrade(self, option) -> None:
        self._last_upgrade_text = apply_upgrade(self._player, option)
        particles.sparkle(self._player.x, self._player.y, (255, 220, 80), count=10, radius=24)

    def _open_shop(self) -> None:
        self._shop_refresh_count = 0
        offers = build_shop_offers(self._player, self._wave_system.current_wave, count=4)
        self.game.push_scene(
            "shop",
            offers=offers,
            player=self._player,
            refresh_cost=refresh_cost(self._shop_refresh_count),
            on_buy=self._buy_shop_offer,
            on_refresh=self._refresh_shop,
            wave=self._wave_system.current_wave,
            message=self._shop_message,
        )

    def _buy_shop_offer(self, offer) -> str:
        if self._player.gold < offer.cost:
            return "金币不足"
        self._player.gold -= offer.cost
        self._shop_message = apply_shop_offer(self._player, offer)
        particles.sparkle(self._player.x, self._player.y, offer.color, count=9, radius=24)
        return self._shop_message

    def _refresh_shop(self):
        cost = refresh_cost(self._shop_refresh_count)
        if self._player.gold < cost:
            self._shop_message = "金币不足，无法刷新"
            return build_shop_offers(self._player, self._wave_system.current_wave, count=4), cost, self._shop_message
        self._player.gold -= cost
        self._shop_refresh_count += 1
        self._shop_message = "商店已刷新"
        return (
            build_shop_offers(self._player, self._wave_system.current_wave, count=4),
            refresh_cost(self._shop_refresh_count),
            self._shop_message,
        )

    def _buy_shop_offer(self, offer) -> str:
        if self._player.gold < offer.cost:
            return "金币不足"
        self._player.gold -= offer.cost
        self._shop_message = apply_shop_offer(self._player, offer)
        particles.sparkle(self._player.x, self._player.y, offer.color, count=9, radius=24)
        return self._shop_message

    def _refresh_shop(self):
        cost = refresh_cost(self._shop_refresh_count)
        if self._player.gold < cost:
            self._shop_message = "金币不足，无法刷新"
            return build_shop_offers(self._player, self._wave_system.current_wave, count=4), cost, self._shop_message
        self._player.gold -= cost
        self._shop_refresh_count += 1
        self._shop_message = "商店已刷新"
        return (
            build_shop_offers(self._player, self._wave_system.current_wave, count=4),
            refresh_cost(self._shop_refresh_count),
            self._shop_message,
        )

    def _check_victory(self, dt: float) -> None:
        if not self._wave_system.finished:
            return
        self._victory_delay += dt
        self._show_victory = True
        if self._victory_delay >= 1.2:
            self.game.set_scene("result", victory=True, stats=self._build_stats(), restart_kwargs={"difficulty": self.difficulty})

    def _handle_combat_feedback(self, kind: str, **payload) -> None:
        if kind == "enemy_hit":
            is_crit = payload.get("is_crit", False)
            killed = payload.get("killed", False)
            color = payload.get("color", (255, 255, 255))
            x = payload.get("x", 0.0)
            y = payload.get("y", 0.0)
            self._hitstop_timer = max(self._hitstop_timer, 0.022 if not is_crit else 0.035)
            camera.shake(70 if not is_crit else 110, 2.5 if not killed else 4.0)
            particles.burst(x, y, color, count=8 if not killed else 16, speed=80, life=0.28, size=4)
            if killed:
                particles.burst(x, y, (255, 255, 255), count=10, speed=95, life=0.25, size=3)
        elif kind == "player_hit":
            self._hitstop_timer = max(self._hitstop_timer, 0.05)
            camera.shake(SCREENSHAKE_PLAYER_HIT, 5.5)
            particles.burst(self._player.x, self._player.y, (255, 90, 90), count=16, speed=110, life=0.35, size=4)

    def _update_perf_profile(self) -> None:
        total_bullets = self._enemy_bullets.count + self._projectiles.count
        pressure = len(self._enemies) + total_bullets * 0.95 + particles.count * 0.3 + self._hazards.count * 10
        self._low_detail = pressure >= 250
        medium_detail = pressure >= 170

        if self._low_detail:
            particles.configure(spawn_scale=0.45, draw_limit=260, low_detail=True)
        elif medium_detail:
            particles.configure(spawn_scale=0.7, draw_limit=440, low_detail=False)
        else:
            particles.configure(spawn_scale=1.0, draw_limit=800, low_detail=False)

        self._projectiles.set_low_detail(self._low_detail)
        self._enemy_bullets.set_low_detail(self._low_detail)
        self._hazards.set_low_detail(self._low_detail)

    def _draw_screen_flash(self, surface: pygame.Surface) -> None:
        flash = self._player.screen_flash
        if flash <= 0:
            return
        alpha = int(flash * 170)
        border = 55
        self._red_overlay.fill((0, 0, 0, 0))
        for idx in range(border):
            current_alpha = int(alpha * (1 - idx / border))
            if current_alpha <= 0:
                continue
            pygame.draw.rect(self._red_overlay, (200, 20, 20, current_alpha), pygame.Rect(idx, idx, SCREEN_WIDTH - idx * 2, SCREEN_HEIGHT - idx * 2), 1)
        surface.blit(self._red_overlay, (0, 0))

    def _draw_death_overlay(self, surface: pygame.Surface) -> None:
        progress = min(1.0, self._death_delay / 2.0)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(progress * 170)))
        surface.blit(overlay, (0, 0))
        if progress > 0.3:
            text = self._font_large.render("战斗失败", True, RED)
            text.set_alpha(int((progress - 0.3) / 0.7 * 255))
            surface.blit(text, text.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 20))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        player = self._player
        fnt = self._font_hud

        shapes.bar(surface, 14, 14, 220, 18, player.hp, player.stats.max_hp, COLOR_HP_BAR, COLOR_HP_BG, border_color=(200, 80, 80), border_radius=4)
        surface.blit(fnt.render(f"生命 {int(player.hp)} / {int(player.stats.max_hp)}", True, WHITE), (14, 36))

        shapes.bar(surface, 14, 60, 220, 14, player.xp, player.xp_to_next, COLOR_XP_BAR, COLOR_XP_BG, border_color=(40, 100, 180), border_radius=3)
        surface.blit(fnt.render(f"等级 {player.level}  {int(player.xp)}/{player.xp_to_next}", True, (160, 210, 255)), (14, 78))
        surface.blit(fnt.render(f"金币 {player.gold}", True, (255, 210, 90)), (14, 102))

        minutes = int(player.survive_time) // 60
        seconds = int(player.survive_time) % 60
        surface.blit(fnt.render(f"{minutes:02d}:{seconds:02d}", True, WHITE), (SCREEN_WIDTH - 100, 14))
        surface.blit(fnt.render(f"击杀 {player.kills}", True, (230, 190, 190)), (SCREEN_WIDTH - 150, 40))
        surface.blit(fnt.render(f"难度 {DIFFICULTY_NAMES[self.difficulty]}", True, (255, 205, 90)), (SCREEN_WIDTH - 210, 66))
        surface.blit(fnt.render(f"敌人 {len(self._enemies)}  掉落 {self._pickups.count}", True, (210, 165, 165)), (SCREEN_WIDTH - 250, 92))
        surface.blit(fnt.render(f"敌方弹幕 {self._enemy_bullets.count}  危险区 {self._hazards.count}", True, (235, 145, 145)), (SCREEN_WIDTH - 275, 118))

        wave_label = f"第 {self._wave_system.current_wave} 波"
        if self._wave_system.is_break:
            wave_label += " - 商店阶段"
        elif self._wave_system.is_boss_wave and self._active_boss() is not None:
            wave_label += " - 首领战"
        elif self._wave_system.cleanup_mode:
            wave_label += " - 清场中"
        surface.blit(self._font_medium.render(wave_label, True, (255, 220, 120)), (14, 132))

        if self._wave_system.is_boss_wave and self._active_boss() is not None:
            time_text = "目标：击败首领"
        else:
            time_text = f"剩余时间 {self._wave_system.time_left:04.1f} 秒"
        surface.blit(self._font_small.render(time_text, True, (180, 180, 200)), (16, 166))

        if self._wave_system.banner.timer > 0:
            banner = self._font_medium.render(self._wave_system.banner.text, True, (255, 230, 120))
            surface.blit(banner, banner.get_rect(centerx=SCREEN_WIDTH // 2, y=32))

        if self._last_upgrade_text:
            tip = self._font_small.render(self._last_upgrade_text, True, (210, 225, 255))
            surface.blit(tip, tip.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 50))

        for idx, weapon in enumerate(self._player.weapons):
            text = self._font_small.render(f"{weapon.NAME}  {weapon.level}级", True, (210, 210, 220))
            surface.blit(text, (14, SCREEN_HEIGHT - 110 + idx * 20))

        if self._show_victory:
            text = self._font_large.render("胜利", True, (255, 225, 120))
            surface.blit(text, text.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2))

    def _draw_boss_bar(self, surface: pygame.Surface) -> None:
        boss = self._active_boss()
        if boss is None:
            return
        outer = pygame.Rect(SCREEN_WIDTH // 2 - 260, 78, 520, 40)
        inner = outer.inflate(-8, -8)
        pygame.draw.rect(surface, (20, 10, 18), outer, border_radius=12)
        pygame.draw.rect(surface, boss.color, outer, 3, border_radius=12)
        shapes.bar(surface, inner.x, inner.y, inner.width, inner.height, boss.hp, boss.max_hp, boss.color, (60, 18, 26), border_radius=9)

        name = self._font_boss.render(boss.boss_name, True, WHITE)
        phase = self._font_small.render(f"当前攻击：{boss.attack_label}", True, (255, 220, 235))
        surface.blit(name, name.get_rect(centerx=SCREEN_WIDTH // 2, y=44))
        surface.blit(phase, phase.get_rect(centerx=SCREEN_WIDTH // 2, y=121))

        if self._boss_intro_timer > 0:
            intro = self._font_large.render("首领来袭", True, boss.color)
            surface.blit(intro, intro.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 120))

    def _active_boss(self):
        for enemy in self._enemies:
            if enemy.alive and getattr(enemy, "is_boss", False):
                return enemy
        return None

    def _clamp_position(self, x: float, y: float, radius: float) -> tuple[float, float]:
        left, top, right, bottom = self._bounds
        return (
            max(left + radius, min(right - radius, x)),
            max(top + radius, min(bottom - radius, y)),
        )

    def _build_stats(self) -> dict:
        return {
            "wave": self._wave_system.current_wave,
            "time": self._player.survive_time,
            "kills": self._player.kills,
            "damage_dealt": self._player.total_damage_dealt,
            "damage_taken": self._player.total_damage_taken,
            "gold": self._player.gold,
            "level": self._player.level,
            "difficulty": self.difficulty,
        }
