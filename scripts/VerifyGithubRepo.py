# -*- coding: utf-8 -*-
"""入口脚本：核对 GitHub 仓库内容

功能：通过 VPS 调用 GitHub API，确认默认分支、文件数量、README 是否存在、是否公开。
实现：读取仓库信息与根目录清单，输出中文摘要。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\VerifyGithubRepo.py
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402


def main():
    """无参数。打印仓库概况与根目录文件。"""
    cfg = ConfigLoader()
    token = cfg.require("github.token")
    owner = cfg.require("github.owner")
    repo = cfg.get("github.repo", "Remote-CMD-Control")
    api = "https://api.github.com/repos/%s/%s" % (owner, repo)
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, err = client.run(
            "curl -s -H 'Authorization: token %s' %s" % (token, api), timeout=60
        )
        info = json.loads(out or "{}")
        print("仓库:", info.get("full_name"))
        print("公开:", not info.get("private", True))
        print("默认分支:", info.get("default_branch"))
        print("体积(KB):", info.get("size"))
        print("地址:", info.get("html_url"))
        code, out, err = client.run(
            "curl -s -H 'Authorization: token %s' %s/contents" % (token, api), timeout=60
        )
        items = json.loads(out or "[]")
        print("\n根目录 %d 项：" % len(items))
        for item in items:
            print("  %-28s %s" % (item.get("name"), item.get("type")))
        code, out, err = client.run(
            "curl -s -o /dev/null -w '%%{http_code}' -H 'Authorization: token %s' "
            "%s/contents/README.md" % (token, api),
            timeout=60,
        )
        print("\nREADME.md 可访问: HTTP", (out or "").strip())
        code, out, err = client.run(
            "curl -s -H 'Authorization: token %s' %s/branches | grep -o '\"name\": *\"[^\"]*\"'" % (token, api),
            timeout=60,
        )
        print("分支:", (out or err).strip())
        code, out, err = client.run(
            "curl -s -H 'Authorization: token %s' %s/commits | grep -o '\"message\": *\"[^\"]*\"'" % (token, api),
            timeout=60,
        )
        print("提交:", (out or err).strip()[:300])


if __name__ == "__main__":
    main()
