# -*- coding: utf-8 -*-
"""入口脚本：由服务器解压并直接取回 frpc.exe / frps.exe

功能：本机 G 盘上的 zip 无法以读模式打开（疑似杀软过滤驱动），改为在 VPS 上解压，
      再把 frpc.exe / frps.exe 逐个 SFTP 下载到本机临时目录，最后复制到 软件/frp-win。
实现：远端 unzip → 临时目录下载 → shutil.copy 落地 → 校验体积。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\PrepareFrpWindows.py
"""

import os
import shutil
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402


def main():
    """无参数。远端解压并取回两个可执行文件。"""
    cfg = ConfigLoader()
    version = cfg.get("frp.version", "0.71.1")
    remote_zip = "/tmp/frp_%s_windows_amd64.zip" % version
    remote_dir = "/tmp/frpwin"
    local_dir = os.path.join(ROOT_DIR, "软件", "frp-win")
    temp_dir = os.path.join(os.environ.get("TEMP", "."), "frp_win_tmp")
    os.makedirs(local_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    client = SshClient(
        host=cfg.require("server.host"),
        port=cfg.get("server.port", 22),
        user=cfg.get("server.user", "root"),
        private_key_path=cfg.get("server.privateKeyPath", ""),
    )
    with client:
        code, out, err = client.run(
            "rm -rf {dir}; mkdir -p {dir}; unzip -oq {zip} -d {dir}; ls -l {dir}/*/".format(
                dir=remote_dir, zip=remote_zip
            ),
            timeout=120,
        )
        print((out or err).strip())
        for name in ("frpc.exe", "frps.exe"):
            remote_file = "%s/frp_%s_windows_amd64/%s" % (remote_dir, version, name)
            temp_file = os.path.join(temp_dir, name)
            client.download(remote_file, temp_file)
            target = os.path.join(local_dir, name)
            shutil.copy(temp_file, target)
            print("%s -> %s (%d 字节)" % (name, target, os.path.getsize(target)))
    print("完成:", local_dir)


if __name__ == "__main__":
    main()
