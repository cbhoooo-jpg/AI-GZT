# -*- coding: utf-8 -*-
"""
editor_app.py — 独立视频剪辑工具 · 图形界面
三个选项卡:视频裁剪 / 视频拼接 / 字幕配音。
所有耗时任务在后台线程执行,通过队列回传进度,界面全程不卡死。
依赖:tkinter(Python 自带) + 同目录 video_editor_core。
"""
import os
import queue
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

import video_editor_core as core

APP_TITLE = "独立视频剪辑工具 V1.0"
VIDEO_TYPES = [("视频文件", "*.mp4 *.mov *.mkv *.avi *.flv *.wmv *.m4v *.ts"),
               ("所有文件", "*.*")]


def human_size(num):
    """字节数转易读文本"""
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%.1f %s" % (num, unit)
        num /= 1024.0
    return "%.1f GB" % num


def fmt_duration(sec):
    """秒 -> HH:MM:SS"""
    sec = int(sec or 0)
    return "%02d:%02d:%02d" % (sec // 3600, sec % 3600 // 60, sec % 60)


def add_progress_area(parent):
    """构建 状态行+进度条+日志区,返回 (容器, 进度变量, 状态变量, 日志框)"""
    box = ttk.Frame(parent)
    status = tk.StringVar(value="就绪")
    ttk.Label(box, textvariable=status).pack(anchor="w")
    progress = tk.IntVar()
    ttk.Progressbar(box, variable=progress, maximum=100).pack(fill="x", pady=(2, 6))
    log = ScrolledText(box, height=7, font=("Consolas", 9), wrap="word")
    log.pack(fill="both", expand=True)
    return box, progress, status, log


class TaskRunner:
    """后台任务执行器:工作线程跑 ffmpeg,队列回传进度/结果/错误,UI 轮询刷新。"""

    def __init__(self, root, on_done):
        self.root = root
        self.on_done = on_done
        self.q = queue.Queue()
        self.busy_widgets = []

    def post(self, func, kwargs=None, busy_widgets=()):
        """启动一个后台任务,执行期间禁用相关按钮"""
        kwargs = dict(kwargs or {})
        self.busy_widgets = list(busy_widgets)
        for w in self.busy_widgets:
            w.configure(state="disabled")

        def worker():
            def progress_cb(stage, pct):
                self.q.put(("progress", stage, pct))
            try:
                kwargs["progress_cb"] = progress_cb
                result = func(**kwargs)
                self.q.put(("done", result))
            except core.EditorError as e:
                self.q.put(("error", str(e)))
            except Exception:
                self.q.put(("error", "程序异常:\n" + traceback.format_exc()[-500:]))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self, progress_var, status_var, log_box):
        """UI 定时轮询队列,刷新进度条/状态/日志"""
        try:
            while True:
                kind, *rest = self.q.get_nowait()
                if kind == "progress":
                    stage, pct = rest
                    progress_var.set(pct)
                    status_var.set("%s中... %d%%" % (stage, pct))
                elif kind == "done":
                    self._release()
                    progress_var.set(100)
                    status_var.set("完成")
                    self.on_done(rest[0], None)
                elif kind == "error":
                    self._release()
                    status_var.set("失败")
                    self.on_done(None, rest[0])
        except queue.Empty:
            pass
        self.root.after(120, lambda: self.poll(progress_var, status_var, log_box))

    def _release(self):
        """恢复被禁用的按钮"""
        for w in self.busy_widgets:
            try:
                w.configure(state="normal")
            except tk.TclError:
                pass
        self.busy_widgets = []


# ============================ 双滑块可视化时间轴 ============================

class RangeTimeline(tk.Canvas):
    """双滑块可视化时间轴:绿色手柄=保留起点、红色手柄=保留终点,两手柄之间
    高亮段即要保留的视频,灰色部分为裁掉的内容;在高亮段中部按住可整体平移。
    纯 tkinter Canvas 自绘,零新依赖;通过两个 StringVar 与输入框双向同步。"""

    HANDLE_W = 10      # 手柄宽度(像素)
    HANDLE_H = 20      # 手柄高度(像素)
    TRACK_Y = 42       # 轨道顶边纵坐标
    TRACK_H = 10       # 轨道高度
    MIN_GAP = 0.2      # 起点/终点最小间隔(秒)

    def __init__(self, master, start_var, end_var, on_change=None, height=104, **kw):
        super().__init__(master, height=height, highlightthickness=0, **kw)
        self.start_var = start_var
        self.end_var = end_var
        self.on_change = on_change
        self.duration = 0.0
        self.start_t = 0.0
        self.end_t = 0.0
        self._drag = None      # 'start' / 'end' / 'pan'
        self._pan_off = 0.0    # 平移按下时鼠标相对区间起点的秒偏移
        self._syncing = False  # 防止 变量->重绘->写变量 递归
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.start_var.trace_add("write", lambda *_a: self._from_vars())
        self.end_var.trace_add("write", lambda *_a: self._from_vars())

    def set_duration(self, duration):
        """导入视频后调用:设定总时长并把区间初始化为整片(0 -> 末尾)"""
        self.duration = max(0.0, float(duration))
        self.start_t, self.end_t = 0.0, self.duration
        self._write_vars()
        self._redraw()
        self._notify()

    # ---------- 坐标换算 / 刻度密度 ----------
    def _margins(self):
        return 36, 36  # 左右留白,容纳首尾刻度文字

    def _x_of(self, t):
        lm, rm = self._margins()
        w = max(1, self.winfo_width() - lm - rm)
        if self.duration <= 0:
            return lm
        return lm + t / self.duration * w

    def _t_of(self, x):
        lm, rm = self._margins()
        w = max(1, self.winfo_width() - lm - rm)
        return max(0.0, min(self.duration, (x - lm) / w * self.duration))

    def _tick_step(self):
        """刻度密度自适应:保证整轴约 6~12 个刻度,长视频自动切大间隔"""
        for step in (1, 2, 5, 10, 15, 30, 60, 120, 300, 600):
            if self.duration / step <= 12:
                return step
        return 600

    @staticmethod
    def _fmt_tick(t, long_fmt):
        m, s = divmod(int(round(t)), 60)
        if not long_fmt:
            return "%gs" % s if m == 0 else "%d:%02d" % (m, s)
        return "%d:%02d" % (m, s)

    @staticmethod
    def _fmt_bubble(t):
        """手柄上方时间气泡,精确到 0.1 秒"""
        m, s = divmod(t, 60)
        if m >= 1:
            return "%d:%04.1f" % (m, s)
        return "%.1f秒" % t
    # ---------- 绘制 ----------
    def _redraw(self):
        self.delete("all")
        if self.duration <= 0:
            self.create_text(self.winfo_width() / 2 if self.winfo_width() else 200, 50,
                             text="导入视频后,拖动滑块选择要保留的片段", fill="#999")
            return
        lm, rm = self._margins()
        x0, x1 = self._x_of(0), self._x_of(self.duration)
        ty = self.TRACK_Y
        # 底层灰轨(被裁掉的部分)
        self.create_rectangle(x0, ty, x1, ty + self.TRACK_H, fill="#d9d9d9", outline="")
        xs, xe = self._x_of(self.start_t), self._x_of(self.end_t)
        # 高亮保留段(绿色)
        self.create_rectangle(xs, ty, xe, ty + self.TRACK_H, fill="#67c23a", outline="")
        # 刻度 + 文字
        step = self._tick_step()
        long_fmt = self.duration >= 60
        t = 0.0
        while t <= self.duration + 1e-6:
            xt = self._x_of(min(t, self.duration))
            self.create_line(xt, ty + self.TRACK_H, xt, ty + self.TRACK_H + 5, fill="#888")
            self.create_text(xt, ty + self.TRACK_H + 17,
                             text=self._fmt_tick(min(t, self.duration), long_fmt),
                             fill="#666", font=("Microsoft YaHei", 8))
            t += step
        # 手柄(三角朝下,压在轨道上沿)
        self._draw_handle(xs, self.start_t, "#2f9e44", "起")
        self._draw_handle(xe, self.end_t, "#e03131", "止")
        # 手柄上方时间气泡
        self.create_text(xs, 12, text=self._fmt_bubble(self.start_t),
                         fill="#2f9e44", font=("Microsoft YaHei", 9, "bold"))
        self.create_text(xe, 12, text=self._fmt_bubble(self.end_t),
                         fill="#e03131", font=("Microsoft YaHei", 9, "bold"))

    def _draw_handle(self, x, t, color, tag):
        ty = self.TRACK_Y
        pts = [x - self.HANDLE_W / 2, ty - 2, x + self.HANDLE_W / 2, ty - 2, x, ty + self.TRACK_H + 4]
        self.create_polygon(pts, fill=color, outline="", tags=tag)

    # ---------- 鼠标交互 ----------
    def _on_press(self, event):
        if self.duration <= 0:
            return
        xs, xe = self._x_of(self.start_t), self._x_of(self.end_t)
        # 命中起点/终点手柄(放宽到 8px)
        if abs(event.x - xs) <= 8:
            self._drag = "start"
        elif abs(event.x - xe) <= 8:
            self._drag = "end"
        elif xs < event.x < xe:
            # 高亮段中部按下:整体平移
            self._drag = "pan"
            self._pan_off = self._t_of(event.x) - self.start_t
        else:
            # 点灰轨:移动最近的手柄
            self._drag = "start" if event.x < xs else "end"

    def _on_drag(self, event):
        if not self._drag or self.duration <= 0:
            return
        t = self._t_of(event.x)
        if self._drag == "start":
            self.start_t = min(t, self.end_t - self.MIN_GAP)
        elif self._drag == "end":
            self.end_t = max(t, self.start_t + self.MIN_GAP)
        else:  # pan:区间长度不变整体平移,到两端自动挡住
            span = self.end_t - self.start_t
            ns = t - self._pan_off
            ns = max(0.0, min(self.duration - span, ns))
            self.start_t, self.end_t = ns, ns + span
        self._write_vars()
        self._redraw()
        self._notify()

    def _on_release(self, _event):
        self._drag = None

    # ---------- 与输入框双向同步 ----------
    def _write_vars(self):
        """滑块 -> 输入框"""
        self._syncing = True
        try:
            self.start_var.set("%.3f" % round(self.start_t, 3))
            self.end_var.set("%.3f" % round(self.end_t, 3))
        finally:
            self._syncing = False

    def _from_vars(self):
        """输入框 -> 滑块(仅接受合法时间,非法输入等点导出时再报错)"""
        if self._syncing or self.duration <= 0:
            return
        try:
            s = core.parse_time(self.start_var.get())
            e = core.parse_time(self.end_var.get())
        except core.EditorError:
            return
        s = max(0.0, min(s, self.duration))
        e = max(0.0, min(e, self.duration))
        if e - s < self.MIN_GAP:
            return  # 不合法的中间态不刷新滑块,避免拖动输入时跳变
        self.start_t, self.end_t = s, e
        self._redraw()

    def _notify(self):
        if self.on_change:
            self.on_change(self.start_t, self.end_t)
# ============================ 选项卡一:视频裁剪 ============================

class TrimTab(ttk.Frame):
    """视频裁剪:快速流拷贝(秒出) / 精确重编码(帧级精确)"""

    def __init__(self, master, root):
        super().__init__(master, padding=10)
        self.root = root
        self.src = ""
        self.info = None
        self.out_path = ""
        self._build()
        self.runner = TaskRunner(root, self._on_done)
        self.after(150, self._poll)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="导入视频", command=self.choose_video).pack(side="left")
        ttk.Button(top, text="选择输出位置(可选)",
                   command=self.choose_output).pack(side="left", padx=6)
        self.info_var = tk.StringVar(value="尚未导入视频")
        ttk.Label(self, textvariable=self.info_var,
                  foreground="#555").pack(anchor="w", pady=(6, 8))

        form = ttk.LabelFrame(self, text="裁剪区间", padding=10)
        form.pack(fill="x")
        ttk.Label(form, text="开始时间:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.start_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.start_var, width=14).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="结束时间:").grid(row=0, column=2, sticky="e", padx=4)
        self.end_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.end_var, width=14).grid(row=0, column=3, sticky="w")
        ttk.Label(form, text="支持 40 / 1:23 / 00:01:23").grid(
            row=0, column=4, sticky="w", padx=8)
        self.mode_var = tk.StringVar(value="fast")
        ttk.Radiobutton(form, text="快速裁剪(流拷贝,秒出,切点对齐关键帧)",
                        variable=self.mode_var, value="fast").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))
        ttk.Radiobutton(form, text="精确裁剪(重编码,帧级精确,速度较慢)",
                        variable=self.mode_var, value="precise").grid(
            row=2, column=0, columnspan=4, sticky="w")
        self.out_var = tk.StringVar()
        ttk.Label(form, textvariable=self.out_var, foreground="#555").grid(
            row=3, column=0, columnspan=5, sticky="w", pady=(6, 0))

        # 可视化双滑块时间轴:绿/红手柄之间的高亮段即保留区间,
        # 与上方开始/结束输入框双向同步;在高亮段中部按住可整体平移
        tl_box = ttk.LabelFrame(self, text="时间轴(拖动两个滑块选择保留片段,中间高亮段保留)", padding=8)
        tl_box.pack(fill="x", pady=(8, 0))
        self.timeline = RangeTimeline(tl_box, self.start_var, self.end_var,
                                                   on_change=self._update_range_label)
        self.timeline.pack(fill="x")
        self.range_var = tk.StringVar(value="保留区间:未导入视频")
        ttk.Label(tl_box, textvariable=self.range_var,
                  foreground="#2f9e44").pack(anchor="w", pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=10)
        self.start_btn = ttk.Button(bar, text="开始裁剪", command=self.start)
        self.start_btn.pack(side="left")

        self.area, self.progress, self.status, self.log = add_progress_area(self)
        self.area.pack(fill="both", expand=True)

    def choose_video(self):
        path = filedialog.askopenfilename(title="选择要裁剪的视频", filetypes=VIDEO_TYPES)
        if not path:
            return
        try:
            info = core.probe_video(path)
        except core.EditorError as e:
            messagebox.showerror("无法读取视频", str(e))
            return
        self.src, self.info = path, info
        audio = "有音轨" if info["has_audio"] else "无音轨"
        self.info_var.set("%s  |  %s  |  %dx%d  |  %.1f fps  |  %s  |  %s" % (
            os.path.basename(path), fmt_duration(info["duration"]),
            info["width"], info["height"], info["fps"] or 0, audio,
            human_size(info["size"])))
        # 初始化双滑块时间轴为整片,并显示保留区间
        self.timeline.set_duration(info["duration"])
        self._update_range_label(0.0, info["duration"])
        self.log.insert("end", "已导入:%s\n" % path)

    def _update_range_label(self, s, e):
        """拖动滑块时刷新'保留区间'提示"""
        self.range_var.set("保留区间:%.1f秒 ~ %.1f秒  (时长 %.1f 秒)"
                           % (s, e, e - s))

    def choose_output(self):
        if not self.src:
            messagebox.showinfo("提示", "请先导入视频")
            return
        default_name = os.path.splitext(os.path.basename(self.src))[0] + "_裁剪.mp4"
        path = filedialog.asksaveasfilename(
            title="保存裁剪结果为", defaultextension=".mp4",
            initialfile=default_name, filetypes=[("MP4 视频", "*.mp4")])
        if path:
            self.out_path = path
            self.out_var.set("输出到:" + path)

    def start(self):
        if not self.src:
            messagebox.showinfo("提示", "请先导入视频")
            return
        try:
            core.parse_time(self.start_var.get())
            core.parse_time(self.end_var.get())
        except core.EditorError as e:
            messagebox.showerror("时间有误", str(e))
            return
        kwargs = {"src": self.src,
                  "start_text": self.start_var.get().strip(),
                  "end_text": self.end_var.get().strip(),
                  "precise": self.mode_var.get() == "precise"}
        if self.out_path:
            kwargs["output"] = self.out_path
        self.log.insert("end", "开始裁剪...\n")
        self.runner.post(core.trim_video, kwargs=kwargs, busy_widgets=(self.start_btn,))

    def _poll(self):
        self.runner.poll(self.progress, self.status, self.log)

    def _on_done(self, result, err):
        if err:
            self.log.insert("end", "失败:" + err + "\n")
            messagebox.showerror("裁剪失败", err)
        else:
            self.log.insert("end", "完成,输出:%s\n" % result)
            messagebox.showinfo("完成", "裁剪完成:\n" + result)
# ============================ 选项卡二:视频拼接 ============================

class ConcatTab(ttk.Frame):
    """视频拼接:多个视频按列表顺序合并,快速流拷贝 / 兼容重编码"""

    def __init__(self, master, root):
        super().__init__(master, padding=10)
        self.root = root
        self.paths = []
        self._build()
        self.runner = TaskRunner(root, self._on_done)
        self.after(150, self._poll)

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="添加视频", command=self.add_videos).pack(side="left")
        ttk.Button(toolbar, text="移除选中", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(toolbar, text="清空列表", command=self.clear_all).pack(side="left")
        ttk.Button(toolbar, text="上移", command=lambda: self.move(-1)).pack(side="left", padx=(18, 2))
        ttk.Button(toolbar, text="下移", command=lambda: self.move(1)).pack(side="left")

        self.listbox = tk.Listbox(self, height=8, selectmode=tk.EXTENDED)
        self.listbox.pack(fill="both", expand=True, pady=8)

        form = ttk.LabelFrame(self, text="拼接方式", padding=10)
        form.pack(fill="x")
        self.mode_var = tk.StringVar(value="fast")
        ttk.Radiobutton(form, text="快速拼接(流拷贝,秒出;要求各视频编码参数一致)",
                        variable=self.mode_var, value="fast").grid(
            row=0, column=0, sticky="w")
        ttk.Radiobutton(form, text="兼容拼接(自动统一分辨率/帧率,分辨率不同也能拼,较慢)",
                        variable=self.mode_var, value="compatible").grid(
            row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(self, text="输出默认放在第一个视频所在目录,文件名:视频拼接_时间戳.mp4",
                  foreground="#555").pack(anchor="w", pady=(6, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=8)
        self.start_btn = ttk.Button(bar, text="开始拼接", command=self.start)
        self.start_btn.pack(side="left")

        self.area, self.progress, self.status, self.log = add_progress_area(self)
        self.area.pack(fill="both", expand=True)

    def add_videos(self):
        paths = filedialog.askopenfilenames(title="选择要拼接的视频(可多选)",
                                            filetypes=VIDEO_TYPES)
        for p in paths:
            if p not in self.paths:
                self.paths.append(p)
                self.listbox.insert(tk.END, "%d. %s" % (len(self.paths), os.path.basename(p)))
        if paths:
            self.log.insert("end", "已添加 %d 个视频,共 %d 个\n" % (len(paths), len(self.paths)))

    def remove_selected(self):
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            del self.paths[idx]
        self._reload_labels()

    def clear_all(self):
        self.paths.clear()
        self.listbox.delete(0, tk.END)

    def move(self, delta):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            messagebox.showinfo("提示", "请选中一个视频后再移动")
            return
        i = sel[0]
        j = i + delta
        if j < 0 or j >= len(self.paths):
            return
        self.paths[i], self.paths[j] = self.paths[j], self.paths[i]
        self._reload_labels()
        self.listbox.selection_set(j)

    def _reload_labels(self):
        """增删/排序后刷新列表文字编号"""
        self.listbox.delete(0, tk.END)
        for i, p in enumerate(self.paths, 1):
            self.listbox.insert(tk.END, "%d. %s" % (i, os.path.basename(p)))

    def start(self):
        if len(self.paths) < 2:
            messagebox.showinfo("提示", "拼接至少需要 2 个视频")
            return
        kwargs = {"paths": list(self.paths),
                  "compatible": self.mode_var.get() == "compatible"}
        self.log.insert("end", "开始拼接 %d 个视频...\n" % len(self.paths))
        self.runner.post(core.concat_videos, kwargs=kwargs, busy_widgets=(self.start_btn,))

    def _poll(self):
        self.runner.poll(self.progress, self.status, self.log)

    def _on_done(self, result, err):
        if err:
            self.log.insert("end", "失败:" + err + "\n")
            messagebox.showerror("拼接失败", err)
        else:
            self.log.insert("end", "完成,输出:%s\n" % result)
            messagebox.showinfo("完成", "拼接完成:\n" + result)
# ============================ 选项卡三:字幕配音 ============================

class SubtitleTab(ttk.Frame):
    """字幕与配音:SRT 导入或逐条编辑,字幕烧录 + edge-tts 字幕转语音"""

    def __init__(self, master, root):
        super().__init__(master, padding=10)
        self.root = root
        self.src = ""
        self.subs = []  # [{'start','end','text'}]
        self.editing = None  # 正在编辑的行号,None=新增
        self._build()
        self.runner = TaskRunner(root, self._on_done)
        self.after(150, self._poll)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="导入视频", command=self.choose_video).pack(side="left")
        ttk.Button(top, text="导入SRT字幕", command=self.import_srt).pack(side="left", padx=6)
        ttk.Button(top, text="导出SRT备份", command=self.export_srt).pack(side="left")
        self.video_var = tk.StringVar(value="尚未导入视频")
        ttk.Label(self, textvariable=self.video_var,
                  foreground="#555").pack(anchor="w", pady=(4, 6))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # 左:字幕列表
        left = ttk.LabelFrame(body, text="字幕条目(双击可载入编辑)", padding=6)
        left.pack(side="left", fill="both", expand=True)
        cols = ("start", "end", "text")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=8)
        self.tree.heading("start", text="开始")
        self.tree.heading("end", text="结束")
        self.tree.heading("text", text="字幕文本")
        self.tree.column("start", width=80, anchor="center")
        self.tree.column("end", width=80, anchor="center")
        self.tree.column("text", width=260)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.load_selected())

        # 右:编辑区 + 参数区
        right = ttk.Frame(body)
        right.pack(side="left", fill="y", padx=(10, 0))

        edit_box = ttk.LabelFrame(right, text="编辑字幕", padding=8)
        edit_box.pack(fill="x")
        ttk.Label(edit_box, text="开始:").grid(row=0, column=0, sticky="e", pady=2)
        self.start_var = tk.StringVar()
        ttk.Entry(edit_box, textvariable=self.start_var, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(edit_box, text="结束:").grid(row=0, column=2, sticky="e")
        self.end_var = tk.StringVar()
        ttk.Entry(edit_box, textvariable=self.end_var, width=10).grid(row=0, column=3, sticky="w")
        ttk.Label(edit_box, text="文本:").grid(row=1, column=0, sticky="ne", pady=4)
        self.text_var = tk.StringVar()
        ttk.Entry(edit_box, textvariable=self.text_var, width=34).grid(
            row=1, column=1, columnspan=3, sticky="we", pady=4)
        btns = ttk.Frame(edit_box)
        btns.grid(row=2, column=0, columnspan=4, sticky="w")
        ttk.Button(btns, text="添加/更新", command=self.upsert).pack(side="left")
        ttk.Button(btns, text="载入选中", command=self.load_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="删除选中", command=self.delete_selected).pack(side="left")

        style_box = ttk.LabelFrame(right, text="字幕样式", padding=8)
        style_box.pack(fill="x", pady=(8, 0))
        ttk.Label(style_box, text="字号:").grid(row=0, column=0, sticky="e")
        self.fontsize_var = tk.IntVar(value=22)
        ttk.Spinbox(style_box, from_=12, to=60, textvariable=self.fontsize_var,
                    width=6).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(style_box, text="位置:").grid(row=0, column=2, sticky="e")
        self.pos_var = tk.StringVar(value="bottom")
        ttk.Combobox(style_box, textvariable=self.pos_var, width=6, state="readonly",
                     values=("bottom", "top")).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(style_box, text="底边距:").grid(row=1, column=0, sticky="e", pady=(4, 0))
        self.margin_var = tk.IntVar(value=30)
        ttk.Spinbox(style_box, from_=0, to=300, textvariable=self.margin_var,
                    width=6).grid(row=1, column=1, sticky="w", padx=4, pady=(4, 0))

        tts_box = ttk.LabelFrame(right, text="配音(edge-tts,需联网)", padding=8)
        tts_box.pack(fill="x", pady=(8, 0))
        self.do_tts_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tts_box, text="同时生成字幕配音",
                        variable=self.do_tts_var).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(tts_box, text="音色:").grid(row=1, column=0, sticky="e", pady=4)
        self.voice_var = tk.StringVar(value=core.TTS_VOICES[0][0])
        voice_names = [v[0] for v in core.TTS_VOICES]
        ttk.Combobox(tts_box, textvariable=self.voice_var, state="readonly",
                     values=voice_names, width=22).grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Label(tts_box, text="语速:").grid(row=2, column=0, sticky="e")
        self.rate_var = tk.StringVar(value="+0%")
        ttk.Combobox(tts_box, textvariable=self.rate_var, width=8,
                     values=("-20%", "-10%", "+0%", "+10%", "+20%")).grid(
            row=2, column=1, sticky="w", padx=4)
        ttk.Label(tts_box, text="原声:").grid(row=2, column=2, sticky="e")
        self.audio_mode_var = tk.StringVar(value="mix")
        ttk.Combobox(tts_box, textvariable=self.audio_mode_var, width=10, state="readonly",
                     values=("mix", "voiceover", "tts_only")).grid(
            row=2, column=3, sticky="w", padx=4)
        ttk.Label(tts_box, text="mix=混合 voiceover=覆盖 tts_only=仅配音;混合时原声音量",
                  foreground="#888").grid(row=3, column=0, columnspan=4, sticky="w")
        self.orig_vol_var = tk.DoubleVar(value=0.3)
        ttk.Scale(tts_box, from_=0, to=1, variable=self.orig_vol_var,
                  orient="horizontal", length=160).grid(row=4, column=0, columnspan=3, sticky="w")
        self.vol_label = ttk.Label(tts_box, text="0.30")
        self.vol_label.grid(row=4, column=3, sticky="w")
        self.orig_vol_var.trace_add("write", lambda *_a: self.vol_label.configure(
            text="%.2f" % self.orig_vol_var.get()))

        action = ttk.Frame(self)
        action.pack(fill="x", pady=8)
        self.start_btn = ttk.Button(action, text="开始导出(烧录字幕)", command=self.start)
        self.start_btn.pack(side="left")

        self.area, self.progress, self.status, self.log = add_progress_area(self)
        self.area.pack(fill="both", expand=True)

    def choose_video(self):
        path = filedialog.askopenfilename(title="选择要加字幕的视频", filetypes=VIDEO_TYPES)
        if not path:
            return
        try:
            info = core.probe_video(path)
        except core.EditorError as e:
            messagebox.showerror("无法读取视频", str(e))
            return
        self.src = path
        self.video_var.set("%s  |  %s  |  %dx%d  |  %s" % (
            os.path.basename(path), fmt_duration(info["duration"]),
            info["width"], info["height"],
            "有音轨" if info["has_audio"] else "无音轨"))

    def import_srt(self):
        path = filedialog.askopenfilename(title="选择 SRT 字幕文件",
                                          filetypes=[("SRT 字幕", "*.srt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            self.subs = core.parse_srt(path)
        except core.EditorError as e:
            messagebox.showerror("SRT 解析失败", str(e))
            return
        self._reload_tree()
        self.log.insert("end", "已导入 %d 条字幕:%s\n" % (len(self.subs), path))

    def export_srt(self):
        if not self.subs:
            messagebox.showinfo("提示", "字幕列表为空")
            return
        path = filedialog.asksaveasfilename(
            title="导出 SRT", defaultextension=".srt", initialfile="字幕备份.srt",
            filetypes=[("SRT 字幕", "*.srt")])
        if path:
            core.build_srt(self.subs, path)
            self.log.insert("end", "SRT 已导出:%s\n" % path)

    def _reload_tree(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.subs:
            self.tree.insert("", tk.END, values=(
                core.fmt_srt_time(s["start"])[:-4].replace(",", "."),
                core.fmt_srt_time(s["end"])[:-4].replace(",", "."), s["text"]))

    def upsert(self):
        try:
            item = {"start": core.parse_time(self.start_var.get()),
                    "end": core.parse_time(self.end_var.get()),
                    "text": self.text_var.get().strip()}
        except core.EditorError as e:
            messagebox.showerror("时间有误", str(e))
            return
        if not item["text"]:
            messagebox.showinfo("提示", "字幕文本不能为空")
            return
        if item["end"] <= item["start"]:
            messagebox.showerror("区间有误", "结束时间必须晚于开始时间")
            return
        if self.editing is None:
            self.subs.append(item)
            self.subs.sort(key=lambda x: x["start"])
        else:
            self.subs[self.editing] = item
            self.subs.sort(key=lambda x: x["start"])
            self.editing = None
        self._reload_tree()
        self.start_var.set("")
        self.end_var.set("")
        self.text_var.set("")

    def load_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        s = self.subs[idx]
        self.start_var.set("%.3f" % s["start"])
        self.end_var.set("%.3f" % s["end"])
        self.text_var.set(s["text"])
        self.editing = idx

    def delete_selected(self):
        sel = self.tree.selection()
        for iid in reversed(sel):
            del self.subs[self.tree.index(iid)]
        self.editing = None
        self._reload_tree()

    def start(self):
        if not self.src:
            messagebox.showinfo("提示", "请先导入视频")
            return
        if not self.subs:
            messagebox.showinfo("提示", "请先导入 SRT 或手动添加字幕")
            return
        kwargs = {
            "src": self.src,
            "subs": list(self.subs),
            "do_tts": self.do_tts_var.get(),
            "voice": self.voice_var.get(),
            "rate": self.rate_var.get(),
            "pitch": "+0Hz",
            "audio_mode": self.audio_mode_var.get(),
            "orig_volume": float(self.orig_vol_var.get()),
            "style": {"fontsize": int(self.fontsize_var.get()),
                      "position": self.pos_var.get(),
                      "margin_v": int(self.margin_var.get())},
        }
        self.log.insert("end", "开始导出%s...\n" % ("(字幕+配音)" if kwargs["do_tts"] else "(仅字幕)"))
        self.runner.post(core.render_subtitles, kwargs=kwargs, busy_widgets=(self.start_btn,))

    def _poll(self):
        self.runner.poll(self.progress, self.status, self.log)

    def _on_done(self, result, err):
        if err:
            self.log.insert("end", "失败:" + err + "\n")
            messagebox.showerror("导出失败", err)
        else:
            self.log.insert("end", "完成,输出:%s\n" % result)
            messagebox.showinfo("完成", "导出完成:\n" + result)
# ============================ 主窗口 ============================

class EditorApp(tk.Tk):
    """主窗口:组装三个选项卡,启动时自检 ffmpeg 是否可用"""

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x680")
        self.minsize(760, 560)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.trim_tab = TrimTab(notebook, self)
        self.concat_tab = ConcatTab(notebook, self)
        self.sub_tab = SubtitleTab(notebook, self)
        notebook.add(self.trim_tab, text="视频裁剪")
        notebook.add(self.concat_tab, text="视频拼接")
        notebook.add(self.sub_tab, text="字幕配音")
        tip = ttk.Label(self, foreground="#888",
                        text="提示:输出文件均带时间戳,不会覆盖源文件;配音功能需联网,仅烧录字幕可离线使用")
        tip.pack(anchor="w", padx=10, pady=(0, 6))
        self.after(300, self._check_ffmpeg)

    def _check_ffmpeg(self):
        """启动自检:ffmpeg 缺失时给出明确安装指引"""
        try:
            exe = core.find_ffmpeg()
            self.trim_tab.log.insert("end", "ffmpeg 就绪:%s\n" % exe)
        except core.EditorError as e:
            messagebox.showerror(
                "环境缺失", str(e) + "\n\n安装后重新双击启动脚本即可。")


def main():
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()