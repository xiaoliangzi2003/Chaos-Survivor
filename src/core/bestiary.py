"""Enemy bestiary data and preview helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from src.entities.enemy import ALL_ELITE_TYPES, ALL_ENEMY_TYPES, create_enemy

_PREVIEW_CANVAS_SIZE = 1600
_LINE_RAIDER_KWARGS = {
    "world_bounds": (-520.0, -360.0, 520.0, 360.0),
    "target_x": 0.0,
    "target_y": 0.0,
}


@dataclass(frozen=True, slots=True)
class BestiaryEntry:
    enemy_id: str
    name: str
    category: str
    style: str
    description: str
    tips: str


@dataclass(frozen=True, slots=True)
class EnemySnapshot:
    hp: int
    speed: int
    damage: int
    xp_drop: int
    gold_drop: int


BESTIARY_ENTRIES: tuple[BestiaryEntry, ...] = (
    BestiaryEntry("zombie", "僵尸", "小怪", "近战压迫", "最基础的近战敌人，移动慢但比较耐打，会持续向玩家逼近。", "利用走位和范围武器边退边清，不要被数量包住。"),
    BestiaryEntry("speeder", "急行者", "小怪", "高速突进", "会蓄力后突然加速冲脸，适合混在怪潮里打乱节奏。", "看到它准备冲刺时横向拉开，不要直线后撤。"),
    BestiaryEntry("lancer", "突刺者", "小怪", "直线穿刺", "会朝玩家方向猛冲，瞬时爆发比普通近战更高。", "保持斜向移动，让它扑空后再回头输出。"),
    BestiaryEntry("wisp", "冰霜幽灵", "小怪", "远程风筝", "会与玩家保持距离并持续发射弹幕。", "优先处理，避免远程弹幕在场上越积越多。"),
    BestiaryEntry("slime_large", "大型史莱姆", "小怪", "分裂压场", "行动最慢，但生命和碰撞伤害最高，死亡后会分裂。", "尽量在空旷区域击杀，避免被分裂体围住。"),
    BestiaryEntry("slime_medium", "中型史莱姆", "小怪", "二段分裂", "由大型史莱姆分裂而来，速度更快，还会继续分裂。", "保持移动，把它们引成一串后集中清理。"),
    BestiaryEntry("slime_small", "小型史莱姆", "小怪", "高速骚扰", "史莱姆家族里速度最快，数量多时压迫感很强。", "不要贪金币，优先清小体型单位避免被追上。"),
    BestiaryEntry("blackhole_mage", "黑洞法师", "小怪", "区域控制", "会在玩家附近召唤黑洞，制造牵引和持续伤害区域。", "看到黑洞立刻离开边缘，别在黑洞与怪潮之间停留。"),
    BestiaryEntry("blink_skirmisher", "闪跃游斗者", "小怪", "闪现切入", "会通过短距离闪现反复切入，近身节奏很灵活。", "输出时多留位移空间，不要站在角落和边界附近。"),
    BestiaryEntry("embermine", "余烬地雷兽", "小怪", "地雷封锁", "喜欢逼近后布置火焰地雷，拖慢玩家的走位空间。", "优先拉开并引爆它布下的危险区域。"),
    BestiaryEntry("siege_pylon", "攻城棱塔", "小怪", "驻点火力", "移动慢但射程远，会持续向玩家压制。", "尽快贴近处理，拖得越久场面越乱。"),
    BestiaryEntry("razorbat", "刃翼蝠", "小怪", "俯冲骚扰", "会高速掠过玩家，穿插在怪群里进行骚扰。", "利用范围和自动索敌武器优先打空中单位。"),
    BestiaryEntry("brood_seeder", "巢种播撒者", "小怪", "召唤增殖", "会不断产出额外小怪，让战场人口迅速膨胀。", "看到它优先集火，不然会把局面拖进刷怪雪崩。"),
    BestiaryEntry("line_raider", "裂空突袭者", "小怪", "无敌穿场", "无敌单位，会先用预警线锁定路线，再高速横穿整张地图。", "看到预警通道就立刻离开，绝对不要和它抢线路。"),
    BestiaryEntry("shield_caster", "护盾施术者", "小怪", "团队增益", "不会直接进攻，但会给附近敌人套上大幅减伤护盾。", "优先击杀它，否则周围怪物会变得很难处理。"),
    BestiaryEntry("wizard", "奥术巫师", "小怪", "定点轰炸", "会隔着怪潮向玩家发射法术弹，是稳定的后排火力点。", "靠机动走位躲弹，同时用穿透或追踪武器处理它。"),
    BestiaryEntry("exploder", "爆裂自毁者", "小怪", "近身爆炸", "接近玩家后会自爆，伤害高但身板脆。", "不要在怪群中心引爆它，尽量在边缘提前点掉。"),
    BestiaryEntry("tank", "重甲蛮牛", "小怪", "重装推进", "高生命高碰撞伤害，适合给其他远程怪创造输出空间。", "用持续伤害和击退把它卡在怪潮外圈。"),
    BestiaryEntry("gunner", "几何枪手", "小怪", "中程点射", "会边走边打，在中距离不断补枪。", "斜向移动最容易躲掉它的直线弹道。"),
    BestiaryEntry("artillery", "炮击方碑", "小怪", "抛射压制", "擅长远距离抛射火力，会把危险点提前铺在前方。", "别停在原地输出，持续移动能让它的大部分炮火落空。"),
    BestiaryEntry("elite_summoner", "精英·召魂统领", "精英", "召唤核心", "强化版召唤单位，能稳定制造额外前排。", "一旦出现就优先集火，避免它把战场重新堆满。"),
    BestiaryEntry("elite_berserker", "精英·狂怒战兽", "精英", "半血狂暴", "高生命近战单位，半血后会进一步加速冲锋。", "最好在安全距离把它一口气压死，别给它狂暴反扑机会。"),
    BestiaryEntry("elite_assassin", "精英·影刃刺客", "精英", "瞬移追猎", "会突然闪到玩家背后，擅长抓走位停顿。", "保持连续移动，背后留足空间。"),
    BestiaryEntry("elite_sentinel", "精英·棱镜哨兵", "精英", "弹幕炮台", "火力更密集的远程精英，会持续制造大片危险区域。", "拉远小怪后回头点杀，避免和其他远程怪叠弹幕。"),
    BestiaryEntry("elite_missile_sniper", "精英·导弹狙击者", "精英", "跟踪爆破", "蓄力后发射跟踪导弹，爆炸后还会留下持续灼烧区域。", "看见蓄力就提前拐弯，让导弹在安全位置炸开。"),
    BestiaryEntry("storm_tyrant", "风暴暴君", "Boss", "多态弹幕", "会在散射、环阵和冲锋之间切换，还会召唤帮手压场。", "预留绕场空间，优先关注它当前切换到的攻击模式。"),
    BestiaryEntry("void_colossus", "虚空巨像", "Boss", "重压控制", "兼具弹幕、引力和范围控制能力，\n是偏厚重的压制型 Boss。",
                  "不要在重力技能附近停留太久，绕大圈拉扯更安全。"),
    BestiaryEntry("geometric_devourer", "几何吞噬者", "Boss",
                  "长蛇追猎", "多关节的蛇形 Boss，会巡航射击、突击冲锋\n并在二阶段加入传送与火球。",
                  "看准头部转向节奏，提前侧移，不要和它比直线奔跑。"),
    BestiaryEntry("sword_shield_duo", "裂锋剑将", "Boss",
                  "剑盾联手·剑",
                  "双 Boss 组合之一。一阶段独自攻击，以近战冲锋突进和剑气连斩为主，"
                  "此时盾卫无敌为其护身。血量降至 50% 后让出攻击权，"
                  "进入蓄势状态，二阶段无敌游走。三阶段双 Boss 同时出手，"
                  "若盾卫先倒则立刻狂暴，释放全向疾风乱刃并加快冲锋节奏。",
                  "一阶段专注走位躲剑气，不要贪伤盾卫。三阶段优先压制剑将，"
                  "拉开距离防止被连续冲锋追上。狂暴后必须全程保持移动。"),
    BestiaryEntry("shield_boss", "铁壁盾卫", "Boss",
                  "剑盾联手·盾",
                  "双 Boss 组合之一。一阶段无敌绕场，掩护剑将进攻。"
                  "二阶段独立攻击，以环形弹幕和防线轰击为主，火力稳定且覆盖面广。"
                  "三阶段与剑将同时出手，弹幕密度大幅上升。"
                  "若剑将先倒则狂暴，发射更密集的环形炮击和多枚追踪重炮。",
                  "二阶段在环形弹幕间隙穿插输出，不要停在弹幕圆心。"
                  "三阶段注意同时规避剑将冲锋与盾卫弹幕的夹击。"
                  "狂暴后追踪重炮难以直线甩掉，需不断转向打乱其追踪轨迹。"),
)

_ENTRY_MAP = {entry.enemy_id: entry for entry in BESTIARY_ENTRIES}


class _PreviewCamera:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._cx = width / 2
        self._cy = height / 2

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        return self._cx + x, self._cy + y

    def is_visible(self, x: float, y: float, radius: float) -> bool:
        sx, sy = self.world_to_screen(x, y)
        return -radius <= sx <= self._width + radius and -radius <= sy <= self._height + radius


def list_bestiary_entries() -> list[BestiaryEntry]:
    return list(BESTIARY_ENTRIES)


def get_bestiary_entry(enemy_id: str) -> BestiaryEntry:
    return _ENTRY_MAP[enemy_id]


def build_enemy_snapshot(enemy_id: str) -> EnemySnapshot:
    enemy = _build_enemy(enemy_id)
    speed = int(enemy.speed)
    if speed <= 0 and hasattr(enemy, "_DASH_SPEED"):
        speed = int(getattr(enemy, "_DASH_SPEED"))
    return EnemySnapshot(
        hp=int(enemy.max_hp),
        speed=speed,
        damage=int(enemy.damage),
        xp_drop=int(enemy.xp_drop),
        gold_drop=int(enemy.gold_drop),
    )


def render_enemy_portrait(enemy_id: str, size: tuple[int, int] = (360, 280)) -> pygame.Surface:
    enemy = _build_enemy(enemy_id)
    enemy._anim_t = 1.2

    canvas = pygame.Surface((_PREVIEW_CANVAS_SIZE, _PREVIEW_CANVAS_SIZE), pygame.SRCALPHA)
    preview_cam = _PreviewCamera(_PREVIEW_CANVAS_SIZE, _PREVIEW_CANVAS_SIZE)

    if enemy_id == "line_raider":
        sx = _PREVIEW_CANVAS_SIZE / 2
        sy = _PREVIEW_CANVAS_SIZE / 2
        enemy._draw_shadow(canvas, sx, sy)
        enemy._draw_shape(canvas, sx, sy, False)
    else:
        enemy.draw(canvas, preview_cam)

    bounds = canvas.get_bounding_rect()
    if bounds.width <= 0 or bounds.height <= 0:
        return pygame.Surface(size, pygame.SRCALPHA)

    padded = bounds.inflate(120, 120)
    padded = padded.clip(canvas.get_rect())
    cropped = canvas.subsurface(padded).copy()

    target_w, target_h = size
    scale = min(target_w / max(1, cropped.get_width()), target_h / max(1, cropped.get_height()))
    scaled_size = (
        max(1, int(cropped.get_width() * scale)),
        max(1, int(cropped.get_height() * scale)),
    )
    scaled = pygame.transform.smoothscale(cropped, scaled_size)

    portrait = pygame.Surface(size, pygame.SRCALPHA)
    portrait.blit(scaled, scaled.get_rect(center=(target_w // 2, target_h // 2 + 6)))
    return portrait


def draw_bestiary_icon(surface: pygame.Surface, rect: pygame.Rect, active: bool = False) -> None:
    border = (255, 220, 108) if active else (118, 150, 210)
    fill = (36, 46, 78) if active else (24, 30, 54)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, border, rect, 2, border_radius=12)

    book = rect.inflate(-14, -12)
    left_page = pygame.Rect(book.x, book.y, book.w // 2 - 3, book.h)
    right_page = pygame.Rect(book.centerx + 3, book.y, book.w // 2 - 3, book.h)
    pygame.draw.rect(surface, (78, 96, 138), left_page, border_radius=8)
    pygame.draw.rect(surface, (86, 108, 154), right_page, border_radius=8)
    pygame.draw.line(surface, border, (book.centerx, book.y + 4), (book.centerx, book.bottom - 4), 2)

    eye_center = (rect.centerx, rect.centery - 2)
    eye_w = int(book.w * 0.46)
    eye_h = int(book.h * 0.24)
    eye_rect = pygame.Rect(0, 0, eye_w, eye_h)
    eye_rect.center = eye_center
    pygame.draw.ellipse(surface, (238, 245, 255), eye_rect, 2)
    pygame.draw.circle(surface, border, eye_center, max(3, eye_h // 3))
    pygame.draw.circle(surface, (255, 255, 255), (eye_center[0] - 2, eye_center[1] - 1), 1)


def _build_enemy(enemy_id: str):
    kwargs = dict(_LINE_RAIDER_KWARGS) if enemy_id == "line_raider" else {}
    return create_enemy(enemy_id, 0.0, 0.0, difficulty=1, **kwargs)


_registered_ids = set(ALL_ENEMY_TYPES) | set(ALL_ELITE_TYPES)
_defined_ids = {entry.enemy_id for entry in BESTIARY_ENTRIES}
if _registered_ids != _defined_ids:
    missing = sorted(_registered_ids - _defined_ids)
    extra = sorted(_defined_ids - _registered_ids)
    raise ValueError(f"Bestiary registry mismatch. Missing={missing}, extra={extra}")
