"""Shop offer generation and application."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.config import RARITY_COLORS
from src.core.rng import rng


@dataclass(slots=True)
class ShopOffer:
    offer_id: str
    name: str
    description: str
    rarity: str
    cost: int
    payload: dict
    sold: bool = False

    @property
    def color(self) -> tuple[int, int, int]:
        return RARITY_COLORS[self.rarity]

    @property
    def rarity_label(self) -> str:
        return {
            "common": "普通",
            "uncommon": "精良",
            "rare": "稀有",
            "epic": "史诗",
            "legendary": "传说",
        }[self.rarity]


_SHOP_POOL = [
    ("heal_patch", "战地绷带", "立即回复 40 点生命。", "common", 16, {"heal": 40}),
    ("max_hp", "巨像骨架", "最大生命值永久提高 20。", "common", 24, {"max_hp": 20}),
    ("attack", "锋刃刻印", "伤害提高 12%。", "uncommon", 26, {"atk_mul": 0.12}),
    ("speed", "速射扳机", "攻击速度提高 15%。", "uncommon", 24, {"atk_speed_mul": 0.15}),
    ("range", "聚焦线圈", "武器范围提高 15%。", "common", 20, {"range_mul": 0.15}),
    ("armor", "铁壁装甲", "护甲提高 1 点。", "uncommon", 25, {"armor": 1}),
    ("pickup", "磁暴吸环", "拾取范围提高 28。", "common", 18, {"pickup_radius": 28}),
    ("crit", "幸运徽记", "暴击率提高 6%。", "rare", 34, {"crit_rate": 0.06}),
    ("projectile", "分裂弹膛", "额外投射物 +1。", "rare", 42, {"proj_bonus": 1}),
    ("gold", "黄金钩爪", "金币收益提高 20%。", "common", 18, {"gold_mul": 0.20}),
]


def build_shop_offers(player, wave: int, count: int = 4) -> list[ShopOffer]:
    entries = list(_SHOP_POOL)
    rng.shuffle(entries)
    offers: list[ShopOffer] = []
    for offer_id, name, desc, rarity, base_cost, payload in entries[:count]:
        wave_cost = max(0, wave - 1) * (2 if rarity in ("rare", "epic", "legendary") else 1)
        offers.append(
            ShopOffer(
                offer_id=offer_id,
                name=name,
                description=desc,
                rarity=rarity,
                cost=base_cost + wave_cost,
                payload=dict(payload),
            )
        )
    return offers


def refresh_cost(refresh_count: int) -> int:
    return 8 + refresh_count * 6


def apply_shop_offer(player, offer: ShopOffer) -> str:
    payload = offer.payload
    if "heal" in payload:
        player.heal(payload["heal"])
        return f"{offer.name} 已购买"

    if "max_hp" in payload:
        player.stats.max_hp += payload["max_hp"]
        player.heal(payload["max_hp"])
    if "atk_mul" in payload:
        player.stats.atk_mul += payload["atk_mul"]
    if "atk_speed_mul" in payload:
        player.stats.atk_speed_mul += payload["atk_speed_mul"]
    if "range_mul" in payload:
        player.stats.range_mul += payload["range_mul"]
    if "armor" in payload:
        player.stats.armor += payload["armor"]
    if "pickup_radius" in payload:
        player.stats.pickup_radius += payload["pickup_radius"]
    if "crit_rate" in payload:
        player.stats.crit_rate += payload["crit_rate"]
    if "proj_bonus" in payload:
        player.stats.proj_bonus += payload["proj_bonus"]
    if "gold_mul" in payload:
        player.stats.gold_mul += payload["gold_mul"]
    return f"{offer.name} 已购买"
