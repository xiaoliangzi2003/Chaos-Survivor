"""音频管理器：背景音乐（随机轮播 + 淡入淡出）& 音效（音调随机化 + 距离衰减 + 立体声声道）。

资源路径：
  ./assets/audio/bgm/   ← 放置 .ogg/.mp3/.wav 背景音乐文件
  ./assets/audio/sfx/hit.wav ← 击中音效文件（唯一一个）
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pygame

if TYPE_CHECKING:
    pass

# ── 路径 ──────────────────────────────────────────────────────────────────────
_ASSETS_ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio"
_BGM_DIR = _ASSETS_ROOT / "bgm"
_SFX_DIR = _ASSETS_ROOT / "sfx"

# ── 参数 ──────────────────────────────────────────────────────────────────────
_BGM_VOLUME = 0.4
_SFX_VOLUME = 0.9
_BGM_FADE_MS = 1500          # 淡入淡出时长（毫秒）
_MAX_HEAR_DIST = 900.0       # 超过此距离不播放音效
_PITCH_VARIANTS = 12         # 预生成的音调变体数量
_PITCH_RANGE = (0.88, 1.14)  # 音调随机范围（乘数）

# 用于标记音乐播放结束的自定义 pygame 事件类型
MUSIC_END_EVENT: int = pygame.USEREVENT + 10


# ── 音频管理器 ────────────────────────────────────────────────────────────────

class _AudioManager:
    def __init__(self) -> None:
        self._ready = False
        self._bgm_tracks: list[str] = []
        self._bgm_idx: int = 0
        self._hit_variants: list[pygame.mixer.Sound] = []
        # 淡入状态
        self._fading_in = False
        self._fade_in_elapsed = 0.0
        self._fade_in_dur = _BGM_FADE_MS / 1000.0

    # ── 初始化 ────────────────────────────────────────────────────────────────

    @staticmethod
    def pre_init() -> None:
        """在 pygame.init() 之前调用，设置混音器参数。"""
        pygame.mixer.pre_init(44100, -16, 2, 512)

    def post_init(self) -> None:
        """在 pygame.init() 之后调用，完成初始化并加载资源。"""
        if self._ready:
            return
        try:
            pygame.mixer.set_num_channels(32)
            self._ready = True
            self._load_assets()
        except Exception as exc:
            print(f"[Audio] post_init failed: {exc}")

    def _load_assets(self) -> None:
        # 背景音乐
        if _BGM_DIR.exists():
            exts = {".ogg", ".mp3", ".wav"}
            tracks = [str(p) for p in sorted(_BGM_DIR.iterdir()) if p.suffix.lower() in exts]
            random.shuffle(tracks)
            self._bgm_tracks = tracks
            if tracks:
                print(f"[Audio] 已加载 {len(tracks)} 首背景音乐")
            else:
                print(f"[Audio] bgm/ 目录为空，背景音乐未启用")
        else:
            print(f"[Audio] bgm/ 目录不存在：{_BGM_DIR}")

        # 击中音效
        hit_path = _SFX_DIR / "hit.wav"
        if hit_path.exists():
            self._load_hit_variants(hit_path)
        else:
            print(f"[Audio] 击中音效未找到：{hit_path}")

    def _load_hit_variants(self, path: Path) -> None:
        try:
            base = pygame.mixer.Sound(str(path))
            arr = pygame.sndarray.array(base)
            self._hit_variants = []
            for _ in range(_PITCH_VARIANTS):
                pitch = random.uniform(*_PITCH_RANGE)
                shifted = _resample(arr, pitch)
                snd = pygame.sndarray.make_sound(shifted)
                self._hit_variants.append(snd)
            print(f"[Audio] 已生成 {_PITCH_VARIANTS} 个音调变体")
        except Exception as exc:
            print(f"[Audio] 击中音效加载失败: {exc}")

    # ── 背景音乐 ──────────────────────────────────────────────────────────────

    def play_bgm(self) -> None:
        """开始播放背景音乐（从随机位置开始）。"""
        if not self._ready or not self._bgm_tracks:
            return
        pygame.mixer.music.set_endevent(MUSIC_END_EVENT)
        pygame.mixer.music.load(self._bgm_tracks[self._bgm_idx])
        pygame.mixer.music.set_volume(_BGM_VOLUME)
        pygame.mixer.music.play(fade_ms=_BGM_FADE_MS)
        self._fading_in = False

    def stop_bgm(self, fade_ms: int = _BGM_FADE_MS) -> None:
        """淡出并停止背景音乐。"""
        if not self._ready:
            return
        pygame.mixer.music.fadeout(fade_ms)

    def on_music_end(self) -> None:
        """当 MUSIC_END_EVENT 触发时调用，切换至下一首并淡入。"""
        if not self._ready or not self._bgm_tracks:
            return
        self._bgm_idx = (self._bgm_idx + 1) % len(self._bgm_tracks)
        try:
            pygame.mixer.music.load(self._bgm_tracks[self._bgm_idx])
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play()
            self._fade_in_elapsed = 0.0
            self._fading_in = True
        except Exception as exc:
            print(f"[Audio] BGM 切换失败: {exc}")

    def update(self, dt: float) -> None:
        """每帧调用，处理淡入逻辑。"""
        if not self._ready or not self._fading_in:
            return
        self._fade_in_elapsed += dt
        t = min(1.0, self._fade_in_elapsed / self._fade_in_dur)
        pygame.mixer.music.set_volume(_BGM_VOLUME * t)
        if t >= 1.0:
            self._fading_in = False

    # ── 音效 ─────────────────────────────────────────────────────────────────

    def play_hit(self, ex: float, ey: float, px: float, py: float) -> None:
        """播放击中音效。

        ex/ey: 敌人坐标（音源），px/py: 玩家坐标（听者）。
        根据距离衰减音量，根据水平方向设置左右声道。
        """
        if not self._ready or not self._hit_variants:
            return

        dx = ex - px
        dy = ey - py
        dist = math.hypot(dx, dy)
        if dist >= _MAX_HEAR_DIST:
            return

        # 距离衰减：非线性，近处响、远处弱
        norm_dist = dist / _MAX_HEAR_DIST
        vol = _SFX_VOLUME * (1.0 - norm_dist) ** 0.55

        # 立体声声道：水平偏移决定左右比例
        # pan ∈ [-1, 1]，-1=全左，0=居中，+1=全右
        pan = max(-1.0, min(1.0, dx / (_MAX_HEAR_DIST * 0.5)))
        # 等功率声相公式
        angle = (pan + 1.0) * 0.5 * math.pi * 0.5  # [0, π/2]
        left_vol = vol * math.cos(angle)
        right_vol = vol * math.sin(angle)

        snd = random.choice(self._hit_variants)
        ch = pygame.mixer.find_channel(True)  # True = 强制分配（抢占最旧）
        if ch is not None:
            ch.play(snd)
            ch.set_volume(left_vol, right_vol)


# ── 辅助：音调变换（重采样） ───────────────────────────────────────────────────

def _resample(arr: np.ndarray, pitch: float) -> np.ndarray:
    """通过线性插值重采样音频数据以改变音调。

    pitch > 1.0 → 音调升高（数组变短，播放更快）
    pitch < 1.0 → 音调降低（数组变长，播放更慢）
    """
    orig_len = len(arr)
    new_len = max(1, int(orig_len / pitch))
    src_idx = np.arange(orig_len, dtype=np.float64)
    dst_idx = np.linspace(0.0, orig_len - 1.0, new_len)

    dtype = arr.dtype
    info = np.iinfo(dtype)

    if arr.ndim == 1:
        out = np.interp(dst_idx, src_idx, arr.astype(np.float64))
        return np.clip(out, info.min, info.max).astype(dtype)
    else:
        out = np.empty((new_len, arr.shape[1]), dtype=dtype)
        for ch in range(arr.shape[1]):
            col = np.interp(dst_idx, src_idx, arr[:, ch].astype(np.float64))
            out[:, ch] = np.clip(col, info.min, info.max).astype(dtype)
        return out


# ── 全局单例 ──────────────────────────────────────────────────────────────────
audio_manager = _AudioManager()
