# -*- coding: utf-8 -*-
"""入口脚本：清理仓库中的临时/旧方案脚本

功能：删除调试期与 RustDesk 方案遗留的脚本，只保留 frp 方案需要的工具，避免公开仓库夹带无关信息。
实现：按白名单删除，删除前逐个打印；本地 备份/ 目录仍保留历史副本。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\CleanupRepo.py
"""

import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

REMOVE = [
    # RustDesk 方案遗留
    "scripts/CheckPeers.py",
    "scripts/ConfigureClient.py",
    "scripts/ConfigureClientToml.py",
    "scripts/DeployServer.py",
    "scripts/DownloadClient.py",
    "scripts/FetchClientViaServer.py",
    "scripts/GetClientId.py",
    "scripts/InspectZip.py",
    "scripts/LaunchClient.bat",
    "scripts/LaunchClient.ps1",
    "scripts/QueryClientRelease.py",
    "scripts/QueryRelease.py",
    "scripts/RemoveRustDeskClient.py",
    "scripts/RemoveRustDeskServer.py",
    "scripts/SelfConnectTest.py",
    "scripts/ShowClientLog.py",
    "scripts/UnzipFrpWindows.py",
    # 一次性调试脚本（涉及私钥名 / 文件属性诊断）
    "scripts/DiagKey.py",
    "scripts/TryUsers.py",
    "scripts/TryKeys.py",
    "scripts/DiagFrpZip.py",
    "scripts/DiagFileAttr.py",
    "scripts/TextProbe.py",
    # 环境适配类一次性脚本
    "scripts/FindProxy.ps1",
    "scripts/FindProxyPort.py",
    "scripts/ListOpenSshReleases.py",
    "scripts/ExtractOpenSshBundle.py",
    "scripts/TestGithubAuth.py",
    "scripts/CheckUac.ps1",
    "scripts/check_env.py",
    "scripts/install_paramiko.bat",
    "scripts/ListClientProcess.ps1",
    "scripts/BringToFront.ps1",
    "scripts/CaptureScreen.ps1",
    "scripts/Screenshot.py",
    "scripts/Probe443.py",
]


def main():
    """无参数。逐个删除目标文件并统计。"""
    removed = 0
    for rel in REMOVE:
        path = os.path.join(ROOT_DIR, rel.replace("/", os.sep))
        if os.path.isfile(path):
            os.remove(path)
            print("已删除:", rel)
            removed += 1
    print("共删除 %d 个文件" % removed)
    remain = sorted(os.listdir(os.path.join(ROOT_DIR, "scripts")))
    print("\n剩余脚本 %d 个：" % len(remain))
    for name in remain:
        print("  ", name)


if __name__ == "__main__":
    main()
