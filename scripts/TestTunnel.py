# -*- coding: utf-8 -*-
"""入口脚本：验证 frp 双向隧道是否真正可用

功能：在本机起一个临时 HTTP 服务（8899），用 frpc 把远端 21118 映射到该服务，
      再从 VPS 上 curl 127.0.0.1:21118，验证「本机 → frps → 被控端」的完整链路与双向收发。
实现：线程内跑 http.server，subprocess 启动 frpc，SSH 远端 curl，结束后清理进程与临时文件。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\TestTunnel.py
"""

import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

from ConfigLayer.ConfigLoader import ConfigLoader  # noqa: E402
from CoreLayer.SshClient import SshClient  # noqa: E402

LOCAL_PORT = 8899
PAYLOAD = "FRP-TUNNEL-OK"


class Handler(BaseHTTPRequestHandler):
    """临时验证用 HTTP 处理器，固定返回 PAYLOAD。"""

    def do_GET(self):
        """无参数。返回固定文本，用于识别请求确实穿过隧道落到本机。"""
        body = PAYLOAD.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        """抑制默认访问日志。"""
        return


def wait_port(port, timeout=10):
    """port：本机端口。timeout：等待秒数。端口可连返回 True。"""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main():
    """无参数。执行隧道连通性验证并输出结论。"""
    cfg = ConfigLoader()
    host = cfg.require("server.host")
    remote_port = cfg.get("frp.peerRemotePort", 21119)
    frpc = os.path.join(ROOT_DIR, "软件", "frp-win", "frpc.exe")
    config_path = os.path.join(ROOT_DIR, "output", "frpc_test.toml")
    log_path = os.path.join(ROOT_DIR, "output", "frpc_test.log")

    config = """serverAddr = "{host}"
serverPort = {bind}
auth.method = "token"
auth.token = "{token}"
log.to = "{log}"
log.level = "debug"

[[proxies]]
name = "tunnel-test"
type = "tcp"
localIP = "127.0.0.1"
localPort = {local}
remotePort = {remote}
""".format(
        host=host,
        bind=cfg.get("frp.bindPort", 21117),
        token=cfg.get("frp.token", ""),
        log=log_path.replace("\\", "/"),
        local=LOCAL_PORT,
        remote=remote_port,
    )
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(config)

    server = HTTPServer(("127.0.0.1", LOCAL_PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("本地验证服务已启动: 127.0.0.1:%d" % LOCAL_PORT)

    proc = subprocess.Popen(
        [frpc, "-c", config_path],
        cwd=os.path.dirname(frpc),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("frpc 已启动, PID=%d，等待隧道建立 ..." % proc.pid)
    time.sleep(6)

    ok = False
    try:
        client = SshClient(
            host=host,
            port=cfg.get("server.port", 22),
            user=cfg.get("server.user", "root"),
            private_key_path=cfg.get("server.privateKeyPath", ""),
        )
        with client:
            code, out, err = client.run(
                "curl -s -m 8 http://127.0.0.1:%d/ || echo CURL_FAIL" % remote_port, timeout=30
            )
            print("VPS 侧访问 127.0.0.1:%d -> %s" % (remote_port, (out or err).strip()))
            ok = PAYLOAD in out
            code, out, err = client.run(
                "sudo -n ss -lntp | grep ':%d'" % remote_port, timeout=30
            )
            print("VPS 侧端口监听:", (out or err).strip() or "无")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server.shutdown()
    print("\n结论:", "隧道连通，双向可用" if ok else "隧道不通，请查看 %s" % log_path)


if __name__ == "__main__":
    main()
