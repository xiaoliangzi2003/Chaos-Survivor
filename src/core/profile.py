"""Simple local profile storage for difficulty unlocks and bestiary progress."""

from __future__ import annotations
import json
from pathlib import Path

from src.core.config import DIFFICULTY_NAMES

def get_save_path() -> Path:
    save_dir = Path.home() / "Documents" / "Chaos Survivor"
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / "player_profile.json"

_PROFILE_PATH = get_save_path()


def _default_profile() -> dict:
    return {
        "max_unlocked_difficulty": 0,
        "defeated_enemy_ids": [],
    }


def _normalize_profile(data: dict | None) -> dict:
    profile = _default_profile()
    if not isinstance(data, dict):
        return profile

    max_idx = int(data.get("max_unlocked_difficulty", 0))
    profile["max_unlocked_difficulty"] = max(0, min(len(DIFFICULTY_NAMES) - 1, max_idx))

    defeated = data.get("defeated_enemy_ids", [])
    if isinstance(defeated, (list, tuple, set)):
        profile["defeated_enemy_ids"] = sorted({str(enemy_id) for enemy_id in defeated if str(enemy_id).strip()})
    return profile


def load_profile() -> dict:
    save_path = get_save_path()

    if not save_path.exists():
        default = _default_profile()
        save_profile(default)
        return default

    try:
        with open(save_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return _default_profile()

    return _normalize_profile(data)


def save_profile(data):
    save_path = get_save_path()
    data = _normalize_profile(data)
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_max_unlocked_difficulty() -> int:
    return load_profile()["max_unlocked_difficulty"]


def unlock_next_difficulty(current_difficulty: int) -> tuple[int, bool]:
    profile = load_profile()
    previous = profile["max_unlocked_difficulty"]
    unlocked = max(previous, min(len(DIFFICULTY_NAMES) - 1, current_difficulty + 1))
    changed = unlocked > previous
    if changed:
        profile["max_unlocked_difficulty"] = unlocked
        save_profile(profile)
    return unlocked, changed


def clamp_difficulty(difficulty: int) -> int:
    return max(0, min(get_max_unlocked_difficulty(), difficulty))


def get_defeated_enemy_ids() -> set[str]:
    return set(load_profile()["defeated_enemy_ids"])


def has_defeated_enemy(enemy_id: str) -> bool:
    return enemy_id in get_defeated_enemy_ids()


def record_defeated_enemy(enemy_id: str) -> bool:
    enemy_id = str(enemy_id).strip()
    if not enemy_id:
        return False

    profile = load_profile()
    defeated = set(profile["defeated_enemy_ids"])
    if enemy_id in defeated:
        return False

    defeated.add(enemy_id)
    profile["defeated_enemy_ids"] = sorted(defeated)
    save_profile(profile)
    return True
