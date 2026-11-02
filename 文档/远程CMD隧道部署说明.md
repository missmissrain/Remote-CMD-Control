# 远程 CMD 隧道部署说明（frp 双工方案）

> 服务器：你自己的 Linux VPS（示例为阿里云 ECS / Alibaba Cloud Linux 3）
> 方案：VPS 跑 frps；本机与对方电脑各跑一个 frpc，把各自的 22 端口（OpenSSH）映射到 VPS
> 效果：**双向互控** —— 本机能 `ssh -p 21119` 进对方 CMD，对方也能 `ssh -p 21118` 进本机 CMD

---

## 一、整体链路

```
            控制端 A（你的本机）                       控制端 B（对方电脑）
        ssh -p 21119 对方用户@你的服务器IP             ssh -p 21118 本机用户@你的服务器IP
                 │                                          ▲
                 ▼                                          │
      ┌──────────────────────────────────────────────────────────┐
      │  VPS   frps   21117 接入                                   │
      │              21118 ──▶ A 的 22 端口（A 自身 sshd）           │
      │              21119 ──▶ B 的 22 端口（B 自身 sshd）           │
      └──────────────────────────────────────────────────────────┘
                 ▲                                          │
                 │                                          ▼
        A 上的 frpc（主动外连）                        B 上的 frpc（主动外连）
```

- 两端都 **主动外连** VPS，所以都不需要公网 IP；
- 隧道是 **TCP 全双工**：命令下行与回显上行同时双向传输；
- 双向互控的前提是**两端都启用 OpenSSH Server**，同一套安装包即可完成。

## 二、服务器端

| 项目 | 内容 |
| --- | --- |
| frps 版本 | 0.71.1 |
| 程序 | `/opt/frp/frps` |
| 配置 | `/etc/frp/frps.toml`（权限 600，含 token） |
| 服务 | `frps.service`，已 enable，开机自启、崩溃自动重启 |
| 接入端口 | 21117（TCP） |
| 隧道端口 | 21118（本机）、21119（对方） |
| 鉴权 token | 见本地 `config/ServerConfig.json`，**不要提交到公开仓库** |

> 端口可自行调整：改 `config/ServerConfig.json` 后重跑部署脚本，并在云安全组放行对应端口。

### 运维命令

```bash
sudo systemctl status frps
sudo systemctl restart frps
sudo journalctl -u frps -f
sudo ss -lntp | grep -E ':(21117|21118|21119)'
cat /etc/frp/frps.toml
```

## 三、Windows 端安装（两端相同）

把 `分发包/FrpWindowsClient` 拷到目标电脑：

| 角色 | 操作 |
| --- | --- |
| 对方电脑（21119） | 双击 `Install.bat` |
| 本机（21118） | 双击 `InstallLocal-21118.bat` |
| 自定义端口 | `Install.bat 21120` |

脚本自动完成：

1. 复制 `frpc.exe` + `frpc.toml` 到 `C:\frp`；
2. 启用 OpenSSH Server（系统可选功能；失败则用随包 `OpenSSH-Win64` 离线装到 `C:\Program Files\OpenSSH`）；
3. 把 SSH 默认 shell 设为 `cmd.exe`；
4. 注册计划任务 `FrpClientWin`（SYSTEM 身份、开机自启）；
5. 自检并打印本机对外端口与连接命令。

卸载：双击 `Uninstall.bat`（结束进程、删计划任务与 `C:\frp`，OpenSSH Server 保留）。

## 四、互相控制

```bat
:: A 控制 B
ssh -p 21119 B的用户名@你的服务器IP

:: B 控制 A
ssh -p 21118 A的用户名@你的服务器IP
```

- 首次连接输入 `yes` 接受指纹；
- 密码是目标电脑的 Windows 登录密码（Microsoft 账户用账户密码）；
- 登录后即 `cmd.exe`，输入 `powershell` 切换；
- 传文件：`scp -P <端口> 本地文件 用户名@你的服务器IP:C:/Users/用户名/Desktop/`。

### 建议改用密钥登录

```bat
ssh-keygen -t ed25519 -C "remote-cmd"
```

把 `id_ed25519.pub` 内容追加到目标机的 `%USERPROFILE%\.ssh\authorized_keys`；
若账户属于 Administrators 组，Windows OpenSSH 还会读
`C:\ProgramData\ssh\administrators_authorized_keys`，需修权限：

```powershell
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
```

## 五、验证记录

| 检查项 | 结果 |
| --- | --- |
| frps 服务 | active (running)，监听 21117 |
| frpc 配置语法 | `frpc verify` 通过 |
| 安装脚本语法 | InstallFrpc.ps1 / UninstallFrpc.ps1 解析无错误 |
| 隧道连通性 | 临时 HTTP 服务经 frpc → VPS 隧道口 → VPS 侧 `curl 127.0.0.1:<端口>` 返回 `FRP-TUNNEL-OK` |
| ssh 端到端 | 需在两端装完（启用 sshd）后用 `ssh -p` 实测 |

## 六、常见问题

| 现象 | 排查 |
| --- | --- |
| `Connection refused` | 目标端 frpc 没连上：看 `C:\frp\frpc.log`，确认 token / serverAddr / 网络 |
| 连接超时 | VPS 上 `ss -lntp \| grep 端口` 无监听；或安全组未放行 |
| `Permission denied` | 用户名或 Windows 密码不对；或改用密钥登录 |
| 指纹冲突 | `ssh-keygen -R "[你的服务器IP]:21119"` |
| 杀毒报毒 | frp 常被误判，把 `C:\frp` 加白名单 |
| 两台连不上同一端口 | `remotePort` 冲突，改成不同端口后重启任务 |
| 家庭版限制 | OpenSSH Server 可用；家庭版无远程桌面，故本方案走 SSH |

## 七、安全提醒

1. token 等于隧道口令，泄露后别人能借你的 VPS 开隧道；**不要提交到公开仓库**。
2. 双工互控意味着两边互相都能进 —— 两端都要设强密码 / 用密钥登录。
3. 公网 IP 与端口一旦公开就会不断被扫描，属正常现象：
   建议在安全组只放行必要端口，并把 `frps.toml` 的 token 定期更换。
