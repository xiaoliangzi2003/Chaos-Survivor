"""战斗场景（阶段 2：地图渲染 + 摄像机；阶段 3+ 继续填充）。"""

import random
import pygame

from src.core.scene        import Scene
from src.core.config       import (SCREEN_WIDTH, SCREEN_HEIGHT,
                                   WHITE, GOLD, GRAY, MAP_THEMES)
from src.core.camera       import camera
from src.core.input        import input_mgr
from src.core.rng          import rng
from src.render.map_renderer import MapRenderer
from src.render.particles    import particles
from src.ui.fonts            import get_font


_THEME_NAMES = list(MAP_THEMES.keys())


class BattleScene(Scene):

    def on_enter(self, **kwargs) -> None:
        self.difficulty  = kwargs.get("difficulty", 1)
        self._font       = get_font(32)
        self._small      = get_font(22)

        # 每局随机选地图主题
        seed = rng.seed()
        theme = rng.choice(_THEME_NAMES)
        self._map = MapRenderer(theme, seed=seed)

        # 初始摄像机位置（世界原点）
        self._cam_x: float = 0.0
        self._cam_y: float = 0.0

        # 粒子测试：在原点发射一簇星光
        particles.clear()
        for _ in range(30):
            particles.burst(0, 0, color=(100, 200, 255),
                            count=1, speed=40, life=1.2, size=3)

        camera.update(self._cam_x, self._cam_y, 0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.game.push_scene("pause")
            # 阶段 2 调试：切换地图主题
            elif event.key == pygame.K_t:
                seed = rng.seed()
                theme = rng.choice(_THEME_NAMES)
                self._map = MapRenderer(theme, seed=seed)

    def update(self, dt: float) -> None:
        # 阶段 2 中直接用 WASD 移动摄像机（阶段 3 替换为玩家驱动）
        speed = 300.0
        dx, dy = input_mgr.move_vector
        self._cam_x += dx * speed * dt
        self._cam_y += dy * speed * dt

        camera.update(self._cam_x, self._cam_y, dt)
        particles.update(dt)

        # 持续在摄像机中心附近散落星点（测试粒子）
        if random.random() < 0.15:
            particles.sparkle(self._cam_x, self._cam_y,
                              color=(255, 220, 80), count=1, radius=20)

    def draw(self, surface: pygame.Surface) -> None:
        # 1. 地图
        self._map.draw(surface, camera)

        # 2. 粒子（世界坐标）
        particles.draw(surface, camera)

        # 3. 原点十字标记（方便确认摄像机对齐）
        from src.render.shapes import cross, circle
        ox, oy = camera.world_to_screen(0, 0)
        cross(surface, (255, 80, 80), ox, oy, 20, width=2)
        circle(surface, (255, 80, 80), ox, oy, 6, width=2)

        # 4. HUD 占位信息
        self._draw_hud(surface)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        # 主题名
        theme_text = self._small.render(
            f"地图主题: {self._map.theme_name}  |  T 键切换主题  |  WASD 移动",
            True, (220, 220, 220))
        surface.blit(theme_text, (10, 10))

        # 摄像机位置
        pos_text = self._small.render(
            f"摄像机: ({self._cam_x:.0f}, {self._cam_y:.0f})  |  ESC 暂停",
            True, GRAY)
        surface.blit(pos_text, (10, 36))

        # 粒子数
        p_text = self._small.render(
            f"粒子数: {particles.count}",
            True, (100, 200, 255))
        surface.blit(p_text, (10, 62))

        # 难度
        diff_text = self._small.render(f"难度: {self.difficulty}", True, GOLD)
        surface.blit(diff_text, (SCREEN_WIDTH - 120, 10))
