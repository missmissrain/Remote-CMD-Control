# 远程 CMD 控制（Remote-CMD-Control）

把 **没有公网 IP 的 Windows 电脑的 CMD** 变成你 VPS 上的一个 SSH 端口，
之后在任何地方 `ssh -p 21119 用户名@你的VPS` 就能像连 Linux 一样操作它。

**双向全双工**：本机和对方电脑各跑一个 frpc，各自占一个 VPS 端口 —— 你能控制它，它也能控制你。

```
            控制端 A（你的本机）
              ssh -p 21119 对方用户@VPS        ssh -p 21118 本机用户@VPS
                     │                                  ▲
                     ▼                                  │
        ┌────────────────────────────────────────────────────┐
        │   VPS 47.x.x.x   frps                              │
        │   21117  frpc 接入    21118 → A 的 22   21119 → B 的 22 │
        └────────────────────────────────────────────────────┘
                     ▲                                  │
                     │  B 主动外连（无需公网 IP）           ▼
              被控端 B（另一台 Windows）
```

---

## 1. 特性

| 特性 | 说明 |
| --- | --- |
| 无需公网 IP | 被控端 **主动外连** VPS，家庭宽带 / 公司内网 / 4G 都能用 |
| 真正的命令行 | 走 Windows 自带 OpenSSH Server，登录即 `cmd.exe`，可 `scp` 传文件 |
| 双工互控 | 两端都装同一套包，互相能连，不存在「只能单向」的限制 |
| Token 鉴权 | frps/frpc 使用 token，防止别人蹭你的 VPS 开隧道 |
| 开机自启 | 装成计划任务（SYSTEM），关掉窗口、重启系统都还在 |
| 离线可装 | 分发包自带 `OpenSSH-Win64`，系统装不上可选功能时直接离线安装 |
| 一键部署 | 服务器端、客户端都有脚本，配置只改一个 JSON |

## 2. 端口规划

| 端口 | 协议 | 用途 |
| --- | --- | --- |
| 21117 | TCP | frpc 接入 frps |
| 21118 | TCP | 映射到「本机」的 22 端口（别人连你的机器） |
| 21119 | TCP | 映射到「对方电脑」的 22 端口（你连对方的机器） |

> 需要在自己的云服务器安全组放行 21117/21118/21119。
> 端口可以改，改 `config/ServerConfig.json` 里的 `frp.*` 后重跑脚本即可。

## 3. 快速开始

### 3.1 准备配置文件

```bat
copy config\ServerConfig.example.json config\ServerConfig.json
```

填入你的服务器地址、登录方式（密码或私钥）和一个随机 token。

### 3.2 部署服务端 frps（Linux VPS）

```bat
D:\py39\python.exe -X utf8 scripts\DeployFrpServer.py
```

脚本会：下载 frps → 写 `/etc/frp/frps.toml` → 安装 `frps.service` → 开机自启 → 打印客户端参数。

### 3.3 打包客户端（含 frpc.exe 与离线 OpenSSH）

```bat
D:\py39\python.exe -X utf8 scripts\BuildFrpcPackage.py
D:\py39\python.exe -X utf8 scripts\ValidatePackage.py
```

产物在 `分发包\FrpWindowsClient\`，约 16 MB，可整个拷走。

### 3.4 在被控电脑上安装

1. 把 `FrpWindowsClient` 文件夹拷过去；
2. **确认包内有 `frpc.toml`**：仓库里的包只有 `frpc.toml.example`，复制一份改名
   `frpc.toml` 并填好 `serverAddr` / `token`（或在本机跑 `scripts\BuildFrpcPackage.py` 自动生成）；
3. 按角色选择安装方式：

| 角色 | 端口 | 操作 |
| --- | --- | --- |
| 对方电脑（你连它） | 21119 | 双击 `Install.bat` |
| 本机（它连你） | 21118 | 双击 `InstallLocal-21118.bat` |
| 自定义 | 21120 等 | 命令行执行 `Install.bat 21120` |

4. UAC 点「是」。脚本自动：复制到 `C:\frp` → 启用 OpenSSH Server → 默认 shell 设为 `cmd.exe`
   → 注册计划任务 `FrpClientWin`（SYSTEM、开机自启）→ 自检并打印连接命令。

### 3.5 开始用

```bat
:: 本机 → 对方电脑（对方占 21119）
ssh -p 21119 对方用户名@你的VPS

:: 对方电脑 → 本机（本机占 21118）
ssh -p 21118 本机用户名@你的VPS
```

- 登录密码 = 那台电脑的 Windows 登录密码；
- 登录后是 `cmd.exe`，输入 `powershell` 可切换；
- 传文件：`scp -P 21119 本地文件 用户名@你的VPS:C:/Users/用户名/Desktop/`；
- 首次连接输入 `yes` 接受主机指纹。

## 4. 目录结构

```
Remote-CMD-Control/
├─ config/
│  ├─ ServerConfig.example.json   # 配置模板（复制成 ServerConfig.json 再填）
│  └─ ServerConfig.json           # 真实配置（已 gitignore）
├─ src/
│  ├─ ConfigLayer/ConfigLoader.py     # 配置读取
│  ├─ CoreLayer/SshClient.py          # paramiko SSH 封装
│  └─ TaskLayer/
│     ├─ ServerProbe.py               # 服务器环境探测
│     └─ FrpServerDeployer.py         # frps 部署
├─ scripts/                    # 全部可执行脚本（部署 / 打包 / 校验 / 备份）
├─ 分发包/FrpWindowsClient/    # 拷到 Windows 上的一键安装包
├─ 软件/                       # frpc/frps 原始二进制（体积大，已 gitignore 压缩包）
├─ 文档/                       # 详细部署说明
└─ README.md
```

## 5. 脚本一览

| 脚本 | 作用 |
| --- | --- |
| `scripts/DeployFrpServer.py` | 部署 / 更新 frps，打印客户端参数 |
| `scripts/ProbeServer.py` | 探测服务器环境（系统、端口、出网能力） |
| `scripts/BuildFrpcPackage.py` | 生成 Windows 一键安装包 |
| `scripts/ValidatePackage.py` | 校验 frpc.toml 与安装脚本语法 |
| `scripts/TestTunnel.py` | 实测隧道双向连通性（临时 HTTP 服务） |
| `scripts/PrepareFrpWindows.py` | 经服务器中转取回 frpc/frps 的 Windows 版 |
| `scripts/FetchOpenSsh.py` | 取回 Win32-OpenSSH 离线包 |
| `scripts/ShowLogs.py` | 查看 frps 日志 |
| `scripts/MakeBackup.py` | 版本备份 |

统一用 `D:\py39\python.exe -X utf8 <脚本>` 运行（Windows 中文路径下必须加 `-X utf8`）。

## 6. 常见问题

| 现象 | 处理 |
| --- | --- |
| `Connection refused` | 被控端 frpc 没连上，看 `C:\frp\frpc.log`，检查 token / serverAddr / 网络 |
| 连接超时 | VPS 上 `ss -lntp \| grep 21119` 无监听；或安全组没放行端口 |
| `Permission denied` | 用户名或 Windows 密码不对；Microsoft 账户用账户密码；或改用密钥登录 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | `ssh-keygen -R "[VPS_IP]:21119"` |
| 杀毒软件报毒 | frp 常被误判为黑客工具，把 `C:\frp` 加白名单 |
| 第二台连不上 | 两台用了同一个 `remotePort`，改成不同端口 |
| 家庭版能不能用 | OpenSSH Server 可用；家庭版没有远程桌面，所以本方案走 SSH |

## 7. 安全须知

1. **不要提交真实配置**：`config/ServerConfig.json`、`分发包/**/frpc.toml` 已在 `.gitignore` 中，
   它们含服务器密码 / token。
2. **token 等于隧道口令**，泄露后别人也能借你的 VPS 开隧道。
3. **双工意味着互相都能进**，两边都要设强密码，强烈建议改用密钥登录并关闭密码认证。
4. 只想自己访问，可在 `frps.toml` 用 `allowPorts` 限制映射端口，或在 VPS 防火墙上限定来源 IP。

## 8. 文档

详细部署与排错见 [`文档/远程CMD隧道部署说明.md`](文档/远程CMD隧道部署说明.md)。

## 9. License

MIT
