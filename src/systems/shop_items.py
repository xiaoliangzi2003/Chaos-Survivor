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
    # ── 回复类 ──────────────────────────────────────────────────────────────
    ("heal_patch",    "战地绷带",   "立刻回复 40 点生命。",                       "common",   16, {"heal": 40}),
    ("big_heal",      "急救血包",   "立刻回复 80 点生命。",                       "uncommon", 28, {"heal": 80}),
    ("full_heal",     "不死药剂",   "立刻将生命回复至上限。",                     "rare",     45, {"heal_full": True}),
    ("hp_regen",      "活泉髓液",   "每秒回复 1.5 点生命。",                      "uncommon", 30, {"hp_regen": 1.5}),
    # ── 生存强化 ────────────────────────────────────────────────────────────
    ("max_hp",        "巨像骨架",   "最大生命永久提高 20。",                      "common",   24, {"max_hp": 20}),
    ("big_max_hp",    "不朽铁盾",   "最大生命提高 40，护甲提高 1。",              "rare",     42, {"max_hp": 40, "armor": 1}),
    ("armor",         "铁壁装甲",   "护甲提高 1 点。",                            "uncommon", 25, {"armor": 1}),
    ("big_armor",     "钢铁要塞",   "护甲提高 3 点。",                            "rare",     40, {"armor": 3}),
    ("dodge",         "幻影步法",   "闪避率提高 8%。",                            "rare",     36, {"dodge_rate": 0.08}),
    ("guardian_bear", "护身小熊",   "获得一次完全免伤护盾，将吸收下一次伤害。",   "epic",     50, {"guardian_shield": 1}),
    # ── 攻击强化 ────────────────────────────────────────────────────────────
    ("attack",        "锋刃刻印",   "伤害提高 12%。",                             "uncommon", 26, {"atk_mul": 0.12}),
    ("big_attack",    "屠神之刃",   "伤害提高 22%。",                             "rare",     40, {"atk_mul": 0.22}),
    ("speed",         "速射扳机",   "攻击速度提高 15%。",                         "uncommon", 24, {"atk_speed_mul": 0.15}),
    ("big_speed",     "超频模块",   "攻击速度提高 28%。",                         "rare",     40, {"atk_speed_mul": 0.28}),
    ("crit",          "幸运徽记",   "暴击率提高 6%。",                            "rare",     34, {"crit_rate": 0.06}),
    ("big_crit",      "命运齿轮",   "暴击率提高 12%。",                           "epic",     52, {"crit_rate": 0.12}),
    ("crit_damage",   "破甲锐刃",   "暴击伤害提高 25%。",                         "rare",     38, {"crit_mul": 0.25}),
    ("projectile",    "分裂弹巢",   "额外投射物 +1。",                            "rare",     42, {"proj_bonus": 1}),
    ("multi_proj",    "弹雨巢穴",   "额外投射物 +2。",                            "epic",     65, {"proj_bonus": 2}),
    ("range",         "聚焦线圈",   "武器范围提高 15%。",                         "common",   20, {"range_mul": 0.15}),
    # ── 机动强化 ────────────────────────────────────────────────────────────
    ("move_speed",    "疾风胫甲",   "移动速度永久提高 26。",                      "uncommon", 24, {"move_speed": 26}),
    ("big_move",      "光速腿甲",   "移动速度永久提高 45。",                      "rare",     36, {"move_speed": 45}),
    # ── 拾取 / 金币 ─────────────────────────────────────────────────────────
    ("pickup",        "磁暴吸环",   "拾取范围提高 28。",                          "common",   18, {"pickup_radius": 28}),
    ("big_pickup",    "引力场核",   "拾取范围提高 60。",                          "uncommon", 28, {"pickup_radius": 60}),
    ("gold",          "黄金钩爪",   "金币收益提高 20%。",                         "common",   18, {"gold_mul": 0.20}),
    ("gold_magnet",   "财富法则",   "金币收益提高 40%，拾取范围提高 18。",        "uncommon", 28, {"gold_mul": 0.40, "pickup_radius": 18}),
    ("xp_boost",      "求知渴望",   "经验获取提高 20%。",                         "common",   20, {"xp_mul": 0.20}),
    # ── 复合 / 特殊 ─────────────────────────────────────────────────────────
    ("speed_combo",   "风暴双刃",   "攻击速度提高 10%，移动速度提高 20。",        "uncommon", 32, {"atk_speed_mul": 0.10, "move_speed": 20}),
    ("atk_range",     "星爆核心",   "伤害提高 8%，武器范围提高 10%。",            "uncommon", 30, {"atk_mul": 0.08, "range_mul": 0.10}),
    ("all_rounder",   "均衡印记",   "伤害+6%，攻速+8%，移速+18，暴击+3%。",      "epic",     55, {"atk_mul": 0.06, "atk_speed_mul": 0.08, "move_speed": 18, "crit_rate": 0.03}),
    ("glass_cannon",  "破坏者意志", "伤害提高 25%，但最大生命降低 20。",          "epic",     38, {"atk_mul": 0.25, "max_hp": -20}),
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

    if "heal_full" in payload:
        player.heal(player.stats.max_hp)
        return f"{offer.name} 已购买"

    if "guardian_shield" in payload:
        player._guardian_shields += payload["guardian_shield"]

    if "max_hp" in payload:
        delta = payload["max_hp"]
        player.stats.max_hp = max(1, player.stats.max_hp + delta)
        if delta > 0:
            player.heal(delta)
        else:
            player.hp = min(player.hp, player.stats.max_hp)

    if "hp_regen" in payload:
        player.stats.hp_regen += payload["hp_regen"]
    if "atk_mul" in payload:
        player.stats.atk_mul += payload["atk_mul"]
    if "atk_speed_mul" in payload:
        player.stats.atk_speed_mul += payload["atk_speed_mul"]
    if "move_speed" in payload:
        player.stats.speed += payload["move_speed"]
    if "range_mul" in payload:
        player.stats.range_mul += payload["range_mul"]
    if "armor" in payload:
        player.stats.armor += payload["armor"]
    if "pickup_radius" in payload:
        player.stats.pickup_radius += payload["pickup_radius"]
    if "crit_rate" in payload:
        player.stats.crit_rate += payload["crit_rate"]
    if "crit_mul" in payload:
        player.stats.crit_mul += payload["crit_mul"]
    if "proj_bonus" in payload:
        player.stats.proj_bonus += payload["proj_bonus"]
    if "gold_mul" in payload:
        player.stats.gold_mul += payload["gold_mul"]
    if "xp_mul" in payload:
        player.stats.xp_mul += payload["xp_mul"]
    if "dodge_rate" in payload:
        player.stats.dodge_rate += payload["dodge_rate"]

    return f"{offer.name} 已购买"
