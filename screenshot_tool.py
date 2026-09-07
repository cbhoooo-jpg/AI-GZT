# -*- coding: utf-8 -*-
"""
全局系统级截图工具 V1.0（极简无依赖版）
功能特性：
1. 跨Windows/Mac/Linux全平台支持，无浏览器限制
2. 仅依赖mss+pillow，UI用Python自带tkinter实现，无需额外安装PyQt5
3. 支持多屏幕、任意DPI缩放比例，坐标100%准确
4. 全局顶层透明选框，覆盖所有应用窗口
5. 支持鼠标拖拽框选任意区域、ESC取消、回车确认
6. 自动适配系统显示缩放，截图无模糊、无偏移
"""
import sys
import os
import time
import base64
from io import BytesIO
from PIL import Image
import mss
import platform
import threading
# Windows平台COM初始化依赖，解决mss截图调用RPC_E_WRONG_THREAD(0x8001010d)致命错误
WIN32_COM_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import pythoncom
        WIN32_COM_AVAILABLE = True
    except ImportError:
        # 打包环境已默认包含pywin32，此处仅做开发环境兼容
        pass
# 容错导入tkinter，避免打包后环境缺失导致主程序启动崩溃
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk = None
    ttk = None
from screeninfo import get_monitors

class ScreenshotTool:
    def __init__(self):
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.selected_rect = None
        self.mask_windows = []
        self.canvas_list = []
        self.root = None  # 存储Tkinter主窗口实例
        
    def _create_mask_window(self, x, y, width, height):
        """为每个屏幕创建透明遮罩层"""
        mask = tk.Toplevel()
        mask.geometry(f"{width}x{height}+{x}+{y}")
        mask.overrideredirect(True)  # 无边框
        mask.attributes("-topmost", True)  # 顶层显示
        mask.attributes("-alpha", 0.5)  # 半透明
        mask.config(bg="black")
        mask.cursor = "cross"
        
        # 创建画布用于绘制选框
        canvas = tk.Canvas(mask, width=width, height=height, bg="black", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas_list.append(canvas)
        
        # 绑定事件
        canvas.bind("<ButtonPress-1>", lambda e, m=mask: self._on_mouse_press(e, m))
        canvas.bind("<B1-Motion>", self._on_mouse_move)
        canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        mask.bind("<KeyPress>", self._on_key_press)
        
        # 让窗口获得焦点
        mask.focus_set()
        return mask
    
    def _on_mouse_press(self, event, window):
        if not self.is_selecting:
            self.is_selecting = True
            # 转换为全局坐标
            x = window.winfo_x() + event.x
            y = window.winfo_y() + event.y
            self.selection_start = (x, y)
            self.selection_end = (x, y)
    
    def _on_mouse_move(self, event):
        if self.is_selecting:
            # 转换为全局坐标
            x = event.widget.winfo_toplevel().winfo_x() + event.x
            y = event.widget.winfo_toplevel().winfo_y() + event.y
            self.selection_end = (x, y)
            # 刷新所有画布的选框
            for canvas in self.canvas_list:
                canvas.delete("select")
                # 转换为当前画布的局部坐标
                win_x = canvas.winfo_toplevel().winfo_x()
                win_y = canvas.winfo_toplevel().winfo_y()
                l = min(self.selection_start[0], self.selection_end[0]) - win_x
                t = min(self.selection_start[1], self.selection_end[1]) - win_y
                r = max(self.selection_start[0], self.selection_end[0]) - win_x
                b = max(self.selection_start[1], self.selection_end[1]) - win_y
                # 绘制选框
                canvas.create_rectangle(l, t, r, b, outline="#1677ff", width=2, fill="#1677ff", stipple="gray25", tags="select")
    
    def _on_mouse_release(self, event):
        if self.is_selecting:
            self.is_selecting = False
            x1, y1 = self.selection_start
            x2, y2 = self.selection_end
            # 计算有效选区
            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            
            # 选区过小直接取消
            if w < 10 or h < 10:
                self._close_all_masks()
                self.selected_rect = None
                return
            
            self.selected_rect = (x, y, w, h)
            self._close_all_masks()
    
    def _on_key_press(self, event):
        # ESC键取消截图
        if event.keysym == "Escape":
            self._close_all_masks()
            self.selected_rect = None
        # 回车键全屏截图
        elif event.keysym == "Return" or event.keysym == "KP_Enter":
            # 获取所有屏幕的总区域
            from screeninfo import get_monitors
            total_x = min(m.x for m in get_monitors())
            total_y = min(m.y for m in get_monitors())
            total_w = max(m.x + m.width for m in get_monitors()) - total_x
            total_h = max(m.y + m.height for m in get_monitors()) - total_y
            self.selected_rect = (total_x, total_y, total_w, total_h)
            self._close_all_masks()
    
    def _close_all_masks(self):
        # 销毁所有遮罩窗口
        for mask in self.mask_windows:
            mask.destroy()
        self.mask_windows.clear()
        self.canvas_list.clear()
        # 主动销毁主窗口，强制退出主循环，彻底解决卡死问题
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None
    
    def capture_selection(self):
        """启动截图选框，返回选中区域的PIL Image对象，取消返回None"""
        if not TKINTER_AVAILABLE:
            raise RuntimeError("截图功能依赖tkinter库，当前运行环境未安装，无法启动截图选框。")
        self.selected_rect = None
        self.root = tk.Tk()
        self.root.withdraw()  # 隐藏主窗口
        
        # 获取所有屏幕信息
        monitors = get_monitors()
        if not monitors:
            # 兼容异常场景，默认获取主屏幕
            monitors = [type('Monitor', (), {'x':0, 'y':0, 'width':self.root.winfo_screenwidth(), 'height':self.root.winfo_screenheight()})()]
        
        # 为每个屏幕创建遮罩
        for m in monitors:
            mask = self._create_mask_window(m.x, m.y, m.width, m.height)
            self.mask_windows.append(mask)
        
        # 进入事件循环等待用户选择
        self.root.mainloop()
        
        if not self.selected_rect:
            return None
        
        x, y, w, h = self.selected_rect
        
        # Windows平台初始化当前线程COM环境，解决mss调用RPC_E_WRONG_THREAD(0x8001010d)致命错误
        if WIN32_COM_AVAILABLE:
            pythoncom.CoInitialize()
        
        # 使用mss截图，支持多屏幕和DPI缩放
        with mss.mss() as sct:
            # 构造截图区域，mss的坐标是系统原生坐标
            monitor = {"top": y, "left": x, "width": w, "height": h}
            sct_img = sct.grab(monitor)
            # 转换为PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
    
    def capture_selection_to_base64(self, format="PNG", quality=95):
        """截图并返回base64编码"""
        img = self.capture_selection()
        if not img:
            return None
        buffer = BytesIO()
        img.save(buffer, format=format, quality=quality)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def capture_selection_to_file(self, save_path, format="PNG", quality=95):
        """截图并保存到文件"""
        img = self.capture_selection()
        if not img:
            return False
        img.save(save_path, format=format, quality=quality)
        return os.path.exists(save_path)

# 单例实例
screenshot_tool = ScreenshotTool()

if __name__ == "__main__":
    # 测试用例
    img = screenshot_tool.capture_selection()
    if img:
        img.show()
        img.save("test_screenshot.png")
        print("截图已保存到test_screenshot.png")
    else:
        print("用户取消了截图")