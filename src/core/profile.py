"""Simple local profile storage for difficulty unlocks and bestiary progress."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import DIFFICULTY_NAMES

_PROFILE_PATH = Path(__file__).resolve().parents[1] / "player_profile.json"


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
    if not _PROFILE_PATH.exists():
        return _default_profile()
    try:
        data = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_profile()
    return _normalize_profile(data)


def save_profile(profile: dict) -> None:
    payload = _normalize_profile(profile)
    _PROFILE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
