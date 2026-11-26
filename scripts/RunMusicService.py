"""音乐接收器启动入口：config 为私有配置路径，默认读取仓库config/MusicConfig.json。

由交互用户登录计划任务通过pythonw启动，不依赖欣爱主程序，也不创建可见终端。
"""

import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.MediaLayer.MusicServer import MusicServer


def main():
    """无参数；解析配置路径并运行唯一HTTP接收器，退出时回收播放器。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config/MusicConfig.json"))
    args = parser.parse_args()
    with MusicServer(args.config) as server:
        server.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log = Path(__file__).resolve().parents[1] / "runtime/MusicStartupError.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        raise
