# -*- coding: utf-8 -*-
"""入口脚本：准备本地 git 仓库并生成待上传的 bundle

功能：初始化仓库、添加文件、扫描暂存内容是否含敏感信息、提交、导出 git bundle。
实现：敏感词扫描覆盖 token 与服务器密码；命中即中止，避免泄密。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\PrepareGithubRepo.py
"""

import os
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402

BUNDLE = os.path.join(ROOT_DIR, "output", "Remote-CMD-Control.bundle")
COMMIT_MSG = """feat: 双向 frp 隧道远程 CMD 控制

- VPS 跑 frps，本机/对方各跑 frpc，把 Windows 的 22 端口映射成 VPS 端口
- 一键分发包：启用 OpenSSH Server、默认 shell 设为 cmd、注册开机自启任务
- 服务端与客户端部署脚本、校验脚本、隧道连通性测试脚本
- 离线 OpenSSH 兜底，系统可选功能不可用时也能装
"""


def run(args, cwd=ROOT_DIR, check=True):
    """args：命令参数列表。cwd：工作目录。check：非零退出码是否抛异常。返回 CompletedProcess。"""
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    if check and result.returncode != 0:
        raise SystemExit(
            "命令失败: %s\n%s\n%s"
            % (" ".join(args), result.stdout.decode("utf-8", "replace"), result.stderr.decode("utf-8", "replace"))
        )
    return result


def secret_candidates():
    """无参数。返回需要扫描的敏感字符串列表。"""
    cfg = ConfigLoader()
    values = [cfg.get("frp.token", ""), cfg.get("server.password", "")]
    return [item for item in values if item and len(item) > 8]


def scan_staged(secrets):
    """secrets：敏感字符串列表。扫描暂存区文件内容，命中返回 [(文件, 命中片段)]。"""
    files = run(["git", "diff", "--cached", "--name-only"]).stdout.decode("utf-8", "replace").splitlines()
    hits = []
    for name in files:
        path = os.path.join(ROOT_DIR, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8", "replace")
        for secret in secrets:
            if secret in text:
                hits.append((name, secret[:6] + "***"))
    return hits


def main():
    """无参数（可加 fresh/amend 参数）。初始化仓库、提交并导出 bundle。
    fresh：删除 .git 后重建，确保历史里没有旧的敏感提交。"""
    args = sys.argv[1:]
    if "fresh" in args and os.path.isdir(os.path.join(ROOT_DIR, ".git")):
        import shutil
        import stat as stat_module

        def _force_remove(func, path, _exc):
            """func：失败的操作。path：目标路径。_exc：异常信息。
            去掉只读属性后重试，解决 Windows 下 .git 对象文件无法删除的问题。"""
            os.chmod(path, stat_module.S_IWRITE)
            func(path)

        shutil.rmtree(os.path.join(ROOT_DIR, ".git"), onerror=_force_remove)
        print("已删除旧 .git，重新初始化")
    if not os.path.isdir(os.path.join(ROOT_DIR, ".git")):
        run(["git", "init", "-b", "main"])
    run(["git", "config", "core.quotepath", "false"])
    run(["git", "config", "user.name", "missmissrain"])
    run(["git", "config", "user.email", "1974704197@qq.com"])
    run(["git", "add", "-A"])
    hits = scan_staged(secret_candidates())
    if hits:
        print("发现敏感信息，已中止提交：")
        for name, sample in hits:
            print("  %s -> %s" % (name, sample))
        sys.exit(2)
    print("敏感信息扫描：未发现 token / 密码")
    status = run(["git", "status", "--porcelain"]).stdout.decode("utf-8", "replace")
    print("待提交文件数:", len([line for line in status.splitlines() if line.strip()]))
    amend = len(sys.argv) > 1 and sys.argv[1] == "amend"
    if status.strip():
        if amend:
            run(["git", "commit", "--amend", "-m", COMMIT_MSG])
        else:
            run(["git", "commit", "-m", COMMIT_MSG])
    else:
        print("无变更，跳过提交")
    log = run(["git", "log", "--oneline", "-3"]).stdout.decode("utf-8", "replace")
    print("最近提交:\n" + log)
    os.makedirs(os.path.dirname(BUNDLE), exist_ok=True)
    run(["git", "bundle", "create", BUNDLE, "--all"])
    print("bundle:", BUNDLE, os.path.getsize(BUNDLE), "字节")


if __name__ == "__main__":
    main()
