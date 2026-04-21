"""Wave progression and enemy spawn scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.config import (
    BOSS_WAVE_INTERVAL,
    DIFFICULTY_SETTINGS,
    ELITE_WAVE_INTERVAL,
    TOTAL_WAVES,
    WAVE_BASE_DURATION,
    WAVE_BREAK_DURATION,
    WAVE_DURATION_INC,
)
from src.core.rng import rng

BOSS_POOL: tuple[str, ...] = (
    "geometric_devourer",
    "storm_tyrant",
    "void_colossus",
)

ELITE_POOL: tuple[str, ...] = (
    "elite_summoner",
    "elite_berserker",
    "elite_assassin",
    "elite_sentinel",
    "elite_missile_sniper",
)


@dataclass(slots=True)
class WaveBanner:
    text: str
    timer: float = 2.0


@dataclass(slots=True)
class WaveStep:
    spawns: list[dict | str] = field(default_factory=list)
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
        self._elite_spawned = False
        self._current_boss_type: str | None = None
        self._used_bosses: set[str] = set()

    @property
    def is_break(self) -> bool:
        return self.state == "break"

    @property
    def is_boss_wave(self) -> bool:
        return self.current_wave % BOSS_WAVE_INTERVAL == 0

    @property
    def is_elite_wave(self) -> bool:
        return not self.is_boss_wave and self.current_wave % ELITE_WAVE_INTERVAL == 0

    @property
    def boss_rank(self) -> int:
        return max(1, self.current_wave // BOSS_WAVE_INTERVAL)

    @property
    def wave_duration(self) -> float:
        return min(60.0, WAVE_BASE_DURATION + WAVE_DURATION_INC * (self.current_wave - 1))

    @property
    def time_left(self) -> float:
        if self.state == "break":
            return max(0.0, WAVE_BREAK_DURATION - self.time_in_state)
        if self.cleanup_mode or self.is_boss_wave:
            return 0.0
        return max(0.0, self.wave_duration - self.time_in_state)

    def update(self, dt: float, alive_count: int, boss_alive: bool = False) -> WaveStep:
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

        if self.is_boss_wave:
            if not self._boss_spawned:
                step.spawns = self._boss_wave_spawns()
                return step
            if self._boss_spawned and not boss_alive:
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

        step.spawns = self._normal_wave_spawns(dt, alive_count)
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

    def _start_next_wave(self) -> None:
        self.current_wave += 1
        self.state = "wave"
        self.time_in_state = 0.0
        self.spawn_timer = 0.0
        self._boss_spawned = False
        self._elite_spawned = False
        self._current_boss_type = None

        title = f"第 {self.current_wave} 波开始"
        if self.is_boss_wave:
            title += "  首领来袭"
        elif self.is_elite_wave:
            title += "  精英波"
        self.banner = WaveBanner(title)

    def _boss_wave_spawns(self) -> list[dict]:
        if self._boss_spawned:
            return []
        self._boss_spawned = True
        boss_type = self._pick_boss_type()
        self._current_boss_type = boss_type
        return [{"etype": boss_type, "boss_rank": self.boss_rank}]

    def _pick_boss_type(self) -> str:
        available = [boss for boss in BOSS_POOL if boss not in self._used_bosses]
        if not available:
            self._used_bosses.clear()
            available = list(BOSS_POOL)
        boss_type = rng.choice(available)
        self._used_bosses.add(boss_type)
        return boss_type

    def _normal_wave_spawns(self, dt: float, alive_count: int) -> list[str]:
        cap = int(34 + self.current_wave * 10 * DIFFICULTY_SETTINGS[self.difficulty]["count_mul"])
        if alive_count >= cap:
            return []

        spawns: list[str] = []
        if self.is_elite_wave and not self._elite_spawned:
            spawns.append(self._choose_elite_type())
            self._elite_spawned = True

        self.spawn_timer += dt
        interval = max(0.17, 1.08 - self.current_wave * 0.03)
        interval /= max(0.8, DIFFICULTY_SETTINGS[self.difficulty]["count_mul"])
        while self.spawn_timer >= interval:
            self.spawn_timer -= interval
            batch = 1 + (1 if self.current_wave >= 8 and rng.chance(0.45) else 0)
            for _ in range(batch):
                spawns.append(self._choose_enemy_type())
        return spawns

    def _choose_elite_type(self) -> str:
        if self.current_wave < 6:
            return "elite_summoner"
        if self.current_wave < 9:
            return rng.choice(("elite_summoner", "elite_berserker"))
        if self.current_wave < 12:
            return rng.choice(("elite_summoner", "elite_berserker", "elite_assassin"))
        if self.current_wave < 15:
            return rng.choice(("elite_assassin", "elite_sentinel", "elite_missile_sniper"))
        return rng.choice(ELITE_POOL)

    def _choose_enemy_type(self) -> str:
        roll = rng.random()
        if self.current_wave <= 2:
            if roll < 0.60:
                return "zombie"
            if roll < 0.86:
                return "speeder"
            return "razorbat"
        if self.current_wave <= 4:
            if roll < 0.28:
                return "zombie"
            if roll < 0.46:
                return "speeder"
            if roll < 0.58:
                return "lancer"
            if roll < 0.70:
                return "razorbat"
            if roll < 0.80:
                return "blink_skirmisher"
            if roll < 0.90:
                return "slime_large"
            if roll < 0.96:
                return "exploder"
            return "wizard"
        if self.current_wave <= 7:
            if roll < 0.17:
                return "zombie"
            if roll < 0.29:
                return "speeder"
            if roll < 0.39:
                return "lancer"
            if roll < 0.49:
                return "wisp"
            if roll < 0.57:
                return "razorbat"
            if roll < 0.64:
                return "blink_skirmisher"
            if roll < 0.71:
                return "embermine"
            if roll < 0.77:
                return "slime_large"
            if roll < 0.83:
                return "brood_seeder"
            if roll < 0.88:
                return "blackhole_mage"
            if roll < 0.93:
                return "line_raider"
            if roll < 0.97:
                return "wizard"
            return "gunner"
        if self.current_wave <= 11:
            if roll < 0.10:
                return "zombie"
            if roll < 0.18:
                return "speeder"
            if roll < 0.26:
                return "lancer"
            if roll < 0.34:
                return "wisp"
            if roll < 0.42:
                return "razorbat"
            if roll < 0.49:
                return "blink_skirmisher"
            if roll < 0.56:
                return "embermine"
            if roll < 0.62:
                return "brood_seeder"
            if roll < 0.69:
                return "slime_large"
            if roll < 0.75:
                return "shield_caster"
            if roll < 0.80:
                return "blackhole_mage"
            if roll < 0.85:
                return "line_raider"
            if roll < 0.89:
                return "wizard"
            if roll < 0.93:
                return "gunner"
            if roll < 0.97:
                return "siege_pylon"
            if roll < 0.99:
                return "artillery"
            return "tank"
        if roll < 0.08:
            return "zombie"
        if roll < 0.15:
            return "speeder"
        if roll < 0.22:
            return "lancer"
        if roll < 0.29:
            return "wisp"
        if roll < 0.36:
            return "razorbat"
        if roll < 0.43:
            return "blink_skirmisher"
        if roll < 0.50:
            return "embermine"
        if roll < 0.57:
            return "brood_seeder"
        if roll < 0.64:
            return "slime_large"
        if roll < 0.70:
            return "shield_caster"
        if roll < 0.75:
            return "blackhole_mage"
        if roll < 0.80:
            return "line_raider"
        if roll < 0.85:
            return "wizard"
        if roll < 0.90:
            return "gunner"
        if roll < 0.95:
            return "siege_pylon"
        if roll < 0.98:
            return "artillery"
        if roll < 0.995:
            return "exploder"
        return "tank"
