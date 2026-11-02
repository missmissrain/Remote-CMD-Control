# -*- coding: utf-8 -*-
"""入口脚本：扫描仓库内容中的敏感信息

功能：同时扫描「工作区文件」与「已提交内容（HEAD）」以及全部提交历史，
      检查主机 IP、服务器密码、frp token、GitHub token、私钥名、用户名是否泄露。
实现：工作区按目录遍历（跳过 .git/软件/备份/output 与真实配置文件），
      HEAD 用 git grep，历史用 git log -S。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ScanRepoSecrets.py
"""

import os
import subprocess
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402

SKIP_DIRS = {".git", "软件", "备份", "output", "__pycache__"}
SKIP_FILES = {os.path.join("config", "ServerConfig.json")}
TEXT_EXT = {".py", ".ps1", ".bat", ".md", ".json", ".toml", ".txt", ".example", ".gitignore"}


def is_ignored(rel):
    """rel：相对路径。返回该文件是否被 .gitignore 排除（被排除的文件不会入库，无需脱敏）。"""
    result = subprocess.run(
        ["git", "check-ignore", "-q", rel], cwd=ROOT_DIR, capture_output=True
    )
    return result.returncode == 0


def git(args):
    """args：git 参数列表。返回 (退出码, 输出文本)。"""
    result = subprocess.run(["git"] + args, cwd=ROOT_DIR, capture_output=True)
    return result.returncode, (result.stdout + result.stderr).decode("utf-8", "replace")


def iter_files():
    """无参数。遍历工作区待检查的文本文件，返回相对路径列表。"""
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, ROOT_DIR)
            if rel in SKIP_FILES:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXT or name in (".gitignore", "LICENSE"):
                if is_ignored(rel):
                    continue
                yield rel, full


def scan_tree(patterns):
    """patterns：敏感串列表。扫描工作区，返回命中列表。"""
    hits = []
    for rel, full in iter_files():
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                for index, line in enumerate(handle, 1):
                    for pattern in patterns:
                        if pattern in line:
                            hits.append("%s:%d  %s" % (rel, index, line.strip()[:100]))
                            break
        except OSError:
            continue
    return hits


def scan_head(patterns):
    """patterns：敏感串列表。扫描 HEAD 已跟踪内容，返回命中列表。"""
    hits = []
    for pattern in patterns:
        code, out = git(["grep", "-n", "-I", "-F", pattern, "HEAD"])
        if code == 0:
            hits.extend(out.strip().splitlines())
    return hits


def scan_history(patterns):
    """patterns：敏感串列表。扫描全部提交历史，返回命中摘要。"""
    hits = []
    for pattern in patterns:
        code, out = git(["log", "--all", "-S", pattern, "--oneline"])
        if code == 0 and out.strip():
            hits.append("[%s] 提交: %s" % (pattern[:6] + "***", out.strip().replace("\n", " | ")))
    return hits


def report(title, hits):
    """title：小节标题。hits：命中列表。打印结果。"""
    print("=== %s ===" % title)
    if hits:
        for line in hits:
            print("  ✗", line)
    else:
        print("  ✓ 无命中")
    print()


def main():
    """无参数。输出三段扫描结果。"""
    cfg = ConfigLoader()
    key_name = os.path.basename(cfg.get("server.privateKeyPath", "").replace("\\", "/"))
    patterns = [
        cfg.get("server.host", ""),
        cfg.get("server.password", ""),
        cfg.get("frp.token", ""),
        cfg.get("github.token", ""),
        key_name,
        os.environ.get("USERNAME", ""),
    ]
    patterns = [item for item in patterns if item and len(item) > 3]
    print("扫描 %d 个敏感串（服务器 IP / 密码 / frp token / GitHub token / 私钥名 / 本机用户名）\n" % len(patterns))
    report("工作区文件（已排除 gitignore 的本地配置）", scan_tree(patterns))
    report("HEAD 已提交内容", scan_head(patterns))
    report("提交历史", scan_history(patterns))


if __name__ == "__main__":
    main()
