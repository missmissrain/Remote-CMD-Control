# -*- coding: utf-8 -*-
"""入口脚本：查询 frp 最新版本与各平台安装包

功能：调用 GitHub API 获取 fatedier/frp 最新 release 的版本号与资源直链，
      并筛选出 linux_amd64 与 windows_amd64 两个包。
实现：requests 拉取 JSON，保存原始数据到 output/frp_release.json。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\QueryFrpRelease.py
"""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import requests  # noqa: E402

API = "https://api.github.com/repos/fatedier/frp/releases/latest"
WANT = ("linux_amd64", "windows_amd64")


def main():
    """无参数。打印版本号与目标平台资源直链。"""
    resp = requests.get(
        API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "frp-deploy"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print("版本:", data.get("tag_name"), "| 发布:", data.get("published_at"))
    picked = {}
    for asset in data.get("assets", []):
        name = asset["name"]
        if name.endswith(".zip") or name.endswith(".tar.gz"):
            for key in WANT:
                if key in name:
                    picked[key] = asset["browser_download_url"]
                    print("%-45s %10d  %s" % (name, asset["size"], asset["browser_download_url"]))
    out_dir = os.path.join(ROOT_DIR, "output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "frp_assets.json"), "w", encoding="utf-8") as handle:
        json.dump({"version": data.get("tag_name"), "assets": picked}, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
