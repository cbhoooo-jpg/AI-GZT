# AI Workbench (AI智能助手)

[![License](https://img.shields.io/github/license/cbhoooo-jpg/AI-GZT)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/cbhoooo-jpg/AI-GZT)](https://github.com/cbhoooo-jpg/AI-GZT/releases/latest)
[![GitHub Downloads](https://img.shields.io/github/downloads/cbhoooo-jpg/AI-GZT/total)](https://github.com/cbhoooo-jpg/AI-GZT/releases)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4)

[简体中文](README.md) | **English**

> A **local-first, auditable** Windows desktop AI workbench. Chat with LLMs in natural language, deploy local offline models, run a built-in RAG knowledge base with vector memory, and extend everything through a plugin system. **All data stays on your machine by default.** Cloud models are configurable in the settings UI and take effect immediately. A multimodal model is required for screenshots and image messages.

## The Story: Software "Argued Out" Between a Goalkeeper and AI

This project started in 2025 with a casual chat: a user **born in the 1970s with zero coding background** wondered whether AI could build him a personal AI workbench.

Multiple AIs (Doubao, Qwen, ERNIE Bot and others) took turns writing the code while the human provided requirements and pushed back on bad ideas — lots of rewrites, lots of arguments. By late 2025 the software had stabilized. **The codebase was written almost entirely by AI itself** — which makes this workbench its own proof of concept: it is especially good at safely writing and editing code.

Even beginners can use it: point the built-in file repository at a source folder and keep customizing the software by talking to the AI.

## Download

| File | Description | Link |
| --- | --- | --- |
| AI Workbench v1.0 Windows Installer | ~199 MB, Python runtime and all dependencies bundled, works out of the box | [GitHub Release](https://github.com/cbhoooo-jpg/AI-GZT/releases/download/v1.0/AI_GZT_Setup_v1.0.exe) · [123pan mirror (China, fast)](https://4004388641.share.123pan.cn/123pan/NFTTwh-w54xv) |

- The installer is **not code-signed** (an open-source project without a signing budget). On the blue Windows SmartScreen dialog click **"More info" → "Run anyway"**, then approve the UAC prompt. This is normal for unsigned software and does not indicate risk.
- A portable ZIP edition is available by emailing **602477958@qq.com** with the subject "AI智能助手 ZIP 免安装版".
- Source code: `git clone https://github.com/cbhoooo-jpg/AI-GZT.git` (or the [Gitee mirror](https://gitee.com/chen-bohan3000/ai-gzt) for China).
## Features

- **Local & private first**: chat history, RAG index and config files are stored locally; the source code is open and auditable
- **Plugin architecture**: a standardized tool-calling protocol with official plugins for image generation, video generation, web collection, file format conversion, process monitoring, screen recording, a WeCom remote channel and more
- **Private RAG knowledge base**: vector retrieval (faiss + gte-small-zh, 512-dim Chinese embeddings) for codebase indexing and memory recall; degrades gracefully when ML dependencies are missing
- **Desktop workbench**: PySide6 desktop app plus a web management UI with a built-in browser, file repository, scheduled tasks (Cron), backups and full audit logs
- **Packaging**: one-click PyInstaller + Inno Setup build; the installer bundles the Python runtime and all dependencies

## Screenshots

**Full-screen workbench and mini floating window** — switch freely between deep work and a quick chat.

![Workbench and floating window](screenshots/05-workspace-and-float.png)

**File repository** — manage project files with upload, categorization, online preview and a code editor. Everything stays local.

![File repository](screenshots/06-repository.png)

**Settings · Model configuration** — configure cloud model APIs or a local model visually; changes take effect immediately without restarting.

![Settings - model configuration](screenshots/07-settings-model.png)

**Audit logs** — every file operation and command execution by the AI is recorded, auditable and traceable.

![Operation logs](screenshots/08-operation-logs.png)

## Quick Start (from source)

Requires **Python 3.11 64-bit** on Windows 10/11.

```bash
git clone https://github.com/cbhoooo-jpg/AI-GZT.git
cd AI-GZT
pip install -r requirements.txt
python main.py
```

On first launch, open **Settings** and configure a model API key (any OpenAI-compatible endpoint works: Doubao/Volcengine Ark, DeepSeek, Qwen, OpenAI, etc.), then set a repository directory. Windows users can instead double-click `Python和依赖安装.bat` to install the full environment automatically.

**About the RAG vector model**: the `gte-small-zh/pytorch_model.bin` weights (~58 MB) are not included in Git to keep the repository small. Source users can download it from [ModelScope](https://modelscope.cn/models/iic/nlp_gte_sentence-embedding_chinese-small) and place it in the `gte-small-zh/` folder. If it is missing, RAG disables itself automatically while all other features keep working. The installer edition already bundles this file.

## Privacy

- Cloud model and image/video generation calls go **directly from your machine to the provider** using your own API key. This project does not proxy or collect any data.
- Local models and vector retrieval run fully offline with no network requests.
- API keys are stored only in your local config.

## Plugins

Plugins live in the `plugins/` directory; each one contains `main.py` + `plugin.json`. Three starter templates (AIGC generation / information collection / local operation) are provided under `plugin_templates/`.

## Community

- Questions and feature requests: [GitHub Issues](https://github.com/cbhoooo-jpg/AI-GZT/issues) (users in China may prefer the [Gitee mirror](https://gitee.com/chen-bohan3000/ai-gzt/issues))
- Read the [FAQ](FAQ.md) and [contributing guide](CONTRIBUTING.md) first; please follow the [code of conduct](CODE_OF_CONDUCT.md)
- Security vulnerabilities: report privately via email to **cbhoooo@163.com**, see [SECURITY.md](.github/SECURITY.md)
- Roadmap: see [ROADMAP.md](ROADMAP.md)

## License

Licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for the full text. When redistributing, retain the copyright notice and LICENSE; mark changed files accordingly.

## Disclaimer

This is a high-privilege local productivity tool (it can run shell commands and read/write files under AI-driven natural-language instructions). Use it only in trusted directories and with prompts you understand. The software is provided "as is"; see the Chinese [README](README.md) for the full disclaimer.