# -*- coding: utf-8 -*-
"""任务层：服务器环境探测

功能：连接目标 VPS，采集系统版本、CPU 架构、内存磁盘、Docker 状态、
      端口占用、防火墙状态、出网能力等部署前必需信息。
实现：按条目执行远端命令并格式化打印，输出中文报告到控制台与日志文件。
注册参数：
    sshClient -- 已配置的 SshClient 实例
默认参数说明：
    探测命令均为只读操作，不修改服务器状态。
"""

import os


class ServerProbe:
    """部署前环境探测器。"""

    def __init__(self, ssh_client):
        self._ssh = ssh_client

    def _collect(self):
        """无参数。返回 [(名称, 远端命令)] 列表。"""
        return [
            ("主机名", "hostname"),
            ("系统版本", "cat /etc/os-release | tr '\\n' ' '"),
            ("内核", "uname -r"),
            ("架构", "uname -m"),
            ("CPU", "nproc"),
            ("内存", "free -m | head -2 | tr '\\n' '|'"),
            ("磁盘", "df -h / | tail -1"),
            ("Docker", "command -v docker || echo NO_DOCKER"),
            ("Docker版本", "docker --version 2>/dev/null || true"),
            ("systemd", "ps -p 1 -o comm= 2>/dev/null || echo unknown"),
            ("已装rustdesk", "ls -l /opt/rustdesk-server 2>/dev/null || echo NOT_INSTALLED"),
            ("端口占用", "ss -lntup 2>/dev/null | grep -E ':(21115|21116|21117|21118|21119)\\b' || echo PORTS_FREE"),
            ("防火墙", "command -v firewall-cmd >/dev/null && firewall-cmd --state 2>/dev/null; "
                       "command -v ufw >/dev/null && ufw status 2>/dev/null; "
                       "iptables -S 2>/dev/null | head -5"),
            ("阿里云元数据", "curl -s -m 3 http://100.100.100.200/latest/meta-data/region-id || echo NO_META"),
            ("GitHub连通", "curl -s -o /dev/null -m 8 -w '%{http_code} %{time_total}s' "
                            "https://github.com/rustdesk/rustdesk-server/releases/latest || echo GITHUB_FAIL"),
            ("DockerHub连通", "curl -s -o /dev/null -m 8 -w '%{http_code} %{time_total}s' "
                               "https://registry-1.docker.io/v2/ || echo HUB_FAIL"),
        ]

    def run(self, log_path=None):
        """log_path：可选，报告同时写入该本地文件。
        返回字典 {探测项: 输出文本}。"""
        result = {}
        lines = []
        for name, cmd in self._collect():
            code, out, err = self._ssh.run(cmd, timeout=40)
            text = (out or "").strip() or (err or "").strip()
            result[name] = text
            lines.append("[%s] %s" % (name, text))
        report = "\n".join(lines)
        print(report)
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write(report + "\n")
        return result
