# -*- coding: utf-8 -*-
"""入口脚本：检查服务器本机防火墙与阿里云 CLI 可用性

功能：确认 firewalld/iptables 是否拦截端口，以及是否存在可用的阿里云访问凭证。
实现：执行状态查询命令并打印结果。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\CheckFirewall.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

CHECKS = [
    ("firewalld", "systemctl is-active firewalld 2>/dev/null; firewall-cmd --list-all 2>/dev/null | head -20"),
    ("iptables", "sudo -n iptables -S 2>/dev/null | head -20"),
    ("nftables", "sudo -n nft list ruleset 2>/dev/null | head -20"),
    ("aliyun-cli", "command -v aliyun || echo NO_CLI"),
    ("aliyun-config", "ls -l ~/.aliyun 2>/dev/null; sudo -n ls -l /root/.aliyun 2>/dev/null; echo DONE"),
    ("ram-role", "curl -s -m 3 http://100.100.100.200/latest/meta-data/ram/security-credentials/ || echo NO_ROLE"),
]


def main():
    """无参数。逐项检查并打印。"""
    cfg = ConfigLoader()
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        for name, cmd in CHECKS:
            code, out, err = client.run(cmd, timeout=40)
            print("[%s] %s" % (name, (out or err).strip()))


if __name__ == "__main__":
    main()
