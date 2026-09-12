# -*- coding: utf-8 -*-
"""
录屏小控制台（脱离工作台独立运行，双击「启动录屏控制台.bat」打开）。

纯文字按钮:开始（全屏/框选）、暂停、继续、结束并保存、关闭；
结束后可在窗口内填“目标秒数”一键生成变速版（如 60 秒压到 40 秒，内容完整）。
所有耗时操作放后台线程，界面不卡死；通过 main.py 的状态文件与录制进程通信。
"""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import main as rec


class RecorderPanel(tk.Tk):
    """录屏控制面板主窗口。"""

    def __init__(self):
        super().__init__()
        self.title("AI智能助手 · 录屏控制台")
        self.geometry("420x470")
        self.resizable(False, False)
        self._busy = False

        # ① 录制范围
        frm1 = ttk.LabelFrame(self, text="1. 录制范围")
        frm1.pack(fill="x", padx=12, pady=(12, 6))
        self.mode_var = tk.StringVar(value="full")
        ttk.Radiobutton(frm1, text="主屏全屏", value="full",
                        variable=self.mode_var).pack(side="left", padx=10, pady=8)
        ttk.Radiobutton(frm1, text="鼠标框选区域", value="region",
                        variable=self.mode_var).pack(side="left", padx=10)

        # ② 控制按钮（全部纯文字，无图标）
        frm2 = ttk.LabelFrame(self, text="2. 录制控制")
        frm2.pack(fill="x", padx=12, pady=6)
        self.btn_start = ttk.Button(frm2, text="开始录制", command=self.on_start)
        self.btn_pause = ttk.Button(frm2, text="暂停", command=self.on_pause)
        self.btn_resume = ttk.Button(frm2, text="继续", command=self.on_resume)
        self.btn_stop = ttk.Button(frm2, text="结束并保存", command=self.on_stop)
        self.btn_start.grid(row=0, column=0, padx=8, pady=10, sticky="ew")
        self.btn_pause.grid(row=0, column=1, padx=8, pady=10, sticky="ew")
        self.btn_resume.grid(row=0, column=2, padx=8, pady=10, sticky="ew")
        self.btn_stop.grid(row=0, column=3, padx=8, pady=10, sticky="ew")
        for c in range(4):
            frm2.columnconfigure(c, weight=1)

        # ③ 实时状态
        frm3 = ttk.LabelFrame(self, text="3. 状态")
        frm3.pack(fill="both", expand=True, padx=12, pady=6)
        self.status_var = tk.StringVar(value="⚪ 未开始")
        ttk.Label(frm3, textvariable=self.status_var, justify="left",
                  wraplength=380).pack(anchor="w", padx=10, pady=8)
        # ④ 成片变速（结束后可用:实际 N 秒指定压到 M 秒，内容完整）
        frm4 = ttk.LabelFrame(self, text="4. 成片变速（结束后可用）")
        frm4.pack(fill="x", padx=12, pady=6)
        row = ttk.Frame(frm4)
        row.pack(fill="x", padx=10, pady=8)
        ttk.Label(row, text="目标时长(秒):").pack(side="left")
        self.target_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.target_var, width=8).pack(side="left")
        self.btn_speed = ttk.Button(row, text="生成加速版", command=self.on_speed)
        self.btn_speed.pack(side="left", padx=8)
        self.speed_hint = tk.StringVar(value="例:实际60秒填40 → 1.5倍速，内容不裁剪")
        ttk.Label(frm4, textvariable=self.speed_hint, foreground="#888").pack(
            anchor="w", padx=10, pady=(0, 8))

        # ⑤ 底部:关闭窗口
        ttk.Button(self, text="关闭", width=12,
                   command=self.on_close).pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._refresh_buttons()
        self.after(500, self._poll_status)

    # ===== 按钮事件:统一放后台线程执行，避免阻塞界面 =====
    def _run_async_raw(self, fn):
        """后台执行任意控制动作并把返回文案刷新到界面。"""
        if self._busy:
            return
        self._busy = True
        self._set_buttons(tk.DISABLED)

        def worker():
            try:
                msg = fn()
                self.after(0, lambda: self._done(msg))
            except Exception as e:
                self.after(0, lambda: self._done(f"❌ {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def on_start(self):
        self._run_async_raw(lambda: rec.run(
            {"action": "start", "mode": self.mode_var.get()}))

    def on_pause(self):
        self._run_async_raw(lambda: rec.run({"action": "pause"}))

    def on_resume(self):
        self._run_async_raw(lambda: rec.run({"action": "resume"}))

    def on_stop(self):
        self._run_async_raw(lambda: rec.run({"action": "stop"}))

    def on_speed(self):
        raw = self.target_var.get().strip()
        if not raw:
            messagebox.showinfo("提示", "请先输入目标时长（秒），例如 40")
            return
        try:
            target = float(raw)
            if target <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "目标时长必须是大于 0 的数字")
            return
        self._run_async_raw(lambda: rec.run(
            {"action": "speed", "target_seconds": target}))

    def _done(self, msg):
        self._busy = False
        self.status_var.set(msg)
        self._refresh_buttons()

    def _set_buttons(self, state):
        for b in (self.btn_start, self.btn_pause, self.btn_resume,
                  self.btn_stop, self.btn_speed):
            b.config(state=state)

    def _refresh_buttons(self):
        """按录制状态切换按钮可用性:开始/暂停/继续/结束。"""
        st = rec.read_status()
        state = st.get("state", "idle")
        pid_ok = rec.is_process_alive(st.get("pid"))
        recording = state == "recording" and pid_ok
        paused = state == "paused" and pid_ok
        active = recording or paused
        self.btn_start.config(state=tk.NORMAL if not active else tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL if recording else tk.DISABLED)
        self.btn_resume.config(state=tk.NORMAL if paused else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if active or state == "starting"
                             else tk.DISABLED)
        self.btn_speed.config(state=tk.NORMAL if state == "finished" else tk.DISABLED)
        if not self._busy:
            self.status_var.set(rec._status_text(st))

    def _poll_status(self):
        """每 0.8 秒刷新一次状态与按钮，不调用 run()，只读状态文件。"""
        try:
            self._refresh_buttons()
        except Exception:
            pass
        self.after(800, self._poll_status)

    def on_close(self):
        st = rec.read_status()
        if rec.is_process_alive(st.get("pid")) and st.get("state") in (
                "recording", "paused"):
            if not messagebox.askokcancel(
                    "确认关闭", "录屏还在进行中，直接关闭控制台不会停止录制进程。\n"
                    "建议先点「结束并保存」。是否仍要关闭控制台？"):
                return
        self.destroy()


if __name__ == "__main__":
    RecorderPanel().mainloop()