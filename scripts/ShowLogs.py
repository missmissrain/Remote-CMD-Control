# -*- coding: utf-8 -*-
"""入口脚本：查看 frps 运行日志

功能：输出 frps 最近日志，用于确认被控端是否成功接入、隧道是否建立或报错。
实现：journalctl 按时间取最近 N 行；带 --since 可只看最新一段。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ShowLogs.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402


def main():
    """无参数。打印 frps 最近 40 行日志。"""
    cfg = ConfigLoader()
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, err = client.run(
            "sudo -n journalctl -u frps --no-pager -n 40 -o cat", timeout=60
        )
        print((out or err).strip())


if __name__ == "__main__":
    main()
