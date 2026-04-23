"""Survivor 3.0 — 入口文件。

用法:
    python main.py           正常启动
    python main.py --debug   启动调试模式（显示 FPS、碰撞l圆等）
"""
import os
import sys

from pathlib import Path

from src.core.game import Game

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 获取【存档文件路径】（读写用：player_profile.json，存在电脑本地，不会丢失）
def get_save_path():
    # 存档存到 我的文档/你的游戏名 文件夹
    save_dir = Path.home() / "Documents" / "Chaos Survivor"
    # 不存在则自动创建文件夹
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir / "player_profile.json"

def main() -> None:
    debug = "--debug" in sys.argv
    game  = Game(debug=debug)
    game.run()


if __name__ == "__main__":
    main()
