# -*- coding: utf-8 -*-
"""入口脚本：在 VPS 上部署 frps

功能：下载安装 frps、写入 token 鉴权配置、systemd 托管、启动并自检，
      最后打印被控端需要的连接参数（地址/端口/token/远程端口）。
实现：分步调用 FrpServerDeployer，任一环节失败立即中止。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\DeployFrpServer.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402
from TaskLayer.FrpServerDeployer import FrpServerDeployer  # noqa: E402


def main():
    """无参数。执行 frps 部署并输出被控端连接参数。"""
    cfg = ConfigLoader()
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    deployer = FrpServerDeployer(
        client,
        version=cfg.get("frp.version", "0.71.1"),
        bind_port=cfg.get("frp.bindPort", 21117),
        token=cfg.get("frp.token", ""),
        install_dir=cfg.get("frp.installDir", "/opt/frp"),
    )
    try:
        client.connect()
        print("[1/5] 准备目录 ...")
        print(deployer.prepare().strip())
        print("[2/5] 下载 frps ...")
        print(deployer.download().strip())
        print("[3/5] 写入配置 ...")
        print(deployer.write_config(cfg.get("frp.logLevel", "info")).strip())
        print("[4/5] 安装 systemd 服务 ...")
        print(deployer.write_service().strip())
        print("[5/5] 启动并自检 ...")
        print(deployer.start().strip())
        print(deployer.status())
        print("\n=== 被控端（另一台 Windows）需要的连接参数 ===")
        print("服务器地址 : %s" % cfg.require("server.host"))
        print("服务器端口 : %s" % cfg.get("frp.bindPort"))
        print("鉴权 token : %s" % cfg.get("frp.token"))
        print("本机隧道口 : %s" % cfg.get("frp.localSideRemotePort"))
        print("对方隧道口 : %s" % cfg.get("frp.peerRemotePort"))
    finally:
        client.close()


if __name__ == "__main__":
    main()
