# -*- coding: utf-8 -*-
"""入口脚本：汇总 VPS 当前状态

功能：一次性采集主机标识、系统、硬件、磁盘、登录方式、frps 服务与端口、安全组可达性等，
      输出中文清单，用于确认当前真实状态。
实现：按条目执行远端命令；本机侧再扫一遍关键端口验证外网可达。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\VpsSummary.py
"""

import os
import socket
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

CHECKS = [
    ("主机名", "hostname"),
    ("系统", "grep PRETTY_NAME /etc/os-release | cut -d= -f2"),
    ("内核/架构", "uname -r; uname -m"),
    ("CPU 核数", "nproc"),
    ("内存", "free -m | awk 'NR==2{print $2\" MB 总 / \"$7\" MB 可用\"}'"),
    ("磁盘", "df -h / | awk 'NR==2{print $2\" 总 / \"$4\" 可用 (\"$5\" 已用)\"}'"),
    ("运行时长", "uptime -p"),
    ("时区/时间", "date '+%Y-%m-%d %H:%M:%S %Z'"),
    ("ssh 密码登录", "sudo -n sshd -T 2>/dev/null | grep -E '^(passwordauthentication|pubkeyauthentication)' | tr '\\n' ' '"),
    ("已启用服务", "systemctl list-unit-files --state=enabled --type=service | grep -E 'frps|rustdesk|nginx|docker' | tr '\\n' ' '"),
    ("frps 状态", "systemctl is-active frps; systemctl is-enabled frps"),
    ("frps 版本", "/opt/frp/frps --version"),
    ("监听端口", "sudo -n ss -lntu | awk 'NR>1{print $1, $5}' | sort -u | tr '\\n' ' | '"),
    ("rustdesk 残留", "ls -d /opt/rustdesk-server /var/lib/rustdesk-server 2>/dev/null || echo 已清除"),
    ("rustdesk 备份", "ls -lh /root/rustdesk-server-backup-*.tar.gz 2>/dev/null | awk '{print $5, $9}'"),
    ("443 服务", "curl -s -m 5 http://127.0.0.1:443/ 2>/dev/null | head -c 120 || echo 未响应"),
]


def probe(host, port, timeout=3.0):
    """host/port：目标地址端口。timeout：超时秒数。返回是否可建立 TCP 连接。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def main():
    """无参数。打印 VPS 汇总信息。"""
    cfg = ConfigLoader()
    host = cfg.require("server.host")
    client = SshClient(
        host=host,
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    print("========== VPS 状态汇总 ==========")
    with client:
        for name, cmd in CHECKS:
            code, out, err = client.run(cmd, timeout=40)
            text = (out or err).strip().replace("\n", " ")
            print("%-12s %s" % (name, text))

    print("\n========== 外网可达性（本机扫描）==========")
    for port in (22, 21117, 21118, 21119, 443):
        print("  %-6d %s" % (port, "开放" if probe(host, port) else "不通"))

    print("\n========== 项目侧配置 ==========")
    print("  服务器地址    %s:%s" % (host, cfg.get("server.port", 22)))
    print("  登录用户      %s（私钥 %s）" % (cfg.get("server.user"), cfg.get("server.privateKeyPath")))
    print("  frp 接入端口  %s" % cfg.get("frp.bindPort"))
    print("  本机隧道口    %s" % cfg.get("frp.localSideRemotePort"))
    print("  对方隧道口    %s" % cfg.get("frp.peerRemotePort"))
    print("  frp 版本      %s" % cfg.get("frp.version"))
    print("  token         %s（本地配置，未入库）" % cfg.get("frp.token"))


if __name__ == "__main__":
    main()
