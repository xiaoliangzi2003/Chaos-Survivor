"""Simple local profile storage for difficulty unlocks."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import DIFFICULTY_NAMES

_PROFILE_PATH = Path(__file__).resolve().parents[1] / "player_profile.json"


def load_profile() -> dict:
    if not _PROFILE_PATH.exists():
        return {"max_unlocked_difficulty": 0}
    try:
        data = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"max_unlocked_difficulty": 0}
    max_idx = int(data.get("max_unlocked_difficulty", 0))
    return {"max_unlocked_difficulty": max(0, min(len(DIFFICULTY_NAMES) - 1, max_idx))}


def save_profile(profile: dict) -> None:
    payload = {"max_unlocked_difficulty": max(0, min(len(DIFFICULTY_NAMES) - 1, int(profile.get("max_unlocked_difficulty", 0))))}
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
