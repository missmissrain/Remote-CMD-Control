# -*- coding: utf-8 -*-
"""入口脚本：补查 VPS 上的杂项信息

功能：确认 rustdesk 备份是否还在、nginx 站点与 443 证书、docker 容器、安全组外的本机防火墙。
实现：一次性执行若干只读命令并打印。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\VpsExtras.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

CHECKS = [
    ("root 目录备份", "ls -lh /root/*.tar.gz 2>/dev/null | awk '{print $5, $9}'"),
    ("nginx 站点", "ls /etc/nginx/conf.d/*.conf 2>/dev/null | tr '\\n' ' '"),
    ("443 服务", "sudo -n ss -lntp | grep ':443' | awk '{print $4, $6}'"),
    ("docker 容器", "sudo -n docker ps --format '{{.Names}} {{.Image}} {{.Status}}' 2>/dev/null"),
    ("本机防火墙", "systemctl is-active firewalld; iptables -S INPUT 2>/dev/null | head -3"),
    ("磁盘明细", "df -h | awk 'NR==1 || /\\.?\\/$|\\/dev\\/vda/' | tail -3"),
    ("最大占用目录", "sudo -n du -sh /opt /var /root /etc 2>/dev/null | sort -h | tail -5"),
]


def main():
    """无参数。打印杂项信息。"""
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
            text = (out or err).strip().replace("\n", " | ")
            print("%-12s %s" % (name, text or "(空)"))


if __name__ == "__main__":
    main()
