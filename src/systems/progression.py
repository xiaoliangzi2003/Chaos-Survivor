"""Upgrade option generation for the level-up scene."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import RARITY_COLORS
from src.core.rng import rng
from src.weapons import WEAPON_ORDER, WEAPON_REGISTRY, create_weapon

MAX_WEAPON_SLOTS = len(WEAPON_ORDER)

RARITY_NAMES = {
    "common": "普通",
    "uncommon": "精良",
    "rare": "稀有",
    "epic": "史诗",
    "legendary": "传说",
}

_STAT_LABELS = {
    "damage": "伤害",
    "count": "数量",
    "pierce": "穿透",
    "cooldown": "冷却",
    "radius": "范围",
    "orbit_radius": "环绕半径",
    "chain_range": "连锁距离",
    "explode_dmg": "爆炸伤害",
    "explode_r": "爆炸范围",
    "slow_dur": "减速持续",
    "slow_mul": "减速幅度",
}


@dataclass(slots=True)
class UpgradeOption:
    option_type: str
    title: str
    description: str
    rarity: str
    weapon_id: str | None = None
    current_level: int = 0
    next_level: int = 1

    @property
    def color(self) -> tuple[int, int, int]:
        return RARITY_COLORS[self.rarity]

    @property
    def rarity_label(self) -> str:
        return RARITY_NAMES[self.rarity]


def build_upgrade_options(player, count: int = 3) -> list[UpgradeOption]:
    options: list[UpgradeOption] = []
    owned_ids = {getattr(weapon, "weapon_id", "") for weapon in player.weapons}

    for weapon in player.weapons:
        if weapon.level >= weapon.MAX_LEVEL:
            continue
        next_level = weapon.level + 1
        options.append(
            UpgradeOption(
                option_type="weapon_upgrade",
                title=f"{weapon.NAME} {next_level} 级",
                description=_describe_weapon_upgrade(weapon),
                rarity=_rarity_for_level(next_level),
                weapon_id=getattr(weapon, "weapon_id", None),
                current_level=weapon.level,
                next_level=next_level,
            )
        )

    if len(player.weapons) < MAX_WEAPON_SLOTS:
        for weapon_id in WEAPON_ORDER:
            if weapon_id in owned_ids:
                continue
            weapon_cls = WEAPON_REGISTRY[weapon_id]
            options.append(
                UpgradeOption(
                    option_type="weapon_new",
                    title=weapon_cls.NAME,
                    description=weapon_cls.DESCRIPTION,
                    rarity="common",
                    weapon_id=weapon_id,
                    current_level=0,
                    next_level=1,
                )
            )

    if not options:
        options.append(
            UpgradeOption(
                option_type="fallback",
                title="活力强化",
                description="回复 30 点生命，并永久提高 10 点最大生命。",
                rarity="uncommon",
            )
        )

    rng.shuffle(options)
    options.sort(key=lambda item: _rarity_rank(item.rarity), reverse=True)
    return options[:count]


def apply_upgrade(player, option: UpgradeOption) -> str:
    if option.option_type == "weapon_new" and option.weapon_id:
        player.add_weapon(create_weapon(option.weapon_id))
        return f"获得新武器：{option.title}"

    if option.option_type == "weapon_upgrade" and option.weapon_id:
        weapon = player.get_weapon(option.weapon_id)
        if weapon and weapon.level_up():
            return f"{weapon.NAME} 升至 {weapon.level} 级"

    player.stats.max_hp += 10
    player.heal(30)
    return "活力强化生效"


def _describe_weapon_upgrade(weapon) -> str:
    current = weapon.LEVEL_DATA[weapon.level - 1]
    next_data = weapon.LEVEL_DATA[weapon.level]
    parts: list[str] = []

    for key, label in _STAT_LABELS.items():
        if key not in current or key not in next_data:
            continue
        before = current[key]
        after = next_data[key]
        if before == after:
            continue
        if key == "cooldown":
            parts.append(f"{label} {before:.2f}秒 -> {after:.2f}秒")
        elif key == "slow_mul":
            parts.append(f"{label} {int((1 - before) * 100)}% -> {int((1 - after) * 100)}%")
        else:
            parts.append(f"{label} {before} -> {after}")

    if not parts:
        return "强化这把武器的核心性能。"
    return "，".join(parts[:3])


def _rarity_for_level(level: int) -> str:
    if level >= 8:
        return "legendary"
    if level >= 7:
        return "epic"
    if level >= 5:
        return "rare"
    if level >= 3:
        return "uncommon"
    return "common"


def _rarity_rank(rarity: str) -> int:
    order = {
        "common": 0,
        "uncommon": 1,
        "rare": 2,
        "epic": 3,
        "legendary": 4,
    }
    return order[rarity]
