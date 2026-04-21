"""Runtime gameplay tuning settings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "gameplay_settings.json"


@dataclass(frozen=True, slots=True)
class SettingDefinition:
    key: str
    label: str
    description: str
    min_value: float
    max_value: float
    step: float
    default: float


@dataclass(slots=True)
class GameplaySettings:
    enemy_hp_mul: float = 1.0
    enemy_damage_mul: float = 1.0
    enemy_speed_mul: float = 1.0
    enemy_count_mul: float = 1.0
    gold_drop_mul: float = 2.0
    xp_gain_mul: float = 1.0
    player_hp_mul: float = 1.0
    player_damage_mul: float = 1.0
    player_speed_mul: float = 1.0
    player_attack_speed_mul: float = 1.0
    player_pickup_radius_mul: float = 1.0


DEFAULT_SETTINGS = GameplaySettings()
SETTING_DEFINITIONS: tuple[SettingDefinition, ...] = (
    SettingDefinition("enemy_hp_mul", "怪物生命倍率", "影响所有小怪、精英和 Boss 的基础生命值。", 0.3, 5.0, 0.1, DEFAULT_SETTINGS.enemy_hp_mul),
    SettingDefinition("enemy_damage_mul", "怪物攻击倍率", "影响敌人的接触伤害、技能伤害和弹幕伤害。", 0.3, 5.0, 0.1, DEFAULT_SETTINGS.enemy_damage_mul),
    SettingDefinition("enemy_speed_mul", "怪物速度倍率", "影响敌人的基础移动速度，位移技能本身不额外放大。", 0.4, 3.0, 0.1, DEFAULT_SETTINGS.enemy_speed_mul),
    SettingDefinition("enemy_count_mul", "怪物数量倍率", "影响普通波次的刷怪上限和刷新节奏。", 0.5, 3.0, 0.1, DEFAULT_SETTINGS.enemy_count_mul),
    SettingDefinition("gold_drop_mul", "金币掉落倍率", "影响敌人掉落金币的数量。默认已调整为 2 倍。", 0.5, 6.0, 0.25, DEFAULT_SETTINGS.gold_drop_mul),
    SettingDefinition("xp_gain_mul", "经验倍率", "影响敌人掉落的经验结晶总量。", 0.5, 5.0, 0.25, DEFAULT_SETTINGS.xp_gain_mul),
    SettingDefinition("player_hp_mul", "玩家生命倍率", "影响新开局时玩家的基础生命值上限。", 0.5, 3.0, 0.1, DEFAULT_SETTINGS.player_hp_mul),
    SettingDefinition("player_damage_mul", "玩家伤害倍率", "影响所有武器和技能造成的最终伤害。", 0.5, 4.0, 0.1, DEFAULT_SETTINGS.player_damage_mul),
    SettingDefinition("player_speed_mul", "玩家移速倍率", "影响新开局时玩家的基础移动速度。", 0.5, 3.0, 0.1, DEFAULT_SETTINGS.player_speed_mul),
    SettingDefinition("player_attack_speed_mul", "玩家攻速倍率", "影响武器冷却与持续型武器刷新频率。", 0.5, 3.0, 0.1, DEFAULT_SETTINGS.player_attack_speed_mul),
    SettingDefinition("player_pickup_radius_mul", "拾取范围倍率", "影响经验与金币的吸附和拾取范围。", 0.5, 3.0, 0.1, DEFAULT_SETTINGS.player_pickup_radius_mul),
)
_DEFINITION_MAP = {item.key: item for item in SETTING_DEFINITIONS}
_settings: GameplaySettings | None = None


def _step_decimals(step: float) -> int:
    text = f"{step:.4f}".rstrip("0").rstrip(".")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def clamp_value(key: str, value: float) -> float:
    meta = _DEFINITION_MAP[key]
    decimals = _step_decimals(meta.step)
    clamped = max(meta.min_value, min(meta.max_value, float(value)))
    steps = round((clamped - meta.min_value) / meta.step)
    snapped = meta.min_value + steps * meta.step
    return round(max(meta.min_value, min(meta.max_value, snapped)), decimals)


def _to_payload(settings: GameplaySettings) -> dict[str, float]:
    return {meta.key: getattr(settings, meta.key) for meta in SETTING_DEFINITIONS}


def _from_payload(data: dict) -> GameplaySettings:
    settings = GameplaySettings()
    for meta in SETTING_DEFINITIONS:
        setattr(settings, meta.key, clamp_value(meta.key, data.get(meta.key, meta.default)))
    return settings


def load_settings() -> GameplaySettings:
    global _settings
    if _settings is not None:
        return _settings

    if not _SETTINGS_PATH.exists():
        _settings = GameplaySettings()
        return _settings

    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _settings = GameplaySettings()
        return _settings

    if not isinstance(data, dict):
        _settings = GameplaySettings()
        return _settings

    _settings = _from_payload(data)
    return _settings


def get_settings() -> GameplaySettings:
    return load_settings()


def save_settings(settings: GameplaySettings | None = None) -> None:
    target = settings or get_settings()
    payload = _to_payload(target)
    _SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def set_setting(key: str, value: float) -> float:
    settings = get_settings()
    snapped = clamp_value(key, value)
    setattr(settings, key, snapped)
    save_settings(settings)
    return snapped


def adjust_setting(key: str, direction: int) -> float:
    meta = _DEFINITION_MAP[key]
    settings = get_settings()
    current = getattr(settings, key)
    return set_setting(key, current + meta.step * direction)


def reset_settings() -> GameplaySettings:
    global _settings
    _settings = GameplaySettings()
    save_settings(_settings)
    return _settings
