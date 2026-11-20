---
title: 构建和检查源码
type: how-to
topics: [android, python, build]
status: stable
updated: 2026-11-20
project: xiaoai-voice-bridge
---

# 构建和检查源码

中转使用 Python 3.12，运行依赖为 `websockets==15.0.1`。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
```

当前 Android 目标为 ARMv7、最低 API 27。工具链：SDK platform 34、build-tools 34.0.0、NDK 28.2.13676358，以及 Android Studio JDK、CMake 和 Ninja。构建请使用 JDK 17 或更新版本，不使用旧 JDK 8。

通过 `ANDROID_HOME`、`JAVA_HOME` 指定工具位置，`NDK_VERSION` 指定 NDK 版本。本地构建默认使用自己的 `~/.android/debug.keystore`；若不存在，先准备自己的调试签名。发布构建可通过 `APK_SIGNING_KEYSTORE` 和 `APK_SIGNING_PASSWORD_FILE` 指定独立签名文件与密码文件，二者不得进入仓库。

```sh
python3 fetch_kws.py
python3 build_runtime.py
python3 build_kws.py
python3 build_screen.py
```

脚本下载 sherpa-onnx v1.13.5 的原生库和固定 wenetspeech 3.3M mobile 模型，并验证归档 SHA-256。公开源码不存储模型或原生库；发布 APK 单独附带许可。`build_runtime.py` 从固定源码构建关闭 TTS / espeak 和说话人分离的运行库，避免引入本项目不用的组件。

输出 APK 为 `android/build/screen/doubao-screen.apk`。不想配置编译环境时，请使用 [Release 安装流程](install-release.md)。

自动检查不能代替其他型号、其他系统及全新机器上的完整安装测试。配置工具不会获取设备权限，也不包含解锁或刷机功能。
