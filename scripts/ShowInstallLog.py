# -*- coding: utf-8 -*-
"""入口脚本：查看本机 frpc 安装日志

功能：读取 output/local_frpc_install.log，检查本机 frpc 是否安装成功。
实现：文件不存在或为空时给出明确提示。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ShowInstallLog.py
"""

import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LOG = os.path.join(ROOT_DIR, "output", "local_frpc_install.log")


def main():
    """无参数。打印安装日志内容。"""
    if not os.path.isfile(LOG):
        print("日志不存在:", LOG)
        return
    print("大小:", os.path.getsize(LOG), "字节")
    with open(LOG, "r", encoding="utf-8", errors="replace") as handle:
        print(handle.read())


if __name__ == "__main__":
    main()
