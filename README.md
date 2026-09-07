# AI智能助手

> 本地优先、可审计的 Windows 桌面 AI 工作台。基于大语言模型实现自然语言交互，支持本地模型离线部署，内置 RAG 私有知识库与向量记忆，采用插件化扩展架构，所有数据默认本地存储。


---

## 未签名安装包如何跳过 SmartScreen（免费版必读）

官方免费安装包未经代码签名（代码签名证书需向权威机构按年付费，签名版作为赞助回报提供），首次双击安装时 Windows 可能弹出安全提示，这是所有未签名软件的正常现象，**不代表软件有风险**。按以下 4 步操作即可顺利安装（前 3 个弹窗仅首次安装未签名版时出现）:

**第 1 步:SmartScreen 蓝色提示窗 —— 点击「更多信息」**

![SmartScreen 蓝色提示窗](screenshots/01-smartscreen.png)

在弹出的蓝色窗口「Windows 已保护你的电脑」中，点击提示文字下方的 **「更多信息」**。

**第 2 步:点击「仍要运行」**

窗口展开后，点击随即出现的 **「仍要运行」** 按钮，安装程序开始启动。

**第 3 步:用户帐户控制（UAC）黄色弹窗 —— 点击「是」**

![UAC 未知发布者弹窗](screenshots/02-uac-unknown.png)

随后弹出黄色的「用户帐户控制」窗口，询问"你要允许来自未知发布者的应用对你的设备进行更改吗？"，发布者显示为"未知"是未签名所致，属正常现象。点击 **「是」** 进入安装向导。

**第 4 步:全中文安装向导内完成安装**

![许可协议页](screenshots/03-license.png)

- 许可协议页:勾选 **「我接受协议」**，点击「下一步」

![选择安装位置页](screenshots/04-install-dir.png)

- 选择目标位置页:确认安装路径（默认安装到当前用户目录），点击「下一步」→「安装」，等待进度条走完即安装完成

> 💡 提示:以上 SmartScreen 与 UAC 提示仅在首次安装未签名版本时出现，安装完成后从桌面/开始菜单启动程序不会再弹出。赞助版安装包经过官方代码签名，双击安装即可跳过第 1~3 步全部提示。
> 📸 截图文件存放于 `screenshots/` 目录，命名与拍摄要点见该目录下说明文件。

## 赞助版说明

本软件源码 **100% 免费开源**（Apache 2.0 协议），功能无任何阉割，自行下载源码即可运行全部能力。如果你希望获得更省心的开箱体验，可通过 **爱发电 / 面包多** 赞助作者，获取赞助版安装包:

- ✅ 使用官方代码签名证书签名，**双击安装零 SmartScreen 警告**，杀毒软件误报率大幅降低
- ✅ 免装 Python 环境与依赖，下载即用
- ✅ 后续大版本更新下载链接、使用答疑支持

赞助完全自愿:不赞助也能使用全部功能——下载源码自行运行，或按上方教程跳过 SmartScreen 安装免费版即可。

---

## 核心特性

- **本地隐私优先**:对话记忆、RAG 知识库、配置文件全部存储在本地，代码开源可审计
- **插件化架构**:标准化工具调用协议，支持图片生成、视频生成、网页采集、文件格式转换、进程监控、企业微信通道等插件，社区可自由扩展
- **RAG 私有知识库**:内置向量检索（faiss + gte-small-zh 中文模型），支持代码库索引与记忆召回，依赖缺失时自动优雅降级
- **桌面工作台**:PySide6 桌面端 + Web 管理界面，内置浏览器、文件仓库、定时任务、备份管理、操作日志
- **工程化打包**:PyInstaller + Inno Setup 一键打包，frozen 环境下自动探测外部 Python 依赖注入

## 开源许可证

本项目基于 **Apache License 2.0** 开源，完整许可证文本见 [LICENSE](LICENSE)。

Copyright 2026 AI智能助手开发团队

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

二次分发时须保留版权声明与 LICENSE 文件；修改过的文件须注明变更。

## ⚠️ 安全与权限声明

本工具为**高权限本地效率工具**，以下能力由 AI 按自然语言指令驱动，请在可信目录、充分理解指令含义的前提下使用:

- **终端命令执行**:可执行任意系统命令
- **文件读写/编辑/删除**:可操作仓库目录内文件（系统目录默认在禁止列表）
- **进程监控与终止**:可扫描并结束运行中的进程（内置系统关键进程保护名单）
- **全局截图**:可截取屏幕任意区域
- **网页采集**:可访问公网网页并提取内容
- **企业微信通道**:启用后可远程接收指令

建议:不要在包含敏感数据的目录中授予仓库权限；插件密钥仅保存在本地配置中。

## 第三方服务与数据隐私

- 云端大模型（如火山方舟/豆包）、图片/视频生成插件:**API Key 由用户自行申请并在设置页配置**，请求直接从本机发往服务商，本项目不中转、不收集任何数据
- 对象存储（火山引擎 TOS）:仅在用户主动配置 AK/SK 后用于文件上传，默认关闭
- 本地模型与向量检索:完全离线运行，无任何网络请求
- 第三方开源组件许可证清单见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)

## 快速开始

**方式一:一键环境安装（推荐，无需手动装任何东西）**

Windows 用户直接双击项目根目录下的 **`Python和依赖安装.bat`**，脚本会自动完成全部环境准备:

1. 检测并自动下载安装 **Python 3.11.9**（华为云镜像，静默安装到当前用户目录，**无需管理员权限**）
2. 检测并自动安装 **VC++ 2015-2022 x64 运行库**（PyTorch 等依赖必需，已安装则自动跳过）
3. 自动升级 pip 并配置清华国内镜像源，加速依赖下载
4. 自动安装 `requirements.txt` 中的全部依赖（总大小约 3.5 GB，预计 5-15 分钟，请耐心等待）
5. 自动校验 PySide6、FastAPI、PyTorch、Transformers 等核心依赖是否安装成功

看到「环境配置全部完成」提示后，直接运行 `python main.py` 启动程序即可。若中途报错，按脚本窗口内的中文提示排查网络后重新运行即可（已安装的步骤会自动跳过）。

**方式二:手动安装（本机已有 Python 3.11 环境的用户）**

```bash
# 环境要求:Python 3.11（向量检索依赖需 3.11）
pip install -r requirements.txt
python main.py
```

首次启动后在「系统设置」中配置模型 API（或选择本地模型），设置仓库目录即可使用。完整打包方案见 `build.py` 与 `AI智能助手Windows单机版跑通方案.md`。

## 源码运行补充:向量模型文件

RAG 私有知识库依赖中文向量模型 `gte-small-zh`（阿里达摩院 GTE 中文向量模型，向量维度 512）。

- **安装版用户无需任何操作**:安装包已内置完整模型文件（`pytorch_model.bin`，约 58 MB），开箱即用。
- **源码用户请注意**:受 GitHub 仓库体积限制，模型权重文件 `pytorch_model.bin` 未纳入 Git 仓库。`git clone` 后需自行下载该文件并放入 `gte-small-zh/` 目录；若缺少该文件，程序启动时 RAG 知识库会**自动降级禁用**（对话、插件等其他功能完全不受影响），控制台会打印警告信息。

**下载方式一:网页直接下载（推荐）**

1. 打开 ModelScope 模型主页:https://modelscope.cn/models/iic/nlp_gte_sentence-embedding_chinese-small
2. 切换到「文件」标签页，在文件列表中找到 `pytorch_model.bin`，点击下载
3. 将下载得到的 `pytorch_model.bin` 放入项目根目录下的 `gte-small-zh/` 文件夹，与 `configuration.json`、`vocab.txt` 等文件同级

**下载方式二:modelscope 命令行**

```bash
pip install modelscope
modelscope download --model iic/nlp_gte_sentence-embedding_chinese-small pytorch_model.bin --local_dir gte-small-zh
```

放置完成后，`gte-small-zh/` 目录结构应如下所示:

```
gte-small-zh/
├── pytorch_model.bin        # ← 需自行下载（约 58 MB）
├── configuration.json
├── config.json
├── vocab.txt
├── tokenizer_config.json
├── special_tokens_map.json
└── ...
```

## 插件开发

插件放置于 `plugins/` 目录，每个插件包含 `main.py` + `plugin.json`，模板参考 `plugin_templates/` 目录下的三类标准模板（AIGC 生成类 / 信息采集查询类 / 本地操作类）。

## 免责声明

本软件按"现状"提供，作者不对使用本工具造成的任何直接或间接损失承担责任。请遵守当地法律法规，勿将本工具用于任何违法用途。