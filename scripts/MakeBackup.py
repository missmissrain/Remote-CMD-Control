# -*- coding: utf-8 -*-
"""入口脚本：生成版本备份

功能：把代码（src/scripts/config）、文档与输出文件复制到 备份/工程名vX.X/，
      并维护 备份/版本记录.json，记录版本号、时间与说明。
实现：按白名单目录复制（不拷贝 软件/ 等大文件），已存在同名版本目录时先清空再写入。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\MakeBackup.py 1.0 "版本说明"
"""

import json
import os
import shutil
import sys
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PROJECT_NAME = "开源远程控制"
BACKUP_ROOT = os.path.join(ROOT_DIR, "备份")
INCLUDE_DIRS = ["src", "scripts", "config", "文档", "output"]
INCLUDE_FILES = ["README.md"]


def main():
    """无参数或接收版本号与说明。执行备份并更新版本记录。"""
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0"
    note = sys.argv[2] if len(sys.argv) > 2 else "首次备份"
    target_dir = os.path.join(BACKUP_ROOT, "%sv%s" % (PROJECT_NAME, version))
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    for name in INCLUDE_DIRS:
        source = os.path.join(ROOT_DIR, name)
        if os.path.isdir(source):
            shutil.copytree(source, os.path.join(target_dir, name))
    for name in INCLUDE_FILES:
        source = os.path.join(ROOT_DIR, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(target_dir, name))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(target_dir, "版本说明.md"), "w", encoding="utf-8") as handle:
        handle.write("# %sv%s\n\n- 备份时间：%s\n- 版本说明：%s\n" % (PROJECT_NAME, version, now, note))
    record_path = os.path.join(BACKUP_ROOT, "版本记录.json")
    records = []
    if os.path.isfile(record_path):
        with open(record_path, "r", encoding="utf-8") as handle:
            records = json.load(handle)
    records = [item for item in records if item.get("version") != version]
    records.append({"version": version, "time": now, "note": note, "path": target_dir})
    records.sort(key=lambda item: item["version"])
    with open(record_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
    print("备份完成:", target_dir)
    print("版本记录:", record_path)


if __name__ == "__main__":
    main()
