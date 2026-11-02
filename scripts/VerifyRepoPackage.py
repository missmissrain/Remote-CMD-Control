# -*- coding: utf-8 -*-
"""入口脚本：核对 GitHub 仓库内分发包目录

功能：列出 分发包/FrpWindowsClient 下的文件，确认 frpc.exe、安装脚本、离线 OpenSSH 都已入库。
实现：GitHub API contents 接口 + 子目录递归一层。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\VerifyRepoPackage.py
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

PACKAGE = "分发包/FrpWindowsClient"


def list_dir(client, token, api, path):
    """client：SSH 客户端。token/api：GitHub 认证与仓库接口。path：仓库内路径（中文需 URL 编码）。
    返回该目录下的条目列表。"""
    from urllib.parse import quote

    url = "%s/contents/%s" % (api, quote(path))
    code, out, err = client.run(
        "curl -s -H 'Authorization: token %s' '%s'" % (token, url), timeout=60
    )
    try:
        return json.loads(out or "[]")
    except ValueError:
        print("解析失败:", (out or err)[:200])
        return []


def main():
    """无参数。打印分发包目录清单。"""
    cfg = ConfigLoader()
    token = cfg.require("github.token")
    api = "https://api.github.com/repos/%s/%s" % (cfg.require("github.owner"), cfg.get("github.repo"))
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        items = list_dir(client, token, api, PACKAGE)
        print("%s 下 %d 项：" % (PACKAGE, len(items)))
        for item in items:
            print("  %-26s %-5s %8s" % (item.get("name"), item.get("type"), item.get("size", "")))
        oss = list_dir(client, token, api, PACKAGE + "/OpenSSH-Win64")
        print("OpenSSH-Win64 下 %d 项（离线兜底组件）" % len(oss))


if __name__ == "__main__":
    main()
