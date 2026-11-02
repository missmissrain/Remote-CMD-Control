# -*- coding: utf-8 -*-
"""任务层：RustDesk 服务端（hbbs/hbbr）部署器

功能：在 Linux 服务器上完成 rustdesk-server 的下载、解压、安装、systemd 托管、
      启停、状态检查与公钥读取，支持非 root 用户通过 sudo 执行。
实现：所有远端操作均通过 SshClient 执行；安装目录与数据目录来自配置；
      二进制以专用系统用户 rustdesk 运行，密钥文件保存在数据目录。
注册参数：
    sshClient   -- SshClient 实例（要求具备免密 sudo 权限）
    installDir  -- 二进制安装目录（默认 /opt/rustdesk-server）
    dataDir     -- 数据/密钥目录（默认 /var/lib/rustdesk-server）
    version     -- 版本号（默认 1.1.16）
    downloadUrl -- 安装包直链（默认 GitHub release 的 linux-amd64.zip）
默认参数说明：
    服务用户为 rustdesk，UID 自动分配；端口使用 RustDesk 官方默认端口。
"""

import os
import time


class RustDeskDeployer:
    """hbbs / hbbr 部署与运维封装。"""

    def __init__(
        self,
        ssh_client,
        install_dir="/opt/rustdesk-server",
        data_dir="/var/lib/rustdesk-server",
        version="1.1.16",
        download_url=None,
    ):
        self._ssh = ssh_client
        self._install_dir = install_dir
        self._data_dir = data_dir
        self._version = version
        self._download_url = download_url or (
            "https://github.com/rustdesk/rustdesk-server/releases/download/%s/"
            "rustdesk-server-linux-amd64.zip" % version
        )

    def _sudo(self, command, timeout=600):
        """command：需要 root 权限的命令。timeout：超时秒数。
        通过 sudo -n 执行并返回标准输出，失败抛异常。"""
        return self._ssh.run_checked("sudo -n bash -lc %s" % _quote(command), timeout=timeout)

    def prepare(self):
        """无参数。创建目录与专用运行用户，返回执行日志文本。"""
        cmd = (
            "set -e; mkdir -p {install} {data}; "
            "id -u rustdesk >/dev/null 2>&1 || useradd -r -s /sbin/nologin -d {data} rustdesk; "
            "chown -R rustdesk:rustdesk {data}; echo PREPARE_OK"
        ).format(install=self._install_dir, data=self._data_dir)
        return self._sudo(cmd, timeout=120)

    def download(self):
        """无参数。下载并解压安装包到安装目录，返回文件列表。"""
        cmd = (
            "set -e; cd /tmp; "
            "curl -fL --retry 3 -o rustdesk-server.zip '{url}'; "
            "rm -rf /tmp/rustdesk-unzip; mkdir -p /tmp/rustdesk-unzip; "
            "unzip -oq rustdesk-server.zip -d /tmp/rustdesk-unzip; "
            "cp -f /tmp/rustdesk-unzip/amd64/hbbs /tmp/rustdesk-unzip/amd64/hbbr "
            "/tmp/rustdesk-unzip/amd64/rustdesk-utils {install}/; "
            "chmod +x {install}/hbbs {install}/hbbr {install}/rustdesk-utils; "
            "ls -l {install}"
        ).format(url=self._download_url, install=self._install_dir)
        return self._sudo(cmd, timeout=900)

    def write_services(self):
        """无参数。写入 hbbs.service 与 hbbr.service，并重载 systemd。"""
        hbbs = _hbbs_unit(self._install_dir, self._data_dir)
        hbbr = _hbbr_unit(self._install_dir, self._data_dir)
        self._ssh.write_remote_file(hbbs, "/tmp/hbbs.service")
        self._ssh.write_remote_file(hbbr, "/tmp/hbbr.service")
        cmd = (
            "set -e; install -m 644 /tmp/hbbs.service /etc/systemd/system/hbbs.service; "
            "install -m 644 /tmp/hbbr.service /etc/systemd/system/hbbr.service; "
            "systemctl daemon-reload; echo SERVICE_FILES_OK"
        )
        return self._sudo(cmd, timeout=120)

    def enable_and_start(self):
        """无参数。开机自启并启动 hbbr、hbbs，返回状态摘要。"""
        cmd = (
            "set -e; systemctl enable hbbr hbbs >/dev/null 2>&1; "
            "systemctl restart hbbr; systemctl restart hbbs; sleep 3; "
            "systemctl is-active hbbr hbbs"
        )
        return self._sudo(cmd, timeout=180)

    def status(self):
        """无参数。返回 hbbs/hbbr 服务状态与监听端口文本。"""
        code, out, err = self._ssh.run(
            "systemctl --no-pager --full status hbbs hbbr | head -60; "
            "echo '--- PORTS ---'; sudo -n ss -lntup | grep -E ':(2111[5-9])\\b' || echo NO_LISTEN"
        )
        return (out or err).strip()

    def read_public_key(self):
        """无参数。返回数据目录中 id_ed25519.pub 的内容（客户端配置用）。"""
        out = self._ssh.run_checked(
            "sudo -n cat %s/id_ed25519.pub" % self._data_dir, timeout=60
        )
        return out.strip()

    def wait_ready(self, retry=15, interval=2):
        """retry：重试次数。interval：每次间隔秒数。
        等待 hbbs 端口就绪，成功返回 True。"""
        for _ in range(retry):
            code, out, _ = self._ssh.run(
                "sudo -n ss -lntu | grep -c ':21116' || true", timeout=30
            )
            if (out or "").strip() not in ("", "0"):
                return True
            time.sleep(interval)
        return False


def _quote(text):
    """text：原始命令文本。返回单引号包裹的 shell 安全字符串。"""
    return "'" + text.replace("'", "'\\''") + "'"


def _hbbs_unit(install_dir, data_dir):
    """install_dir/data_dir：安装与数据目录。返回 hbbs 的 systemd 单元文本。"""
    return """[Unit]
Description=RustDesk ID/Rendezvous Server (hbbs)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=rustdesk
Group=rustdesk
WorkingDirectory={data}
ExecStart={install}/hbbs -r 127.0.0.1:21117
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
""".format(install=install_dir, data=data_dir)


def _hbbr_unit(install_dir, data_dir):
    """install_dir/data_dir：安装与数据目录。返回 hbbr 的 systemd 单元文本。"""
    return """[Unit]
Description=RustDesk Relay Server (hbbr)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=rustdesk
Group=rustdesk
WorkingDirectory={data}
ExecStart={install}/hbbr
Restart=always
RestartSec=3
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
""".format(install=install_dir, data=data_dir)
