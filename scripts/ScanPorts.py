# -*- coding: utf-8 -*-
"""入口脚本：扫描 VPS 常见服务端口

功能：探测目标服务器上 SSH 备选端口与 RustDesk 相关端口是否开放。
实现：使用 socket 并发 connect，输出开放端口列表及 SSH 标识。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ScanPorts.py
"""

import socket
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402

PORTS = [21, 22, 80, 443, 2222, 2022, 2200, 22022, 3389, 8080,
         21114, 21115, 21116, 21117, 21118, 21119, 8443]


def probe(host, port, timeout=3.0):
    """host/port：目标地址与端口。timeout：超时秒数。
    返回 (端口, 是否开放, 首行 banner)。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        banner = ""
        try:
            sock.settimeout(1.5)
            data = sock.recv(128)
            banner = data.decode("utf-8", "replace").strip().replace("\r\n", " ")
        except Exception:  # noqa: BLE001
            pass
        return port, True, banner
    except Exception:  # noqa: BLE001
        return port, False, ""
    finally:
        sock.close()


def main():
    """无参数。扫描端口并打印结果。"""
    cfg = ConfigLoader()
    host = cfg.require("server.host")
    for port in PORTS:
        _, opened, banner = probe(host, port)
        if opened:
            print("开放 %5d  %s" % (port, banner))


if __name__ == "__main__":
    main()
