# -*- coding: utf-8 -*-
"""入口脚本：取回 Win32-OpenSSH 离线安装包

功能：查询 PowerShell/Win32-OpenSSH 最新版本，在 VPS 上下载 OpenSSH-Win64.zip，
      再 SFTP 取回到 软件/OpenSSH-Win64.zip，供分发包做离线兜底。
实现：requests 查 release，远端 curl + 本地 SFTP 下载。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\FetchOpenSsh.py
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

import requests  # noqa: E402

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

API = "https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest"
PINNED_TAG = "v9.5.0.0p1-Beta"


def pick_asset(data):
    """data：release JSON。返回 OpenSSH-Win64.zip 的直链，找不到返回 None。"""
    for asset in data.get("assets", []):
        if asset["name"].lower() == "openssh-win64.zip":
            return asset["browser_download_url"]
    return None


def main():
    """无参数。查询版本并取回 OpenSSH-Win64.zip（优先使用固定稳定版）。"""
    url = None
    version = PINNED_TAG
    if PINNED_TAG:
        resp = requests.get(
            "https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/tags/" + PINNED_TAG,
            headers={"User-Agent": "frp-deploy"},
            timeout=30,
        )
        if resp.status_code == 200:
            url = pick_asset(resp.json())
    if not url:
        resp = requests.get(
            API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "frp-deploy"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        version = data.get("tag_name")
        url = pick_asset(data)
    if not url:
        raise SystemExit("未找到 OpenSSH-Win64.zip 资源")
    print("版本:", version)
    print("直链:", url)

    cfg = ConfigLoader()
    remote = "/tmp/OpenSSH-Win64.zip"
    local = os.path.join(ROOT_DIR, "软件", "OpenSSH-Win64.zip")
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, err = client.run(
            "curl -fL --retry 3 -o %s '%s' && ls -l %s" % (remote, url, remote), timeout=1800
        )
        print((out or err).strip().splitlines()[-1])
        if code != 0:
            raise SystemExit("远端下载失败")
        client.download(remote, local)
    print("已保存:", local, os.path.getsize(local), "字节")
    with open(os.path.join(ROOT_DIR, "output", "openssh_release.json"), "w", encoding="utf-8") as handle:
        json.dump({"version": version, "url": url}, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
