# -*- coding: utf-8 -*-
"""任务层：frps 服务端部署器

功能：在 Linux VPS 上安装 frps（frp 服务端），生成带 token 鉴权的配置，
      用 systemd 托管，实现「被控端 frpc 主动连入、本机通过 VPS 端口反连」的双向隧道。
实现：所有远端操作经 SshClient 执行；二进制落地到 /opt/frp，配置落地 /etc/frp/frps.toml，
      服务名 frps.service；端口统一从配置读取，避免与已放行端口冲突。
注册参数：
    sshClient  -- SshClient 实例（需免密 sudo）
    version    -- frp 版本号（默认 0.71.1）
    bind_port  -- frpc 接入端口（默认 21117）
    token      -- 鉴权令牌（默认取配置）
    install_dir-- 安装目录（默认 /opt/frp）
默认参数说明：
    配置文件路径固定 /etc/frp/frps.toml，systemd 单元固定 /etc/systemd/system/frps.service。
"""


class FrpServerDeployer:
    """frps 安装、配置与运维封装。"""

    def __init__(self, ssh_client, version="0.71.1", bind_port=21117, token="", install_dir="/opt/frp"):
        self._ssh = ssh_client
        self._version = version
        self._bind_port = bind_port
        self._token = token
        self._install_dir = install_dir

    def _sudo(self, command, timeout=600):
        """command：需要 root 的命令。timeout：超时秒数。返回标准输出，失败抛异常。"""
        return self._ssh.run_checked("sudo -n bash -lc %s" % _quote(command), timeout=timeout)

    def prepare(self):
        """无参数。创建目录并清理旧版本。"""
        cmd = "set -e; mkdir -p {dir} /etc/frp; rm -f {dir}/frps; echo PREPARE_OK".format(
            dir=self._install_dir
        )
        return self._sudo(cmd, timeout=60)

    def download(self):
        """无参数。下载官方 tar.gz 并解出 frps，返回版本信息。"""
        url = (
            "https://github.com/fatedier/frp/releases/download/v{ver}/frp_{ver}_linux_amd64.tar.gz"
        ).format(ver=self._version)
        cmd = (
            "set -e; cd /tmp; curl -fL --retry 3 -o frp.tar.gz '{url}'; "
            "rm -rf /tmp/frp-pkg; mkdir -p /tmp/frp-pkg; "
            "tar xzf frp.tar.gz -C /tmp/frp-pkg --strip-components=1; "
            "install -m 755 /tmp/frp-pkg/frps {dir}/frps; "
            "{dir}/frps --version"
        ).format(url=url, dir=self._install_dir)
        return self._sudo(cmd, timeout=900)

    def write_config(self, log_level="info"):
        """log_level：日志级别（默认 info）。写入 /etc/frp/frps.toml。"""
        text = (
            "# frps 服务端配置（由部署脚本生成）\n"
            "bindPort = {port}\n"
            'log.to = "console"\n'
            'log.level = "{level}"\n'
            "\n[auth]\n"
            'method = "token"\n'
            'token = "{token}"\n'
            "\n# 允许所有端口映射；如需限制可在此处加 allowPorts\n"
            "\n[transport]\n"
            "maxPoolCount = 20\n"
            "tcpMux = true\n"
        ).format(port=self._bind_port, level=log_level, token=self._token)
        self._ssh.write_remote_file(text, "/tmp/frps.toml")
        return self._sudo("install -m 600 /tmp/frps.toml /etc/frp/frps.toml && cat /etc/frp/frps.toml")

    def write_service(self):
        """无参数。写入 frps.service 并重载 systemd。"""
        unit = """[Unit]
Description=frp server (frps)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={dir}/frps -c /etc/frp/frps.toml
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
""".format(dir=self._install_dir)
        self._ssh.write_remote_file(unit, "/tmp/frps.service")
        cmd = (
            "set -e; install -m 644 /tmp/frps.service /etc/systemd/system/frps.service; "
            "systemctl daemon-reload; echo SERVICE_OK"
        )
        return self._sudo(cmd, timeout=120)

    def start(self):
        """无参数。开机自启并启动 frps，返回状态。"""
        cmd = "set -e; systemctl enable frps >/dev/null 2>&1; systemctl restart frps; sleep 2; systemctl is-active frps"
        return self._sudo(cmd, timeout=120)

    def status(self):
        """无参数。返回服务状态与端口监听情况。"""
        code, out, err = self._ssh.run(
            "systemctl --no-pager --full status frps | head -20; "
            "echo '--- PORTS ---'; sudo -n ss -lntp | grep -E ':(%d)\\b' || echo NO_LISTEN" % self._bind_port,
            timeout=60,
        )
        return (out or err).strip()


def _quote(text):
    """text：原始命令。返回单引号包裹的安全 shell 字符串。"""
    return "'" + text.replace("'", "'\\''") + "'"
