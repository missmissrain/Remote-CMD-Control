# -*- coding: utf-8 -*-
"""核心层：SSH 远程执行客户端

功能：封装 paramiko，提供单次连接执行命令、上传下载文件、批量执行命令的能力。
实现：支持密码与私钥两种认证方式；命令统一返回 (退出码, 标准输出, 标准错误)；
      提供 run_sudo 以便在 root 环境下执行需要特权或较长超时的命令。
注册参数：
    host          -- 服务器地址（必填）
    port          -- SSH 端口（默认 22）
    user          -- 登录用户（默认 "root"）
    password      -- 登录密码（默认 ""，与 privateKeyPath 二选一）
    privateKeyPath-- 私钥文件路径（默认 ""）
    timeout       -- 连接超时秒数（默认 20）
默认参数说明：
    paramiko 的 AutoAddPolicy 会自动接受首次连接的主机指纹，便于自动化部署。
"""

import paramiko


class SshClient:
    """基于 paramiko 的 SSH 会话封装。"""

    def __init__(
        self,
        host,
        port=22,
        user="root",
        password="",
        private_key_path="",
        timeout=20,
    ):
        self._host = host
        self._port = int(port)
        self._user = user
        self._password = password
        self._private_key_path = private_key_path
        self._timeout = timeout
        self._client = None

    def connect(self):
        """无参数。建立 SSH 连接，已连接时直接返回自身。"""
        if self._client is not None:
            return self
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": self._host,
            "port": self._port,
            "username": self._user,
            "timeout": self._timeout,
            "banner_timeout": self._timeout,
            "auth_timeout": self._timeout,
            "allow_agent": False,
            "look_for_keys": False,
        }
        if self._private_key_path:
            kwargs["key_filename"] = self._private_key_path
        else:
            kwargs["password"] = self._password
        client.connect(**kwargs)
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(30)
        self._client = client
        return self

    def close(self):
        """无参数。关闭连接。"""
        if self._client is not None:
            self._client.close()
            self._client = None

    def run(self, command, timeout=300, get_pty=False):
        """command：要在远端执行的 shell 命令。
        timeout：命令执行超时秒数。
        get_pty：是否申请伪终端（交互式命令需要）。
        返回 (退出码, 标准输出文本, 标准错误文本)。"""
        self.connect()
        stdin, stdout, stderr = self._client.exec_command(
            command, timeout=timeout, get_pty=get_pty
        )
        stdin.close()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        code = stdout.channel.recv_exit_status()
        return code, out, err

    def run_checked(self, command, timeout=300, label=""):
        """command：远端命令。timeout：超时秒数。label：日志标签。
        执行命令，退出码非 0 时抛出 RuntimeError，成功返回标准输出。"""
        code, out, err = self.run(command, timeout=timeout)
        if code != 0:
            raise RuntimeError(
                "远程命令失败[%s] 退出码=%s\n命令: %s\nstdout: %s\nstderr: %s"
                % (label or command, code, command, out.strip(), err.strip())
            )
        return out

    def upload(self, local_path, remote_path):
        """local_path：本地文件路径。remote_path：远端目标路径。
        通过 SFTP 上传文件，返回远端路径。"""
        self.connect()
        sftp = self._client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()
        return remote_path

    def download(self, remote_path, local_path):
        """remote_path：远端文件路径。local_path：本地保存路径。
        通过 SFTP 下载文件，返回本地路径。"""
        self.connect()
        sftp = self._client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()
        return local_path

    def write_remote_file(self, content, remote_path, mode=None):
        """content：文本内容（UTF-8）。remote_path：远端路径。mode：可选八进制权限。
        直接写入远端文件，避免本地临时文件。"""
        self.connect()
        sftp = self._client.open_sftp()
        try:
            with sftp.open(remote_path, "w") as handle:
                handle.write(content)
            if mode is not None:
                sftp.chmod(remote_path, mode)
        finally:
            sftp.close()
        return remote_path

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
