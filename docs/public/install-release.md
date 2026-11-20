# 安装 v0.1.0 公开测试版

适用于已具备授权 root ADB 的 LX04 / 2.42.118 Release。权限、供电和免责声明请先看 [README](../../README.md#使用须知与免责声明)。安装包不内置作者的地址、设备令牌或 Key；不提供 root、解锁或刷机工具。

## 下载什么

从 [GitHub Releases](https://github.com/if-lensman/xiaoai-voice-bridge/releases) 下载：

| 文件 | 用途 |
|---|---|
| `xiaoai-voice-bridge-0.1.0-install.zip` | 配置、ADB 安装脚本、Compose、许可说明 |
| `xiaoai-voice-bridge-0.1.0-lx04.apk` | LX04 音箱 APP，ARMv7 / Android API 27 |
| `xiaoai-voice-bridge-0.1.0-relay-linux-arm64.tar.gz` | ARM64 NAS Docker 镜像 |
| `xiaoai-voice-bridge-0.1.0-relay-linux-amd64.tar.gz` | Intel / AMD x86-64 NAS Docker 镜像 |
| `SHA256SUMS` | 下载文件校验值 |

NAS 上运行 `uname -m`：`aarch64` 选 ARM64；`x86_64` 选 AMD64。其他架构未提供镜像。只需下载一个 NAS 镜像，音箱 APK 与 NAS 架构无关。

Linux 可用 `sha256sum --ignore-missing -c SHA256SUMS`；macOS 可用 `shasum -a 256 文件名` 与校验表比对。解压安装工具，把 APK 放在工具目录内。

## 1. 在电脑准备自己的配置

电脑需要 Python 3.12 或更新版本、Android platform-tools（ADB）。配置脚本不需要额外 Python 依赖：

```sh
python3 setup_relay.py
```

依次输入 NAS 的局域网 IPv4、音箱的局域网 IPv4、豆包实时语音 Key（隐藏输入）。脚本随机生成设备令牌，输出 `.env`、`private/volc-api-key`、`private/service-config.json` 和空的 `data/` 目录。不要分享这些文件。NAS 与音箱建议使用 DHCP 地址保留。

已有配置时脚本会停止，避免覆盖。在电脑保留配置备份；需要改地址或令牌时，编辑本地私有文件，并重新安装配置、重启中转使双方一致。语音 Key 来自豆包语音控制台，不是火山方舟推理 Key。

## 2. 把中转放到 NAS

把 `.env`、`private/`、`data/`、`compose.yaml` 和选中的镜像归档传到 NAS 上为本项目新建的同一目录。`.env` 是隐藏文件，也要传。

在该目录执行（以下为 ARM64 示例，AMD64 替换文件名）：

```sh
gunzip -c xiaoai-voice-bridge-0.1.0-relay-linux-arm64.tar.gz | docker load
sudo chown -R 10001:10001 private data
sudo chmod 700 private data
sudo chmod 600 private/*
docker compose up -d --no-build
docker compose ps
docker compose exec relay python cloud.py
```

镜像名为 `local/xiaoai-voice-bridge:0.1.0`。安装工具的 Compose 不需要构建或拉取镜像；健康检查成功后，云端检查应显示 `session_created` 与 `session_closed_cleanly` 为 `true`。请勿把 18878 端口映射到公网。音箱与中转使用局域网令牌连接，云端使用加密 WebSocket。

QNAP 的 Docker CLI 可能不在 SSH 默认 PATH。使用 Container Station 的实际 Docker 路径，不需要重启 NAS 或其他应用。

## 3. 在电脑安装音箱 APP

确认 ADB 已连接且获得授权，使用 `adb devices` 查看自己的序列号：

```sh
python3 install_terminal.py \
  --serial YOUR_DEVICE_SERIAL \
  --apk xiaoai-voice-bridge-0.1.0-lx04.apk \
  --config private/service-config.json
```

脚本只支持已验证的 LX04，检查 root ADB 后安装、授权麦克风、写入配置并启动前台服务。已有 APP 配置会先备份到本机 `private/device-backups/`。语音 Key 不会传入音箱。

首次从其他签名的私有测试包迁移时，Android 可能拒绝覆盖安装。先备份原 APP 配置，再卸载旧包并安装；卸载会清除 APP 数据。后续公开版沿用同一发布签名。

## 4. 检查与退出

唤醒“豆包豆包”，问一个简短问题，检查声音和双方字幕；再测试触屏打断、“再见”结束、回到小爱以及重启自启。正常运行不保存录音或逐轮对话日志。

NAS 暂停：`docker compose stop`；恢复：`docker compose up -d --no-build`。卸载 APP 可执行 `adb -s YOUR_DEVICE_SERIAL uninstall local.lx04.doubao.screen`，这会删除 APP 的私有配置；请先备份。无需操作系统或引导分区。

这是首个公开测试版。离线检查与镜像测试不等于所有 NAS、固件及全新设备上的安装均已验证；触屏打断可用，普通说话直接抢话的完整全双工尚未实现。
