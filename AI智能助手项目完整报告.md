# AI智能助手项目完整报告
---
## 一、项目概述
AI智能助手是一款面向Windows平台的本地化AI生产力工具，采用「桌面端外壳+Web工作台+插件化扩展」的架构设计，支持本地大模型调用、文件智能编辑、RAG代码检索、系统工具集成等能力，所有用户数据默认本地存储，兼顾易用性与隐私安全性。

| 项目属性 | 详情 |
| --- | --- |
| 项目名称 | AI智能助手 |
| 首次发布时间 | 2026-07-19 |
| 当前版本 | V1.1 |
| 支持平台 | Windows 10/11 64位 |
| 核心技术栈 | Python 3.8+、PySide6、FastAPI、Vue2、Element UI |
| 授权模式 | Apache 2.0 完全免费开源，无激活、无注册码、无功能限制；赞助版仅为自愿赞助回报（代码签名安装包、免装环境），功能与免费版完全一致 |

## 二、核心功能模块
项目核心功能按职责划分为7个独立模块，模块间低耦合高内聚，所有模块均已完成V1.0版本开发:

| 模块名称 | 核心文件 | 功能描述 | 完成状态 |
| --- | --- | --- | --- |
| 桌面端外壳 | main.py、ai_browser.py、screenshot_tool.py | 提供系统托盘、悬浮窗、内置浏览器、全局截图等桌面原生能力 | ✅ 已完成 |
| API服务层 | api_server.py | 基于FastAPI提供本地HTTP服务，支撑所有Web工作台接口、SSE实时推送、文件操作代理 | ✅ 已完成 |
| AI能力层 | llm_client.py、memory_cache.py、rag_manager.py | 统一大模型调用、多会话向量记忆、代码RAG检索，支持本地/云端模型无缝切换 | ✅ 已完成 |
| Web工作台 | 所有web_*.html、chat_ui.html、chat_float.html | 基于Vue2+Element UI构建的可视化操作界面，包含对话、文件管理、插件市场、系统设置等页面 | ✅ 已完成 |
| 项目管理体系 | project_manual_manager.py、auto_sync_monitor.py | 自动维护项目手册、双向同步文件变更，实现项目资产的自动归档与索引 | ✅ 已完成 |
| 插件体系 | tool_template_manager.py、plugins/目录、web_plugin_market.html | 第三方插件热加载、一键安装/卸载/启停、模板生成、插件市场，内置9款官方插件；2026-09-15起插件活跃开发拆分至独立仓库「AI智能助手插件集」，主仓库仅保留冻结快照（详见第七章） | ✅ 已完成 |
| 系统工具 | scheduler_manager.py、build.py | 定时任务调度、安装包打包等配套工具链 | ✅ 已完成 |

## 三、官方插件清单
当前内置9款官方插件（截至2026-09-15冻结快照），覆盖AIGC生成、信息采集、系统操作、文件处理、远程通道、知识管理六大类场景。**9款插件自2026-09-15起在主仓库冻结留档，活跃开发与BUG修复统一在独立仓库「AI智能助手插件集」进行，修复不回灌主仓库（架构方案详见第七章）**:

| 插件目录 | 插件名称 | 版本 | 所属分类 | 核心功能 | 状态 |
| --- | --- | --- | --- | --- | --- |
| channel_wecom | 企业微信远程通道 | 1.0.0 | 远程通道 | 企业微信自建应用双向消息桥接，手机远程操作本地助手，凭证运行时注入零硬编码 | 🔒 主仓库冻结 |
| file_converter | 文件格式转换 | 1.1.0 | 文件处理 | PNG/JPG/WebP/BMP/ICO/GIF图片互转，MD转Word/Excel，本地处理 | 🔒 主仓库冻结 |
| image_generator | AI图片生成 | 1.1.0 | AIGC生成 | 豆包Seedream 3K/4K文生图/图生图/多图融合/多角度卡片 | 🔒 主仓库冻结 |
| info_collector | AI助手网页功能操作 | 2.0.0 | 信息采集 | 联网搜索采集、网页操作、结构化报告自动保存本地 | 🔒 主仓库冻结 |
| process_monitor | 本地进程监控 | 1.0.0 | 系统操作 | 后台进程监控，AI识别恶意程序分级处置，白名单管理 | 🔒 主仓库冻结 |
| rag_enhance | RAG增强与本地知识库 | 1.2.0 | 知识管理 | 文件名毫秒搜索、Markdown知识库、网页剪藏、文档问答，100%本地 | 🔒 主仓库冻结 |
| safe_file_editor | 文件编辑补充 | 1.0.0 | 文件处理 | 含参数关键词内容的防截断安全编辑，原生edit_file的补充插件 | 🔒 主仓库冻结 |
| screen_recorder | 屏幕录制 | 1.1.0 | 系统操作 | 全屏/框选/指定显示器录制H.264 MP4，暂停续录、变速压缩、独立控制台 | 🔒 主仓库冻结 |
| shipin_shengcheng | 视频生成 | 1.0.0 | AIGC生成 | 豆包Seedance文生视频/图生视频，本地素材自动上传TOS | 🔒 主仓库冻结 |

> 插件安装/卸载/启停/配置全套接口在 api_server.py（/api/plugin/*），市场页为 web_plugin_market.html，加载器为 tool_template_manager.py（运行时扫描 plugins/ 目录），开发模板在 plugin_templates/ 目录。

## 四、当前开发进度
按照V1.1版本迭代规划，当前各项任务进度如下:

| 任务名称 | 预估耗时 | 进度 | 状态 |
| --- | --- | --- | --- |
| 项目手册多格式代码元数据提取（HTML内嵌JS/独立JS-TS/PS1/BAT/ISS提取器+2个真机漏提BUG修复） | 0.5天 | 100%，commit 3eb94ff已推Gitee，2026-09-15真机全量同步复测通过（web_log 10方法、web_file_repo 20方法全部正确，零回归） | ✅ 已完成 |
| 视频剪辑工具V1.1「音量调整」选项卡（音量0~200%、防爆音限幅、无音轨拦截，视频流不重编码） | 0.3天 | 代码开发中，工作区3文件未提交 | 🔄 开发中，待真机测试 |
| 首次安装仓库默认路径修复（Windows默认D:/AI仓库文件夹，空串兜底） | 0.2天 | 代码完成 | 🔄 待重新打包真机测试 |
| 插件独立仓库拆分（主仓库精简+插件集独立项目+AI上下文过滤，详见第七章） | 0.5天 | 阶段0/1已完成（memory_cache提示词cca14fe、插件集本地仓库7cf84ff、主仓库.gitignore c8155f6）；阶段2（file_filter_config过滤plugins）、阶段3（junction联调脚本）待执行；Gitee私有远程待创建 | 🔄 进行中 |

## 五、版本迭代记录
| 版本号 | 发布时间 | 更新内容 |
| --- | --- | --- |
| V1.0 | 2026-07-19 | 项目初始化，完成核心桌面端、Web工作台、基础插件体系开发 |
| V1.1 | 2026-08-13 | 确定MD转Office文档极简落地方案，AI零额外负担输出通用MD即可直接转换为Word/Excel，内置无感知兜底校验 |
| 工程架构调整 | 2026-09-15 | 插件拆分独立仓库:9款插件在主仓库冻结留档（commit c8155f6，.gitignore新增/plugins/整体忽略，已跟踪34个文件不受影响）；独立仓库「AI智能助手插件集」本地初始化（root-commit 7cf84ff，36文件，已通过密钥审计:凭证全部运行时注入、代码零硬编码）；memory_cache固定召回新增"末两轮停止工具调用"规则（cca14fe）；项目手册多格式元数据提取架构升级（3eb94ff）。详见第七章 |

## 六、风险应对预案
针对开发与运行过程中可能出现的风险，已提前制定对应应对方案:

| 风险点 | 影响等级 | 应对方案 | 状态 |
| --- | --- | --- | --- |
| 插件集仓库公开后泄露凭证（TOS AK/SK、企业微信CorpID/Secret、方舟api_key） | 高 | 公开前强制密钥审计（2026-09-15已审:三类高风险插件凭证全部走plugin_config运行时注入，TOS的AK/SK在主程序不在插件仓库，9个plugin.json的default无真实密钥）；仓库先私有跑通，公开时机另行决策；user_config.json、*/runtime/、*.log永久忽略 | ✅ 审计通过，仓库保持私有 |
| 主仓库plugins清空后误执行git restore或误提交删除，破坏冻结快照 | 高 | /plugins/整体忽略规则只对未跟踪文件生效，已跟踪34个文件仍在git中；任何设备看到plugins目录为空属预期（用户主动清空），严禁git restore、严禁git add -A提交删除；打包前由用户手动放回插件，build.py与AI_GZT.spec的打包配置不改动 | 🔄 长期执行（见第七章操作须知） |
| file_filter_config过滤plugins后误伤打包/手册/RAG链路 | 中 | 过滤仅作用于扫盘配置（get_project_tree/手册/RAG/备份四条链路统一生效），打包走spec显式datas声明互不相关；阶段2改完必须真机全量同步验证:手册插件条目消失、核心代码条目无损 | ⏳ 阶段2待执行 |
| junction联调在无权限/换机环境失效 | 低 | 仅用于本机开发联调（mklink /J不需管理员权限），发布走插件市场安装不依赖junction；脚本支持一键拆除 | ⏳ 阶段3待执行 |
| 提示词源码更新被本机旧配置覆盖（memory_config.json已保存fixed_recall时运行时以配置为准） | 中 | 2026-09-15已核实本机memory_config.json的slot2已含新第5条，无覆盖问题；其他设备同步后需在设置页核对/重置提示词 | ✅ 本机已核实 |

## 七、插件独立仓库拆分架构（跨设备同步必读）

> 本章节为2026-09-15拍板的架构决策，供任意设备（含笔记本电脑）同步后由AI直接阅读理解，执行相关任务前必须先通读本章节。

### 7.1 背景与目标
9个插件34个文件约80条函数条目，已占主项目手册函数索引约1/3，插件继续增多将稀释AI对核心代码（api_server/main/llm_client等）的注意力。目标:①插件活跃开发独立成仓，主仓库保持精简；②利用"文件夹即项目、独立手册+独立RAG标签"的既有设计，让插件开发的AI上下文天然隔离；③现有9插件冻结留档、继续随安装包分发，不影响存量用户。

### 7.2 目标架构
D:/AI仓库文件夹/
├── AI智能助手/              ← 主仓库（核心+插件框架，保持精简）
│   ├── api_server.py        ← 插件市场/安装接口（框架，保留）
│   ├── tool_template_manager.py ← 插件加载器（PLUGIN_DIR=plugins/，保留）
│   ├── web_plugin_market.html   ← 插件市场页（保留）
│   ├── plugin_templates/    ← 3个开发模板（脚手架，保留）
│   └── plugins/             ← 9个冻结插件:git中保留快照，日常工作区可清空
└── AI智能助手插件集/         ← 独立git仓库（插件市场源，当前私有）
    ├── channel_wecom/ … shipin_shengcheng/（9插件直接放顶层，不套plugins/层）
    ├── README.md（9插件总索引）、.gitignore（含user_config.json、*/runtime/、*.log、手册）

### 7.3 已完成事项（阶段0+1，2026-09-15）
| 项 | 结果 |
| --- | --- |
| memory_cache.py提示词 | commit cca14fe已推Gitee:固定召回slot2新增第5条"工具调用最后两轮必须停止任务并输出进度说明"；本机memory_config.json已核实含新规则 |
| 插件集密钥审计 | 通过:channel_wecom/shipin_shengcheng/image_generator凭证全部走plugin_config运行时注入，TOS的AK/SK在主程序不在插件仓库，9个plugin.json的default无真实密钥 |
| 插件集本地仓库 | D:/AI仓库文件夹/AI智能助手插件集 已git init，root-commit 7cf84ff，36文件入库（含.gitignore+总索引README），尚未配置远程 |
| 主仓库.gitignore | commit c8155f6已推Gitee:新增/plugins/整体忽略；实测已跟踪的34个冻结插件文件继续跟踪（git对已跟踪文件不应用ignore），模拟新插件目录被精确忽略 |
### 7.4 待办事项（阶段2起，未完成前任何设备不得跳过）
| 阶段 | 内容 | 验证方式 |
| --- | --- | --- |
| 阶段2 | file_filter_config.py的EXCLUDE_DIR_NAMES增加'plugins'，get_project_tree/手册/RAG/备份四条扫盘链路统一过滤插件；改完触发主手册全量同步 | 真机验证:手册第三章插件条目消失、核心代码条目无损；打包链路不受影响（spec显式datas与过滤配置无关） |
| 阶段3 | 插件集仓库放「关联开发环境.bat」:mklink /J把选定插件目录联接到主程序plugins/，改代码即时生效，支持一键拆除 | 联接后主程序能加载插件、拆除后恢复原状 |
| 远程关联 | 用户在Gitee新建私有空仓库（建议名ai-gzt-plugins），插件集仓库关联remote并首次推送；公开时机另行决策 | git log两端哈希一致 |
| 阶段4（后续版本） | 插件集维护market_manifest.json，插件发版打zip挂Release，市场页读清单→复用/api/plugin/install下载解压；下载白名单补加Gitee域名 | 插件市场在线安装走通 |

### 7.5 跨设备操作须知（笔记本电脑等任何设备的AI必须遵守）
1. **主仓库plugins目录为空是预期状态**（用户2026-09-15起主动清空，打包前才放回）:看到`git status`中plugins为deleted或目录不存在，**严禁执行`git restore plugins/`，严禁`git add -A`/`git commit -a`连带提交删除**；34个冻结文件安全保存在git历史中。
2. **打包工作流**:需要打包时由用户手动把插件集仓库的9个插件文件夹复制回主仓库plugins/，再执行一键打包.bat；打包完成后可再次清空。**不得修改build.py和AI_GZT.spec的插件打包配置**。
3. **插件修复流**:所有插件BUG修复与新功能只在「AI智能助手插件集」独立仓库进行，**不回灌主仓库**；发版说明中指引用户卸载旧插件→到插件市场安装新版。
4. **仓库边界**:AI智能助手插件集是独立git仓库（独立手册、独立RAG项目标签），不得把它复制/提交进主仓库；两台设备分别用各自远程同步。
5. **提交纪律**:主仓库提交前必须`git status`核对，视频剪辑工具（V1.1开发中）等旁线改动不得连带提交；精确`git add <文件名>`。
6. 阶段2完成前，若某设备plugins目录非空，主项目手册仍可能收录插件条目，属过滤未生效的已知状态，不影响使用。

### 7.6 插件市场直连下载规划
Git不支持只下载仓库的一个子文件夹，因此不采用git clone整仓方案。目标形态:插件集仓库维护market_manifest.json（插件名/版本/简介/下载URL/requirements），每插件发版打独立zip挂Gitee Release附件，主程序web_plugin_market.html读清单后复用现有/api/plugin/install接口下载解压到plugins/并热重载；需把Gitee域名加入api_server下载白名单（现白名单含github.com）。

### 7.7 关键commit索引
| commit | 仓库 | 内容 |
| --- | --- | --- |
| cca14fe | 主仓库（已推Gitee） | memory_cache固定召回新增末两轮停止工具调用规则 |
| 3eb94ff | 主仓库（已推Gitee） | 项目手册多格式代码元数据提取架构升级+2个HTML漏提BUG修复 |
| c8155f6 | 主仓库（已推Gitee） | .gitignore新增/plugins/整体忽略，插件拆分独立仓库 |
| 7cf84ff | 插件集本地仓库（未配远程） | root-commit:9插件36文件，含.gitignore与总索引README |
