"""Weapon registry and factory helpers."""

from __future__ import annotations

from src.weapons.chain_lightning import ChainLightning
from src.weapons.fire_nova import FireNova
from src.weapons.homing_missile import HomingMissile
from src.weapons.ice_dart import IceDart
from src.weapons.magic_dagger import MagicDagger
from src.weapons.orbit_orb import OrbitOrb

WEAPON_REGISTRY: dict[str, type] = {
    "magic_dagger": MagicDagger,
    "orbit_orb": OrbitOrb,
    "ice_dart": IceDart,
    "chain_lightning": ChainLightning,
    "fire_nova": FireNova,
    "homing_missile": HomingMissile,
}

WEAPON_ORDER: tuple[str, ...] = tuple(WEAPON_REGISTRY.keys())
STARTING_WEAPON_IDS: tuple[str, ...] = ("magic_dagger", "orbit_orb")


def create_weapon(weapon_id: str):
    cls = WEAPON_REGISTRY[weapon_id]
    weapon = cls()
    weapon.weapon_id = weapon_id
    return weapon


def iter_weapon_defs():
    for weapon_id in WEAPON_ORDER:
        yield weapon_id, WEAPON_REGISTRY[weapon_id]
