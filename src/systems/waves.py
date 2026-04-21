"""Wave progression and enemy spawn scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.config import (
    BOSS_WAVES,
    DIFFICULTY_SETTINGS,
    ELITE_WAVE_INTERVAL,
    TOTAL_WAVES,
    WAVE_BASE_DURATION,
    WAVE_BREAK_DURATION,
    WAVE_DURATION_INC,
)
from src.core.rng import rng

_BOSS_ROTATION = {
    5: "storm_tyrant",
    10: "elite_summoner",
    15: "elite_sentinel",
    20: "elite_assassin",
}


@dataclass(slots=True)
class WaveBanner:
    text: str
    timer: float = 2.0


@dataclass(slots=True)
class WaveStep:
    spawns: list[str] = field(default_factory=list)
    entered_break: bool = False
    started_wave: bool = False
    victory_ready: bool = False


class WaveSystem:
    def __init__(self, difficulty: int) -> None:
        self.difficulty = difficulty
        self.current_wave = 1
        self.state = "wave"
        self.time_in_state = 0.0
        self.spawn_timer = 0.0
        self.cleanup_mode = False
        self.finished = False
        self.banner = WaveBanner("第 1 波开始")
        self._boss_spawned = False

    def update(self, dt: float, alive_count: int) -> WaveStep:
        step = WaveStep()
        if self.finished:
            return step

        self.time_in_state += dt
        if self.banner.timer > 0:
            self.banner.timer = max(0.0, self.banner.timer - dt)

        if self.state == "break":
            if self.time_in_state >= WAVE_BREAK_DURATION:
                self._start_next_wave()
                step.started_wave = True
            return step

        if self.cleanup_mode:
            if alive_count == 0:
                self.finished = True
                self.banner = WaveBanner("胜利")
                step.victory_ready = True
            return step

        step.spawns = self._spawn_requests(dt, alive_count)
        if self.time_in_state >= self.wave_duration:
            if self.current_wave >= TOTAL_WAVES:
                self.cleanup_mode = True
                self.banner = WaveBanner("清理残余敌人")
            else:
                self.state = "break"
                self.time_in_state = 0.0
                self.spawn_timer = 0.0
                self.banner = WaveBanner(f"第 {self.current_wave + 1} 波即将开始")
                step.entered_break = True
        return step

    @property
    def wave_duration(self) -> float:
        return WAVE_BASE_DURATION + WAVE_DURATION_INC * (self.current_wave - 1)

    @property
    def is_break(self) -> bool:
        return self.state == "break"

    @property
    def time_left(self) -> float:
        if self.state == "break":
            return max(0.0, WAVE_BREAK_DURATION - self.time_in_state)
        if self.cleanup_mode:
            return 0.0
        return max(0.0, self.wave_duration - self.time_in_state)

    def _start_next_wave(self) -> None:
        self.current_wave += 1
        self.state = "wave"
        self.time_in_state = 0.0
        self.spawn_timer = 0.0
        self._boss_spawned = False
        title = f"第 {self.current_wave} 波开始"
        if self.current_wave in BOSS_WAVES:
            title += "  首领来袭"
        elif self.current_wave % ELITE_WAVE_INTERVAL == 0:
            title += "  精英波"
        self.banner = WaveBanner(title)

    def _spawn_requests(self, dt: float, alive_count: int) -> list[str]:
        cap = int(34 + self.current_wave * 10 * DIFFICULTY_SETTINGS[self.difficulty]["count_mul"])
        if alive_count >= cap:
            return []

        spawns: list[str] = []
        self.spawn_timer += dt
        interval = max(0.17, 1.08 - self.current_wave * 0.03)
        interval /= max(0.8, DIFFICULTY_SETTINGS[self.difficulty]["count_mul"])

        if self.current_wave in BOSS_WAVES and not self._boss_spawned:
            spawns.append(_BOSS_ROTATION[self.current_wave])
            self._boss_spawned = True

        while self.spawn_timer >= interval:
            self.spawn_timer -= interval
            batch = 1 + (1 if self.current_wave >= 8 and rng.chance(0.45) else 0)
            for _ in range(batch):
                spawns.append(self._choose_enemy_type())
        return spawns

    def _choose_enemy_type(self) -> str:
        roll = rng.random()
        if self.current_wave <= 2:
            return "zombie" if roll < 0.75 else "speeder"
        if self.current_wave <= 4:
            if roll < 0.40:
                return "zombie"
            if roll < 0.60:
                return "speeder"
            if roll < 0.77:
                return "lancer"
            if roll < 0.90:
                return "exploder"
            return "wizard"
        if self.current_wave <= 7:
            if roll < 0.28:
                return "zombie"
            if roll < 0.44:
                return "speeder"
            if roll < 0.58:
                return "lancer"
            if roll < 0.70:
                return "wisp"
            if roll < 0.82:
                return "wizard"
            if roll < 0.92:
                return "gunner"
            return "tank"
        if self.current_wave <= 11:
            if roll < 0.22:
                return "zombie"
            if roll < 0.34:
                return "speeder"
            if roll < 0.48:
                return "lancer"
            if roll < 0.60:
                return "wisp"
            if roll < 0.72:
                return "wizard"
            if roll < 0.84:
                return "gunner"
            if roll < 0.94:
                return "artillery"
            return "tank"
        if roll < 0.18:
            return "zombie"
        if roll < 0.30:
            return "speeder"
        if roll < 0.42:
            return "lancer"
        if roll < 0.52:
            return "wisp"
        if roll < 0.64:
            return "wizard"
        if roll < 0.76:
            return "gunner"
        if roll < 0.88:
            return "artillery"
        if roll < 0.95:
            return "exploder"
        return "tank"
