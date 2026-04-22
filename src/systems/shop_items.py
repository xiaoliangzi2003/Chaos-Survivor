"""Shop offer generation and application."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    locked: bool = False

    @property
    def color(self) -> tuple[int, int, int]:
        return RARITY_COLORS[self.rarity]

    @property
    def rarity_label(self) -> str:
        return {
            "common": "普通",
            "uncommon": "优秀",
            "rare": "精良",
            "epic": "史诗",
            "legendary": "传说",
        }[self.rarity]


_SHOP_POOL = [
    # (offer_id, name, description, rarity, base_cost, payload)
    ("heal_patch",     "战地绷带",   "立刻回复 40 点生命值。",                               "common",   14, {"heal": 40}),
    ("regen_potion",   "回复药剂",   "每秒回复 5 点生命，持续 10 秒。",                      "uncommon", 22, {"hp_regen_temp": (5.0, 10.0)}),
    ("heart_vessel",   "心之容器",   "生命上限提升 20 点。",                                 "common",   20, {"max_hp": 20}),
    ("phantom_cloak",  "幻影斗篷",   "闪避几率提升 8%。",                                    "rare",     36, {"dodge_rate": 0.08}),
    ("totem_undying",  "不死图腾",   "获得一次完全免伤护盾，可吸收下一次伤害。",            "epic",     52, {"guardian_shield": 1}),
    ("rapid_trigger",  "速射扳机",   "攻击速度提升 10%。",                                   "uncommon", 24, {"atk_speed_mul": 0.10}),
    ("lucky_seal",     "幸运印记",   "幸运值提升 5 点，增加稀有物品出现概率。",             "uncommon", 18, {"lucky": 5}),
    ("power_gauntlet", "暴力拳套",   "暴击几率提升 12%。",                                   "rare",     34, {"crit_rate": 0.12}),
    ("split_nest",     "分裂弹巢",   "额外投射物 +1，但伤害降低为原来的 90%。",             "rare",     38, {"proj_bonus": 1, "atk_mul_factor": 0.9}),
    ("wind_boots",     "疾风之靴",   "移动速度提升 10%。",                                   "uncommon", 22, {"speed_mul": 0.10}),
    ("holy_shield",    "神圣护盾",   "防御值提升 1 点。",                                    "common",   18, {"armor": 1}),
    ("vampire_bat",    "吸血蝙蝠",   "攻击时回复造成伤害 1% 的生命值。",                    "rare",     40, {"vampire": 0.01}),
    ("magnet",         "吸铁石",     "拾取范围提升 40。",                                    "common",   16, {"pickup_radius": 40}),
    ("higher_math",    "高等数学",   "经验获取提高 20%。",                                   "common",   18, {"xp_mul": 0.20}),
    ("gold_magnet",    "吸金磁",     "金币收益提高 20%。",                                   "uncommon", 22, {"gold_mul": 0.20}),
    ("adrenaline",     "肾上腺素",   "本波未受伤时伤害 ×150%，受伤后失效，每波重置。",      "epic",     48, {"adrenaline": True}),
    ("voucher",        "购物券",     "获得 1 张购物券，可免费购买商店中任意商品。",          "epic",     30, {"voucher": 1}),
    ("white_flag",     "白色旗帜",   "怪物数量减少 10%。",                                   "uncommon", 20, {"enemy_count_mul": 0.90}),
    ("monster_bait",   "怪物诱饵",   "怪物数量增加 10%（高风险高回报）。",                  "common",    8, {"enemy_count_mul": 1.10}),
    ("heavy_armor",    "沉重盔甲",   "防御值提升 2 点，但移动速度降低 10%。",               "uncommon", 26, {"armor": 2, "speed_mul": -0.10}),
    ("berserker_mark", "狂战印记",   "血量越低，伤害越高（最高可达 180% 伤害）。",           "epic",     46, {"berserker": True}),
    ("coin_attack",    "金弹之器",   "拾取金币时 40% 概率对随机敌人造成 30 点伤害。",       "uncommon", 22, {"coin_attack": True}),
    ("long_stick",     "长杆",       "武器攻击范围提升 20。",                               "common",   18, {"range_bonus": 20.0}),
    ("mine_item",      "地雷",       "每 12 秒在脚下生成一枚地雷，波次间保留。",            "rare",     40, {"mine_item": True}),
    ("prism",          "三棱镜",     "每持有 1 种武器提升 5% 伤害（当前武器数量生效）。",   "rare",     36, {"prism": True}),
    ("turret_item",    "炮塔",       "每 12 秒生成一座自动炮塔攻击敌人，波次间保留。",      "epic",     50, {"turret_item": True}),
    ("mushroom_item",  "毒蘑菇",     "每 30 秒生成毒蘑菇，吸引敌人并使其中毒，波次间保留。","epic",    48, {"mushroom_item": True}),
    ("knockback_bat",  "击退棒",     "击退力提升 2 点。",                                   "common",   16, {"kb_bonus": 2.0}),
    ("bait",           "诱饵",       "伤害提升 15%，下一波次将额外出现一只精英怪。",        "uncommon", 26, {"atk_mul": 0.15, "spawn_elite": 1}),
    ("campfire",       "篝火",       "在原地生成篝火，站在附近时每秒回复 1 点生命值。",     "uncommon", 24, {"campfire": True}),
]

# Rarity weights at lucky=0
_RARITY_BASE: dict[str, float] = {
    "common":    50.0,
    "uncommon":  30.0,
    "rare":      15.0,
    "epic":       4.0,
    "legendary":  1.0,
}


def _rarity_weights(lucky: int) -> dict[str, float]:
    bonus = min(lucky, 60)
    w = dict(_RARITY_BASE)
    w["common"]    = max(5.0, w["common"]    - bonus * 0.8)
    w["uncommon"]  = max(5.0, w["uncommon"]  - bonus * 0.2)
    w["rare"]      = max(10.0, w["rare"]     + bonus * 0.5)
    w["epic"]      =           w["epic"]     + bonus * 0.3
    w["legendary"] =           w["legendary"] + bonus * 0.2
    return w


def build_shop_offers(
    player,
    wave: int,
    count: int = 4,
    locked_offers: list[ShopOffer] | None = None,
) -> list[ShopOffer]:
    locked = [o for o in (locked_offers or []) if o.locked]
    locked_ids = {o.offer_id for o in locked}

    lucky = getattr(getattr(player, "stats", None), "lucky", 0)
    weights = _rarity_weights(lucky)
    weight_values = list(weights.values())
    rarities = list(weights.keys())

    # Pool grouped by rarity, excluding locked items
    pool_by_rarity: dict[str, list] = {r: [] for r in rarities}
    for entry in _SHOP_POOL:
        if entry[0] not in locked_ids:
            r = entry[3]
            if r in pool_by_rarity:
                pool_by_rarity[r].append(entry)

    remaining = count - len(locked)
    new_offers: list[ShopOffer] = []
    chosen_ids: set[str] = set()

    for _ in range(max(0, remaining)):
        # Pick rarity weighted by lucky
        picked_rarity = rng.choices(rarities, weights=weight_values, k=1)[0]

        candidates = [e for e in pool_by_rarity[picked_rarity] if e[0] not in chosen_ids]
        if not candidates:
            # Fall back to any available entry
            candidates = [e for e in _SHOP_POOL if e[0] not in locked_ids and e[0] not in chosen_ids]
        if not candidates:
            break

        entry = rng.choice(candidates)
        chosen_ids.add(entry[0])
        offer_id, name, desc, rarity, base_cost, payload = entry
        wave_cost = max(0, wave - 1) * (2 if rarity in ("rare", "epic", "legendary") else 1)
        new_offers.append(
            ShopOffer(
                offer_id=offer_id,
                name=name,
                description=desc,
                rarity=rarity,
                cost=base_cost + wave_cost,
                payload=dict(payload),
            )
        )

    return locked + new_offers


def refresh_cost(refresh_count: int) -> int:
    return 8 + refresh_count * 6


def apply_shop_offer(player, offer: ShopOffer) -> str:
    p = offer.payload

    if "heal" in p:
        player.heal(p["heal"])

    if "hp_regen_temp" in p:
        rate, duration = p["hp_regen_temp"]
        player._timed_regen_buffs.append([rate, duration])

    if "max_hp" in p:
        delta = p["max_hp"]
        player.stats.max_hp = max(1, player.stats.max_hp + delta)
        if delta > 0:
            player.heal(delta)
        else:
            player.hp = min(player.hp, player.stats.max_hp)

    if "guardian_shield" in p:
        player._guardian_shields += p["guardian_shield"]

    if "dodge_rate" in p:
        player.stats.dodge_rate += p["dodge_rate"]

    if "atk_speed_mul" in p:
        player.stats.atk_speed_mul += p["atk_speed_mul"]

    if "lucky" in p:
        player.stats.lucky += p["lucky"]

    if "crit_rate" in p:
        player.stats.crit_rate += p["crit_rate"]

    if "proj_bonus" in p:
        player.stats.proj_bonus += p["proj_bonus"]

    if "atk_mul" in p:
        player.stats.atk_mul += p["atk_mul"]

    if "atk_mul_factor" in p:
        player.stats.atk_mul *= p["atk_mul_factor"]

    if "speed_mul" in p:
        player.stats.speed = int(player.stats.speed * (1.0 + p["speed_mul"]))

    if "armor" in p:
        player.stats.armor += p["armor"]

    if "vampire" in p:
        player.stats.vampire += p["vampire"]

    if "pickup_radius" in p:
        player.stats.pickup_radius += p["pickup_radius"]

    if "xp_mul" in p:
        player.stats.xp_mul += p["xp_mul"]

    if "gold_mul" in p:
        player.stats.gold_mul += p["gold_mul"]

    if "adrenaline" in p:
        player.stats.adrenaline = True
        player.adrenaline_active = True

    if "voucher" in p:
        player.vouchers += p["voucher"]

    if "enemy_count_mul" in p:
        new_mul = player.stats.enemy_count_mul * p["enemy_count_mul"]
        player.stats.enemy_count_mul = max(0.5, new_mul) if p["enemy_count_mul"] < 1.0 else new_mul

    if "berserker" in p:
        player.stats.berserker = True

    if "range_bonus" in p:
        player.stats.range_bonus += p["range_bonus"]

    if "kb_bonus" in p:
        player.stats.kb_bonus += p["kb_bonus"]

    if "coin_attack" in p:
        player.stats.coin_attack = True

    if "prism" in p:
        player.stats.prism = True

    if "mine_item" in p:
        player.stats.mine_item = True

    if "turret_item" in p:
        player.stats.turret_item = True

    if "mushroom_item" in p:
        player.stats.mushroom_item = True

    if "spawn_elite" in p:
        player.spawn_elite_count += p["spawn_elite"]

    if "campfire" in p:
        cb = getattr(player, "spawn_campfire_callback", None)
        if cb is not None:
            cb()

    return f"{offer.name} 已购买"
