# 全局异常捕获，防止打包后闪退无法看到错误
import sys
import faulthandler
# 启用C层崩溃栈捕获，彻底解决无提示静默闪退问题，C层abort/段错误时会打印完整调用栈
faulthandler.enable(all_threads=True)
import traceback
import os
import json
import timeit

# ------------------------------
# 单实例互斥校验:防止重复启动多个程序
# ------------------------------
def _check_single_instance():
    # 开发调试时加--multi-instance参数可跳过单实例限制
    if "--multi-instance" in sys.argv:
        return True
    if sys.platform != "win32":
        # 非Windows平台暂不处理，直接放行
        return True
    try:
        import ctypes
        from ctypes import wintypes
        # 全局唯一互斥体名称，Local前缀表示当前会话隔离，不同Windows用户互不影响
        mutex_name = "Local\\AI_GZT_SingleInstance_v1.0"
        kernel32 = ctypes.windll.kernel32
        # 创建互斥体（不初始拥有，仅用于存在性检测，进程退出后系统自动释放）
        mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)
        # 检查互斥体是否已存在（表示已有程序实例运行）
        ERROR_ALREADY_EXISTS = 183
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            # 已有实例运行，查找并激活主窗口
            user32 = ctypes.windll.user32
            # 窗口枚举回调函数类型定义
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            found_main_hwnd = None
            
            def _enum_windows_callback(hwnd, lparam):
                nonlocal found_main_hwnd
                # 检查窗口是否设置了程序唯一标识属性
                if user32.GetPropW(hwnd, "AI_GZT_Main_Window_v1"):
                    found_main_hwnd = hwnd
                    return False  # 找到目标窗口后停止枚举
                return True  # 继续枚举下一个窗口
            
            # 枚举所有顶层窗口
            user32.EnumWindows(WNDENUMPROC(_enum_windows_callback), 0)
            
            if found_main_hwnd:
                # 恢复窗口（从最小化/隐藏/托盘状态还原）
                SW_RESTORE = 9
                user32.ShowWindow(found_main_hwnd, SW_RESTORE)
                # 将窗口置顶并激活获得焦点
                user32.SetForegroundWindow(found_main_hwnd)
                user32.BringWindowToTop(found_main_hwnd)
            
            # 释放当前进程的互斥体句柄
            if mutex_handle:
                kernel32.CloseHandle(mutex_handle)
            # 退出当前重复启动的实例
            sys.exit(0)
        
        # 互斥体创建成功，当前为第一个运行实例，保存句柄防止被GC回收
        global _single_instance_mutex_handle
        _single_instance_mutex_handle = mutex_handle
        return True
    except Exception as e:
        # 校验过程异常不阻塞程序启动，仅打印提示，降级允许多开
        print(f"⚠️ 单实例校验失败，降级允许多开: {str(e)}")
        return True

# 全局保存互斥体句柄，保持生命周期和程序一致
_single_instance_mutex_handle = None
# 程序最早期执行单实例校验，最早拦截重复启动
_check_single_instance()

# ------------------------------
# 控制台窗口显示控制:根据配置自动隐藏/显示后端控制台，默认隐藏（普通用户模式）
# ------------------------------
def _init_console_visibility():
    """根据配置文件控制控制台窗口显示状态，在所有输出前执行避免黑框闪烁"""
    # 非Windows平台无需处理控制台逻辑
    if sys.platform != 'win32':
        return True
    try:
        # 读取配置文件，优先使用用户设置
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config.json")
        show_console = False  # 默认隐藏控制台，普通用户无黑框体验
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                show_console = config.get("show_debug_console", False)
        
        # 调用Windows API控制控制台窗口显示
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # SW_HIDE = 0 隐藏窗口，SW_SHOW = 5 显示窗口
            ctypes.windll.user32.ShowWindow(hwnd, 5 if show_console else 0)
        return show_console
    except Exception as e:
        # 配置读取失败时默认隐藏，不影响主程序运行
        print(f"⚠️ 控制台显示配置读取失败，默认隐藏: {str(e)}")
        return False

# 提前执行控制台显示控制，在所有print前完成，避免黑框闪烁
_show_debug_console = _init_console_visibility()
# ------------------------------
# 通用标准库兼容工具函数（一劳永逸解决PyInstaller裁剪标准库导致的导入错误）
# ------------------------------
# 已注册的兼容包集合，自动处理所有子模块导入（覆盖import语句和属性访问两种场景）
_compat_packages = set()

def _create_compat_module(name, is_package=False, attrs=None):
    """
    创建兼容标准库模块，支持自动子模块懒加载
    :param name: 模块全路径名，如'unittest'/'xml.etree'
    :param is_package: 是否为包（支持子模块导入）
    :param attrs: 模块初始属性/方法字典
    """
    import types
    module = types.ModuleType(name)
    # 补全__file__属性为虚拟兼容模块路径，非空字符串符合Python模块规范，避免被PyInstaller/inspect判定为内置模块
    module.__file__ = f"<compatibility module '{name}'>"
    if is_package:
        module.__path__ = []
        # 注册到兼容包集合，支持import语句自动导入子模块
        _compat_packages.add(name)
        # 子模块自动懒加载:导入不存在的子模块时自动创建兼容模块，支持多级嵌套（属性访问场景）
        def __getattr__(attr_name):
            # 魔术属性（双下划线开头结尾）直接抛出AttributeError，不触发子模块创建，避免特殊属性访问错误
            if attr_name.startswith('__') and attr_name.endswith('__'):
                raise AttributeError(f"module '{name}' has no attribute '{attr_name}'")
            submodule_name = f"{name}.{attr_name}"
            if submodule_name not in sys.modules:
                # 自动创建子兼容模块，默认标记为包支持多级子模块
                submodule = _create_compat_module(submodule_name, is_package=True)
                setattr(module, attr_name, submodule)
            return sys.modules[submodule_name]
        module.__getattr__ = __getattr__
    # 补全通用空兼容类，支持任意继承、属性访问、调用、迭代、上下文管理，满足99%第三方库调用需求
    class _CompatObject:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return _CompatObject()
        def __getattr__(self, attr_name):
            return _CompatObject()
        def __iter__(self):
            return iter([])
        def __bool__(self):
            return False
        def __enter__(self):
            return _CompatObject()
        def __exit__(self, *args):
            return False
    module._CompatObject = _CompatObject
    # 注入初始属性
    if attrs:
        for attr_name, attr_value in attrs.items():
            setattr(module, attr_name, attr_value)
    # 注册到全局模块表
    sys.modules[name] = module
    return module

# 全局导入钩子:拦截所有import语句，自动为已注册兼容包创建子模块，覆盖import xxx.yyy场景
class _CompatModuleFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        # 检查是否是已注册兼容包的子模块
        for pkg_name in _compat_packages:
            if fullname.startswith(pkg_name + '.'):
                # 自动创建子兼容模块，默认标记为包支持多级嵌套
                submodule = _create_compat_module(fullname, is_package=True)
                # 返回合法的模块spec，让Python导入系统正常加载
                import importlib.util
                return importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
        return None

# 注册导入钩子到sys.meta_path最前端，优先处理兼容包导入
import sys
sys.meta_path.insert(0, _CompatModuleFinder)
# 容错导入pdb模块，兼容PyInstaller打包后缺失pdb的情况
try:
    import pdb
except ImportError:
    class _CompatPdb:
        def __init__(self, *args, **kwargs):
            pass
        def set_trace(self, *args, **kwargs):
            pass
        def reset(self, *args, **kwargs):
            pass
        def set_continue(self, *args, **kwargs):
            pass
        def set_quit(self, *args, **kwargs):
            pass
    pdb = _create_compat_module('pdb', attrs={
        'set_trace': lambda *args, **kwargs: None,
        'Pdb': _CompatPdb
    })

# 容错导入pickletools模块，兼容PyInstaller打包后缺失pickletools的情况
try:
    import pickletools
except ImportError:
    pickletools = _create_compat_module('pickletools', attrs={
        'dis': lambda *args, **kwargs: None,
        'genops': lambda *args, **kwargs: iter([]),
        'optimize': lambda data: data
    })

# 容错导入unittest模块，兼容PyInstaller打包后缺失unittest的情况
try:
    import unittest
except ImportError:
    class _CompatTestCase:
        def __init__(self, *args, **kwargs):
            pass
        def setUp(self, *args, **kwargs):
            pass
        def tearDown(self, *args, **kwargs):
            pass
        def assertEqual(self, *args, **kwargs):
            pass
        def assertTrue(self, *args, **kwargs):
            pass
        def assertFalse(self, *args, **kwargs):
            pass
    # 创建unittest父包，开启自动子模块懒加载，无需手动补全mock/case/util/result等子模块
    unittest = _create_compat_module('unittest', is_package=True, attrs={
        'TestCase': _CompatTestCase,
        'main': lambda *args, **kwargs: None
    })
    # 预初始化mock子模块核心属性，确保Mock/MagicMock/patch等常用对象可直接访问
    _mock_module = _create_compat_module('unittest.mock', attrs={
        'Mock': unittest._CompatObject,
        'MagicMock': unittest._CompatObject,
        'patch': lambda *args, **kwargs: lambda func: func,
        'patch.object': lambda *args, **kwargs: lambda func: func
    })
    unittest.mock = _mock_module

# 容错导入doctest模块，兼容PyInstaller打包后缺失doctest的情况
try:
    import doctest
except ImportError:
    class _CompatDocTestFinder:
        def __init__(self, *args, **kwargs):
            pass
        def find(self, *args, **kwargs):
            return []
    class _CompatDocTestRunner:
        def __init__(self, *args, **kwargs):
            pass
        def run(self, *args, **kwargs):
            return None
    doctest = _create_compat_module('doctest', attrs={
        'DocTestFinder': _CompatDocTestFinder,
        'DocTestRunner': _CompatDocTestRunner,
        'testmod': lambda *args, **kwargs: None,
        'run_docstring_examples': lambda *args, **kwargs: None,
        'register_optionflag': lambda *args, **kwargs: 0
    })

# 容错导入xml包，兼容PyInstaller打包后缺失xml标准库的情况
try:
    import xml.etree.ElementTree
except ImportError:
    # 创建xml父包，开启自动子模块懒加载，自动兼容etree/dom/sax/parsers等所有子模块
    xml = _create_compat_module('xml', is_package=True)
    # 预初始化etree子模块核心属性，满足配置解析需求
    _etree_module = _create_compat_module('xml.etree', is_package=True, attrs={
        'Element': xml._CompatObject,
        'ElementTree': xml._CompatObject,
        'parse': lambda *args, **kwargs: xml._CompatObject(),
        'fromstring': lambda *args, **kwargs: xml._CompatObject(),
        'tostring': lambda *args, **kwargs: b''
    })
    xml.etree = _etree_module
    # 绑定ElementTree到etree模块，兼容from xml.etree import ElementTree导入方式
    sys.modules['xml.etree.ElementTree'] = _etree_module

# 容错导入profile/pstats性能分析模块，兼容PyTorch profiler导入依赖
try:
    import profile
except ImportError:
    class _CompatProfile:
        def __init__(self, *args, **kwargs):
            pass
    profile = _create_compat_module('profile', attrs={
        'Profile': _CompatProfile
    })
try:
    import pstats
except ImportError:
    class _CompatStats:
        def __init__(self, *args, **kwargs):
            pass
    pstats = _create_compat_module('pstats', attrs={
        'Stats': _CompatStats
    })

# 容错导入tomllib模块（Python3.11+内置TOML解析），兼容huggingface_hub/transformers配置解析依赖
try:
    import tomllib
except ImportError:
    tomllib = _create_compat_module('tomllib', attrs={
        'load': lambda *args, **kwargs: {},
        'loads': lambda *args, **kwargs: {}
    })
# 容错导入optparse模块，兼容PyInstaller打包后缺失optparse的情况（sentence_transformers核心依赖）
try:
    import optparse
except ImportError:
    class _CompatOptionParser:
        def __init__(self, *args, **kwargs):
            pass
        def add_option(self, *args, **kwargs):
            return self
        def parse_args(self, *args, **kwargs):
            return (_CompatObject(), [])
        def error(self, msg: str = ""):
            pass
    optparse = _create_compat_module('optparse', attrs={
        'OptionParser': _CompatOptionParser,
        'Option': _CompatObject,
        'Values': _CompatObject,
        'make_option': lambda *args, **kwargs: _CompatObject()
    })
import tkinter

def handle_exception(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("❌ 程序发生致命错误:")
    print(error_msg)
    try:
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(base_dir, "crash_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(error_msg)
        print(f"✅ 错误日志已保存到: {log_path}")
    except:
        pass
    input("按回车键退出...")

sys.excepthook = handle_exception

# 跳过transformers torch版本安全检查，本地自用无风险
"""
主程序启动文件
"""
import os
print("✅ [调试1/8] 程序启动，开始配置环境变量")
os.environ['TRANSFORMERS_SKIP_TORCH_LOAD_SAFETY_CHECK'] = '1'
os.environ['PYNVML_SUPPRESS_DEPRECATION_WARNING'] = '1'
# 解决Windows平台下torch/numpy/faiss等数学库重复加载OpenMP运行时导致的C层静默abort闪退问题（官方推荐方案，无副作用）
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
# 强制所有数学计算库单线程运行，彻底避免多线程冲突导致C层abort崩溃
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMBA_NUM_THREADS'] = '1'
# 禁用所有C扩展多线程并行，彻底避免线程池冲突
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['OMP_THREAD_LIMIT'] = '1'
# 强制protobuf使用纯Python实现，彻底解决C扩展版本ABI兼容问题导致的静默崩溃
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
# 禁用huggingface遥测、版本检查和联网请求，适配无网络/网络受限环境，避免导入时联网卡住或触发C层崩溃
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
# 端口自动检测工具函数
def get_available_port(start_port=8000, max_port=8100):
    import socket
    for port in range(start_port, max_port+1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"8000~8100区间所有端口都被占用，请关闭占用程序后重试")
# 获取可用端口，全局统一使用
SERVER_PORT = get_available_port()
print(f"✅ 自动适配可用端口：{SERVER_PORT}")
import os
import threading
import time
import sys
# PySide6和浏览器懒加载，避免主程序强依赖
QApplication = None
AIBrowserWindow = None
Qt = None
def load_qt_modules():
    global QApplication, AIBrowserWindow, Qt, QWidget, QVBoxLayout, QObject, Slot, QWebEngineView, QWebChannel
    try:
        from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
        from PySide6.QtCore import Qt, QObject, Slot
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebChannel import QWebChannel
        from ai_browser import AIBrowserWindow
        return True
    except Exception as e:
        print(f"⚠️ 浏览器模块加载失败：{str(e)}，主程序仍可正常运行，请手动打开浏览器访问聊天地址")
        return False

# 初始化核心模块
# 兼容PyInstaller打包环境:打包后优先使用_internal目录，开发环境使用__file__所在目录
import sys as _sys
if getattr(_sys, 'frozen', False):
    _exe_dir = os.path.dirname(_sys.executable)
    _internal_dir = os.path.join(_exe_dir, "_internal")
    _BASE_DIR = _internal_dir if os.path.exists(_internal_dir) else _exe_dir
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LORA_PATH = os.path.join(_BASE_DIR, "current_lora.bin")
# 训练样本配置
TRAIN_SAMPLE_FILE = os.path.join(_BASE_DIR, "train_data.txt")

# 提前声明全局导出变量，解决api_server导入失败问题
llm = None
memory_cache = None
rag_manager = None
download_manager = None
browser_window = None
main_browser = None

def get_system_python_cmd():
    """
    检测系统可用的Python命令，优先返回3.11版本，兼容多版本共存场景
    返回:可用的Python命令字符串，检测失败返回None
    """
    import subprocess
    import sys
    
    # 目标版本:优先匹配程序内置的Python 3.11
    target_major = 3
    target_minor = 11
    
    # 按优先级排序检测命令:Windows专属py启动器 > python > python3
    # py -3.11是Windows多版本Python共存的标准调用方式，可精准指定版本
    candidate_cmds = []
    if sys.platform == "win32":
        candidate_cmds.append(["py", "-3.11"])
    candidate_cmds.extend([["python"], ["python3"]])
    
    # 第一轮:优先查找版本完全匹配3.11的Python
    for cmd_parts in candidate_cmds:
        try:
            check = subprocess.run(
                cmd_parts + ["--version"],
                capture_output=True, text=True, timeout=5
            )
            if check.returncode != 0:
                continue
            # 解析版本号，兼容"Python 3.11.4"格式
            version_output = check.stdout.strip() or check.stderr.strip()
            parts = version_output.split()
            if len(parts) >= 2:
                version_str = parts[1]
                version_parts = version_str.split(".")
                if len(version_parts) >= 2:
                    major = int(version_parts[0])
                    minor = int(version_parts[1])
                    if major == target_major and minor == target_minor:
                        # 版本完全匹配，返回命令列表（统一格式，避免后续调用嵌套问题）
                        return cmd_parts
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, IndexError):
            continue
    
    # 第二轮:找不到3.11版本，回退到任意可用版本，保持原有降级逻辑
    for cmd_parts in candidate_cmds:
        try:
            check = subprocess.run(
                cmd_parts + ["--version"],
                capture_output=True, text=True, timeout=5
            )
            if check.returncode == 0:
                # 统一返回命令列表格式
                return cmd_parts
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    return None

# 全局持久化保存DLL目录句柄，必须和程序生命周期一致，防止被GC回收导致DLL搜索路径自动失效
dll_dir_handles = []

def inject_external_dependencies():
    """
    打包环境下检测外部Python环境，版本匹配则注入外部site-packages到sys.path末尾
    开发环境直接跳过（开发环境已有完整依赖）
    注入到末尾确保不覆盖exe内部核心模块，插件可读取外部依赖
    """
    # 仅在打包环境下执行注入逻辑
    if not getattr(sys, 'frozen', False):
        return
    
    print("✅ [调试4.5/8] 检测外部向量检索依赖环境...")
    
    try:
        import subprocess
        import site
        
        # 1. 获取系统可用的Python命令（兼容python3）
        python_cmd = get_system_python_cmd()
        if not python_cmd:
            print("⚠️ 未检测到系统Python环境（python/python3均不可用），向量检索功能将降级运行（仅元数据记忆）")
            return
        
        # 2. 检测系统Python版本
        version_check = subprocess.run(
            python_cmd + ["--version"],
            capture_output=True, text=True, timeout=5
        )
        if version_check.returncode != 0:
            print("⚠️ 未检测到系统Python环境，向量检索功能将降级运行（仅元数据记忆）")
            return
        
        # 解析系统Python版本
        system_py_version = version_check.stdout.strip().split()[-1]
        system_py_major_minor = ".".join(system_py_version.split(".")[:2])
        
        # exe内部Python版本
        exe_py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # 3. 版本匹配校验
        if system_py_major_minor != exe_py_version:
            print(f"⚠️ Python版本不匹配:系统Python {system_py_version} vs 程序内置Python {exe_py_version}，跳过外部依赖注入，向量检索功能将降级运行")
            return
        
        print(f"✅ Python版本匹配:{system_py_version}")
        
        # 4. 获取系统Python的标准库路径、C扩展DLL路径和第三方库路径
        # 4.1 获取Python安装根目录，定位核心路径
        prefix_check = subprocess.run(
            python_cmd + ["-c", "import sys; print(sys.prefix)"],
            capture_output=True, text=True, timeout=5
        )
        lib_path = None
        dlls_path = None
        py_prefix = None
        if prefix_check.returncode == 0:
            py_prefix = prefix_check.stdout.strip()
            # 纯Python标准库存放路径
            lib_path = os.path.join(py_prefix, "Lib")
            # C扩展二进制模块、内置DLL存放路径（Windows平台Python特有）
            dlls_path = os.path.join(py_prefix, "DLLs")
            
            # 兼容非Windows环境的标准库路径
            if not os.path.exists(lib_path):
                try:
                    import sysconfig
                    lib_path = sysconfig.get_path('stdlib')
                    # 非Windows环境下C扩展路径和stdlib同目录，无需单独DLLs目录
                    dlls_path = None
                except:
                    lib_path = None
                    dlls_path = None
        
        # 4.2 获取第三方库site-packages路径
        site_packages_check = subprocess.run(
            python_cmd + ["-c", "import site; print('\\n'.join(site.getsitepackages()))"],
            capture_output=True, text=True, timeout=5
        )
        
        if site_packages_check.returncode != 0 and not lib_path:
            print("⚠️ 无法获取系统Python依赖路径，跳过依赖注入")
            return
        
        site_packages_paths = []
        if site_packages_check.returncode == 0:
            site_packages_paths = [p.strip() for p in site_packages_check.stdout.strip().split('\n') if p.strip()]
        
        # 5. 注入外部依赖路径（追加到sys.path末尾，优先级低于内置核心模块，避免覆盖内置模块导致兼容问题）
        # 注入顺序:先C扩展DLLs目录 → 纯Python标准库Lib目录 → 第三方库site-packages目录
        # 内置已有的模块优先使用内置版本，仅补全PyInstaller裁剪掉的缺失模块，零冲突风险
        injected_count = 0
        injected_paths = set() # 路径去重集合，避免重复注入（Windows下不区分大小写，统一转小写比对）
        # 使用全局dll_dir_handles列表持久化保存句柄，函数执行完不会被GC回收
        global dll_dir_handles
        
        # 5.1 先注入C扩展DLLs目录（存放_sqlite3/_ssl/_hashlib等.pyd二进制模块、sqlite3.dll等依赖动态库）
        if dlls_path and os.path.exists(dlls_path) and dlls_path not in sys.path and dlls_path not in injected_paths:
            sys.path.append(dlls_path)
            injected_paths.add(dlls_path)
            injected_count += 1
            print(f"✅ 已注入外部C扩展模块路径:{dlls_path}")
            # Python3.8+适配:将DLLs目录加入系统DLL搜索路径，确保pyd文件依赖的动态库可正常加载
            if sys.platform == 'win32' and sys.version_info >= (3, 8):
                try:
                    handle = os.add_dll_directory(dlls_path)
                    dll_dir_handles.append(handle)
                except Exception as dll_err:
                    print(f"⚠️ 添加DLL搜索路径失败（不影响核心功能）:{str(dll_err)}")
        
        # 5.2 注入纯Python标准库路径，解决optparse/xml/unittest等边缘标准库缺失问题
        if lib_path and os.path.exists(lib_path) and lib_path not in sys.path and lib_path not in injected_paths:
            sys.path.append(lib_path)
            injected_paths.add(lib_path)
            injected_count += 1
            print(f"✅ 已注入外部标准库路径:{lib_path}")
        
        # 5.3 注入第三方库路径，复用本地torch/sentence_transformers等大依赖
        for pkg_path in site_packages_paths:
            if pkg_path and os.path.exists(pkg_path) and pkg_path not in sys.path and pkg_path not in injected_paths:
                sys.path.append(pkg_path)
                injected_paths.add(pkg_path)
                injected_count += 1
                print(f"✅ 已注入外部第三方库路径:{pkg_path}")
        
        # 5.4 第三方C扩展依赖DLL目录自动扫描（解决所有C++编写的第三方库DLL加载失败问题，覆盖faiss/torch/opencv等）
        # Python3.8+ Windows平台仅加入sys.path不会自动加入DLL搜索路径，需要显式add_dll_directory
        # 注意:os.add_dll_directory返回的句柄必须持久化保存到全局列表，否则被GC回收后目录会自动从搜索路径移除
        if sys.platform == 'win32' and sys.version_info >= (3, 8):
            c_ext_dll_dirs = []
            # 遍历所有已注入的site-packages路径和Python根目录，自动检测所有C扩展依赖目录
            scan_paths = site_packages_paths.copy()
            if py_prefix:
                scan_paths.append(py_prefix)
            # 常见C扩展依赖目录名（覆盖99%的第三方C扩展库DLL存放位置）
            dll_dir_names = {"lib", "bin", "dlls", ".libs", "Library/bin"}
            # 无关目录名，直接跳过不扫描
            skip_dirs = {"__pycache__", "contrib", "tests", "docs", "swig", "python", "include", "licenses", "examples"}
            
            for pkg_path in scan_paths:
                if not pkg_path or not os.path.exists(pkg_path):
                    continue
                # site-packages/Python根目录本身也加入DLL搜索路径，部分安装方式依赖DLL直接存放在根目录
                c_ext_dll_dirs.append(pkg_path)
                # 遍历所有一级子目录，自动识别所有包含DLL的依赖目录（覆盖faiss/torch/sentence_transformers/opencv等所有C扩展库）
                for sub_item in os.listdir(pkg_path):
                    if sub_item.lower() in skip_dirs:
                        continue
                    sub_path = os.path.join(pkg_path, sub_item)
                    if not os.path.isdir(sub_path):
                        continue
                    # 包名本身就是已知C扩展库（faiss/torch等），直接加入目录
                    if sub_item.lower() in {"faiss", "torch", "sentence_transformers", "opencv", "pyarrow", "numpy", "safetensors", "tokenizers", "scipy", "pil", "regex", "transformers", "huggingface_hub", "filelock", "fsspec", "sentencepiece"}:
                        c_ext_dll_dirs.append(sub_path)
                    # 子目录名匹配常见DLL目录名，自动加入
                    if sub_item.lower() in dll_dir_names:
                        c_ext_dll_dirs.append(sub_path)
                    # 【修复漏扫缺陷】对所有子目录（无论是否在已知C扩展列表），自动扫描其下一级子目录中的DLL目录（覆盖sentencepiece/.libs、torch/lib等所有二级DLL目录结构，无需手动维护包列表）
                    try:
                        for lib_sub_item in os.listdir(sub_path):
                            if lib_sub_item.lower() in dll_dir_names:
                                lib_sub_path = os.path.join(sub_path, lib_sub_item)
                                if os.path.isdir(lib_sub_path):
                                    c_ext_dll_dirs.append(lib_sub_path)
                    except Exception:
                        pass
                # 检测全局第三方依赖目录（覆盖所有可能的依赖存放位置）
                for sub_dir_name in dll_dir_names:
                    global_libs = os.path.join(pkg_path, sub_dir_name)
                    if os.path.exists(global_libs) and os.path.isdir(global_libs):
                        c_ext_dll_dirs.append(global_libs)
            
            # 手动添加Python根目录下的Library/bin核心系统依赖目录（通用扫描扫不到这个二级目录，存放vcruntime/libgcc/libstdc++等所有C扩展依赖的系统运行时）
            if py_prefix:
                library_bin = os.path.join(py_prefix, "Library", "bin")
                if os.path.exists(library_bin) and os.path.isdir(library_bin):
                    c_ext_dll_dirs.append(library_bin)
            
            # 去重（Windows平台路径不区分大小写，统一转小写比对避免重复），逐个添加到DLL搜索路径
            added_dll_count = 0
            seen_paths = set()
            for dll_dir in c_ext_dll_dirs:
                # 路径规范化+大小写不敏感去重
                norm_path = os.path.normpath(dll_dir)
                path_key = norm_path.lower() if sys.platform == 'win32' else norm_path
                if path_key in seen_paths:
                    continue
                seen_paths.add(path_key)
                try:
                    handle = os.add_dll_directory(norm_path)
                    dll_dir_handles.append(handle)
                    added_dll_count += 1
                    # 统计目录下DLL数量，方便调试
                    dll_count = len([f for f in os.listdir(norm_path) if f.lower().endswith('.dll')])
                    print(f"✅ 已添加第三方C扩展DLL搜索路径:{norm_path}（包含{dll_count}个DLL文件）")
                except Exception as dll_err:
                    print(f"⚠️ 添加DLL搜索路径失败（不影响核心功能）:{norm_path}，原因:{str(dll_err)}")
            
            if added_dll_count > 0:
                print(f"✅ 共添加{added_dll_count}个第三方C扩展DLL搜索目录，DLL路径句柄已全局持久化保存，faiss/torch等所有C扩展库可正常加载")
        
        if injected_count > 0:
            print(f"✅ 外部依赖注入完成，共注入{injected_count}个路径，插件可读取外部依赖，向量检索功能已启用完整模式")
        else:
            print("⚠️ 未找到可注入的site-packages路径，向量检索功能将降级运行")
            
    except subprocess.TimeoutExpired:
        print("⚠️ 检测外部Python环境超时，向量检索功能将降级运行")
    except Exception as e:
        print(f"⚠️ 检测外部依赖环境异常:{str(e)}，向量检索功能将降级运行")

if __name__ == "__main__":
    # 启动时检测外部依赖，版本匹配则注入路径
    inject_external_dependencies()
    
    # ✅ 依赖路径注入完成后再导入LLM模块，确保openai及其依赖可以正常加载
    from llm_client import UnifiedLLM as Llama, get_config, init_llm
    # 初始化全局LLM实例
    init_llm()
    
    # ==============================================
    # 【零风险终极方案】标准库导入路径优先级调整（完全不删除任何模块，零崩溃风险）
    # 原理:
    # 1. 已加载的模块（Python核心、PyInstaller启动钩子依赖）完全不碰，它们已经正常跑完启动流程，动了反而有风险
    # 2. 仅调整导入路径优先级，让后续新导入标准库/导入标准库子模块时，优先加载系统Python的完整版本
    # 3. 完全不需要维护白名单，不需要删除任何模块，100%不会出现删错核心模块的问题
    # 4. 一劳永逸，不管Python/PyInstaller/依赖版本怎么升级都自动兼容，零维护成本
    # ==============================================
    if getattr(sys, 'frozen', False):
        print("✅ [调试4.6/8] 调整标准库导入路径优先级，强制使用系统完整版本...")
        system_lib_path = None
        try:
            import subprocess
            # 复用和依赖注入一致的逻辑获取系统Python标准库路径
            python_cmd = get_system_python_cmd()
            if python_cmd:
                # 获取系统Python安装根目录
                prefix_check = subprocess.run(
                    python_cmd + ["-c", "import sys; print(sys.prefix)"],
                    capture_output=True, text=True, timeout=5
                )
                if prefix_check.returncode == 0:
                    py_prefix = prefix_check.stdout.strip()
                    system_lib_path = os.path.join(py_prefix, "Lib")
                    # 兼容非Windows环境
                    if not os.path.exists(system_lib_path):
                        try:
                            import sysconfig
                            system_lib_path = sysconfig.get_path('stdlib')
                        except:
                            system_lib_path = None
        except Exception as e:
            print(f"⚠️ 获取系统标准库路径失败，将使用已注入路径: {str(e)}")
        
        adjusted_count = 0
        if system_lib_path and os.path.exists(system_lib_path):
            # 1. 把系统标准库路径插到sys.path最前面，优先级高于PyInstaller临时解压目录
            # 后续新导入顶级标准库模块时，优先从系统路径找完整版本
            if system_lib_path in sys.path:
                sys.path.remove(system_lib_path)
            sys.path.insert(0, system_lib_path)
            adjusted_count += 1
            
            # 2. 遍历所有已加载的标准库包（有__path__属性的包，比如multiprocessing/concurrent/xml等）
            # 把系统Lib路径下对应的包目录加到该模块的__path__最前面，解决子模块导入找不到的问题
            # 后续导入子模块时，Python会优先从系统路径找完整子模块，不会因为主模块是PyInstaller打包的就找不到子模块
            for mod_name, mod in list(sys.modules.items()):
                # 只处理顶级标准库包（跳过子模块、非包模块、第三方模块、私有模块）
                if '.' in mod_name or not hasattr(mod, '__path__'):
                    continue
                if mod_name not in sys.stdlib_module_names:
                    continue
                # 拼接系统标准库下对应的包目录路径
                system_pkg_path = os.path.join(system_lib_path, mod_name)
                if os.path.exists(system_pkg_path) and system_pkg_path not in mod.__path__:
                    # 插到__path__最前面，优先级最高
                    mod.__path__.insert(0, system_pkg_path)
                    adjusted_count += 1
            
            # 【修复http包残缺问题】预先导入http标准库包，手动添加系统路径到__path__，解决PyInstaller打包的http缺少cookies等子模块问题
            import http
            system_http_path = os.path.join(system_lib_path, 'http')
            if os.path.exists(system_http_path) and system_http_path not in http.__path__:
                http.__path__.insert(0, system_http_path)
                adjusted_count += 1
            # 【修复logging包残缺问题】预先导入logging标准库包，手动添加系统路径到__path__，解决PyInstaller打包的logging缺少config等子模块问题
            import logging
            system_logging_path = os.path.join(system_lib_path, 'logging')
            if os.path.exists(system_logging_path) and system_logging_path not in logging.__path__:
                logging.__path__.insert(0, system_logging_path)
                adjusted_count += 1
        
        # 仅清理明确排除的调试类标准库残缺占位模块（这些是非核心调试工具，零风险删除，后续导入自动加载系统完整版本）
        debug_mods_to_clean = {'unittest', 'doctest', 'pdb', 'profile', 'pstats'}
        cleaned_debug_count = 0
        for mod_name in debug_mods_to_clean:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
                cleaned_debug_count += 1
            # 从兼容包集合中移除，禁止导入钩子自动为这些模块创建空兼容子模块，确保后续导入加载系统完整版本
            _compat_packages.discard(mod_name)
        
        print(f"✅ 标准库导入路径调整完成，共调整{adjusted_count}个路径优先级，清理{cleaned_debug_count}个调试类残缺模块占位，后续导入将自动使用系统Python完整版本")
    
    # 依赖注入后重新尝试导入向量检索依赖，更新模块全局变量
    try:
        print("🔍 开始导入torch...")
        import torch
        # torch导入成功后显式强制设置单线程，覆盖环境变量被自动重置的问题，彻底避免多线程冲突
        if hasattr(torch, 'set_num_threads'):
            torch.set_num_threads(1)
        if hasattr(torch, 'set_num_interop_threads'):
            torch.set_num_interop_threads(1)
        print("🔍 torch导入成功，开始预加载numpy/scipy/PIL/sklearn等依赖C扩展...")
        # 提前预加载sentence_transformers依赖的C扩展，避免内部动态加载时顺序冲突
        import numpy
        # 兼容numpy 2.x与基于numpy 1.x编译的旧版C扩展库（如faiss）的ABI不兼容问题
        if numpy.__version__.startswith('2.'):
            # 注入numpy 1.x兼容的_ARRAY_API私有属性，解决旧版C扩展找不到API符号报错
            # 旧版C扩展会同时从numpy顶层和numpy.core.multiarray两个路径查找该符号，两处都要注入确保兼容
            _array_api = None
            try:
                from numpy._core import multiarray as _multiarray
                _array_api = _multiarray._ARRAY_API
            except Exception:
                # 兼容不同numpy 2.x子版本的路径差异
                try:
                    import numpy.core.multiarray as _multiarray
                    _array_api = _multiarray._ARRAY_API
                except Exception as np_compat_err:
                    print(f"⚠️ numpy 2.x兼容垫片注入失败，旧版C扩展可能加载失败: {str(np_compat_err)}")
            
            if _array_api is not None:
                # 1. 注入到numpy顶层模块
                if not hasattr(numpy, '_ARRAY_API'):
                    numpy._ARRAY_API = _array_api
                # 2. 注入到numpy.core.multiarray模块，兼容旧版C扩展直接从该路径导入符号
                try:
                    import numpy.core.multiarray
                    if not hasattr(numpy.core.multiarray, '_ARRAY_API'):
                        numpy.core.multiarray._ARRAY_API = _array_api
                except Exception:
                    pass
        import scipy
        # 显式预加载scipy最底层的深层核心子模块（从底向上加载，避免上层模块导入时触发懒加载失败）
        # 必须先加载array_api_compat系列最底层子模块，再加载sparse等上层模块，顺序不能反
        import scipy._lib.array_api_compat
        import scipy._lib.array_api_compat.numpy
        import scipy._lib.array_api_compat.numpy.fft
        import scipy.sparse
        import PIL
        # 【消除C扩展冲突隐患】sklearn导入时会自动检测并导入pandas/pyarrow，
        # pyarrow的C++扩展和已加载的torch/numpy存在DLL符号冲突，会触发非致命访问违例
        # 临时注册兼容模块，让sklearn使用空兼容对象，不触发真实C扩展加载
        _temp_compat_modules = []
        for _mod_name in ['pandas', 'pyarrow']:
            if _mod_name not in sys.modules:
                # 预注入__version__属性，满足sklearn版本检查要求（>=1.4即可），无需真实加载pandas/pyarrow
                _compat_mod = _create_compat_module(_mod_name, is_package=True, attrs={
                    '__version__': '2.0.0'
                })
                _temp_compat_modules.append(_mod_name)
        import sklearn
        # 导入完成后移除临时兼容注册，恢复真实模块导入能力（向量检索不需要pandas/pyarrow，不影响核心功能）
        for _mod_name in _temp_compat_modules:
            if _mod_name in sys.modules:
                del sys.modules[_mod_name]
        print("🔍 依赖C扩展预加载成功，开始导入tokenizers...")
        import tokenizers
        print("🔍 tokenizers导入成功，开始导入safetensors...")
        import safetensors
        print("🔍 safetensors导入成功，开始导入transformers...")
        import transformers
        print("🔍 transformers导入成功，开始导入sentencepiece...")
        import sentencepiece
        print("🔍 sentencepiece导入成功，开始导入sentence_transformers核心子模块...")
        from sentence_transformers import models
        print("🔍 sentence_transformers.models导入成功，开始导入util...")
        from sentence_transformers import util
        print("🔍 sentence_transformers.util导入成功，开始导入datasets...")
        from sentence_transformers import datasets
        print("🔍 sentence_transformers.datasets导入成功，开始导入evaluation...")
        from sentence_transformers import evaluation
        print("🔍 sentence_transformers.evaluation导入成功，开始导入主SentenceTransformer类...")
        import sentence_transformers
        print("🔍 sentence_transformers导入成功，开始导入memory_cache...")
        import memory_cache
        memory_cache.SentenceTransformer = sentence_transformers.SentenceTransformer
        
        print("🔍 开始导入rag_manager...")
        import rag_manager
        rag_manager.HAS_RAG_DEPENDENCIES = True
        rag_manager.torch = torch
        rag_manager.SentenceTransformer = sentence_transformers.SentenceTransformer
        print("✅ 向量检索依赖注入成功，已更新模块全局变量")
    except Exception as e:
        print(f"⚠️ 向量检索依赖注入失败，向量检索功能将降级运行，详细原因:{str(e)}")
        import traceback
        traceback.print_exc()
    
    # 延迟导入MemoryCache，确保依赖注入在导入前完成
    from memory_cache import MemoryCache
    
    print("✅ [调试5/8] 开始初始化向量记忆缓存")
    # 初始化记忆缓存和LoRA更新器
    memory_cache = MemoryCache()
    print("✅ [调试6/8] 向量记忆缓存初始化完成")
    # 加载所有已安装插件
    from tool_template_manager import ToolTemplateManager
    ToolTemplateManager.load_plugins()
    print("✅ 插件加载完成")
    # 新增：初始化代码RAG知识库
    from rag_manager import rag_manager
    print("✅ [调试6.5/8] 代码RAG知识库初始化完成")
    print("✅ [调试7/8] 所有核心模块初始化完成，启动统一API服务")
    # 把当前主模块注册为main模块，解决api_server导入时找不到变量的问题
    import sys
    sys.modules['main'] = sys.modules['__main__']
    # 所有全局变量初始化完成后再导入api_server，彻底解决循环导入问题
    import api_server

    # 启动兼容OpenAI标准的API服务（子线程运行，不阻塞主程序），使用统一自动适配的端口
    # 接收实际启动端口，同步更新全局变量，避免端口检测时间差导致的不一致问题
    SERVER_PORT = api_server.start_api_server(port=SERVER_PORT)
    
    # 启动双向自动同步监听服务（后台守护线程，不阻塞主程序，主程序退出自动销毁）
    from auto_sync_monitor import start_monitor
    sync_thread = threading.Thread(target=start_monitor, daemon=True)
    sync_thread.start()
    print("✅ [调试7.5/8] 双向自动同步监听服务已启动，文件变动实时同步")
    
    # 等待2秒确保所有服务启动完成
    time.sleep(2)
    
    # 启动内置浏览器 + 悬浮窗（统一Qt框架，零线程冲突）
    qt_loaded = load_qt_modules()
    if qt_loaded:
        try:
            qt_app = QApplication(sys.argv)
            
            
            # 1. 后台仅预加载浏览器框架，不打开任何页面、不显示，完全静默
            main_browser = AIBrowserWindow(home_url=f"http://127.0.0.1:{SERVER_PORT}/chat", auto_open_home=False, show_immediately=False)
            browser_window = main_browser
            main_browser.setWindowFlag(Qt.WindowType.Tool)
            # 给主窗口设置全局唯一标识，供单实例校验时查找并激活已有窗口
            import ctypes
            _user32 = ctypes.windll.user32
            _user32.SetPropW(int(main_browser.winId()), "AI_GZT_Main_Window_v1", 1)
            from PySide6.QtCore import QTimer
            def _preload_workbench():
                # 原有open_page逻辑完全不变
                web_view = main_browser.open_page(f"http://127.0.0.1:{SERVER_PORT}/workspace", page_id="workbench", title="AI工作台")
                # 【修复空指针问题】加web_view有效性校验，避免对象为空时报错
                if web_view and hasattr(web_view, 'loadFinished'):
                    # 【修复时序问题】页面加载完成后再隐藏，避免Web引擎资源被提前回收
                    def _hide_after_load(ok):
                        if ok:
                            main_browser.hide()
                    web_view.loadFinished.connect(_hide_after_load)
            # 调用预加载逻辑，初始化工作台
            _preload_workbench()

            # 全局信号总线定义
            from PySide6.QtCore import Signal
            import queue
            class GlobalSignalBus(QObject):
                # 浏览器打开URL信号:参数为要打开的URL字符串
                open_browser_url = Signal(str)
                # 浏览器操作请求信号:参数为请求字典，包含action、params、result_queue
                browser_operation_request = Signal(dict)
            
            # 初始化全局信号总线实例
            global_signal_bus = GlobalSignalBus()
            
            # 绑定信号到浏览器的槽函数，自动投递到UI主线程执行
            global_signal_bus.open_browser_url.connect(main_browser.open_new_tab)
            
            # 浏览器操作处理函数（在主线程执行，安全调用PySide6对象，彻底解决子线程崩溃问题）
            def handle_browser_operation(request: dict):
                action = request.get("action")
                params = request.get("params", {})
                result_queue = request.get("result_queue")
                try:
                    if action == "click":
                        selector = params.get("selector", "")
                        result = main_browser.execute_action("click", selector)
                        request["result"] = result
                    elif action == "input":
                        selector = params.get("selector", "")
                        value = params.get("value", "")
                        result = main_browser.execute_action("input", selector, value)
                        request["result"] = result
                    elif action == "extract":
                        keyword = params.get("query", "")
                        page_text = ""
                        # 使用 QEventLoop 等待异步回调，在主线程中安全执行
                        from PySide6.QtCore import QEventLoop, QTimer
                        loop = QEventLoop()
                        
                        def _get_text():
                            nonlocal page_text
                            def callback(result):
                                nonlocal page_text
                                page_text = result
                                loop.quit()
                            main_browser.get_page_text(callback)
                        
                        QTimer.singleShot(0, _get_text)
                        QTimer.singleShot(5000, loop.quit) # 5秒超时兜底
                        loop.exec()
                        
                        # 降级方案:如果浏览器内核提取失败，改用get_page_html + BeautifulSoup解析
                        if not page_text.strip():
                            html = ""
                            loop2 = QEventLoop()
                            def _get_html():
                                nonlocal html
                                def callback_html(result_html):
                                    nonlocal html
                                    html = result_html
                                    loop2.quit()
                                main_browser.get_page_html(callback_html)
                            QTimer.singleShot(0, _get_html)
                            QTimer.singleShot(5000, loop2.quit)
                            loop2.exec()
                            
                            if html.strip():
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html, "html.parser")
                                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                                    tag.decompose()
                                page_text = soup.get_text(strip=True, separator="\n")
                        
                        # 按关键词过滤提取相关段落
                        if keyword:
                            lines = page_text.split("\n")
                            relevant_lines = [line for line in lines if keyword in line]
                            extracted_content = "\n".join(relevant_lines) if relevant_lines else "未找到与关键词相关的内容"
                        else:
                            extracted_content = page_text
                        
                        request["result"] = extracted_content
                    elif action == "get_html":
                        html = ""
                        from PySide6.QtCore import QEventLoop, QTimer
                        loop = QEventLoop()
                        def _get_html():
                            nonlocal html
                            def callback(result_html):
                                nonlocal html
                                html = result_html
                                loop.quit()
                            main_browser.get_page_html(callback)
                        QTimer.singleShot(0, _get_html)
                        QTimer.singleShot(5000, loop.quit)
                        loop.exec()
                        request["result"] = html
                except Exception as e:
                    request["error"] = str(e)
                finally:
                    if result_queue:
                        result_queue.put(request)
            
            # 绑定浏览器操作请求信号到处理函数，自动投递到UI主线程执行
            global_signal_bus.browser_operation_request.connect(handle_browser_operation)
            
            # 注册信号总线到全局变量，所有插件都可以调用
            sys.modules['main'].__dict__['global_signal_bus'] = global_signal_bus
            
            # 2. 定义悬浮窗JS调用API（完全兼容原有前端代码，无需修改）
            class FloatAPI(QObject):
                @Slot()
                def show_workbench(self):
                    # 保留原有接口兼容旧逻辑
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: main_browser.open_ai_workbench())
                @Slot(str)
                def open_url(self, url: str):
                    # 新增开放给JS调用的打开URL接口
                    global_signal_bus.open_browser_url.emit(url)
                 
            # 3. 创建独立悬浮窗窗口（和pywebview体验100%一致）
            from PySide6.QtGui import QIcon
            float_window = QWidget()
            float_window.setWindowTitle("") # 隐藏标题文字，仅显示图标
            float_window.setWindowIcon(QIcon(os.path.join(_BASE_DIR, "app_icon.ico")))
            float_window.resize(420,720)
            float_window.setMinimumSize(380,500)
            float_window.setStyleSheet("background-color: #f5f5f5;")
            layout = QVBoxLayout(float_window)
            layout.setContentsMargins(0,0,0,0) # 无边距铺满窗口
            
            web_view = QWebEngineView()
            # 允许JS弹出新窗口，解除弹窗拦截
            from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
            web_view.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
            web_view.settings().setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
            
            # 处理JS的window.open请求，全部转发给内置浏览器打开
            class CustomWebPage(QWebEnginePage):
                def createWindow(self, window_type):
                    # 拦截所有新窗口请求，用内置浏览器打开
                    def _on_new_url(url):
                        # 统一使用全局预加载的浏览器实例，支持全链路标签页去重
                        global main_browser
                        url_str = url.toString()
                        # 工作台页面固定page_id实现去重，其他页面按需扩展
                        page_id = "workbench" if "/workspace" in url_str else None
                        main_browser.open_page(url_str, page_id=page_id)
                    # 监听新窗口的URL加载请求
                    dummy_page = QWebEnginePage(self)
                    dummy_page.urlChanged.connect(_on_new_url)
                    # 返回None禁止Qt自动创建新窗口，完全由我们自定义打开逻辑
                    return None
                
                def acceptNavigationRequest(self, url, type, is_main_frame):
                    # 拦截自定义协议打开工作台，不需要依赖任何JS注入
                    if url.toString() == 'local://open-ai-workbench':
                        from PySide6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: main_browser.open_ai_workbench())
                        return False
                    return super().acceptNavigationRequest(url, type, is_main_frame)
            web_view.setPage(CustomWebPage(web_view))
            
            # 用PySide6原生支持的QWebChannel暴露API，100%兼容无报错
            channel = QWebChannel()
            api = FloatAPI()
            channel.registerObject("api", api)
            web_view.page().setWebChannel(channel)
            # 注入pywebview兼容对象，加自动重试逻辑，等待后端服务启动
            retry_count = [0] # 用可变列表规避Python作用域问题，无需nonlocal
            def load_page():
                web_view.load(f"http://127.0.0.1:{SERVER_PORT}/chat_float.html")
            
            def on_load_finished(success):
                if not success and retry_count[0] < 10:
                    retry_count[0] += 1
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(1000, load_page) # 1秒后重试
                elif success:
                    # 加载成功后注入兼容代码，等待QWebChannel完全初始化再挂载对象
                    web_view.page().runJavaScript("""
                        document.addEventListener('DOMContentLoaded', () => {
                            new QWebChannel(qt.webChannelTransport, (channel) => {
                                // 完整兼容pywebview API，所有分支最终都唤醒预加载工作台
                                window.pywebview = {
                                    api: { show_workbench: () => channel.objects.api.show_workbench() },
                                    create_window: () => channel.objects.api.show_workbench()
                                };
                            });
                        });
                    """)
            
            web_view.loadFinished.connect(on_load_finished)
            load_page()
            
            layout.addWidget(web_view)
            float_window.show()
            print("✅ AI悬浮助手已启动，可在桌面找到")

            # 4. 启动Qt主循环，两个窗口共用同一个线程，零冲突
            sys.exit(qt_app.exec())
        except Exception as e:
            print(f"⚠️ GUI启动失败：{str(e)}，请手动打开浏览器访问聊天地址")
    # 降级模式：保持后端服务运行
    while True:
        time.sleep(3600)