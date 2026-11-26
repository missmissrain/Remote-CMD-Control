"""远控音乐CLI：通过SSH执行，读取标准输入中的JSON，或用--payload接受UTF8 Base64指令。

参数config为本机私有配置路径；无输入默认查询status。只输出一行JSON，不记录音频地址。
"""

import argparse
import base64
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.MediaLayer.MusicClient import MusicClient


def main():
    """无参数；解码有界请求并调用回环接口，失败返回ok=false与非零退出码。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config/MusicConfig.json"))
    parser.add_argument("--payload")
    parser.add_argument("--action", choices=["status", "pause", "resume", "stop"])
    args = parser.parse_args()
    try:
        if args.payload and args.action:
            raise ValueError("payload与action不能同时指定")
        raw = (base64.b64decode(args.payload, validate=True) if args.payload else
               b"" if args.action or sys.stdin.isatty() else sys.stdin.buffer.read(65537))
        if len(raw) > 65536:
            raise ValueError("请求过大")
        data = json.loads(raw.decode("utf-8")) if raw.strip() else {"action": args.action or "status"}
        if args.action and args.action != "status":
            data["requestId"] = uuid.uuid4().hex
        result = MusicClient(args.config).send_request(data)
    except Exception as exc:
        result = {"ok": False, "error": "音乐指令失败：" + type(exc).__name__}
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
