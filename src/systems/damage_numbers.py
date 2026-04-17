"""伤害浮字系统：数字向上飘动 + 渐隐，暴击放大变色。"""

import pygame
from src.core.camera import Camera
from src.ui.fonts    import get_font

_LIFE      = 0.85    # 默认存活时间（秒）
_RISE_SPD  = 55      # 上升速度 px/s
_CRIT_SCALE = 1.5    # 暴击字体倍率


class _DmgNum:
    __slots__ = ("x", "y", "text", "color", "life", "max_life",
                 "size", "vy", "alpha")

    def __init__(self, x: float, y: float, text: str,
                 color: tuple, size: int, life: float) -> None:
        self.x     = x
        self.y     = y
        self.text  = text
        self.color = color
        self.size  = size
        self.life  = life
        self.max_life = life
        self.vy    = -_RISE_SPD
        self.alpha = 255


class DamageNumbers:
    """
    全局伤害浮字管理器。
    使用世界坐标存储，draw() 时转换为屏幕坐标。
    """

    def __init__(self) -> None:
        self._nums: list[_DmgNum] = []
        self._fonts: dict[int, pygame.font.Font] = {}

    def _font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            self._fonts[size] = get_font(size, bold=True)
        return self._fonts[size]

    # ── 添加 ──────────────────────────────────────────
    def add(self, x: float, y: float, amount: float,
            is_crit: bool = False,
            is_heal: bool = False,
            custom_color: tuple | None = None) -> None:
        if is_heal:
            color = (80, 255, 120)
            size  = 22
            text  = f"+{int(amount)}"
        elif is_crit:
            color = (255, 220, 40)
            size  = 30
            text  = f"{int(amount)}!"
        else:
            color = (255, 120, 120)
            size  = 22
            text  = str(int(amount))

        if custom_color:
            color = custom_color

        # 轻微随机横向偏移，避免叠字
        import random
        ox = random.randint(-12, 12)
        self._nums.append(_DmgNum(x + ox, y - 10, text, color, size, _LIFE))

    # ── 更新 ──────────────────────────────────────────
    def update(self, dt: float) -> None:
        keep = []
        for n in self._nums:
            n.life -= dt
            if n.life <= 0:
                continue
            n.y    += n.vy * dt
            n.vy   *= 0.92        # 减速
            ratio   = n.life / n.max_life
            n.alpha = int(255 * min(1.0, ratio * 2))   # 后半段渐隐
            keep.append(n)
        self._nums = keep

    # ── 绘制 ──────────────────────────────────────────
    def draw(self, surface: pygame.Surface, cam: Camera) -> None:
        for n in self._nums:
            sx, sy = cam.world_to_screen(n.x, n.y)
            # 离屏跳过
            w, h = surface.get_size()
            if sx < -60 or sx > w + 60 or sy < -40 or sy > h + 40:
                continue
            font = self._font(n.size)
            txt  = font.render(n.text, True, n.color)
            if n.alpha < 255:
                txt.set_alpha(n.alpha)
            # 居中绘制
            surface.blit(txt, txt.get_rect(
                centerx=int(sx), centery=int(sy)))

    def clear(self) -> None:
        self._nums.clear()


# 全局单例
damage_numbers = DamageNumbers()
