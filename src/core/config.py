"""全局常量与平衡配置。"""

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "幸存者 3.0"
WORLD_WIDTH = 3600
WORLD_HEIGHT = 2400
WORLD_LEFT = -WORLD_WIDTH / 2
WORLD_RIGHT = WORLD_WIDTH / 2
WORLD_TOP = -WORLD_HEIGHT / 2
WORLD_BOTTOM = WORLD_HEIGHT / 2

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
RED = (220, 50, 50)
GREEN = (50, 200, 80)
BLUE = (60, 120, 220)
YELLOW = (240, 210, 40)
ORANGE = (240, 140, 30)
PURPLE = (160, 60, 220)
CYAN = (40, 210, 210)
PINK = (230, 100, 180)
GOLD = (255, 200, 30)
DARK_GREEN = (20, 80, 30)
DARK_BLUE = (10, 20, 60)

COLOR_HP_BAR = (200, 50, 50)
COLOR_HP_BG = (80, 20, 20)
COLOR_XP_BAR = (60, 180, 255)
COLOR_XP_BG = (20, 40, 80)
COLOR_GOLD = GOLD
COLOR_UI_BG = (15, 15, 25, 210)
COLOR_UI_BORDER = (80, 80, 120)

RARITY_COLORS = {
    "common": WHITE,
    "uncommon": (80, 200, 80),
    "rare": (80, 120, 255),
    "epic": (180, 60, 255),
    "legendary": GOLD,
}

PLAYER_DEFAULT = {
    "max_hp": 100,
    "hp_regen": 0.0,
    "speed": 220,
    "pickup_radius": 60,
    "crit_rate": 0.05,
    "crit_mul": 1.5,
    "dodge_rate": 0.0,
    "atk_mul": 1.0,
    "atk_speed_mul": 1.0,
    "proj_bonus": 0,
    "range_mul": 1.0,
    "xp_mul": 1.0,
    "gold_mul": 1.0,
    "armor": 0,
}

TOTAL_WAVES = 20
WAVE_BASE_DURATION = 30
WAVE_DURATION_INC = 0.5
WAVE_BREAK_DURATION = 3.0
BOSS_WAVES = {5, 10, 15, 20}
ELITE_WAVE_INTERVAL = 3
MAX_ENEMIES = 300

XP_GEM_VALUES = {"small": 1, "medium": 5, "large": 25}


def xp_to_next_level(level: int) -> int:
    return int(5 + level * 3 + level * level * 0.4)


DIFFICULTY_NAMES = ["新手", "普通", "困难", "精英", "噩梦", "地狱"]

DIFFICULTY_SETTINGS = {
    0: {"hp_mul": 0.7, "dmg_mul": 0.6, "count_mul": 0.8, "reward_mul": 0.8},
    1: {"hp_mul": 1.0, "dmg_mul": 1.0, "count_mul": 1.0, "reward_mul": 1.0},
    2: {"hp_mul": 1.3, "dmg_mul": 1.2, "count_mul": 1.2, "reward_mul": 1.2},
    3: {"hp_mul": 1.6, "dmg_mul": 1.4, "count_mul": 1.4, "reward_mul": 1.4},
    4: {"hp_mul": 2.0, "dmg_mul": 1.7, "count_mul": 1.6, "reward_mul": 1.7},
    5: {"hp_mul": 2.5, "dmg_mul": 2.0, "count_mul": 2.0, "reward_mul": 2.0},
}

MAX_PARTICLES = 800
MAX_PARTICLES_LO = 300

MAP_THEMES = {
    "grassland": {
        "bg": (34, 85, 34),
        "tile1": (38, 95, 38),
        "tile2": (30, 75, 30),
        "deco": (20, 60, 20),
    },
    "desert": {
        "bg": (180, 155, 90),
        "tile1": (190, 165, 100),
        "tile2": (170, 145, 80),
        "deco": (150, 120, 60),
    },
    "snowfield": {
        "bg": (200, 215, 230),
        "tile1": (210, 225, 240),
        "tile2": (190, 205, 220),
        "deco": (160, 175, 195),
    },
}
TILE_SIZE = 64

SCREENSHAKE_BOSS_ENTER = 300
SCREENSHAKE_BOSS_ATTACK = 150
SCREENSHAKE_PLAYER_HIT = 120

SCORE_KILL_BASE = 10
SCORE_WAVE_BONUS = 500
SCORE_BOSS_BONUS = 2000
SCORE_SURVIVE_MULT = 1.2
