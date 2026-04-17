"""随机数管理器：统一种子，便于复盘与调试。"""

import random
from typing import Optional, Sequence, TypeVar

T = TypeVar("T")

class RNG:
    """项目级随机数单例。"""

    def __init__(self) -> None:
        self._seed: Optional[int] = None
        self._rng = random.Random()

    # ── 种子 ─────────────────────────────────────────
    def seed(self, s: Optional[int] = None) -> int:
        """设置种子；不传则随机生成并返回实际种子。"""
        if s is None:
            s = random.randrange(0, 2**31)
        self._seed = s
        self._rng.seed(s)
        return s

    @property
    def current_seed(self) -> Optional[int]:
        return self._seed

    # ── 基础接口（镜像 random 模块常用方法） ──────────
    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._rng.choice(seq)

    def choices(self, population: Sequence[T], weights=None, k: int = 1) -> list[T]:
        return self._rng.choices(population, weights=weights, k=k)

    def shuffle(self, lst: list) -> None:
        self._rng.shuffle(lst)

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        return self._rng.sample(population, k)

    def chance(self, probability: float) -> bool:
        """返回 True 的概率为 probability（0–1）。"""
        return self._rng.random() < probability


# 全局单例
rng = RNG()
