# AI智能助手 项目手册
---
## 一、项目核心信息
1. 项目名称：AI智能助手
2. 创建时间：2026-09-07 10:46:24
3. 负责人：AI助手

## 二、全项目文件明细清单
| 文件名称 | 所属项目 | 功能描述 |
| --- | --- | --- |
| AI智能助手项目手册.md | AI智能助手 | 项目全量信息说明、规范定义、文件索引 |
| .gitignore | AI智能助手 | 其他文件 |
| ai_browser.py | AI智能助手 | 智能助手内置浏览器 V1.0（核心功能版） |
| AI_GZT.spec | AI智能助手 | 其他文件 |
| AI_GZT_User_Guide.md | AI智能助手 | Markdown文档 |
| AI智能助手功能清单.md | AI智能助手 | Markdown文档 |
| AI智能助手项目完整报告.md | AI智能助手 | Markdown文档 |
| api_server.py | AI智能助手 | API服务层 V1.0 |
| app_icon.ico | AI智能助手 | 其他文件 |
| auto_sync_monitor.py | AI智能助手 | 双向自动同步监听模块 |
| build.py | AI智能助手 | AI智能助手 PyInstaller 打包脚本 |
| chat_float.html | AI智能助手 | AI悬浮助手 |
| chat_ui.html | AI智能助手 | AI智能体对话界面 |
| config.example.json | AI智能助手 | 配置文件 |
| config.json | AI智能助手 | 配置文件 |
| convert_icon.py | AI智能助手 | PNG转ICO超清圆形图标转换脚本 |
| editor_empty_bg.png | AI智能助手 | 图片资源 |
| file_editor.html | AI智能助手 | 文件预览 |
| LICENSE | AI智能助手 | 其他文件 |
| llm_client.py | AI智能助手 | 统一模型调用客户端 |
| logo.png | AI智能助手 | 图片资源 |
| main.py | AI智能助手 | 其他文件 |
| memory_cache.py | AI智能助手 | 向量记忆库 |
| memory_config.json | AI智能助手 | 配置文件 |
| project_manual_manager.py | AI智能助手 | 项目手册管理核心模块 |
| prompt_templates.json | AI智能助手 | 配置文件 |
| Python和依赖安装.bat | AI智能助手 | 其他文件 |
| rag_manager.py | AI智能助手 | 添加文件到RAG库，自动提取项目归属标签 |
| README.md | AI智能助手 | Markdown文档 |
| requirements.txt | AI智能助手 | 文本文件 |
| sample.html | AI智能助手 | 记忆管理 - AI智能助手 |
| scheduler_manager.py | AI智能助手 | 其他文件 |
| screenshot_tool.py | AI智能助手 | 全局系统级截图工具 V1.0（极简无依赖版） |
| setup.iss | AI智能助手 | 其他文件 |
| THIRD_PARTY_LICENSES.md | AI智能助手 | Markdown文档 |
| tool_template_manager.py | AI智能助手 | AI助手指令固化模块 |
| web_about.html | AI智能助手 | 关于 - AI工作台 |
| web_backup.html | AI智能助手 | 文件备份管理 |
| web_file_repo.html | AI智能助手 | 文件仓库 |
| web_log.html | AI智能助手 | 操作日志 |
| web_plugin_market.html | AI智能助手 | 插件市场 - AI智能助手 |
| web_scheduler.html | AI智能助手 | 定时任务管理 - AI智能助手 |
| web_settings.html | AI智能助手 | 系统设置 |
| web_workspace.html | AI智能助手 | AI工作台 |
| 一键打包.bat | AI智能助手 | 其他文件 |
| code_rag/code.index | AI智能助手/code_rag | 其他文件 |
| gte-small-zh/.msc | AI智能助手/gte-small-zh | 其他文件 |
| gte-small-zh/.mv | AI智能助手/gte-small-zh | 其他文件 |
| gte-small-zh/config.json | AI智能助手/gte-small-zh | 配置文件 |
| gte-small-zh/configuration.json | AI智能助手/gte-small-zh | 配置文件 |
| gte-small-zh/README.md | AI智能助手/gte-small-zh | Markdown文档 |
| gte-small-zh/requirements.txt | AI智能助手/gte-small-zh | 文本文件 |
| gte-small-zh/special_tokens_map.json | AI智能助手/gte-small-zh | 配置文件 |
| gte-small-zh/tokenizer.json | AI智能助手/gte-small-zh | 配置文件 |
| gte-small-zh/tokenizer_config.json | AI智能助手/gte-small-zh | 配置文件 |
| gte-small-zh/vocab.txt | AI智能助手/gte-small-zh | 文本文件 |
| gte-small-zh/resources/dual-encoder.png | AI智能助手/gte-small-zh/resources | 图片资源 |
| Languages/ChineseSimplified.isl | AI智能助手/Languages | 其他文件 |
| Languages/ChineseSimplified.isl.bak | AI智能助手/Languages | 其他文件 |
| plugins/channel_wecom/main.py | AI智能助手/plugins/channel_wecom | 企业微信远程通道插件 |
| plugins/channel_wecom/plugin.json | AI智能助手/plugins/channel_wecom | 配置文件 |
| plugins/channel_wecom/README.md | AI智能助手/plugins/channel_wecom | Markdown文档 |
| plugins/channel_wecom/requirements.txt | AI智能助手/plugins/channel_wecom | 文本文件 |
| plugins/file_converter/main.py | AI智能助手/plugins/file_converter | 文件格式转换插件 |
| plugins/file_converter/plugin.json | AI智能助手/plugins/file_converter | 配置文件 |
| plugins/file_converter/README.md | AI智能助手/plugins/file_converter | Markdown文档 |
| plugins/file_converter/requirements.txt | AI智能助手/plugins/file_converter | 文本文件 |
| plugins/image_generator/main.py | AI智能助手/plugins/image_generator | AI图片生成插件 |
| plugins/image_generator/plugin.json | AI智能助手/plugins/image_generator | 配置文件 |
| plugins/image_generator/README.md | AI智能助手/plugins/image_generator | Markdown文档 |
| plugins/image_generator/requirements.txt | AI智能助手/plugins/image_generator | 文本文件 |
| plugins/info_collector/main.py | AI智能助手/plugins/info_collector | 其他文件 |
| plugins/info_collector/plugin.json | AI智能助手/plugins/info_collector | 配置文件 |
| plugins/info_collector/README.md | AI智能助手/plugins/info_collector | Markdown文档 |
| plugins/info_collector/requirements.txt | AI智能助手/plugins/info_collector | 文本文件 |
| plugins/process_monitor/main.py | AI智能助手/plugins/process_monitor | 其他文件 |
| plugins/process_monitor/plugin.json | AI智能助手/plugins/process_monitor | 配置文件 |
| plugins/process_monitor/README.md | AI智能助手/plugins/process_monitor | Markdown文档 |
| plugins/process_monitor/requirements.txt | AI智能助手/plugins/process_monitor | 文本文件 |
| plugins/rag_enhance/main.py | AI智能助手/plugins/rag_enhance | 其他文件 |
| plugins/rag_enhance/plugin.json | AI智能助手/plugins/rag_enhance | 配置文件 |
| plugins/safe_file_editor/main.py | AI智能助手/plugins/safe_file_editor | 其他文件 |
| plugins/safe_file_editor/plugin.json | AI智能助手/plugins/safe_file_editor | 配置文件 |
| plugins/shipin_shengcheng/main.py | AI智能助手/plugins/shipin_shengcheng | 其他文件 |
| plugins/shipin_shengcheng/plugin.json | AI智能助手/plugins/shipin_shengcheng | 配置文件 |
| plugins/shipin_shengcheng/README.md | AI智能助手/plugins/shipin_shengcheng | Markdown文档 |
| plugins/shipin_shengcheng/requirements.txt | AI智能助手/plugins/shipin_shengcheng | 文本文件 |
| plugin_templates/template_aigc_generate_AIGC生成类插件模板.md | AI智能助手/plugin_templates | Markdown文档 |
| plugin_templates/template_info_collect_信息采集查询类插件模板.md | AI智能助手/plugin_templates | Markdown文档 |
| plugin_templates/template_local_operation_本地操作类插件模板.md | AI智能助手/plugin_templates | Markdown文档 |
| screenshots/01-smartscreen.png | AI智能助手/screenshots | 图片资源 |
| screenshots/01b-smartscreen-expanded.png | AI智能助手/screenshots | 图片资源 |
| screenshots/02-uac-unknown.png | AI智能助手/screenshots | 图片资源 |
| screenshots/03-license.png | AI智能助手/screenshots | 图片资源 |
| screenshots/04-install-dir.png | AI智能助手/screenshots | 图片资源 |
| screenshots/README.md | AI智能助手/screenshots | Markdown文档 |
| static/axios.min.js | AI智能助手/static | 其他文件 |
| static/clike.min.js | AI智能助手/static | 其他文件 |
| static/codemirror.min.css | AI智能助手/static | 其他文件 |
| static/codemirror.min.js | AI智能助手/static | 其他文件 |
| static/css.min.js | AI智能助手/static | 其他文件 |
| static/docx-preview.min.js | AI智能助手/static | 其他文件 |
| static/element-ui.min.css | AI智能助手/static | 其他文件 |
| static/element-ui.min.js | AI智能助手/static | 其他文件 |
| static/foldgutter.min.css | AI智能助手/static | 其他文件 |
| static/github.min.css | AI智能助手/static | 其他文件 |
| static/highlight.min.js | AI智能助手/static | 其他文件 |
| static/htmlmixed.min.js | AI智能助手/static | 其他文件 |
| static/javascript.min.js | AI智能助手/static | 其他文件 |
| static/python.min.js | AI智能助手/static | 其他文件 |
| static/sql.min.js | AI智能助手/static | 其他文件 |
| static/vue.min.js | AI智能助手/static | 其他文件 |
| static/xlsx.full.min.js | AI智能助手/static | 其他文件 |
| static/fonts/element-icons.ttf | AI智能助手/static/fonts | 其他文件 |
| static/fonts/element-icons.woff | AI智能助手/static/fonts | 其他文件 |
| tools/file_editor_config.py | AI智能助手/tools | 文件编辑工具配置项 |
| tools/file_editor_tool_desc.md | AI智能助手/tools | Markdown文档 |
| tools/intelligent_file_editor.py | AI智能助手/tools | 生产级文件编辑工具（标准工程化集成方案） |

## 三、项目所有文件功能明细（文件开发完成后自动更新）

### 📄 文件名：AI智能助手项目手册.md
- 所属模块：AI智能助手
- 功能描述：项目全量信息说明、规范定义、文件索引
- 实现状态：✅ 已实现

### 📄 文件名：.gitignore
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：ai_browser.py
- 所属模块：AI智能助手
- 功能描述：智能助手内置浏览器 V1.0（核心功能版）
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | DownloadManagerDialog | 类 | 暂无描述 |
  | CustomWebPage | 类 | 暂无描述 |
  | CustomWebView | 类 | 暂无描述 |
  | AIBrowserWindow | 类 | 主浏览器窗口 |
  | DownloadManagerDialog.add_task | 函数 | 新增下载任务到列表 |
  | DownloadManagerDialog.update_task_progress | 函数 | 更新任务进度 |
  | DownloadManagerDialog.mark_task_finished | 函数 | 标记任务完成（自动清理假死任务） |
  | DownloadManagerDialog.clear_single_task | 函数 | 清理单个任务 |
  | DownloadManagerDialog.clear_finished_tasks | 函数 | 清空已完成/失败的任务 |
  | CustomWebPage.acceptNavigationRequest | 函数 | 拦截工作台页面跳转，禁止替换工作台根页面，所有内部跳转强制新开标签 |
  | CustomWebView.contextMenuEvent | 函数 | 暂无描述 |
  | CustomWebView.createWindow | 函数 | 暂无描述 |
  | AIBrowserWindow.init_window | 函数 | 暂无描述 |
  | AIBrowserWindow.init_ui | 函数 | 暂无描述 |
  | AIBrowserWindow.load_config | 函数 | 加载配置:优先读取全局config.json，自动迁移旧的browser_config.json配置 |
  | AIBrowserWindow.save_config | 函数 | 保存配置:直接写入全局config.json，不再生成独立的browser_config.json |
  | AIBrowserWindow.set_default_download_path | 函数 | 设置默认下载路径，直接写入全局config.json |
  | AIBrowserWindow.update_download_path | 函数 | 对外提供的实时更新下载路径接口，供API层调用，无需重启立即生效 |
  | AIBrowserWindow.add_new_tab | 函数 | 新建标签页，page_id不为空时启用去重逻辑 |
  | AIBrowserWindow.open_page | 函数 | 对外提供的打开页面统一入口，完全符合要求的执行流程：调出浏览器→检查页面→存在则停止，不存在则打开 |
  | AIBrowserWindow.open_ai_workbench | 函数 | 暂无描述 |
  | AIBrowserWindow.close_tab | 函数 | 关闭标签页 |
  | AIBrowserWindow.current_tab_changed | 函数 | 当前标签页切换时更新地址栏 |
  | AIBrowserWindow.update_tab_title | 函数 | 更新标签页标题 |
  | AIBrowserWindow.update_address_bar | 函数 | 更新地址栏 |
  | AIBrowserWindow.load_address | 函数 | 加载地址栏输入的地址 |
  | AIBrowserWindow.go_back | 函数 | 后退 |
  | AIBrowserWindow.go_forward | 函数 | 前进 |
  | AIBrowserWindow.refresh_page | 函数 | 刷新 |
  | AIBrowserWindow.go_home | 函数 | 回到首页 |
  | AIBrowserWindow.open_new_tab | 函数 | 线程安全的新建标签页打开URL接口，自动运行在UI主线程 |
  | AIBrowserWindow.load_favorites | 函数 | 加载本地收藏夹 |
  | AIBrowserWindow.save_favorites | 函数 | 保存收藏夹到本地 |
  | AIBrowserWindow.refresh_favorites_menu | 函数 | 刷新收藏夹菜单 |
  | AIBrowserWindow.add_current_to_favorites | 函数 | 收藏当前页面 |
  | AIBrowserWindow.clear_favorites | 函数 | 清空收藏夹 |
  | AIBrowserWindow.delete_single_favorite | 函数 | 删除单个收藏 |
  | AIBrowserWindow.handle_download_request | 函数 | 处理所有下载请求（适配PySide6 6.7+ 最新版API，100%兼容所有场景） |
  | AIBrowserWindow.update_download_progress | 函数 | 实时更新下载进度（适配新版API，解决大文件卡0%问题） |
  | AIBrowserWindow.download_finished | 函数 | 下载完成处理 |
  | AIBrowserWindow.download_state_changed | 函数 | 下载状态变更处理（适配新版独立枚举） |
  | AIBrowserWindow.run_js_sync | 函数 | 同步执行JavaScript并返回结果（基于QEventLoop阻塞等待回调） |
  | AIBrowserWindow.get_page_html | 函数 | 获取当前页面的完整HTML源码 |
  | AIBrowserWindow.get_page_text | 函数 | 获取当前页面的纯文本内容 |
  | AIBrowserWindow.execute_action | 函数 | 统一执行操作接口，支持点击、输入、滚动等行为 |
- 实现状态：✅ 已实现

### 📄 文件名：AI_GZT.spec
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：AI_GZT_User_Guide.md
- 所属模块：AI智能助手
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：AI智能助手功能清单.md
- 所属模块：AI智能助手
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：AI智能助手项目完整报告.md
- 所属模块：AI智能助手
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：api_server.py
- 所属模块：AI智能助手
- 功能描述：API服务层 V1.0
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | ChatCompletionMessage | 类 | 暂无描述 |
  | ChatCompletionRequest | 类 | 暂无描述 |
  | ChatRequest | 类 | 暂无描述 |
  | TaskSubmitRequest | 类 | 暂无描述 |
  | ChatStopRequest | 类 | 暂无描述 |
  | FileWriteRequest | 类 | 暂无描述 |
  | FileCreateRequest | 类 | 暂无描述 |
  | FileDeleteRequest | 类 | 暂无描述 |
  | FileRenameRequest | 类 | 暂无描述 |
  | FileEditRequest | 类 | 暂无描述 |
  | ConfigSetRequest | 类 | 暂无描述 |
  | RepositoryPathSetRequest | 类 | 暂无描述 |
  | ForbiddenPathAddRequest | 类 | 暂无描述 |
  | ForbiddenPathDeleteRequest | 类 | 暂无描述 |
  | DownloadStartRequest | 类 | 暂无描述 |
  | DownloadCancelRequest | 类 | 暂无描述 |
  | BrowserOpenRequest | 类 | 暂无描述 |
  | MemoryConfigUpdateRequest | 类 | 暂无描述 |
  | MemoryLibraryClearRequest | 类 | 暂无描述 |
  | MemoryFileClearRequest | 类 | 暂无描述 |
  | PromptSaveRequest | 类 | 暂无描述 |
  | PromptResetRequest | 类 | 暂无描述 |
  | PluginInstallRequest | 类 | 暂无描述 |
  | PluginOperateRequest | 类 | 暂无描述 |
  | PluginConfigSaveRequest | 类 | 暂无描述 |
  | PluginActionRequest | 类 | 暂无描述 |
  | PluginGenerateRequest | 类 | 暂无描述 |
  | PluginPreviewRequest | 类 | 暂无描述 |
  | SwitchProjectRequest | 类 | 暂无描述 |
  | DeleteProjectRequest | 类 | 暂无描述 |
  | ProjectManualCreateRequest | 类 | 暂无描述 |
  | ProjectManualSyncRequest | 类 | 暂无描述 |
  | BackupRestoreRequest | 类 | 暂无描述 |
  | BackupDeleteRequest | 类 | 暂无描述 |
  | BackupCleanRequest | 类 | 暂无描述 |
  | ChineseToPinyinRequest | 类 | 暂无描述 |
  | SelectPathRequest | 类 | 暂无描述 |
  | get_default_repository_path | 函数 | 获取跨平台默认仓库路径:统一使用当前用户文档目录下的AI仓库文件夹（任何Windows/Mac/Linux均存在） |
  | get_project_history_file | 函数 | 获取当前项目对应的历史存储文件路径 |
  | load_config | 函数 | 暂无描述 |
  | save_config | 函数 | 暂无描述 |
  | init_repository_path | 函数 | 暂无描述 |
  | load_global_history | 函数 | 暂无描述 |
  | save_global_history | 函数 | 暂无描述 |
  | is_port_used | 函数 | 暂无描述 |
  | get_available_port | 函数 | 暂无描述 |
  | init_whitelist_paths | 函数 | 初始化全局白名单路径，配置更新时自动调用重新加载 |
  | is_path_forbidden | 函数 | 校验路径是否在禁止操作列表中 |
  | safe_escape_restore | 函数 | 暂无描述 |
  | push_sse_message | 函数 | 线程安全的SSE消息推送，支持在子线程中调用，解决TestClient跨事件循环无法唤醒主循环Queue的问题 |
  | broadcast_file_change | 函数 | 全局广播文件变动事件到所有前端连接，支持同步线程调用 |
  | build_simple_tree | 函数 | 生成极简纯树形目录结构，无冗余信息，自动过滤系统目录和隐藏文件，同时返回全量路径映射表 |
  | add_operation_log | 函数 | 新增操作日志，自动记录时间，按倒序存储 |
  | add_file_operation_log | 函数 | 统一文件操作日志格式，所有文件操作统一调用 |
  | update_current_project_file_list | 函数 | 更新当前项目的文件清单内存缓存，操作文件后自动调用，无需用户手动刷新 |
  | get_real_physical_path | 函数 | 将输入路径转换为标准化的真实物理绝对路径，兼容Windows/Mac/Linux |
  | get_relative_path | 函数 | 将绝对路径转换为相对于当前基准目录（当前项目根/仓库根）的相对路径，统一使用/作为分隔符，路径在基准目录外则直接返回绝对路径 |
  | load_upload_map | 函数 | 加载本地路径与公网URL映射表 |
  | save_upload_map | 函数 | 保存本地路径与公网URL映射表 |
  | upload_file_to_tos | 函数 | 上传本地文件到火山TOS对象存储，返回永久公网URL |
  | init_default_prompt_tpl | 函数 | 暂无描述 |
  | load_prompt_tpl | 函数 | 暂无描述 |
  | select_path_dialog | 函数 | 弹出系统原生文件/文件夹选择对话框，返回选中的绝对路径，取消则返回空字符串 |
  | start_api_server | 函数 | 子线程启动API服务，支持外部指定端口，未指定则默认8000 |
- 实现状态：✅ 已实现

### 📄 文件名：app_icon.ico
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：auto_sync_monitor.py
- 所属模块：AI智能助手
- 功能描述：双向自动同步监听模块
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | FileChangeHandler | 类 | 普通文件变动事件处理器：反向同步 → 文件变动更新对应项目手册 |
  | ManualChangeHandler | 类 | 项目手册变动事件处理器 |
  | get_repository_path | 函数 | 动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码 |
  | trigger_file_change_notify | 函数 | 暂无描述 |
  | start_monitor | 函数 | 启动双向监听服务 |
  | FileChangeHandler.on_any_event | 函数 | 统一处理所有文件变动事件 |
- 实现状态：✅ 已实现

### 📄 文件名：build.py
- 所属模块：AI智能助手
- 功能描述：AI智能助手 PyInstaller 打包脚本
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | find_inno_setup_compiler | 函数 | 自动识别Inno Setup编译器路径，兼容32/64位系统默认安装位置 |
- 实现状态：✅ 已实现

### 📄 文件名：chat_float.html
- 所属模块：AI智能助手
- 功能描述：AI悬浮助手
- 实现状态：✅ 已实现

### 📄 文件名：chat_ui.html
- 所属模块：AI智能助手
- 功能描述：AI智能体对话界面
- 实现状态：✅ 已实现

### 📄 文件名：config.example.json
- 所属模块：AI智能助手
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：config.json
- 所属模块：AI智能助手
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：convert_icon.py
- 所属模块：AI智能助手
- 功能描述：PNG转ICO超清圆形图标转换脚本
- 实现状态：✅ 已实现

### 📄 文件名：editor_empty_bg.png
- 所属模块：AI智能助手
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：file_editor.html
- 所属模块：AI智能助手
- 功能描述：文件预览
- 实现状态：✅ 已实现

### 📄 文件名：LICENSE
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：llm_client.py
- 所属模块：AI智能助手
- 功能描述：统一模型调用客户端
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | MockModel | 类 | 暂无描述 |
  | UnifiedLLM | 类 | 暂无描述 |
  | get_config | 函数 | 对外公开的配置读取接口，和内部逻辑完全一致，保证配置统一 |
  | image_to_base64 | 函数 | 通用图片转base64工具函数，支持自动压缩大图 |
  | chat | 函数 | 统一聊天调用接口，自动切换本地/云模型 |
  | init_llm | 函数 | 初始化全局LLM实例，必须在依赖路径注入完成后调用，避免提前导入依赖失败 |
  | MockModel.create_chat_completion | 函数 | 暂无描述 |
  | UnifiedLLM.create_chat_completion | 函数 | 完全兼容原有调用接口，纯云端模型调用，支持流式/非流式、配置热更新、自动重试 |
  | completions.create | 函数 | 暂无描述 |
- 实现状态：✅ 已实现

### 📄 文件名：logo.png
- 所属模块：AI智能助手
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：main.py
- 所属模块：AI智能助手
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | _CompatModuleFinder | 类 | 暂无描述 |
  | handle_exception | 函数 | 暂无描述 |
  | get_available_port | 函数 | 暂无描述 |
  | load_qt_modules | 函数 | 暂无描述 |
  | get_system_python_cmd | 函数 | 检测系统可用的Python命令，优先返回3.11版本，兼容多版本共存场景 |
  | inject_external_dependencies | 函数 | 打包环境下检测外部Python环境，版本匹配则注入外部site-packages到sys.path末尾 |
  | _CompatModuleFinder.find_spec | 函数 | 暂无描述 |
  | _CompatPdb.set_trace | 函数 | 暂无描述 |
  | _CompatPdb.reset | 函数 | 暂无描述 |
  | _CompatPdb.set_continue | 函数 | 暂无描述 |
  | _CompatPdb.set_quit | 函数 | 暂无描述 |
  | _CompatTestCase.setUp | 函数 | 暂无描述 |
  | _CompatTestCase.tearDown | 函数 | 暂无描述 |
  | _CompatTestCase.assertEqual | 函数 | 暂无描述 |
  | _CompatTestCase.assertTrue | 函数 | 暂无描述 |
  | _CompatTestCase.assertFalse | 函数 | 暂无描述 |
  | _CompatDocTestFinder.find | 函数 | 暂无描述 |
  | _CompatDocTestRunner.run | 函数 | 暂无描述 |
  | _CompatOptionParser.add_option | 函数 | 暂无描述 |
  | _CompatOptionParser.parse_args | 函数 | 暂无描述 |
  | _CompatOptionParser.error | 函数 | 暂无描述 |
  | FloatAPI.show_workbench | 函数 | 暂无描述 |
  | FloatAPI.open_url | 函数 | 暂无描述 |
  | CustomWebPage.createWindow | 函数 | 暂无描述 |
  | CustomWebPage.acceptNavigationRequest | 函数 | 暂无描述 |
- 实现状态：✅ 已实现

### 📄 文件名：memory_cache.py
- 所属模块：AI智能助手
- 功能描述：向量记忆库
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | MemoryCache | 类 | 暂无描述 |
  | MemoryCache.add_memory | 函数 | 新增记忆到缓存，支持绑定会话ID，自动加毫秒级时间戳 |
  | MemoryCache.get_session_history | 函数 | 获取指定会话的最近N轮历史，按时间倒序排列，彻底解决时间错位问题 |
  | MemoryCache.recall_memory | 函数 | 召回相关记忆：返回固定召回+向量召回两部分内容，互相独立不干扰 |
  | MemoryCache.get_ready_for_lora | 函数 | 获取符合写入LoRA条件的记忆（调用≥3次，未同步） |
  | MemoryCache.mark_synced | 函数 | 标记记忆已同步到LoRA，后续不再召回 |
  | MemoryCache.clear_project_memory | 函数 | 清空指定项目的所有记忆，project_name传"default"清空全局主记忆库，传项目名清空对应项目记忆 |
  | MemoryCache.build_full_vector_index | 函数 | 全量重建记忆向量索引，和当前meta中的记忆完全对齐，清除所有残留向量，同步重置ID为连续值避免错位 |
  | MemoryCache.load_config | 函数 | 加载记忆配置 |
  | MemoryCache.save_config | 函数 | 保存记忆配置 |
  | MemoryCache.load_tools | 函数 | 加载工具列表 |
  | MemoryCache.update_config | 函数 | 更新配置（供前端调用） |
  | MemoryCache.get_fixed_recall | 函数 | 获取固定召回内容（工具+预留位） |
  | MemoryCache.export_for_finetune | 函数 | 导出所有记忆为LoRA微调格式数据集 |
- 实现状态：✅ 已实现

### 📄 文件名：memory_config.json
- 所属模块：AI智能助手
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：project_manual_manager.py
- 所属模块：AI智能助手
- 功能描述：项目手册管理核心模块
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | ProjectManualManager | 类 | 暂无描述 |
  | get_repository_path | 函数 | 动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码 |
  | ProjectManualManager.generate_template | 函数 | 生成标准化项目手册模板 |
  | ProjectManualManager.extract_code_metadata | 函数 | 提取代码文件的元数据：类名、函数名、功能描述 |
  | ProjectManualManager.parse_file_overview_table | 函数 | 解析手册中的全项目文件明细清单表格 |
  | ProjectManualManager.update_manual_detail_table | 函数 | 反向同步：自动更新手册的全项目文件明细清单 |
- 实现状态：✅ 已实现

### 📄 文件名：prompt_templates.json
- 所属模块：AI智能助手
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：Python和依赖安装.bat
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：rag_manager.py
- 所属模块：AI智能助手
- 功能描述：添加文件到RAG库，自动提取项目归属标签
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | CodeRAGManager | 类 | 暂无描述 |
  | get_repository_path | 函数 | 动态获取当前配置的仓库路径，自动适配配置更新，避免硬编码，配置路径和其他模块完全对齐 |
  | CodeRAGManager.add_file | 函数 | 添加单个文件到RAG库，自动提取项目归属标签 |
  | CodeRAGManager.delete_file | 函数 | 删除单个文件的索引 |
  | CodeRAGManager.delete_project | 函数 | 删除指定项目的所有RAG索引 |
  | CodeRAGManager.build_full_index | 函数 | 全量扫描项目目录构建索引，返回统计结果（优化版:增量校验+多线程预处理+批量生成向量） |
  | CodeRAGManager.search | 函数 | 检索相关代码片段，支持按项目过滤 |
- 实现状态：✅ 已实现

### 📄 文件名：README.md
- 所属模块：AI智能助手
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：requirements.txt
- 所属模块：AI智能助手
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：sample.html
- 所属模块：AI智能助手
- 功能描述：记忆管理 - AI智能助手
- 实现状态：✅ 已实现

### 📄 文件名：scheduler_manager.py
- 所属模块：AI智能助手
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | SchedulerManager | 类 | 暂无描述 |
  | SchedulerManager.set_server_port | 函数 | 设置API服务端口，由api_server启动时动态注入，避免硬编码导致跨工作台误触发 |
  | SchedulerManager.start | 函数 | 启动调度器，恢复所有活跃任务 |
  | SchedulerManager.shutdown | 函数 | 关闭调度器 |
  | SchedulerManager.load_tasks | 函数 | 从JSON文件加载任务列表 |
  | SchedulerManager.save_tasks | 函数 | 保存任务列表到JSON文件 |
  | SchedulerManager.get_all_tasks | 函数 | 获取所有任务 |
  | SchedulerManager.get_task | 函数 | 获取单个任务 |
  | SchedulerManager.create_task | 函数 | 创建新任务 |
  | SchedulerManager.update_task | 函数 | 更新任务 |
  | SchedulerManager.cancel_task | 函数 | 取消任务 |
  | SchedulerManager.delete_task | 函数 | 删除任务 |
- 实现状态：✅ 已实现

### 📄 文件名：screenshot_tool.py
- 所属模块：AI智能助手
- 功能描述：全局系统级截图工具 V1.0（极简无依赖版）
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | ScreenshotTool | 类 | 暂无描述 |
  | ScreenshotTool.capture_selection | 函数 | 启动截图选框，返回选中区域的PIL Image对象，取消返回None |
  | ScreenshotTool.capture_selection_to_base64 | 函数 | 截图并返回base64编码 |
  | ScreenshotTool.capture_selection_to_file | 函数 | 截图并保存到文件 |
- 实现状态：✅ 已实现

### 📄 文件名：setup.iss
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：THIRD_PARTY_LICENSES.md
- 所属模块：AI智能助手
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：tool_template_manager.py
- 所属模块：AI智能助手
- 功能描述：AI助手指令固化模块
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | ToolTemplateManager | 类 | 暂无描述 |
  | ToolTemplateManager.load_plugins | 函数 | 扫描plugins目录加载所有已启用的插件 |
  | ToolTemplateManager.load_preset_templates | 函数 | 加载plugin_templates目录下所有预制MD模板，仅解析头部元数据，适配新[FILE]块模板体系，错误模板自动跳过不影响整体 |
  | ToolTemplateManager.get_preset_template_list | 函数 | 获取所有预制模板列表，前端插件开发页面直接调用展示 |
  | ToolTemplateManager.get_merged_tool_list | 函数 | 获取合并后的内置工具+已启用插件列表 |
  | ToolTemplateManager.get_plugin_config | 函数 | 获取插件配置信息 |
  | ToolTemplateManager.generate_command | 函数 | 生成工具指令，已取消所有白名单和参数校验，只要能解析就直接生成 |
  | ToolTemplateManager.validate_command | 函数 | 校验指令是否为合法的模板生成指令，取消工具白名单校验，只要结构合法就通过 |
  | ToolTemplateManager.generate_plugin_template | 函数 | 一键生成符合规范的插件完整结构，适配新[FILE]块模板体系，无任何旧逻辑兼容 |
- 实现状态：✅ 已实现

### 📄 文件名：web_about.html
- 所属模块：AI智能助手
- 功能描述：关于 - AI工作台
- 实现状态：✅ 已实现

### 📄 文件名：web_backup.html
- 所属模块：AI智能助手
- 功能描述：文件备份管理
- 实现状态：✅ 已实现

### 📄 文件名：web_file_repo.html
- 所属模块：AI智能助手
- 功能描述：文件仓库
- 实现状态：✅ 已实现

### 📄 文件名：web_log.html
- 所属模块：AI智能助手
- 功能描述：操作日志
- 实现状态：✅ 已实现

### 📄 文件名：web_plugin_market.html
- 所属模块：AI智能助手
- 功能描述：插件市场 - AI智能助手
- 实现状态：✅ 已实现

### 📄 文件名：web_scheduler.html
- 所属模块：AI智能助手
- 功能描述：定时任务管理 - AI智能助手
- 实现状态：✅ 已实现

### 📄 文件名：web_settings.html
- 所属模块：AI智能助手
- 功能描述：系统设置
- 实现状态：✅ 已实现

### 📄 文件名：web_workspace.html
- 所属模块：AI智能助手
- 功能描述：AI工作台
- 实现状态：✅ 已实现

### 📄 文件名：一键打包.bat
- 所属模块：AI智能助手
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：code_rag/code.index
- 所属模块：AI智能助手/code_rag
- 功能描述：其他文件
- 实现状态：⏳ 待开发

### 📄 文件名：gte-small-zh/.msc
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/.mv
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/config.json
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/configuration.json
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/README.md
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/requirements.txt
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/special_tokens_map.json
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/tokenizer.json
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/tokenizer_config.json
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/vocab.txt
- 所属模块：AI智能助手/gte-small-zh
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：gte-small-zh/resources/dual-encoder.png
- 所属模块：AI智能助手/gte-small-zh/resources
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：Languages/ChineseSimplified.isl
- 所属模块：AI智能助手/Languages
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：Languages/ChineseSimplified.isl.bak
- 所属模块：AI智能助手/Languages
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/channel_wecom/main.py
- 所属模块：AI智能助手/plugins/channel_wecom
- 功能描述：企业微信远程通道插件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | WeComChannelPlugin | 类 | 暂无描述 |
  | init_plugin | 函数 | 暂无描述 |
  | test_connection | 函数 | 模块级测试连接入口，主程序加载插件时自动注入plugin_config配置 |
  | run | 函数 | 模块级统一执行入口，主程序加载插件时自动注入plugin_config配置 |
  | WeComChannelPlugin.send_text_message | 函数 | 发送文本消息到企业微信，返回(是否成功, 错误信息) |
  | WeComChannelPlugin.upload_file | 函数 | 上传本地文件到企业微信，返回media_id |
  | WeComChannelPlugin.send_file_message | 函数 | 发送文件/图片消息 |
  | WeComChannelPlugin.test_connection | 函数 | 测试企业微信API连接是否正常 |
  | WeComChannelPlugin.get_channel_status | 函数 | 获取通道运行状态 |
  | WeComChannelPlugin.start | 函数 | 启动插件后台轮询 |
  | WeComChannelPlugin.stop | 函数 | 停止插件 |
  | WeComChannelPlugin.run | 函数 | 插件统一入口 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/channel_wecom/plugin.json
- 所属模块：AI智能助手/plugins/channel_wecom
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/channel_wecom/README.md
- 所属模块：AI智能助手/plugins/channel_wecom
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/channel_wecom/requirements.txt
- 所属模块：AI智能助手/plugins/channel_wecom
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/file_converter/main.py
- 所属模块：AI智能助手/plugins/file_converter
- 功能描述：文件格式转换插件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用 |
  | run | 函数 | 插件主入口 |
  | uninstall | 函数 | 插件卸载时调用 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/file_converter/plugin.json
- 所属模块：AI智能助手/plugins/file_converter
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/file_converter/README.md
- 所属模块：AI智能助手/plugins/file_converter
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/file_converter/requirements.txt
- 所属模块：AI智能助手/plugins/file_converter
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/image_generator/main.py
- 所属模块：AI智能助手/plugins/image_generator
- 功能描述：AI图片生成插件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用 |
  | run | 函数 | 插件主方法，生成图片入口 |
  | uninstall | 函数 | 插件卸载时自动调用，可选清理资源 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/image_generator/plugin.json
- 所属模块：AI智能助手/plugins/image_generator
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/image_generator/README.md
- 所属模块：AI智能助手/plugins/image_generator
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/image_generator/requirements.txt
- 所属模块：AI智能助手/plugins/image_generator
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/info_collector/main.py
- 所属模块：AI智能助手/plugins/info_collector
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用 |
  | search_baidu | 函数 | 百度搜索，获取结果列表 |
  | crawl_page_content | 函数 | 爬取单个网页正文内容（统一使用requests库，线程安全无崩溃） |
  | extract_entries | 函数 | 提取可操作入口 |
  | format_output | 函数 | 格式化输出内容 |
  | save_to_file | 函数 | 保存到本地文件 |
  | run | 函数 | 插件主入口，按action参数分发到6种原子操作模式 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/info_collector/plugin.json
- 所属模块：AI智能助手/plugins/info_collector
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/info_collector/README.md
- 所属模块：AI智能助手/plugins/info_collector
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/info_collector/requirements.txt
- 所属模块：AI智能助手/plugins/info_collector
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/process_monitor/main.py
- 所属模块：AI智能助手/plugins/process_monitor
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | SystemGuard | 类 | 系统保护名单（硬编码，不可修改，防止误杀系统关键进程） |
  | ProcessMonitor | 类 | 进程监控主引擎 |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用，支持自动启动配置 |
  | run | 函数 | 插件主方法，支持多种操作指令，兼容自然语言query解析 |
  | uninstall | 函数 | 插件卸载时自动调用 |
  | SystemGuard.is_protected | 函数 | 检查进程是否在系统保护名单中 |
  | ProcessMonitor.set_server_port | 函数 | 设置API服务端口，由api_server启动时动态注入 |
  | ProcessMonitor.scan_once | 函数 | 执行一次进程扫描，支持双模式 |
  | ProcessMonitor.start | 函数 | 启动监控线程，启动成功后自动同步配置开关为开启状态 |
  | ProcessMonitor.stop | 函数 | 停止监控线程，停止后自动同步配置开关为关闭状态 |
  | ProcessMonitor.confirm_allow_process | 函数 | 用户确认允许进程运行，自动加入白名单，取消倒计时 |
  | ProcessMonitor.confirm_terminate_process | 函数 | 用户确认立即终止进程 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/process_monitor/plugin.json
- 所属模块：AI智能助手/plugins/process_monitor
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/process_monitor/README.md
- 所属模块：AI智能助手/plugins/process_monitor
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/process_monitor/requirements.txt
- 所属模块：AI智能助手/plugins/process_monitor
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/rag_enhance/main.py
- 所属模块：AI智能助手/plugins/rag_enhance
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | RAGEnhancePlugin | 类 | 暂无描述 |
  | run | 函数 | 插件统一入口，兼容两种调用方式: |
  | RAGEnhancePlugin.on_load | 函数 | 插件完全加载完成后由主程序调用，执行后台任务初始化，避免导入阶段启动线程被中断 |
  | RAGEnhancePlugin.scan_directory | 函数 | 扫描指定目录，全量同步文件名索引缓存，自动清理已删除文件的无效记录 |
  | RAGEnhancePlugin.search_files | 函数 | 按文件名搜索文件 |
  | RAGEnhancePlugin.read_file_content | 函数 | 读取任意支持格式的文件内容，自动适配格式解析 |
  | RAGEnhancePlugin.should_auto_save | 函数 | 判断内容是否需要自动存入知识库 |
  | RAGEnhancePlugin.save_note | 函数 | 保存Markdown笔记到知识库，自动加入RAG索引 |
  | RAGEnhancePlugin.search_notes | 函数 | 搜索知识库中的Markdown笔记 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/rag_enhance/plugin.json
- 所属模块：AI智能助手/plugins/rag_enhance
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/safe_file_editor/main.py
- 所属模块：AI智能助手/plugins/safe_file_editor
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | SafeFileEditorPlugin | 类 | 安全文件编辑插件主类，仅做参数名映射，核心编辑逻辑完全复用现有成熟能力 |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用 |
  | run | 函数 | 插件主方法，接收插件独立参数，执行安全编辑 |
  | uninstall | 函数 | 插件卸载时自动调用 |
  | SafeFileEditorPlugin.execute_edit | 函数 | 执行安全编辑，核心逻辑:将插件独立参数映射为原生编辑器参数，完全走独立参数通道，100%避免截断 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/safe_file_editor/plugin.json
- 所属模块：AI智能助手/plugins/safe_file_editor
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/shipin_shengcheng/main.py
- 所属模块：AI智能助手/plugins/shipin_shengcheng
- 功能描述：其他文件
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | upload_local_file_to_public_url | 函数 | 自动上传本地文件到公网并返回URL |
  | init | 函数 | 插件初始化方法，安装/启用/配置修改时自动调用 |
  | run | 函数 | 插件入口方法，接收LLM传入的参数，返回执行结果 |
- 实现状态：✅ 已实现

### 📄 文件名：plugins/shipin_shengcheng/plugin.json
- 所属模块：AI智能助手/plugins/shipin_shengcheng
- 功能描述：配置文件
- 实现状态：✅ 已实现

### 📄 文件名：plugins/shipin_shengcheng/README.md
- 所属模块：AI智能助手/plugins/shipin_shengcheng
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugins/shipin_shengcheng/requirements.txt
- 所属模块：AI智能助手/plugins/shipin_shengcheng
- 功能描述：文本文件
- 实现状态：✅ 已实现

### 📄 文件名：plugin_templates/template_aigc_generate_AIGC生成类插件模板.md
- 所属模块：AI智能助手/plugin_templates
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugin_templates/template_info_collect_信息采集查询类插件模板.md
- 所属模块：AI智能助手/plugin_templates
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：plugin_templates/template_local_operation_本地操作类插件模板.md
- 所属模块：AI智能助手/plugin_templates
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/01-smartscreen.png
- 所属模块：AI智能助手/screenshots
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/01b-smartscreen-expanded.png
- 所属模块：AI智能助手/screenshots
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/02-uac-unknown.png
- 所属模块：AI智能助手/screenshots
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/03-license.png
- 所属模块：AI智能助手/screenshots
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/04-install-dir.png
- 所属模块：AI智能助手/screenshots
- 功能描述：图片资源
- 实现状态：✅ 已实现

### 📄 文件名：screenshots/README.md
- 所属模块：AI智能助手/screenshots
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：static/axios.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/clike.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/codemirror.min.css
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/codemirror.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/css.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/docx-preview.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/element-ui.min.css
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/element-ui.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/foldgutter.min.css
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/github.min.css
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/highlight.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/htmlmixed.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/javascript.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/python.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/sql.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/vue.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/xlsx.full.min.js
- 所属模块：AI智能助手/static
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/fonts/element-icons.ttf
- 所属模块：AI智能助手/static/fonts
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：static/fonts/element-icons.woff
- 所属模块：AI智能助手/static/fonts
- 功能描述：其他文件
- 实现状态：✅ 已实现

### 📄 文件名：tools/file_editor_config.py
- 所属模块：AI智能助手/tools
- 功能描述：文件编辑工具配置项
- 实现状态：✅ 已实现

### 📄 文件名：tools/file_editor_tool_desc.md
- 所属模块：AI智能助手/tools
- 功能描述：Markdown文档
- 实现状态：✅ 已实现

### 📄 文件名：tools/intelligent_file_editor.py
- 所属模块：AI智能助手/tools
- 功能描述：生产级文件编辑工具（标准工程化集成方案）
- 包含类&核心函数列表：
  | 名称 | 类型 | 功能描述 |
  | --- | --- | --- |
  | ContentMatcher | 类 | 纯内容匹配核心类（工业级优化版，和稳定版完全一致） |
  | IntelligentFileEditor | 类 | 生产级文件编辑器，可直接作为智能体工具调用 |
  | ContentMatcher.normalize_text | 函数 | 将文本转换为统一的视觉标准格式，消除无关格式差异 |
  | ContentMatcher.find_similar_block | 函数 | 在原始文件内容中查找与目标块视觉相似的内容块 |
  | IntelligentFileEditor.backup_single_file | 函数 | 公开方法:备份单个文件，供外部全量备份等接口调用 |
  | IntelligentFileEditor.get_backup_list | 函数 | 获取所有备份文件列表 |
  | IntelligentFileEditor.restore_backup | 函数 | 恢复指定备份文件 |
  | IntelligentFileEditor.delete_backup | 函数 | 删除指定备份文件 |
  | IntelligentFileEditor.clean_expired_backup | 函数 | 清理过期备份文件，返回删除数量 |
  | IntelligentFileEditor.edit_file | 函数 | 编辑文件主入口，支持4种操作类型 |
- 实现状态：✅ 已实现


## 四、功能开发计划
| 步骤 | 功能内容 | 预估耗时 | 状态 |
| --- | --- | --- | --- |
| 1 | 开源合规准备:全项目敏感信息扫描（API密钥/硬编码路径/个人信息/私钥） | 已完成 | ✅ 完成 |
| 2 | 创建 Apache-2.0 LICENSE 许可证文件 | 已完成 | ✅ 完成 |
| 3 | 创建 README.md（含许可证声明、权限风险声明、第三方服务说明） | 已完成 | ✅ 完成 |
| 4 | 开源路径清理:新建.gitignore与config.example.json模板；6个代码文件9处硬编码D:/AI路径全部中性化为~/Documents动态路径（py_compile校验通过、残留为零） | 已完成 | ✅ 完成 |
| 5 | 开源方案A执行:删除keygen.py/auth_manager.py/activation_dialog.py共3个激活模块文件；清理main.py启动激活校验块与channel_wecom死导入（py_compile通过、全项目零残留引用）；4份文档同步（用户指南改"首次启动说明"、功能清单/完整报告移除激活条目、README新增SmartScreen跳过教程与赞助版说明） | 已完成 | ✅ 完成 |
| 6 | 一键打包工具:新建「一键打包.bat」，双击自动完成 Python3.11检测 → 创建/复用.venv虚拟环境 → 清华源安装requirements.txt依赖（已装秒过）→ 虚拟环境内执行build.py打包（PyInstaller绿色版+Inno Setup安装包自动编译）→ 报告产物路径，每步失败均有中文提示并暂停；.gitignore同步新增.venv/venv/env虚拟环境排除项（约3.5G不进git）；零侵入不改动build.py/setup.iss现有逻辑 | 已完成 | ✅ 完成 |
| 7 | 安装包汉化补全+README配图框架:①Languages/ChineseSimplified.isl新增许可协议页/选择目标位置页/附加任务页共16个缺失汉化键（含Inno Setup 6 modern向导样式专用Label3键），取消注释96个现成中文条目（浏览对话框/Ready页摘要/目录校验/卸载确认/常见错误等），修复安装向导半中半英问题；②README的SmartScreen章节由3步改为4步图文教程（SmartScreen蓝窗→UAC黄窗→许可协议页→选择安装位置页），嵌入4张截图引用；③新建screenshots/目录及截图说明文件（命名规范、拍摄要点、Zone.Identifier本地触发蓝窗方法）；零代码改动，重新打包即生效 | 已完成 | ✅ 完成（截图待重拍放入） |
| 8 | 汉化语言文件彻底重建:任务7补丁实测仅部分生效（向导粗标题/许可单选框仍英文、磁盘空间行%1未替换成数字），根因是旧isl基于Inno Setup 5键名、与本机IS6.3+官方Default.isl的281个Messages键不匹配（旧键LicenseAcceptedRadio/SelectDirLabel等已废弃，新键为WizardLicense/LicenseAccepted/WizardSelectDir/SelectDirDesc，占位符由%1改为[mb]/[gb]）；以官方Default.isl键序为骨架重建ChineseSimplified.isl:236条内置标准译法+37条沿用现有中文+8条英文兜底，键名100%对齐官方，覆盖许可/目录/任务/就绪/安装/卸载/错误/文件冲突全流程；原文件自动备份为ChineseSimplified.isl.bak；零代码改动，重新打包即全中文 | 已完成 | ✅ 完成（待重新打包实测） |
| 9 | 向导标题栏占位符修复:任务8重建isl时误将SetupWindowTitle译为"安装 - [name/ver]"，该键与官方Default.isl一致仅支持%1参数替换、不解析[name/ver]常量，导致向导所有页面标题栏字面量显示"安装 - [name/ver]"（正文[name]替换正常）；对照官方Default.isl改回"安装 - %1"（运行时替换为"AI智能助手 1.0"），WelcomeLabel2的[name/ver]属官方原生写法（该键支持常量展开）保持不动；用户5张实测截图验收通过:SmartScreen蓝窗/UAC黄窗/许可页/目录页全中文、磁盘空间"至少需要601.5MB"数字正常（%1 bug已消除）；零代码改动；2026-09-07 18:19已重新打包（dist/AI_GZT_Setup_v1.0.exe，198.9MB，晚于汉化文件17:50），标题栏修复已进包 | 已完成 | ✅ 完成 |
| 10 | 安装教程截图归档:用户5张实拍截图源文件定位于工作台上传文件夹（_internal/上传文件夹/截图_17887733*.png），按时间序复制到screenshots/并规范命名:01-smartscreen.png（蓝窗初始态73KB）、01b-smartscreen-expanded.png（蓝窗展开态86KB，备用留档README未引用）、02-uac-unknown.png（UAC黄窗55KB）、03-license.png（许可页152KB）、04-install-dir.png（目录页147KB），README引用的4张图文件名100%匹配、大小与源一致；screenshots/README.md说明文件同步重写为现状清单（03/04拍摄于任务9标题栏修复前、标题栏带[name/ver]字面量，经用户确认直接使用不重拍，页面正文全中文不影响教程；18:19重打包后如想获得完美标题栏截图，可重拍03/04覆盖同名文件、无需改任何引用）；过程中处置两次文件写入异常（edit_file混入</parameter>协议标签残留、PowerShell -NoNewline导致30行被拼成1行），最终删除重建并校验行数/首尾/无标签残留全部正常 | 已完成 | ✅ 完成 |

## 五、风险评估与应对
| 风险点 | 影响等级 | 应对方案 | 状态 |
| --- | --- | --- | --- |

## 六、版本迭代记录
| 版本号 | 发布时间 | 更新内容 | 负责人 |
| --- | --- | --- | --- |
| V1.0 | 2026-09-07 10:46:24 | 项目初始化 | |
