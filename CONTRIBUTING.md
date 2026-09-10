# 参与贡献指南（Contributing Guide）

首先，感谢你对 **AI智能助手（AI-GZT）** 的兴趣！本项目由一位零基础开发者与 AI 协作完成，我们尤其欢迎同样没有开源经验的朋友提交第一个 Issue 或 PR——不必担心"不够格"。

## 一、行为准则

参与本项目即表示你同意遵守 [《贡献者公约》CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md):保持友善、尊重差异、就事论事。

## 二、开发环境准备

1. 环境要求:Windows 10/11 + Python 3.11（向量检索依赖暂不支持其他版本）；
2. 克隆仓库（国内推荐 Gitee 镜像）:
   - GitHub:`git clone https://github.com/cbhoooo-jpg/AI-GZT.git`
   - Gitee:`git clone https://gitee.com/chen-bohan3000/ai-gzt.git`
3. Windows 用户直接双击根目录 `Python和依赖安装.bat` 一键安装全部依赖（约 3.5 GB）；已有环境可 `pip install -r requirements.txt`；
4. RAG 向量模型权重 `gte-small-zh/pytorch_model.bin`（约 58 MB）未纳入 Git，按 README「源码运行补充」章节指引下载；缺失时程序自动降级，不影响其他功能；
5. 启动:`python main.py`。

## 三、目录结构速览

| 路径 | 作用 |
| --- | --- |
| `main.py` / `api_server.py` | 程序入口、本地 FastAPI 服务与工具路由 |
| `ai_browser.py` | PySide6 工作台外壳、内置浏览器与悬浮窗 |
| `memory_cache.py` / `rag_manager.py` | 对话记忆、本地向量库与召回 |
| `llm_client.py` | 多厂商大模型客户端 |
| `plugins/` | 插件目录，每个插件一个子文件夹（`main.py` + `plugin.json`） |
| `plugin_templates/` | 三类官方插件模板（AIGC 生成 / 信息采集 / 本地操作） |
| `web_*.html`、`chat_ui.html` | 前端页面（Vue 2 + Element UI，静态资源在 `static/`） |
| `tools/` | 内置工具（如智能文件编辑器） |

## 四、提交 Issue

- Bug 请说明:**系统版本、Python 环境或安装包版本、复现步骤、期望与实际表现、日志截图**；
- 功能建议请描述:使用场景、期望行为、是否愿意参与开发；
- 国内用户推荐在 [Gitee Issues](https://gitee.com/chen-bohan3000/ai-gzt/issues) 反馈，也可使用 [GitHub Issues](https://github.com/cbhoooo-jpg/AI-GZT/issues)。

## 五、提交 Pull Request / 合并请求

1. Fork 仓库并新建分支，分支名建议 `feat/xxx`、`fix/xxx`、`docs/xxx`；
2. 提交信息建议使用简洁中文或 [Conventional Commits](https://www.conventionalcommits.org/) 前缀（如 `fix: 修复观测台快照序列化`）；
3. 一个 PR 只解决一件事，并在描述中写明「改了什么、为什么、如何自测」；
4. **请勿提交任何含密钥的本地配置**（`config.json`、`memory_config.json` 等已在 `.gitignore` 中忽略），涉及配置变更请同步修改 `config.example.json`；
5. 提交前请自测:`python -m py_compile` 校验改动的 Python 文件，前端页面在浏览器中实际走一遍流程。

## 六、开发新插件（最常见的扩展方式）

1. 复制 `plugin_templates/` 下最贴近的模板到 `plugins/你的插件名/`；
2. 必须包含 `main.py`（实现标准工具调用协议）与 `plugin.json`（插件元数据、入参 JSON Schema）；
3. 插件新增第三方依赖时，在插件目录自带 `requirements.txt`，并在 `THIRD_PARTY_LICENSES.md` 登记组件与许可证；
4. 优先复用项目已有能力（配置中心、日志、文件过滤、本地 RAG），不要在插件中硬编码密钥或绕过系统禁止目录；
5. 按钮与交互遵循现有 UI 风格，按钮不使用图标，保持界面整洁。

## 七、许可证与贡献协议

本项目基于 **Apache License 2.0** 开源。你提交的贡献默认在同一许可证下授权；你应保证提交内容为本人原创或拥有合法授权，且不包含你无权分发的第三方专有代码。引入新依赖时请确认其许可证与 Apache-2.0 兼容（警惕 GPL 类强传染许可，必要时在 PR 中说明）。

再次感谢你的贡献，欢迎加入！