# -*- coding: utf-8 -*-
"""入口脚本：校验分发包配置与脚本语法

功能：1) 用 frpc verify 校验 frpc.toml 语法；2) 用 PowerShell 解析器检查两个 ps1 是否有语法错误；
      3) 汇总包内文件清单与体积。
实现：subprocess 调 frpc.exe verify 与 powershell Parser，输出中文结论。
运行方式：D:\\py39\\python.exe -X utf8 scripts\\ValidatePackage.py
"""

import os
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PKG = os.path.join(ROOT_DIR, "分发包", "FrpWindowsClient")

PS_CHECK = r"""
$files = @('InstallFrpc.ps1','UninstallFrpc.ps1')
foreach ($f in $files) {
  $p = Join-Path $env:PKG $f
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$errors) | Out-Null
  if ($errors.Count -eq 0) { Write-Output ("OK   " + $f) }
  else { Write-Output ("FAIL " + $f); $errors | ForEach-Object { Write-Output ("     " + $_.Message) } }
}
"""


def main():
    """无参数。执行校验并打印结果。"""
    frpc = os.path.join(PKG, "frpc.exe")
    toml = os.path.join(PKG, "frpc.toml")
    result = subprocess.run([frpc, "verify", "-c", toml], capture_output=True)
    print("[frpc verify] 退出码=%d" % result.returncode)
    print((result.stdout + result.stderr).decode("utf-8", "replace").strip() or "(无输出)")
    check = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", PS_CHECK],
        capture_output=True,
        env=dict(os.environ, PKG=PKG),
    )
    print("[ps1 语法检查]")
    print(check.stdout.decode("utf-8", "replace").strip())
    total = 0
    for name in sorted(os.listdir(PKG)):
        path = os.path.join(PKG, name)
        if os.path.isfile(path):
            total += os.path.getsize(path)
    print("[包体积] %.1f MB" % (total / 1048576.0))


if __name__ == "__main__":
    main()
