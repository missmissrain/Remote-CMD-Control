# -*- coding: utf-8 -*-
"""入口脚本：探测 VPS 环境

功能：读取配置、连接服务器、输出部署前环境报告（含 sudo 权限检查）。
实现：调用 ConfigLoader 与 SshClient，再交给 ServerProbe 采集。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ProbeServer.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402
from TaskLayer.ServerProbe import ServerProbe  # noqa: E402


def build_client():
    """无参数。按配置文件构造 SshClient 实例，返回 (配置对象, 客户端)。"""
    cfg = ConfigLoader()
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        password=cfg.get("server.password", ""),
        private_key_path=cfg.get("server.privateKeyPath", ""),
        timeout=cfg.get("server.connectTimeoutSec", 20),
    )
    return cfg, client


def main():
    """无参数。执行环境探测并输出中文报告。"""
    cfg, client = build_client()
    try:
        client.connect()
        print("已连接 %s@%s" % (cfg.get("server.user"), cfg.require("server.host")))
        code, out, err = client.run("id; sudo -n true && echo SUDO_OK || echo SUDO_NEED_PASSWORD")
        print(out.strip() or err.strip())
        ServerProbe(client).run(
            log_path=os.path.join(ROOT_DIR, "output", "服务器环境报告.txt")
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
