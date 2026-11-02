# -*- coding: utf-8 -*-
"""入口脚本：把本地仓库推送成 GitHub 仓库 Remote-CMD-Control

功能：本机直连 github.com 被网络阻断，因此把 git bundle 传到 VPS，
      由 VPS 创建仓库并 push；成功后把本地 origin 指向 GitHub。
实现：GitHub REST API 建仓 + 远端 clone bundle + push；token 从本地配置读取，不入库。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\PushToGithub.py
"""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

BUNDLE = os.path.join(ROOT_DIR, "output", "Remote-CMD-Control.bundle")
REMOTE_BUNDLE = "/tmp/Remote-CMD-Control.bundle"


def main():
    """无参数。建仓并推送，随后设置本地 origin。"""
    if not os.path.isfile(BUNDLE):
        raise SystemExit("缺少 bundle，请先运行 PrepareGithubRepo.py")

    cfg = ConfigLoader()
    token = cfg.require("github.token")
    owner = cfg.require("github.owner")
    repo = cfg.get("github.repo", "Remote-CMD-Control")
    api_url = "https://api.github.com/repos/%s/%s" % (owner, repo)
    payload = json.dumps(
        {
            "name": repo,
            "description": "双向 frp 隧道：把无公网 IP 的 Windows CMD 映射成 VPS 上的 SSH 入口，互相可远程控制",
            "private": False,
            "has_issues": True,
            "has_wiki": False,
            "has_projects": False,
        }
    )
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        print("[1/4] 检查 git 环境 ...")
        code, out, err = client.run("git --version", timeout=30)
        print((out or err).strip())

        print("[2/4] 上传 bundle ...")
        client.upload(BUNDLE, REMOTE_BUNDLE)
        code, out, _ = client.run("ls -l %s | awk '{print $5}'" % REMOTE_BUNDLE, timeout=30)
        print("远端 bundle 大小:", (out or "").strip())

        print("[3/4] 创建 GitHub 仓库（recreate 模式会先删除旧仓库）...")
        if "recreate" in sys.argv:
            client.run(
                "curl -s -o /dev/null -X DELETE -H 'Authorization: token %s' %s" % (token, api_url),
                timeout=120,
            )
            print("已删除旧仓库（连同全部历史），3 秒后重建 ...")
            import time

            time.sleep(3)
        create_cmd = (
            "code=$(curl -s -o /tmp/repo.json -w '%%{http_code}' -X POST "
            "-H 'Authorization: token %s' -H 'Accept: application/vnd.github+json' "
            "-H 'Content-Type: application/json' -d '%s' https://api.github.com/user/repos); "
            "echo HTTP:$code"
        ) % (token, payload.replace("'", "'\\''"))
        code, out, err = client.run(create_cmd, timeout=120)
        print((out or err).strip())

        print("[4/4] 克隆 bundle 并推送到 GitHub ...")
        push_cmd = (
            "set -e; cd /tmp; rm -rf rc-push; "
            "git clone -q %s rc-push; cd rc-push; "
            "for i in 1 2 3; do "
            "git -c credential.helper= -c user.name=%s -c user.email=1974704197@qq.com "
            "push -q https://x-access-token:%s@github.com/%s/%s.git HEAD:refs/heads/main --tags --force && break || sleep 5; "
            "done; echo PUSH_DONE"
        ) % (REMOTE_BUNDLE, owner, token, owner, repo)
        code, out, err = client.run(push_cmd, timeout=900)
        print((out or err).strip())
        if "PUSH_DONE" not in out:
            raise SystemExit("推送失败")
        # 清理鉴权测试时留下的临时分支
        client.run(
            "curl -s -o /dev/null -X DELETE -H 'Authorization: token %s' "
            "%s/git/refs/heads/auth-test-1" % (token, api_url),
            timeout=60,
        )
        client.run("rm -rf /tmp/rc-push %s" % REMOTE_BUNDLE, timeout=60)

    subprocess.run(["git", "remote", "remove", "origin"], cwd=ROOT_DIR, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/%s/%s.git" % (owner, repo)],
        cwd=ROOT_DIR,
        capture_output=True,
    )
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=ROOT_DIR, capture_output=True
    ).stdout.decode().strip()
    print("本地 origin 已设置，当前分支:", branch)
    print("仓库地址: https://github.com/%s/%s" % (owner, repo))


if __name__ == "__main__":
    main()
