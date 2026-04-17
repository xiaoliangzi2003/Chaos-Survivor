"""Survivor 3.0 — 入口文件。

用法:
    python main.py           正常启动
    python main.py --debug   启动调试模式（显示 FPS、碰撞l圆等）
"""

import sys
from src.core.game import Game


def main() -> None:
    debug = "--debug" in sys.argv
    game  = Game(debug=debug)
    game.run()


if __name__ == "__main__":
    main()
