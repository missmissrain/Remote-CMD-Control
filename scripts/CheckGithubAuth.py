# -*- coding: utf-8 -*-
"""入口脚本：校验 GitHub Token 并检查仓库名是否可用

功能：通过 VPS 访问 GitHub API，验证 token 有效性、查看当前用户、检查目标仓库是否已存在。
实现：token 由 config/ServerConfig.json 的 github.token 提供（该文件不入库），日志不打印 token。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\CheckGithubAuth.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402


def main():
    """无参数。校验 token 与仓库名。"""
    cfg = ConfigLoader()
    token = cfg.require("github.token")
    owner = cfg.require("github.owner")
    repo = cfg.get("github.repo", "Remote-CMD-Control")
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, err = client.run(
            "curl -s -H 'Authorization: token %s' https://api.github.com/user" % token,
            timeout=60,
        )
        text = (out or err).strip()
        print("[用户信息]", text.splitlines()[1] if len(text.splitlines()) > 1 else text[:200])
        code, out, err = client.run(
            "curl -s -o /dev/null -w '%%{http_code}' -H 'Authorization: token %s' "
            "https://api.github.com/repos/%s/%s" % (token, owner, repo),
            timeout=60,
        )
        print("[仓库是否存在] HTTP", (out or err).strip())


if __name__ == "__main__":
    main()
