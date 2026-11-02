# -*- coding: utf-8 -*-
"""入口脚本：从 GitHub 下载整个仓库快照做脱敏复核

功能：不信本地状态，在 VPS 上直接下载 GitHub 仓库 tarball 并解压，
      对全部文件逐个搜索服务器 IP、密码、frp token、GitHub token、私钥名。
实现：curl tarball → tar 解包 → grep -rn 逐项匹配 → 输出命中文件与行。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\AuditGithubPublic.py
"""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

REMOTE_DIR = "/tmp/repo-audit"


def main():
    """无参数。下载快照并逐项搜索敏感串。"""
    cfg = ConfigLoader()
    owner = cfg.require("github.owner")
    repo = cfg.get("github.repo", "Remote-CMD-Control")
    patterns = {
        "服务器IP": cfg.get("server.host", ""),
        "服务器密码": cfg.get("server.password", ""),
        "frp token": cfg.get("frp.token", ""),
        "GitHub token": cfg.get("github.token", ""),
        "私钥名": os.path.basename(cfg.get("server.privateKeyPath", "").replace("\\", "/")),
    }
    patterns = {k: v for k, v in patterns.items() if v and len(v) > 3}
    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        print("仓库: https://github.com/%s/%s" % (owner, repo))
        cmd = (
            "set -e; rm -rf {d}; mkdir -p {d}; cd {d}; "
            "curl -sL --retry 3 --max-time 120 https://api.github.com/repos/{o}/{r}/tarball/main "
            "-o repo.tgz; tar xzf repo.tgz; ls -d */ | head -1"
        ).format(d=REMOTE_DIR, o=owner, r=repo)
        code, out, err = client.run(cmd, timeout=300)
        if code != 0:
            raise SystemExit("下载失败: %s" % (err or out))
        snapshot = (out or "").strip().splitlines()[-1].strip("/")
        print("快照目录:", snapshot)

        code, out, _ = client.run(
            "cd %s/%s && find . -type f | wc -l" % (REMOTE_DIR, snapshot), timeout=60
        )
        print("文件总数:", (out or "").strip())

        print("\n=== 敏感串搜索结果 ===")
        total = 0
        for name, value in patterns.items():
            code, out, err = client.run(
                "cd {d}/{s} && grep -rn -F -- '{v}' . 2>/dev/null | head -10".format(
                    d=REMOTE_DIR, s=snapshot, v=value
                ),
                timeout=120,
            )
            hits = (out or "").strip()
            if hits:
                total += 1
                print("[%s] ✗ 命中：" % name)
                for line in hits.splitlines():
                    print("   ", line.replace(value, value[:4] + "***"))
            else:
                print("[%s] ✓ 未出现" % name)

        code, out, _ = client.run(
            "rm -rf %s/repo.tgz" % REMOTE_DIR, timeout=60
        )
        print("\n结论:", "全部干净" if total == 0 else "仍有 %d 类敏感信息泄露" % total)


if __name__ == "__main__":
    main()
