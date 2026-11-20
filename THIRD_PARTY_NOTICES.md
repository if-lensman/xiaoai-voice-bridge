# Third-party components

The MIT license in this repository applies to the project's own code, not to third-party models, libraries, firmware or cloud services.

## Android APK

- Direction and keyword configuration reference: [rolazd/xiaoai-doubao](https://github.com/rolazd/xiaoai-doubao), MIT. This project implements its own LX04 Android terminal and NAS relay.
- [sherpa-onnx v1.13.5](https://github.com/k2-fsa/sherpa-onnx/tree/v1.13.5), Apache-2.0. The release runtime is built from its pinned source with TTS/espeak, speaker diarization, WebSocket and unused application targets disabled. Project JNI glue is in `android/kws_bridge.cpp`.
- Keyword model: `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01-mobile`, Apache License 2.0 as stated in the upstream archive README. The three ONNX files and `tokens.txt` are copied without modification. `wake.txt` is this project's custom keyword configuration. The model card's training-data attribution and upstream URL are retained in `licenses/kws-model-README.md`.
- ONNX Runtime 1.27.1: MIT plus its third-party notices. Runtime comes from the pinned sherpa-onnx Android distribution; license texts are from Microsoft.ML.OnnxRuntime 1.27.1 on official NuGet (provenance in `licenses/onnxruntime-provenance.txt`).
- sherpa-onnx dependencies: kaldi-native-fbank / kissfft, kaldi-decoder / kaldifst / OpenFst, simple-sentencepiece, Eigen, nlohmann JSON. Their original license and notice files are retained under `licenses/`. These include Apache-2.0, BSD, MIT and MPL-2.0 terms; they are not relicensed under the project MIT license. Eigen source is available from the upstream archive referenced in `licenses/README.md`.
- Android NDK r28c `libc++_shared.so`: LLVM / libc++ licenses and exceptions, with the NDK notices retained under `licenses/`.

The same `licenses/` texts and this notice are embedded in the APK under `assets/licenses/` and included in the installation bundle. No upstream vendor firmware or device-unlock tools are included.

## NAS image

- [websockets 15.0.1](https://github.com/python-websockets/websockets/tree/15.0.1), BSD-3-Clause. Its installed distribution retains its license metadata.
- The Docker image uses the official Python 3.12 slim image. Python and Debian packages retain their own license/copyright metadata inside the base image. The project notice and license directory are also included in the image.

Cloud voice service is provided separately by its operator under its own account, usage and billing terms. No service credentials, private addresses, audio recordings or signing keys are distributed.
