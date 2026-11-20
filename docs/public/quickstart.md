---
title: 从已具备 ADB 权限的 LX04 开始接入
type: how-to
topics: [xiaoai, docker, getting-started]
status: stable
updated: 2026-11-20
project: xiaoai-voice-bridge
---

# 从已具备 ADB 权限的 LX04 开始接入

本文从事先准备好的、已授权的 root ADB 环境开始，不介绍权限获取、解锁、刷机或原机恢复。APP 本身不提供提权功能。使用前请先阅读 README 的[使用须知与免责声明](../../README.md#使用须知与免责声明)。当前实测 LX04 / 2.42.118 Release，先准备稳定供电。

## 1. 准备语音服务和部署配置

在[豆包语音控制台](https://console.volcengine.com/speech/new/setting/apikeys)开通实时语音服务并创建语音 Key，不使用火山方舟通用推理 Key。不要将 Key 放入截图、聊天或公开的 Compose 文件。

项目提供 `setup_relay.py`，以下地址只是示例，必须换成自己的地址：

```sh
python3 setup_relay.py --relay-ip 192.168.1.100 --speaker-ip 192.168.1.101
```

脚本隐藏读取 Key，并生成 `private/volc-api-key`、`private/service-config.json` 和 `.env`。语音 Key 只给中转使用；音箱配置只有地址和随机设备令牌。私有目录不进 Git 或分享包。

NAS 没有 Python 时，可以在电脑准备这些文件，再通过自己的 SSH 连接传入 NAS。

## 2. 在 NAS 启动中转

Compose 从 `.env` 读取地址，不包含作者实际设备地址。在本项目目录执行：

```sh
sudo chown -R 10001:10001 private data
sudo chmod 700 private data
sudo chmod 600 private/*
docker compose up -d --build
docker compose ps
docker compose exec relay python cloud.py
```

预期：容器健康，云端检查显示 `session_created` 与 `session_closed_cleanly` 为 `true`。这一步不录音、不播放，只检查语音服务连接。

QNAP 的 Docker 可能不在 SSH 默认 PATH，需使用 Container Station 实际目录中的 Docker CLI。不要为本项目重启整个 NAS 或其他应用。

## 3. 构建并安装终端

按[构建说明](build.md)生成 APK。安装脚本明确选择自己的设备：

```sh
python3 install_terminal.py \
  --serial YOUR_DEVICE_SERIAL \
  --apk android/build/screen/doubao-screen.apk \
  --config private/service-config.json
```

安装脚本检查 LX04 和 root ADB，备份已有配置后再写入；不刷写系统或引导分区。预期结果是前台服务启动，屏幕可打开豆包对话页。

## 4. 先完成一轮小测试

说“豆包豆包”，问候完成后问一个简短问题；观察双方字幕。等回答结束后说“再见”，确认返回待机，再次唤醒。

接着测试触屏打断、触屏结束和空闲结束。日常对话稳定后，再确认音箱重启自启。容器策略是 `unless-stopped`，人工停止后不会自行恢复。

排错只分享去掉敏感信息的错误码，不分享 Key、令牌或完整私有配置。

正常运行不保存录音、问题、回答或逐轮日志，只保留健康状态。只有异常类型进入容器日志。
