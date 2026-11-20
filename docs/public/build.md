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

当前 Android 目标为 ARMv7、最低 API 27。工具链：SDK platform 34、build-tools 34.0.0、NDK 28.2.13676358，以及 Android Studio JDK。构建请使用 JDK 17 或更新版本，不使用旧 JDK 8。

通过 `ANDROID_HOME`、`JAVA_HOME` 指定工具位置，`NDK_VERSION` 指定 NDK 版本。使用自己的 `~/.android/debug.keystore`；若不存在，先准备自己的调试签名。

```sh
python3 fetch_kws.py
python3 build_kws.py
python3 build_screen.py
```

脚本下载 sherpa-onnx v1.13.5 的原生库和固定 wenetspeech 3.3M mobile 模型，并验证归档 SHA-256。第三方模型和库不随公开源码再分发。

输出 APK 为 `android/build/screen/doubao-screen.apk`。当前没有预编译 APK 下载，请从源码构建。

自动检查不能代替其他型号、其他系统及全新机器上的完整安装测试。配置工具不会获取设备权限，也不包含解锁或刷机功能。
