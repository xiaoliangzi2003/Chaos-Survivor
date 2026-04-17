"""空间哈希网格：加速大量实体的碰撞查询，避免 O(n²) 遍历。"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.entity import Entity

_CELL = 96   # 格子尺寸（px）—— 约等于最大实体直径的 2 倍


class SpatialGrid:
    """
    每帧 clear() + 批量 insert()，再按需 query_radius()。
    不维护增量更新，适合游戏主循环模式。
    """

    def __init__(self, cell_size: int = _CELL) -> None:
        self.cell_size = cell_size
        self._cells: dict[tuple[int, int], list] = {}

    # ── 写入 ──────────────────────────────────────────
    def clear(self) -> None:
        self._cells.clear()

    def insert(self, entity: "Entity") -> None:
        key = self._key(entity.x, entity.y)
        if key not in self._cells:
            self._cells[key] = []
        self._cells[key].append(entity)

    # ── 查询 ──────────────────────────────────────────
    def query_radius(self, x: float, y: float,
                     radius: float) -> list["Entity"]:
        """返回以 (x,y) 为圆心、radius 为半径的矩形范围内所有实体（粗筛，含误报）。"""
        cs  = self.cell_size
        x0  = int((x - radius) // cs)
        y0  = int((y - radius) // cs)
        x1  = int((x + radius) // cs)
        y1  = int((y + radius) // cs)
        out = []
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                cell = self._cells.get((cx, cy))
                if cell:
                    out.extend(cell)
        return out

    def query_point(self, x: float, y: float) -> list["Entity"]:
        cell = self._cells.get(self._key(x, y))
        return cell if cell else []

    # ── 辅助 ──────────────────────────────────────────
    def _key(self, x: float, y: float) -> tuple[int, int]:
        cs = self.cell_size
        return (int(x // cs), int(y // cs))
