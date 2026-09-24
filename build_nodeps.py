# -*- coding: utf-8 -*-
"""
AI智能助手 PyInstaller 打包脚本（全外置依赖版 / NoDeps）
功能:将整个工作台打包为可一键安装的程序；所有第三方依赖全部外置，用户需先自行安装依赖
使用方法:直接运行 python build_nodeps.py

【孪生文件声明】
本脚本由 build.py 复制而来，公共逻辑需与 build.py 保持同步。
后续若升级 Python 版本 / 修改依赖清单 / 调整 Inno 探测路径，请同步修改 build.py 与本文件。
"""

import os
import sys
import dis

# === Python dis.py Bug 兼容补丁 ===
# Python 3.10.0 的 dis._get_const_info 在解析某些复杂字节码时会抛出 IndexError，
# 导致 PyInstaller 依赖分析阶段崩溃。此补丁在发生越界时返回安全占位值，绕过该 Bug。
# 注意:不同 Python 版本的 _get_const_info 函数签名不同:
#   - Python 3.10: _get_const_info(const_index, const_list) - 2个参数
#   - Python 3.11+: _get_const_info(deop, arg, co_consts) - 3个参数
# 使用 *args 兼容不同版本，仅在发生 IndexError 时返回安全占位值。
_orig_get_const_info = dis._get_const_info
def _safe_get_const_info(*args):
    try:
        return _orig_get_const_info(*args)
    except IndexError:
        return None, ''
dis._get_const_info = _safe_get_const_info
# === 补丁结束 ===

import PyInstaller.__main__

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 定义要打包的单文件数据
data_files = [
    'chat_float.html', 'chat_ui.html', 'file_editor.html', 'sample.html',
    'web_backup.html', 'web_file_repo.html', 'web_log.html', 'web_plugin_market.html',
    'web_scheduler.html', 'web_settings.html', 'web_workspace.html', 'web_about.html',
    'config.example.json', 'memory_config.json', 'prompt_templates.json', 'requirements.txt',
    'logo.png', 'app_icon.ico', 'editor_empty_bg.png',
    'AI_GZT_User_Guide.md', 'THIRD_PARTY_LICENSES.md'
]

# 定义要打包的目录数据
data_dirs = [
    'static', 'plugins', 'plugin_templates', 'tools', 'gte-small-zh'
]

# 定义隐藏导入（项目本地模块 + 被exclude的第三方库依赖的标准库模块，不依赖PyInstaller自动扫描）
hidden_imports = [
    # 项目本地模块，确保所有本地代码被正确打包
    'memory_cache', 'rag_manager', 'api_server', 'llm_client',
    'tool_template_manager', 'auto_sync_monitor', 'ai_browser',
    'screenshot_tool', 'project_manual_manager', 'scheduler_manager',
    'file_filter_config',   # 文件扫描噪音过滤统一配置模块
    'command_runner',       # 长命令后台任务机制P0:进程树命令执行器
    'background_task_manager',  # 长命令后台任务机制P1:后台任务管理器
    'ast_symbol_index',     # 符号定位器
    # === FastAPI/Starlette/Web服务依赖的标准库模块（因第三方库被exclude，静态分析无法识别，强制收集） ===
    'http', 'http.cookies', 'http.client', 'http.server',
    'email', 'email.mime', 'email.mime.multipart', 'email.mime.text',
    'mimetypes', 'html', 'html.parser',
    'urllib', 'urllib.parse', 'urllib.request',
    'colorsys',
    'logging.config',
    'pypinyin'
]

# 构建命令参数
cmd = [
    'main.py',
    '--name=AI_GZT_NoDeps',
    '--noconfirm',          # 覆盖输出目录
    '--clean',              # 清理临时文件
    '--console',            # 显示控制台窗口（方便查看日志）
    '--icon=app_icon.ico',  # 自定义程序图标
]

# 添加单文件数据
for f in data_files:
    # Windows 使用 ; 作为分隔符，Linux/Mac 使用 :
    sep = ';' if sys.platform == 'win32' else ':'
    cmd.append(f'--add-data={f}{sep}.')

# 添加目录数据
for d in data_dirs:
    sep = ';' if sys.platform == 'win32' else ':'
    cmd.append(f'--add-data={d}{sep}{d}')

# 添加隐藏导入
for mod in hidden_imports:
    cmd.append(f'--hidden-import={mod}')

# 添加排除模块
# 【全外置版核心策略】除 Python 标准库外，所有第三方库一律排除，不打包进产物。
# 用户运行前必须先执行「Python和依赖安装.bat」安装全部依赖；缺失依赖时
# main.py 会打印明确指引（版本软提示 + 缺依赖兜底），不会静默闪退。
excludes = [
    # 非核心调试类标准库（不需要打包，运行时自动加载系统版本）
    'unittest', 'doctest', 'pdb', 'profile', 'pstats',
    # === 非核心可选第三方依赖排除，不内置 ===
    # Web服务相关子模块
    'uvicorn', 'uvicorn.logging', 'uvicorn.protocols', 'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off',
    'fastapi', 'fastapi.middleware', 'fastapi.middleware.cors',
    'fastapi.staticfiles', 'fastapi.responses',
    'sse_starlette', 'sse_starlette.sse',
    'pydantic', 'pydantic_core', 'pydantic._internal', 'pydantic.deprecated', 'pydantic.networks', 'pydantic.types', 'pydantic.fields',
    'multipart', 'multipart.multipart',
    # 向量检索/AI相关
    'torch', 'torchvision', 'torchaudio', 'tensorboard', 'torch.distributed',
    'sentence_transformers', 'transformers', 'tensorflow', 'keras',
    'scipy', 'sklearn', 'scikit-learn', 'sentencepiece', 'safetensors',
    'faiss', 'faiss._swigfaiss', 'tokenizers', 'huggingface_hub', 'nltk', 'datasets',
    # === 【全外置版专属】真外置清单:以下库一律不打包，全部由用户机 site-packages 提供 ===
    # GUI 框架（内置浏览器/悬浮窗）
    'PySide6', 'shiboken6',
    # 数值/图像/文本处理
    'numpy', 'PIL', 'lxml', 'psutil', 'yaml',
    # 网络请求链路
    'certifi', 'charset_normalizer', 'idna', 'urllib3', 'requests',
    # OpenAI 及各传输层依赖
    'openai', 'httpx', 'httpcore', 'h11', 'anyio', 'sniffio',
    'distro', 'tqdm', 'annotated_types', 'typing_extensions', 'jiter',
    # Web 服务剩余件
    'starlette', 'click',
    # 资讯采集/定时任务/截图/拼音等可选功能依赖
    'newspaper3k', 'bs4', 'tldextract',
    'watchdog', 'apscheduler', 'pytz', 'tzlocal',
    'mss', 'screeninfo', 'pypinyin',
    'volcengine', 'tos',
]

for mod in excludes:
    cmd.append(f'--exclude-module={mod}')

print("🚀 开始执行打包（全外置依赖版），可能需要几分钟时间，请耐心等待...")
print(f"📦 执行命令: PyInstaller {' '.join(cmd)}")

# 执行打包
PyInstaller.__main__.run(cmd)
# === 全外置版说明 ===
# builtin_third_party_libs 置空，跳过"手动复制第三方库"环节。与 build.py 的差异点就在此:
# build.py 会把核心启动库复制进 _internal，本脚本一律不复制，所有依赖全部由用户机 site-packages
# 提供（通过 main.py 的外部依赖注入加载）。
import shutil
import site

# 获取当前Python环境的site-packages目录路径（兼容虚拟环境，优先定位存在目标库的路径，解决虚拟环境下路径识别错误问题）
site_packages_path = None
# 第一步:遍历site.getsitepackages()返回的所有路径，优先找存在openai目录的有效路径
for path in site.getsitepackages():
    if os.path.exists(os.path.join(path, 'openai')):
        site_packages_path = path
        break
# 第二步:如果没找到，尝试用sys.prefix拼接虚拟环境默认site-packages路径（适配部分特殊虚拟环境配置）
if not site_packages_path:
    if sys.platform == 'win32':
        candidate = os.path.join(sys.prefix, 'Lib', 'site-packages')
    else:
        candidate = os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages')
    if os.path.exists(os.path.join(candidate, 'openai')):
        site_packages_path = candidate
# 第三步:兜底使用第一个路径，兼容极端环境
if not site_packages_path:
    site_packages_path = site.getsitepackages()[0]

# === 打包前环境强制校验:必须在安装了完整requirements.txt依赖的虚拟环境中执行 ===
def _lib_exists(lib_name, site_path):
    """检查第三方库是否存在，兼容目录包、单文件.py/.pyd/.so模块形式"""
    if os.path.isdir(os.path.join(site_path, lib_name)):
        return True
    for ext in ['.py', '.pyd', '.so']:
        if os.path.isfile(os.path.join(site_path, f"{lib_name}{ext}")):
            return True
    return False

required_core_libs = ['numpy', 'fastapi', 'pydantic', 'pydantic_core', 'jiter', 'typing_extensions', 'uvicorn', 'openai']
missing_libs = [lib for lib in required_core_libs if not _lib_exists(lib, site_packages_path)]
if missing_libs:
    print(f"❌ 打包环境错误:当前Python环境缺失核心依赖 {missing_libs}")
    print("💡 请先激活安装了requirements.txt所有依赖的项目虚拟环境，再执行build_nodeps.py打包脚本！")
    sys.exit(1)
print(f"✅ 打包环境校验通过:{site_packages_path}")

# 需要内置的第三方库列表（全外置版:置空，不复制任何库）
builtin_third_party_libs = []
# PyInstaller单目录模式下的内置库存放路径
target_lib_dir = os.path.join(BASE_DIR, 'dist', 'AI_GZT_NoDeps', '_internal')

# === 补建 data_dirs 中的空目录（PyInstaller 的 --add-data 按目录内文件递归收集，空目录不会生成目标目录，此处统一兜底补建，确保产物结构完整） ===
for d in data_dirs:
    empty_dir_dst = os.path.join(target_lib_dir, d)
    if not os.path.exists(empty_dir_dst):
        os.makedirs(empty_dir_dst, exist_ok=True)
        print(f"✅ 补建空目录 [{d}] -> {empty_dir_dst}（PyInstaller 按文件收集，空目录不会自动生成）")

# 全外置版:builtin_third_party_libs 为空，下方循环不会复制任何库，保留结构以便与 build.py 对照
for lib_name in builtin_third_party_libs:
    import glob
    dist_info_dirs = glob.glob(os.path.join(site_packages_path, f"{lib_name}-*.dist-info"))
    src_lib_path = None
    is_dir = False
    src_dir_path = os.path.join(site_packages_path, lib_name)
    if os.path.isdir(src_dir_path):
        src_lib_path = src_dir_path
        is_dir = True
    else:
        for ext in ['.py', '.pyd', '.so']:
            src_file_path = os.path.join(site_packages_path, f"{lib_name}{ext}")
            if os.path.isfile(src_file_path):
                src_lib_path = src_file_path
                is_dir = False
                break
    if src_lib_path:
        dst_lib_path = os.path.join(target_lib_dir, lib_name)
        if os.path.exists(dst_lib_path):
            if os.path.isdir(dst_lib_path):
                shutil.rmtree(dst_lib_path)
            else:
                os.remove(dst_lib_path)
        if is_dir:
            shutil.copytree(src_lib_path, dst_lib_path)
        else:
            shutil.copy2(src_lib_path, dst_lib_path)
        for dist_info_src in dist_info_dirs:
            dist_info_name = os.path.basename(dist_info_src)
            dist_info_dst = os.path.join(target_lib_dir, dist_info_name)
            if os.path.exists(dist_info_dst):
                shutil.rmtree(dist_info_dst)
            shutil.copytree(dist_info_src, dist_info_dst)
        print(f"✅ 内置第三方库 [{lib_name}] 复制完成（含版本元数据）")
    else:
        print(f"⚠️  当前Python环境未检测到 [{lib_name}] 库，跳过内置复制，将走外部系统路径加载")

# === 手动将说明文档复制到exe同级目录，兼容DOCS_DIR优先查找逻辑，避免文档在_internal目录找不到 ===
docs_output_dir = os.path.join(BASE_DIR, 'dist', 'AI_GZT_NoDeps')
for doc_file in ['AI_GZT_User_Guide.md', 'THIRD_PARTY_LICENSES.md']:
    src_doc = os.path.join(target_lib_dir, doc_file)
    dst_doc = os.path.join(docs_output_dir, doc_file)
    if os.path.exists(src_doc):
        shutil.copy2(src_doc, dst_doc)
        print(f"✅ 说明文档 [{doc_file}] 已复制到exe同级目录")
    else:
        print(f"⚠️  未找到源文档 [{doc_file}]，跳过复制")

# === 自动编译Inno Setup安装包（使用独立的外置版脚本 setup_external.iss） ===
import subprocess

def find_inno_setup_compiler():
    """自动识别Inno Setup编译器路径，兼容32/64位系统默认安装位置"""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

iscc_path = find_inno_setup_compiler()
if iscc_path:
    print("\n🔨 检测到Inno Setup，开始编译安装向导...")
    setup_script = os.path.join(BASE_DIR, "setup_external.iss")
    result = subprocess.run([iscc_path, setup_script], cwd=BASE_DIR)
    if result.returncode == 0:
        installer_path = os.path.join(BASE_DIR, "dist", "AI_GZT_NoDeps_Setup_v1.1.exe")
        print(f"✅ 安装包编译成功: {installer_path}")
    else:
        print("⚠️  安装包编译失败，请检查setup_external.iss脚本或Inno Setup安装是否正常")
else:
    print("\nℹ️  未检测到 Inno Setup 6，跳过安装包编译，绿色版已生成")
    print("💡 如需生成标准安装向导，请安装 Inno Setup 6 后重新运行打包脚本: https://jrsoftware.org/isdl.php")
print("\n✅ 打包全部完成（全外置依赖版）！")
print(f"📁 可执行文件位于: {os.path.join(BASE_DIR, 'dist', 'AI_GZT_NoDeps', 'AI_GZT_NoDeps.exe')}")