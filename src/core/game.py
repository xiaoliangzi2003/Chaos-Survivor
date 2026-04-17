"""主游戏类：pygame 初始化、场景状态机、主循环。"""

import sys
import pygame

from src.core.config  import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from src.core.input   import input_mgr
from src.core.camera  import camera
from src.core.scene   import Scene
from src.ui.fonts     import get_font


class Game:
    """
    场景状态机。已注册场景：
        "menu"    — 主菜单
        "battle"  — 战斗
        "pause"   — 暂停（覆盖层）
        "upgrade" — 升级选择
        "shop"    — 商店
        "result"  — 结算
    """

    def __init__(self, debug: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock   = pygame.time.Clock()
        self.debug   = debug
        self.running = True

        self._scenes:       dict[str, Scene]   = {}
        self._scene_stack:  list[Scene]         = []   # 支持覆盖层（暂停）
        self._current_name: str                 = ""

        # 调试信息（pygame 初始化后才能调用 get_font）
        self._fps_font = get_font(24)

        # 延迟导入避免循环
        self._register_scenes()

    # ── 场景注册 ─────────────────────────────────────
    def _register_scenes(self) -> None:
        from src.scenes.menu    import MenuScene
        from src.scenes.battle  import BattleScene
        from src.scenes.pause   import PauseScene
        from src.scenes.upgrade import UpgradeScene
        from src.scenes.shop    import ShopScene
        from src.scenes.result  import ResultScene

        self._scenes = {
            "menu":    MenuScene(self),
            "battle":  BattleScene(self),
            "pause":   PauseScene(self),
            "upgrade": UpgradeScene(self),
            "shop":    ShopScene(self),
            "result":  ResultScene(self),
        }

    # ── 场景切换 ──────────────────────────────────────
    def set_scene(self, name: str, **kwargs) -> None:
        """清除整个栈，切换到新场景。"""
        for s in reversed(self._scene_stack):
            s.on_exit()
        self._scene_stack.clear()

        scene = self._scenes[name]
        self._current_name = name
        self._scene_stack.append(scene)
        scene.on_enter(**kwargs)

    def push_scene(self, name: str, **kwargs) -> None:
        """压栈（用于暂停、升级等覆盖层）。"""
        scene = self._scenes[name]
        self._scene_stack.append(scene)
        scene.on_enter(**kwargs)

    def pop_scene(self) -> None:
        """弹出覆盖层，恢复下面的场景。"""
        if len(self._scene_stack) > 1:
            self._scene_stack[-1].on_exit()
            self._scene_stack.pop()

    @property
    def current_scene(self) -> Scene:
        return self._scene_stack[-1]

    # ── 主循环 ────────────────────────────────────────
    def run(self) -> None:
        self.set_scene("menu")

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            # 防止极端帧时间（例如窗口拖动后）导致物理穿透
            dt = min(dt, 0.05)

            events = pygame.event.get()
            input_mgr.update(events)

            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                self.current_scene.handle_event(event)

            self.current_scene.update(dt)

            # 绘制：底层场景先画，覆盖层后画
            for scene in self._scene_stack:
                scene.draw(self.screen)

            if self.debug:
                self._draw_debug()

            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # ── 调试信息 ──────────────────────────────────────
    def _draw_debug(self) -> None:
        fps_text = self._fps_font.render(
            f"FPS: {self.clock.get_fps():.0f}", True, (255, 255, 0)
        )
        self.screen.blit(fps_text, (SCREEN_WIDTH - 90, 8))
