# -*- coding: utf-8 -*-
"""
智能助手内置浏览器 V1.0（核心功能版）
功能特性：
1. 支持独立运行，可单独作为普通浏览器使用
2. 多标签页管理，支持拖拽排序、关闭、切换
3. 页面去重能力，同一页面仅打开一次，重复点击自动激活
4. 基础导航功能：前进/后退/刷新/地址栏/搜索
5. 无缝集成现有AI助手系统
"""
import sys
import os
import json
import base64
import threading
# ========== Cookie自动复用加密工具 ==========
COOKIE_STORAGE_FILE = "browser_cookies_encrypted.json"
# 本地加密密钥（自动生成，每个客户端唯一）
_ENCRYPT_KEY = base64.b64encode(os.urandom(32)).decode() if not os.path.exists(".cookie_key") else open(".cookie_key", "r", encoding="utf-8").read().strip()
if not os.path.exists(".cookie_key"):
    with open(".cookie_key", "w", encoding="utf-8") as f:
        f.write(_ENCRYPT_KEY)
    # 隐藏密钥文件
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(".cookie_key", 0x02) # 隐藏属性

def _encrypt_cookie_data(data: dict) -> str:
    """加密Cookie数据"""
    data_str = json.dumps(data, ensure_ascii=False)
    encrypted = []
    for i, c in enumerate(data_str):
        key_char = _ENCRYPT_KEY[i % len(_ENCRYPT_KEY)]
        encrypted.append(chr(ord(c) ^ ord(key_char)))
    return base64.b64encode(''.join(encrypted).encode("utf-8")).decode("utf-8")

def _decrypt_cookie_data(encrypted_str: str) -> dict:
    """解密Cookie数据"""
    try:
        decoded = base64.b64decode(encrypted_str).decode("utf-8")
        decrypted = []
        for i, c in enumerate(decoded):
            key_char = _ENCRYPT_KEY[i % len(_ENCRYPT_KEY)]
            decrypted.append(chr(ord(c) ^ ord(key_char)))
        return json.loads(''.join(decrypted))
    except:
        return {}
# ========== 结束Cookie加密工具 ==========
# 禁用浏览器控制台日志、开启全部音视频解码器支持，伪装Chrome UA解决视频网站兼容问题
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-logging --log-level=3 --no-sandbox --disable-web-security --allow-running-insecure-content --enable-clipboard-read-write --enable-features=PlatformHEVCDecoderSupport,VaapiVideoDecoder,FFmpegVideoDecoder,FFmpegAudioDecoder,HardwareMediaKeyHandling,Widevine --autoplay-policy=no-user-gesture-required --disable-features=UseChromeOSDirectVideoDecoder,MediaFoundationVideoDecoder --user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"'
os.environ['QT_ENABLE_PATENTED_CODECS'] = '1'
from PySide6.QtCore import Qt, QStandardPaths, QUrl, QTimer, QTranslator, QRect, QPoint, QSize, QDateTime, Slot
from PySide6.QtGui import QAction, QDesktopServices, QPixmap, QGuiApplication, QPainter, QColor, QPen, QCursor, QShortcut, QKeySequence
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QPushButton, QToolBar, QStatusBar, QLabel, QFileDialog, QMenu, QMessageBox, QProgressBar, QDialog, QListWidget, QListWidgetItem, QPushButton)
import json
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, QStandardPaths, QFileInfo
from PySide6.QtGui import QIcon, QAction
# ========== 下载管理面板类 ==========
class DownloadManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 下载管理")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self)
        
        # 顶部操作栏
        top_bar = QHBoxLayout()
        self.set_path_btn = QPushButton("⚙️ 设置默认下载路径")
        self.set_path_btn.clicked.connect(parent.set_default_download_path)
        self.clear_finished_btn = QPushButton("🗑️ 清空已完成任务")
        self.clear_finished_btn.clicked.connect(self.clear_finished_tasks)
        top_bar.addWidget(self.set_path_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.clear_finished_btn)
        self.layout.addLayout(top_bar)
        
        # 下载任务列表
        self.download_list = QListWidget()
        self.layout.addWidget(self.download_list)
        
        # 任务存储
        self.tasks = {}
    
    def add_task(self, download_item, file_name):
        """新增下载任务到列表"""
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # 任务信息
        info_label = QLabel(f"📄 {file_name}\n⏳ 准备中... 0%")
        info_label.setMinimumWidth(350)
        # 操作按钮
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.clicked.connect(lambda: download_item.cancel())
        open_btn = QPushButton("📂 打开文件")
        open_btn.hide()
        open_folder_btn = QPushButton("📁 打开文件夹")
        open_folder_btn.hide()
        
        layout.addWidget(info_label)
        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(open_btn)
        layout.addWidget(open_folder_btn)
        layout.setContentsMargins(5,5,5,5)
        
        item.setSizeHint(widget.sizeHint())
        self.download_list.addItem(item)
        self.download_list.setItemWidget(item, widget)
        
        # 存储任务信息
        self.tasks[download_item] = {
            "item": item,
            "widget": widget,
            "info_label": info_label,
            "cancel_btn": cancel_btn,
            "open_btn": open_btn,
            "open_folder_btn": open_folder_btn,
            "file_name": file_name,
            "save_path": ""
        }
    
    def update_task_progress(self, download_item, percent, speed, save_path=""):
        """更新任务进度"""
        if download_item not in self.tasks:
            return
        task = self.tasks[download_item]
        task["save_path"] = save_path
        task["info_label"].setText(f"📄 {task['file_name']}\n⏳ 下载中... {percent}% ({speed:.1f}MB/s)")
    
    def mark_task_finished(self, download_item, success=True):
        """标记任务完成（自动清理假死任务）"""
        if download_item not in self.tasks:
            return
        task = self.tasks[download_item]
        task["cancel_btn"].hide()
        if success:
            task["info_label"].setText(f"📄 {task['file_name']}\n✅ 下载完成")
            task["open_btn"].show()
            task["open_folder_btn"].show()
            # 绑定打开操作
            task["open_btn"].clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(task["save_path"])))
            task["open_folder_btn"].clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(task["save_path"]))))
            # 可选：下载完成5分钟后自动清理任务，不需要可以删掉下面两行
            from threading import Timer
            Timer(300, lambda: self.clear_single_task(download_item)).start()
        else:
            task["info_label"].setText(f"📄 {task['file_name']}\n❌ 下载已取消/失败")
            # 失败任务1分钟后自动清理
            from threading import Timer
            Timer(60, lambda: self.clear_single_task(download_item)).start()
    
    def clear_single_task(self, download_item):
        """清理单个任务"""
        if download_item in self.tasks:
            row = self.download_list.row(self.tasks[download_item]["item"])
            self.download_list.takeItem(row)
            del self.tasks[download_item]
    
    def clear_finished_tasks(self):
        """清空已完成/失败的任务"""
        to_remove = []
        for item, task in self.tasks.items():
            if not task["cancel_btn"].isVisible():
                to_remove.append(item)
        for item in to_remove:
            row = self.download_list.row(self.tasks[item]["item"])
            self.download_list.takeItem(row)
            del self.tasks[item]
# 自定义WebPage，自动授予剪贴板读写权限（全版本PySide6兼容）+ 导航拦截
from PySide6.QtWebEngineCore import QWebEnginePage
class CustomWebPage(QWebEnginePage):
    def __init__(self, browser_window, web_view, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        self.web_view = web_view
        # 兼容PySide6不同版本的权限请求信号，解决"permissionRequested属性不存在"报错
        if hasattr(self, 'permissionRequested'):
            # 新版PySide6（>=6.7）信号
            self.permissionRequested.connect(self._handle_permission_new)
        elif hasattr(self, 'featurePermissionRequested'):
            # 旧版PySide6（<6.7）信号
            self.featurePermissionRequested.connect(self._handle_permission_old)
    
    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        """拦截工作台页面跳转，禁止替换工作台根页面，所有内部跳转强制新开标签"""
        # 仅拦截工作台主页面的主框架跳转
        if "workbench" in self.browser_window.opened_pages and self.web_view == self.browser_window.opened_pages["workbench"] and is_main_frame:
            # 放行刷新操作，不拦截
            if navigation_type == QWebEnginePage.NavigationTypeReload:
                return super().acceptNavigationRequest(url, navigation_type, is_main_frame)
            # 放行锚点跳转 + 同源IP跳转（127.0.0.1和localhost互跳不拦截）
            current_url = self.url().toString()
            target_url = url.toString()
            from urllib.parse import urlparse
            current_path = urlparse(current_url).path
            target_path = urlparse(target_url).path
            # 仅路径相同的同源跳转/锚点跳转直接放行
            if ( '#' in target_url and target_url.split('#')[0] == current_url.split('#')[0] ) or target_path == current_path:
                return super().acceptNavigationRequest(url, navigation_type, is_main_frame)
            # 其他所有跳转（训练中心、样本管理、外部链接等）全部强制新开标签
            self.browser_window.add_new_tab(url, "加载中...")
            return False
        # 非工作台页面全部正常放行，遵循默认跳转逻辑
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)

    def _handle_permission_new(self, origin, permission_type):
        """新版API权限请求处理"""
        # 自动允许剪贴板读写权限
        if permission_type in (QWebEnginePage.ClipboardRead, QWebEnginePage.ClipboardWrite):
            self.setPermission(origin, permission_type, QWebEnginePage.PermissionGrantedByUser)
        else:
            # 其他权限透传给父类处理
            try:
                super().permissionRequested.emit(origin, permission_type)
            except:
                pass

    def _handle_permission_old(self, origin, feature):
        """旧版API权限请求处理"""
        # 自动允许剪贴板读写权限
        if feature in (QWebEnginePage.ClipboardRead, QWebEnginePage.ClipboardWrite):
            self.setFeaturePermission(origin, feature, QWebEnginePage.PermissionGrantedByUser)
        else:
            # 其他权限透传给父类处理
            try:
                super().featurePermissionRequested.emit(origin, feature)
            except:
                pass

# 自定义WebView，处理新窗口请求
class CustomWebView(QWebEngineView):
    def __init__(self, browser_window, parent=None):
        super().__init__(parent)
        self.browser_window = browser_window
        # 替换为自定义WebPage，自动授权剪贴板+导航拦截，传入浏览器实例和当前webview
        self.setPage(CustomWebPage(self.browser_window, self, self))
    def contextMenuEvent(self, event):
        # 自定义中文原生右键菜单，100%调用系统原生接口，功能完整无需翻译包
        menu = QMenu(self)
        
        # 编辑类操作（原生功能）
        select_all_action = QAction("📝 全选", self)
        select_all_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.SelectAll))
        menu.addAction(select_all_action)
        
        copy_action = QAction("📋 复制", self)
        copy_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Copy))
        menu.addAction(copy_action)
        
        cut_action = QAction("✂️ 剪切", self)
        cut_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Cut))
        menu.addAction(cut_action)
        
        paste_action = QAction("📄 粘贴", self)
        paste_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Paste))
        menu.addAction(paste_action)
        
        menu.addSeparator()
        
        # 浏览器操作（原生功能，自动根据历史记录判断是否可用）
        back_action = QAction("⏪ 后退", self)
        back_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Back))
        menu.addAction(back_action)
        
        forward_action = QAction("⏩ 前进", self)
        forward_action.triggered.connect(lambda: self.page().triggerAction(QWebEnginePage.WebAction.Forward))
        menu.addAction(forward_action)
        
        reload_action = QAction("🔄 刷新页面", self)
        reload_action.triggered.connect(lambda: self.reload())
        menu.addAction(reload_action)
        
        inspect_action = QAction("🔍 检查元素", self)
        inspect_action.triggered.connect(lambda: self.page().setDevToolsPage(self.page().createWindow(QWebEnginePage.WebWindowType.WebBrowserTab)))
        menu.addAction(inspect_action)
        
        menu.addSeparator()
        
        # 显示菜单
        menu.exec(event.globalPos())

    def createWindow(self, window_type):
        new_view = CustomWebView(self.browser_window)
        # 绑定信号
        new_view.titleChanged.connect(lambda title, view=new_view: self.browser_window.update_tab_title(view, title))
        new_view.urlChanged.connect(lambda url, view=new_view: self.browser_window.update_address_bar(view, url))
        new_view.loadProgress.connect(lambda progress: self.browser_window.status_bar.showMessage(f"加载中... {progress}%") if progress < 100 else self.browser_window.status_bar.clearMessage())
        # 绑定新窗口的下载信号
        new_view.page().profile().downloadRequested.connect(self.browser_window.handle_download_request)
        # 添加到标签页
        index = self.browser_window.tab_widget.addTab(new_view, "加载中...")
        self.browser_window.tab_widget.setCurrentIndex(index)
        return new_view

class AIBrowserWindow(QMainWindow):
    """主浏览器窗口"""
    def __init__(self, home_url="http://localhost:8000/chat", auto_open_home=True, show_immediately=True, parent=None):
        super().__init__(parent)
        # 启动开关参数绑定为实例属性，全类可访问
        self.auto_open_home = auto_open_home
        self.show_immediately = show_immediately
        # 全局页面去重记录
        self.opened_pages = dict()
        # open_page调用互斥锁，防止并发调用导致去重失效（线程安全版）
        self._open_page_lock = threading.Lock()
        # 动态首页/根地址，适配自动端口
        from urllib.parse import urlparse
        parsed_url = urlparse(home_url)
        self.home_url = home_url
        self.root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        # 默认下载路径
        self.default_download_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        # 收藏夹配置
        self.favorites_file = "browser_favorites.json"
        self.favorites = self.load_favorites()
        
        # ========== Cookie自动复用配置 ==========
        self.cookie_storage = COOKIE_STORAGE_FILE
        # 加载已加密保存的Cookie
        if os.path.exists(self.cookie_storage):
            try:
                with open(self.cookie_storage, "r", encoding="utf-8") as f:
                    encrypted_content = f.read().strip()
                    self.saved_cookies = _decrypt_cookie_data(encrypted_content)
            except:
                self.saved_cookies = {}
        else:
            self.saved_cookies = {}
        # 全局Cookie存储实例
        from PySide6.QtWebEngineCore import QWebEngineCookieStore
        from PySide6.QtNetwork import QNetworkCookie
        self.QNetworkCookie = QNetworkCookie
        self.cookie_store = None # 延迟初始化，避免悬空指针
        self._cookie_initialized = False # 初始化标记，避免重复绑定
        # ========== 结束Cookie配置 ==========
        
        self.init_window()
        self.init_ui()
        self.refresh_favorites_menu()

    def init_window(self):
        self.setWindowTitle("AI智能助手桌面软件 V1.0")
        self.setGeometry(100, 100, 1200, 800)
        # 设置窗口图标可自定义
        self.setWindowIcon(QIcon("icon.png"))

    def init_ui(self):
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 导航工具栏
        nav_toolbar = QToolBar()
        nav_toolbar.setMovable(False)
        self.addToolBar(nav_toolbar)

        # 导航按钮
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(40)
        self.back_btn.clicked.connect(self.go_back)
        nav_toolbar.addWidget(self.back_btn)

        self.forward_btn = QPushButton("→")
        self.forward_btn.setFixedWidth(40)
        self.forward_btn.clicked.connect(self.go_forward)
        nav_toolbar.addWidget(self.forward_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(self.refresh_page)
        nav_toolbar.addWidget(self.refresh_btn)

        self.home_btn = QPushButton("🏠")
        self.home_btn.setFixedWidth(40)
        self.home_btn.clicked.connect(self.go_home)
        nav_toolbar.addWidget(self.home_btn)

        # 收藏按钮
        self.favorite_btn = QPushButton("⭐️")
        self.favorite_btn.setFixedWidth(40)
        self.favorite_btn.clicked.connect(self.add_current_to_favorites)
        nav_toolbar.addWidget(self.favorite_btn)

        # 收藏夹菜单按钮
        self.favorites_menu_btn = QPushButton("📑 收藏夹")
        self.favorites_menu_btn.setFixedWidth(80)
        self.favorites_menu = QMenu()
        self.favorites_menu_btn.setMenu(self.favorites_menu)
        nav_toolbar.addWidget(self.favorites_menu_btn)

        # 地址栏
        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.load_address)
        nav_toolbar.addWidget(self.address_bar)

        # 新建标签页按钮
        self.new_tab_btn = QPushButton("+ 新标签页")
        self.new_tab_btn.setFixedWidth(100)
        self.new_tab_btn.clicked.connect(lambda: self.add_new_tab(QUrl("https://www.bing.com"), "新标签页"))
        nav_toolbar.addWidget(self.new_tab_btn)

        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.current_tab_changed)
        main_layout.addWidget(self.tab_widget)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        # ========== 下载功能初始化 ==========
        # 状态栏下载进度条，默认隐藏
        self.download_progress = QProgressBar()
        self.download_progress.setMaximumWidth(200)
        self.download_progress.hide()
        self.status_bar.addPermanentWidget(self.download_progress)
        # 下载状态标签
        self.download_label = QLabel(" ")
        self.status_bar.addPermanentWidget(self.download_label)
        # 多下载任务进度存储，避免并发下载混乱
        self.download_progress_data = {}
        # 下载请求去重集合，避免重复绑定导致的重复任务
        self.processed_downloads = set()
        # ========== 全局唯一绑定下载请求 + 大文件专属优化（无空指针风险） ==========
        from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
        default_profile = QWebEngineProfile.defaultProfile()
        # 大文件优化配置
        default_profile.setHttpCacheMaximumSize(64 * 1024 * 1024) # 缓冲区升级到64MB，大文件写入流畅不卡顿
        default_profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies) # 持久化Cookie，自动适配防盗链校验
        default_profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache) # 缓存到磁盘，不占内存避免被系统强制中断
        default_profile.settings().setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True) # 兼容HTTP/自签名证书站点大文件
        default_profile.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True) # 开启本地存储避免会话过期
        # 绑定下载信号（仅绑定一次，无重复触发）
        default_profile.downloadRequested.connect(self.handle_download_request)

        # ========== 下载配置和管理面板初始化 ==========
        # 加载配置:统一从全局config.json读取，自动迁移旧配置
        self.config = self.load_config()
        # 优先使用全局配置的download_path，不存在则fallback到系统默认下载目录
        global_download_path = self.config.get("download_path", "")
        if global_download_path and os.path.exists(global_download_path):
            self.default_download_path = global_download_path
        else:
            self.default_download_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        # 初始化时同步设置Qt WebEngine内核的下载路径，确保首次启动就使用配置路径
        default_profile.setDownloadPath(self.default_download_path)
        # 下载管理面板
        self.download_manager = DownloadManagerDialog(self)
        # 工具栏新增下载管理按钮
        self.download_manager_btn = QPushButton("📥 下载管理")
        self.download_manager_btn.clicked.connect(self.download_manager.show)
        nav_toolbar.addWidget(self.download_manager_btn)

        # 初始化默认打开首页（AI助手本地聊天页）
        if self.auto_open_home:
            self.add_new_tab(QUrl(self.home_url), "AI助手主页", page_id="main")
        # 强制显示窗口，置顶避免被控制台遮挡
        if self.show_immediately:
            self.show()
            self.activateWindow()
        # 移除初始化默认创建的空白标签
        self.tab_widget.removeTab(0)
        # 启动阶段标记：仅启动后3秒内生效，防止重复开工作台
        self.is_launch_stage = True
        # 5秒后自动关闭启动阶段拦截，恢复正常多标签功能
        QTimer.singleShot(5000, lambda: setattr(self, 'is_launch_stage', False))
        
    def _get_global_config_path(self):
        """获取全局config.json的绝对路径，自动适配开发/打包环境"""
        if getattr(sys, 'frozen', False):
            # 打包后EXE同级目录
            return os.path.join(os.path.dirname(sys.executable), "config.json")
        else:
            # 开发环境项目根目录
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    def load_config(self):
        """加载配置:优先读取全局config.json，自动迁移旧的browser_config.json配置"""
        global_config_path = self._get_global_config_path()
        # 旧配置迁移:如果存在旧的browser_config.json，自动迁移到全局配置
        old_config_path = "browser_config.json"
        if os.path.exists(old_config_path):
            try:
                with open(old_config_path, "r", encoding="utf-8") as f:
                    old_config = json.load(f)
                old_download_path = old_config.get("default_download_path", "")
                # 旧配置有有效路径且全局配置没有时，自动迁移
                if old_download_path and os.path.exists(old_download_path):
                    if os.path.exists(global_config_path):
                        with open(global_config_path, "r", encoding="utf-8") as f:
                            global_config = json.load(f)
                        if not global_config.get("download_path"):
                            global_config["download_path"] = old_download_path
                            with open(global_config_path, "w", encoding="utf-8") as f:
                                json.dump(global_config, f, ensure_ascii=False, indent=4)
                            print(f"✅ 已自动迁移旧浏览器下载路径配置到全局配置: {old_download_path}")
                # 迁移完成删除旧配置文件
                os.remove(old_config_path)
                print(f"✅ 已删除冗余的旧配置文件: {old_config_path}")
            except Exception as e:
                print(f"⚠️ 旧配置迁移失败: {str(e)}")
        
        # 读取全局配置
        config = {}
        if os.path.exists(global_config_path):
            try:
                with open(global_config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except:
                pass
        return config
    
    def save_config(self):
        """保存配置:直接写入全局config.json，不再生成独立的browser_config.json"""
        global_config_path = self._get_global_config_path()
        try:
            # 读取现有全局配置
            if os.path.exists(global_config_path):
                with open(global_config_path, "r", encoding="utf-8") as f:
                    global_config = json.load(f)
            else:
                global_config = {}
            # 更新下载路径字段
            if "download_path" in self.config:
                global_config["download_path"] = self.config["download_path"]
            # 写入全局配置
            with open(global_config_path, "w", encoding="utf-8") as f:
                json.dump(global_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ 保存全局配置失败: {str(e)}")
    
    def set_default_download_path(self):
        """设置默认下载路径，直接写入全局config.json"""
        path = QFileDialog.getExistingDirectory(self, "选择默认下载文件夹", self.default_download_path)
        if path:
            self.default_download_path = path
            self.config["download_path"] = path
            self.save_config()
            QMessageBox.information(self, "提示", f"默认下载路径已设置为:\n{path}")
    
    @Slot(str)
    def update_download_path(self, new_path: str):
        """
        对外提供的实时更新下载路径接口，供API层调用，无需重启立即生效
        :param new_path: 新的下载目录绝对路径
        """
        if not new_path or not os.path.exists(new_path):
            return False, "路径不存在或无效"
        # 更新内存中的路径，立即生效，后续下载自动使用新路径
        self.default_download_path = new_path
        self.config["download_path"] = new_path
        self.save_config()
        # 同步更新Qt WebEngine内核的下载路径，确保内核实际使用新路径
        self.page().profile().setDownloadPath(new_path)
        print(f"? 下载路径已实时更新为: {new_path}")
        return True, "下载路径更新成功，即时生效"

    def add_new_tab(self, url, title="新标签页", page_id=None):
        """新建标签页，page_id不为空时启用去重逻辑"""
        # 终极兜底：仅启动阶段拦截多开，启动结束后恢复正常新建标签能力
        if self.is_launch_stage and self.tab_widget.count() >= 1:
            self.tab_widget.setCurrentIndex(0)
            return self.tab_widget.currentWidget()
        # 页面去重判断
        if page_id and page_id in self.opened_pages:
                # 激活已有标签页
                index = self.tab_widget.indexOf(self.opened_pages[page_id])
                if index >= 0:
                    # 页面已存在，仅切换到该标签，不执行任何加载/打开操作，直接返回
                    self.tab_widget.setCurrentIndex(index)
                    return self.opened_pages[page_id]
                else:
                    # 索引失效，销毁旧的无效实例，避免静默运行冲突
                    self.opened_pages[page_id].deleteLater()
                    self.opened_pages.pop(page_id, None)

        # 新建自定义WebView，支持新窗口打开
        web_view = CustomWebView(self)

        # 【修复时序问题】提前记录去重映射，保证加载url时拦截逻辑已经能识别到工作台
        if page_id:
            self.opened_pages[page_id] = web_view
            # 标签页关闭时清除记录
            web_view.destroyed.connect(lambda pid=page_id: self.opened_pages.pop(pid, None))
        
        # 自动注入该域名已保存的登录态Cookie，跳过登录验证
        target_domain = url.host().strip('.')
        if target_domain:
            self._load_saved_cookies_for_domain(target_domain, url)

        web_view.load(url)
        # 【修复时序问题】第一个页面加载完成后初始化CookieStore，确保Profile完全就绪
        if not self._cookie_initialized:
            def init_cookie_after_load(ok):
                if ok and not self._cookie_initialized:
                    self.cookie_store = QWebEngineProfile.defaultProfile().cookieStore()
                    # 绑定Cookie变更自动保存
                    self.cookie_store.cookieAdded.connect(self._on_cookie_changed)
                    self.cookie_store.cookieRemoved.connect(self._on_cookie_changed)
                    self._cookie_initialized = True
            web_view.loadFinished.connect(init_cookie_after_load)
        # 工作台页面绑定自动刷新兜底逻辑
        if page_id == "workbench":
            web_view.loadFinished.connect(lambda ok: self._auto_refresh_blank_workbench(web_view, ok))
        web_view.load(url)
        # 工作台页面绑定自动刷新兜底逻辑
        if page_id == "workbench":
            web_view.loadFinished.connect(lambda ok: self._auto_refresh_blank_workbench(web_view, ok))

        # 绑定页面信号
        web_view.titleChanged.connect(lambda title, view=web_view: self.update_tab_title(view, title))
        web_view.urlChanged.connect(lambda url, view=web_view: self.update_address_bar(view, url))
        web_view.loadProgress.connect(lambda progress: self.status_bar.showMessage(f"加载中... {progress}%") if progress < 100 else self.status_bar.clearMessage())
        # 绑定下载信号
        web_view.page().profile().downloadRequested.connect(self.handle_download_request)

        # 添加到标签页
        index = self.tab_widget.addTab(web_view, title)
        self.tab_widget.setCurrentIndex(index)

        return web_view

    def open_page(self, url, page_id=None, title=None):
        """对外提供的打开页面统一入口，完全符合要求的执行流程：调出浏览器→检查页面→存在则停止，不存在则打开"""
        # 线程安全互斥锁：非阻塞抢锁，抢不到直接返回，彻底避免并发去重失效
        if not self._open_page_lock.acquire(blocking=False):
            return
        try:
            # 第一步：强制调出浏览器到前台，不管任何状态都先执行
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
            self.show()
            self.raise_()
            self.activateWindow()
            
            # 第二步：双重校验页面是否存在，彻底解决判断失效问题+优先选加载成功的页面
            if page_id and page_id in self.opened_pages:
                index = self.tab_widget.indexOf(self.opened_pages[page_id])
                if index >= 0:
                    # 校验页面是否正常加载，排除空白页
                    existing_view = self.opened_pages[page_id]
                    page_url = existing_view.url().toString()
                    # 如果是空白页，销毁旧实例，重新打开
                    if page_url == "about:blank" or page_url.startswith("data:text/html,"):
                        existing_view.deleteLater()
                        self.opened_pages.pop(page_id, None)
                        self.tab_widget.removeTab(index)
                    else:
                        # 正常页面直接切换
                        self.tab_widget.setCurrentIndex(index)
                        return existing_view
            # 第三步:页面不存在才执行新建打开操作
            if not title:
                title = page_id if page_id else "新页面"
            web_view = self.add_new_tab(QUrl(url), title, page_id)
            return web_view
        finally:
            # 立即释放锁，线程安全锁无死锁风险
            self._open_page_lock.release()

    # 工作台专属打开方法：复用open_page全链路锁+去重逻辑，彻底解决并发重复创建问题
    def open_ai_workbench(self):
        self.open_page(f"{self.root_url}/workspace", page_id="workbench", title="AI工作台")
    def _auto_refresh_blank_workbench(self, web_view, load_ok):
        """工作台页面空白自动刷新兜底，最多重试3次，避免无限刷新"""
        # 仅处理工作台页面
        if "workbench" not in self.opened_pages or web_view != self.opened_pages["workbench"]:
            return
        # 初始化刷新计数器
        if not hasattr(web_view, "_refresh_count"):
            web_view._refresh_count = 0
        # 加载失败/空白页判断：加载失败 或者 页面内容为空/是about:blank
        page_url = web_view.url().toString()
        is_blank = not load_ok or page_url == "about:blank" or page_url.startswith("data:text/html,")
        if is_blank and web_view._refresh_count < 3:
            web_view._refresh_count +=1
            # 延迟100ms刷新，避免服务未就绪
            QTimer.singleShot(100, web_view.reload)
            self.status_bar.showMessage(f"工作台加载失败，自动重试第{web_view._refresh_count}次...")
        elif not is_blank:
            # 加载成功，重置计数器
            web_view._refresh_count = 0

    def close_tab(self, index):
        """关闭标签页"""
        web_view = self.tab_widget.widget(index)
        if self.tab_widget.tabText(index).strip() == "AI工作台":
            return
        if self.tab_widget.count() <= 1:
            QMessageBox.warning(self, "提示", "至少保留一个标签页")
            return
        self.tab_widget.removeTab(index)
        web_view.deleteLater()

    def current_tab_changed(self, index):
        """当前标签页切换时更新地址栏"""
        web_view = self.tab_widget.currentWidget()
        if web_view:
            self.address_bar.setText(web_view.url().toString())

    def update_tab_title(self, web_view, title):
        """更新标签页标题"""
        index = self.tab_widget.indexOf(web_view)
        if index >= 0:
            # 固定工作台标题，不允许页面修改
            if "workbench" in self.opened_pages and web_view == self.opened_pages["workbench"]:
                self.tab_widget.setTabText(index, "AI工作台")
            else:
                self.tab_widget.setTabText(index, title)

    def update_address_bar(self, web_view, url):
        """更新地址栏"""
        if web_view == self.tab_widget.currentWidget():
            self.address_bar.setText(url.toString())

    def load_address(self):
        """加载地址栏输入的地址"""
        url = self.address_bar.text().strip()
        if not url:
            return
        # 自动补全http
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        self.tab_widget.currentWidget().load(QUrl(url))

    def go_back(self):
        """后退"""
        self.tab_widget.currentWidget().back()

    def go_forward(self):
        """前进"""
        self.tab_widget.currentWidget().forward()

    def refresh_page(self):
        """刷新"""
        self.tab_widget.currentWidget().reload()

    def go_home(self):
        """回到首页"""
        self.open_page(self.root_url, page_id="main", title="AI助手主页")
    @Slot(str)
    def open_new_tab(self, url: str):
        """
        线程安全的新建标签页打开URL接口，自动运行在UI主线程
        :param url: 要打开的网页地址
        """
        from PySide6.QtCore import QUrl
        
        target_url = QUrl(url)
        # 优先复用同域名已打开的标签页，避免重复开卡
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, "url") and tab.url().host() == target_url.host():
                self.tab_widget.setCurrentIndex(i)
                tab.load(target_url)
                return
        # 无复用标签则新建
        new_webview = CustomWebView(self)
        new_webview.load(target_url)
        # 标签标题随页面自动更新
        new_webview.titleChanged.connect(
            lambda title, idx=self.tab_widget.count(): 
                self.tab_widget.setTabText(idx, title if len(title) < 15 else title[:15] + "...")
        )
        tab_index = self.tab_widget.addTab(new_webview, "加载中...")
        self.tab_widget.setCurrentIndex(tab_index)
        
    def load_favorites(self):
        """加载本地收藏夹"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_favorites(self):
        """保存收藏夹到本地"""
        with open(self.favorites_file, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def refresh_favorites_menu(self):
        """刷新收藏夹菜单"""
        self.favorites_menu.clear()
        if not self.favorites:
            self.favorites_menu.addAction("暂无收藏")
            return
        for idx, fav in enumerate(self.favorites):
            # 改用二级子菜单实现打开+删除功能，兼容所有PySide6版本
            fav_submenu = QMenu(fav["title"], self.favorites_menu)
            # 打开链接选项
            open_action = fav_submenu.addAction("🔗 打开链接")
            open_action.triggered.connect(lambda *args, url=fav["url"]: self.open_page(url))
            # 删除收藏选项
            delete_action = fav_submenu.addAction("🗑️ 删除收藏")
            delete_action.triggered.connect(lambda *args, del_idx=idx: self.delete_single_favorite(del_idx))
            # 添加到收藏夹主菜单
            self.favorites_menu.addMenu(fav_submenu)
        # 添加管理选项
        self.favorites_menu.addSeparator()
        clear_action = self.favorites_menu.addAction("🗑️ 清空收藏夹")
        clear_action.triggered.connect(self.clear_favorites)

    def add_current_to_favorites(self):
        """收藏当前页面"""
        current_webview = self.tab_widget.currentWidget()
        if not current_webview:
            return
        url = current_webview.url().toString()
        title = self.tab_widget.tabText(self.tab_widget.currentIndex())
        # 去重
        for fav in self.favorites:
            if fav["url"] == url:
                QMessageBox.information(self, "提示", "该页面已在收藏夹中")
                return
        self.favorites.append({"url": url, "title": title})
        self.save_favorites()
        self.refresh_favorites_menu()
        QMessageBox.information(self, "提示", "收藏成功")

    def clear_favorites(self):
        """清空收藏夹"""
        confirm = QMessageBox.question(self, "确认", "确定要清空所有收藏吗？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            self.favorites = []
            self.save_favorites()
            self.refresh_favorites_menu()
            QMessageBox.information(self, "提示", "收藏夹已清空")
    def delete_single_favorite(self, idx):
        """删除单个收藏"""
        if idx <0 or idx >= len(self.favorites):
            return
        fav_title = self.favorites[idx]["title"]
        confirm = QMessageBox.question(self, "确认删除", f"确定要删除收藏「{fav_title}」吗？", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            del self.favorites[idx]
            self.save_favorites()
            self.refresh_favorites_menu()
            QMessageBox.information(self, "提示", "删除成功")
    def _on_cookie_changed(self, cookie):
        """Cookie变更时自动加密保存到本地"""
        try:
            # 空校验，避免访问已释放对象
            if not self.cookie_store or not self._cookie_initialized:
                return
            domain = cookie.domain().strip('.')
            if not domain:
                return
            # 初始化域名存储
            if domain not in self.saved_cookies:
                self.saved_cookies[domain] = []
            # 转换Cookie为可序列化格式
            cookie_data = {
                "name": cookie.name().data().decode("utf-8"),
                "value": cookie.value().data().decode("utf-8"),
                "domain": cookie.domain(),
                "path": cookie.path(),
                "expires": cookie.expirationDate().toString(Qt.ISODate) if cookie.expirationDate().isValid() else None,
                "secure": cookie.isSecure(),
                "httpOnly": cookie.isHttpOnly()
            }
            # 去重:删除同域名同名旧Cookie
            self.saved_cookies[domain] = [c for c in self.saved_cookies[domain] if c["name"] != cookie_data["name"]]
            # 新增新Cookie
            self.saved_cookies[domain].append(cookie_data)
            # 加密保存到本地
            encrypted_data = _encrypt_cookie_data(self.saved_cookies)
            with open(self.cookie_storage, "w", encoding="utf-8") as f:
                f.write(encrypted_data)
        except Exception as e:
            # Cookie保存失败不影响主流程，静默忽略
            pass

    def _load_saved_cookies_for_domain(self, domain: str, target_url: QUrl):
        """打开指定域名时自动注入已保存的登录态Cookie"""
        try:
            if domain not in self.saved_cookies or not self.saved_cookies[domain]:
                return
            # 遍历该域名所有保存的Cookie，注入到CookieStore
            for cookie_data in self.saved_cookies[domain]:
                # 跳过已过期的Cookie
                if cookie_data.get("expires"):
                    from PySide6.QtCore import QDateTime
                    expires = QDateTime.fromString(cookie_data["expires"], Qt.ISODate)
                    if expires.isValid() and expires < QDateTime.currentDateTime():
                        continue
                # 构造Cookie对象
                cookie = self.QNetworkCookie(
                    cookie_data["name"].encode("utf-8"),
                    cookie_data["value"].encode("utf-8")
                )
                cookie.setDomain(cookie_data["domain"])
                cookie.setPath(cookie_data["path"])
                if cookie_data.get("secure"):
                    cookie.setSecure(cookie_data["secure"])
                if cookie_data.get("httpOnly"):
                    cookie.setHttpOnly(cookie_data["httpOnly"])
                if cookie_data.get("expires"):
                    expires = QDateTime.fromString(cookie_data["expires"], Qt.ISODate)
                    if expires.isValid():
                        cookie.setExpirationDate(expires)
                # 注入Cookie
                self.cookie_store.setCookie(cookie, target_url)
        except Exception as e:
            # Cookie注入失败不影响主流程，静默忽略
            pass
    # ========== 下载功能核心实现 ==========
    def handle_download_request(self, download_item):
        """处理所有下载请求（适配PySide6 6.7+ 最新版API，100%兼容所有场景）"""
        # 🔴 去重逻辑：同一个下载请求只处理一次
        download_uid = id(download_item)
        if download_uid in self.processed_downloads:
            return
        self.processed_downloads.add(download_uid)
        # 优先使用用户自定义的下载路径
        download_dir = self.default_download_path
        file_name = download_item.suggestedFileName()
        save_path = os.path.join(download_dir, file_name)
        
        # 重名文件自动加后缀避免覆盖
        counter = 1
        while os.path.exists(save_path):
            name, ext = os.path.splitext(file_name)
            save_path = os.path.join(download_dir, f"{name}({counter}){ext}")
            counter += 1
        final_dir, final_name = os.path.split(save_path)
        
        # 【适配新版：仅未被accept的请求才允许设置路径】
        if download_item.state() == QWebEngineDownloadRequest.DownloadRequested:
            download_item.setDownloadDirectory(final_dir)
            download_item.setDownloadFileName(final_name)
            download_item.accept()
        else:
            # 已经被自动accept的请求，直接使用已有的路径
            final_name = download_item.downloadFileName()
        
        # 初始化当前下载项的进度数据
        self.download_progress_data[download_item] = {
            "received": 0,
            "total": 0,
            "file_name": final_name,
            "save_path": save_path
        }
        # 新增任务到下载管理面板
        self.download_manager.add_task(download_item, final_name)
        
        # 绑定最新版下载信号
        download_item.receivedBytesChanged.connect(lambda: self.update_download_progress(download_item))
        download_item.totalBytesChanged.connect(lambda: self.update_download_progress(download_item))
        download_item.stateChanged.connect(lambda state: self.download_state_changed(state, download_item))
        
        # 显示下载提示
        self.download_label.setText(f"准备下载：{final_name}")
        self.download_progress.show()
    
    def update_download_progress(self, download_item):
        """实时更新下载进度（适配新版API，解决大文件卡0%问题）"""
        if download_item not in self.download_progress_data:
            return
        # 获取最新进度
        data = self.download_progress_data[download_item]
        data["received"] = download_item.receivedBytes()
        data["total"] = download_item.totalBytes()
        speed = data["received"] / (1024 * 1024) if data["received"] > 0 else 0
        
        if data["total"] > 0:
            percent = int(data["received"] / data["total"] * 100)
            self.download_progress.setValue(percent)
            self.download_label.setText(f"下载中：{data['file_name']} {percent}% ({speed:.1f}MB/s)")
            # 同步更新下载管理面板
            self.download_manager.update_task_progress(download_item, percent, speed, data["save_path"])
        else:
            # 未获取到总大小（大文件场景），显示已下载大小，不卡0%
            received_mb = data["received"] / (1024 * 1024)
            self.download_progress.setRange(0, 0) # 滚动进度条
            self.download_label.setText(f"下载中：{data['file_name']} 已下载{received_mb:.1f}MB ({speed:.1f}MB/s)")
            # 同步更新面板
            if download_item in self.download_manager.tasks:
                self.download_manager.tasks[download_item]["info_label"].setText(f"📄 {data['file_name']}\n⏳ 下载中... 已下载{received_mb:.1f}MB ({speed:.1f}MB/s)")
    
    def download_finished(self, download_item):
        """下载完成处理"""
        if download_item not in self.download_progress_data:
            return
        data = self.download_progress_data[download_item]
        save_path = os.path.join(download_item.downloadDirectory(), data["file_name"])
        
        self.download_label.setText(f"下载完成：{data['file_name']}")
        # 操作提示弹窗
        msg = QMessageBox(self)
        msg.setWindowTitle("✅ 下载完成")
        msg.setText(f"文件已保存到：\n{save_path}")
        open_file_btn = msg.addButton("📂 打开文件", QMessageBox.ActionRole)
        open_folder_btn = msg.addButton("📁 打开所在文件夹", QMessageBox.ActionRole)
        msg.addButton("确定", QMessageBox.AcceptRole)
        msg.exec()
        
        # 响应用户操作
        if msg.clickedButton() == open_file_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(save_path))
        elif msg.clickedButton() == open_folder_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(save_path)))
        
        # 清理进度数据
        del self.download_progress_data[download_item]
        
        # 重置进度UI
        self.download_progress.hide()
        self.download_progress.setValue(0)
        # 3秒后清除提示
        from threading import Timer
        Timer(3, lambda: self.download_label.setText(" ")).start()
    
    def download_state_changed(self, state, download_item):
        """下载状态变更处理（适配新版独立枚举）"""
        download_uid = id(download_item)
        if state == QWebEngineDownloadRequest.DownloadCompleted:
            # 下载完成，调用完成处理逻辑
            self.download_finished(download_item)
            # 标记任务完成
            self.download_manager.mark_task_finished(download_item, success=True)
            # 重置进度UI
            self.download_progress.hide()
            self.download_progress.setValue(0)
            # 3秒后清除提示
            from threading import Timer
            Timer(3, lambda: self.download_label.setText(" ")).start()
            # 清理去重标记
            if download_uid in self.processed_downloads:
                self.processed_downloads.remove(download_uid)
        elif state == QWebEngineDownloadRequest.DownloadCancelled or state == QWebEngineDownloadRequest.DownloadInterrupted:
            self.download_label.setText("❌ 下载已取消/失败")
            # 标记任务失败
            self.download_manager.mark_task_finished(download_item, success=False)
            self.download_progress.hide()
            self.download_progress.setValue(0)
            # 清理进度数据
            if download_item in self.download_progress_data:
                del self.download_progress_data[download_item]
            # 清理去重标记
            if download_uid in self.processed_downloads:
                self.processed_downloads.remove(download_uid)
            from threading import Timer
            Timer(2, lambda: self.download_label.setText(" ")).start()

    # ========== AI自动化操作API接口 ==========
    def run_js_sync(self, script: str, timeout_ms: int = 5000) -> str:
        """
        同步执行JavaScript并返回结果（基于QEventLoop阻塞等待回调）
        :param script: 要执行的JavaScript代码
        :param timeout_ms: 超时时间（毫秒），默认5秒
        :return: JavaScript执行结果（字符串形式）
        """
        from PySide6.QtCore import QEventLoop, QTimer
        
        current_view = self.tab_widget.currentWidget()
        if not current_view:
            return ""
            
        loop = QEventLoop()
        result_container = {"value": ""}
        
        def js_callback(result):
            if result is not None:
                result_container["value"] = str(result)
            loop.quit()
            
        current_view.page().runJavaScript(script, js_callback)
        
        # 设置超时定时器，防止页面无响应导致无限阻塞
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        timer.start(timeout_ms)
        
        loop.exec()
        timer.stop()
        return result_container["value"]

    def get_page_html(self) -> str:
        """获取当前页面的完整HTML源码"""
        script = "document.documentElement.outerHTML"
        return self.run_js_sync(script)

    def get_page_text(self) -> str:
        """获取当前页面的纯文本内容"""
        script = "document.body.innerText"
        return self.run_js_sync(script)

    def execute_action(self, action_type: str, selector: str, value: str = None) -> str:
        """
        统一执行操作接口，支持点击、输入、滚动等行为
        :param action_type: 操作类型 (click/input/scroll)
        :param selector: CSS选择器
        :param value: 输入内容或滚动距离
        :return: 操作结果状态
        """
        if action_type == "click":
            script = f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    if (el) {{
                        el.click();
                        return 'success';
                    }}
                    return 'element not found';
                }})();
            """
        elif action_type == "input":
            if value is None:
                return "input action requires 'value' parameter"
            # 转义单引号，防止JS语法错误
            safe_value = value.replace("'", "\\'")
            script = f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    if (el) {{
                        el.value = '{safe_value}';
                        // 触发input和change事件，兼容React/Vue等现代前端框架
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'success';
                    }}
                    return 'element not found';
                }})();
            """
        elif action_type == "scroll":
            distance = value if value else "window.innerHeight"
            script = f"window.scrollBy(0, {distance}); return 'scrolled';"
        else:
            return f"unsupported action type: {action_type}"
            
        return self.run_js_sync(script)
    # ========== 结束AI操作API接口 ==========

# 独立运行入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    browser = AIBrowserWindow()
    browser.show()
    sys.exit(app.exec())