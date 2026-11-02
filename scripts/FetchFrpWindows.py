# -*- coding: utf-8 -*-
"""入口脚本：经服务器中转下载 frp Windows 包并解压

功能：本机直连 GitHub 下载被 403 拦截，改为在 VPS 下载后 SFTP 取回，
      再把 frpc.exe / frps.exe 解压到 软件/frp-win 目录。
实现：远端 curl + 本地 zipfile 解压，保留 frpc.exe 与 frps.exe。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\FetchFrpWindows.py
"""

import os
import sys
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402


def main():
    """无参数。下载并解压 frp Windows 包。"""
    cfg = ConfigLoader()
    version = cfg.get("frp.version", "0.71.1")
    file_name = "frp_%s_windows_amd64.zip" % version
    url = "https://github.com/fatedier/frp/releases/download/v%s/%s" % (version, file_name)
    remote_path = "/tmp/%s" % file_name
    local_dir = os.path.join(ROOT_DIR, "软件")
    os.makedirs(local_dir, exist_ok=True)
    local_zip = os.path.join(local_dir, file_name)

    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, _ = client.run(
            "ls -l %s 2>/dev/null | awk '{print $5}'" % remote_path, timeout=30
        )
        size = (out or "").strip()
        if not size.isdigit() or int(size) < 5 * 1024 * 1024:
            print("远端下载中 ...")
            code, out, err = client.run(
                "curl -fL --retry 3 -o %s '%s' && ls -l %s" % (remote_path, url, remote_path),
                timeout=1800,
            )
            print((out or err).strip().splitlines()[-1])
            if code != 0:
                raise SystemExit("远端下载失败")
        print("回传中 ...")
        client.download(remote_path, local_zip)

    out_dir = os.path.join(local_dir, "frp-win")
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(local_zip) as archive:
        for name in archive.namelist():
            base = os.path.basename(name)
            if base in ("frpc.exe", "frps.exe"):
                with archive.open(name) as source, open(os.path.join(out_dir, base), "wb") as target:
                    target.write(source.read())
                print("已解压:", base)
    print("完成:", out_dir)


if __name__ == "__main__":
    main()
