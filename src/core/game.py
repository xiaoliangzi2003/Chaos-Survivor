"""游戏主循环与场景管理。"""

from __future__ import annotations

import sys

import pygame

from src.core.camera import camera
from src.core.config import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE
from src.core.gameplay_settings import get_settings
from src.core.input import input_mgr
from src.core.scene import Scene
from src.ui.fonts import get_font


class Game:
    def __init__(self, debug: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.debug = debug
        self.running = True
        self.fullscreen = False
        self.logical_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.screen = pygame.Surface(self.logical_size)
        self._window = None
        self._apply_display_mode()

        self.clock = pygame.time.Clock()
        self._fps_font = get_font(24)
        self._scenes: dict[str, Scene] = {}
        self._scene_stack: list[Scene] = []
        self._current_name = ""
        self.gameplay_settings = get_settings()

        self._register_scenes()

    def _apply_display_mode(self) -> None:
        if self.fullscreen:
            info = pygame.display.Info()
            self._window = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            self._window = pygame.display.set_mode(self.logical_size)

    def toggle_fullscreen(self, enabled: bool | None = None) -> None:
        self.fullscreen = (not self.fullscreen) if enabled is None else bool(enabled)
        self._apply_display_mode()

    def get_mouse_pos(self) -> tuple[int, int]:
        mx, my = pygame.mouse.get_pos()
        window_w, window_h = self._window.get_size()
        lx = int(mx * self.logical_size[0] / max(1, window_w))
        ly = int(my * self.logical_size[1] / max(1, window_h))
        return lx, ly

    def display_mode_label(self) -> str:
        return "全屏" if self.fullscreen else "窗口"

    def _register_scenes(self) -> None:
        from src.scenes.battle import BattleScene
        from src.scenes.bestiary import BestiaryScene
        from src.scenes.menu import MenuScene
        from src.scenes.pause import PauseScene
        from src.scenes.result import ResultScene
        from src.scenes.settings import SettingsScene
        from src.scenes.shop import ShopScene
        from src.scenes.upgrade import UpgradeScene

        self._scenes = {
            "menu": MenuScene(self),
            "battle": BattleScene(self),
            "pause": PauseScene(self),
            "upgrade": UpgradeScene(self),
            "shop": ShopScene(self),
            "settings": SettingsScene(self),
            "bestiary": BestiaryScene(self),
            "result": ResultScene(self),
        }

    def set_scene(self, name: str, **kwargs) -> None:
        for scene in reversed(self._scene_stack):
            scene.on_exit()
        self._scene_stack.clear()

        scene = self._scenes[name]
        self._current_name = name
        self._scene_stack.append(scene)
        scene.on_enter(**kwargs)

    def push_scene(self, name: str, **kwargs) -> None:
        scene = self._scenes[name]
        self._scene_stack.append(scene)
        scene.on_enter(**kwargs)

    def pop_scene(self) -> None:
        if len(self._scene_stack) > 1:
            self._scene_stack[-1].on_exit()
            self._scene_stack.pop()

    @property
    def current_scene(self) -> Scene:
        return self._scene_stack[-1]

    def run(self) -> None:
        self.set_scene("menu")

        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)

            events = pygame.event.get()
            input_mgr.update(events)

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                self.current_scene.handle_event(event)

            self.current_scene.update(dt)

            self.screen.fill((0, 0, 0))
            for scene in self._scene_stack:
                scene.draw(self.screen)

            if self.debug:
                self._draw_debug()

            if self._window.get_size() == self.logical_size:
                self._window.blit(self.screen, (0, 0))
            else:
                scaled = pygame.transform.smoothscale(self.screen, self._window.get_size())
                self._window.blit(scaled, (0, 0))
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def _draw_debug(self) -> None:
        fps_text = self._fps_font.render(f"FPS: {self.clock.get_fps():.0f}", True, (255, 255, 0))
        self.screen.blit(fps_text, (SCREEN_WIDTH - 90, 8))
