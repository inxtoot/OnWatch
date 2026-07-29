# -*- coding: utf-8 -*-
import threading
import os
import re
import time
import tkinter as tk
from tkinter import ttk, messagebox
from concurrent.futures import ThreadPoolExecutor
from pynput import keyboard, mouse

from .mixins import DataMixin, NetworkMixin, PlaybackMixin, UIMixin
from .updater import UpdateChecker
from .version import get_version


class IntegratedApp(DataMixin, NetworkMixin, PlaybackMixin, UIMixin):
    """主应用类：通过Mixin组合所有功能"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"OnWatch {get_version()}（学习版）")
        self.root.geometry("580x600")
        self.root.minsize(580, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ---------- 并发锁 ----------
        self.data_lock = threading.RLock()

        # ---------- 目录与文件 ----------
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.window_geometry_file = os.path.join(self.data_dir, 'window_geometry.json')
        self.settings_file = os.path.join(self.data_dir, 'settings.json')
        self.positions_file = os.path.join(self.data_dir, 'ccqu.json')
        self.history_file = os.path.join(self.data_dir, 'logs.json')
        self.log_file = os.path.join(self.data_dir, 'log.txt')

        self.zbiao_dir = os.path.join(os.path.dirname(__file__), '..', 'zbiao')
        if not os.path.exists(self.zbiao_dir):
            os.makedirs(self.zbiao_dir)

        # ---------- 核心数据 ----------
        self.stock_codes = ["", "", "", "", ""]
        self.stock_pool = {}
        self.positions = []
        self.history = []
        self.next_pos_id = 0
        self.shares_per_trade = 500
        self.take_profit = 1.0
        self.stop_loss = 1.0
        self.auto_refresh_enabled = True
        self.price_update_lock = threading.Lock()
        self.password = "123"

        self.commission_rate = 0.0003
        self.stamp_tax_rate = 0.001
        self.transfer_fee_rate = 0.00001

        # ---------- 播放相关 ----------
        self.playback_active = False
        self.stop_playback_flag = False
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        self.loop_count = 1
        self.sample_enabled = tk.BooleanVar(value=False)
        self.sample_interval = tk.IntVar(value=10)
        self.precision_mode = tk.BooleanVar(value=False)

        self.script_queue = []
        self.queue_lock = threading.Lock()
        self.queue_processing = False

        self.sort_field = 'buy_time'
        self.sort_reverse = True

        self.executor = ThreadPoolExecutor(max_workers=5)

        self.monitor_cells = {}
        self.position_rows = {}

        # ---------- 加载数据 ----------
        self.load_config()
        self.load_positions()
        self.load_history()

        # ---------- 构建UI ----------
        self.setup_ui()

        # ---------- 启动监听 ----------
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, suppress=True)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

        self.mouse_listener = mouse.Listener()
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

        # ---------- 启动定时刷新 ----------
        self.schedule_auto_refresh()

        # ---------- 初始化更新检查器（静默检测） ----------
        self.updater = UpdateChecker(self)
        self.updater.check_for_updates()

        self.log("程序启动成功")

    # ---------- 手动检查更新 ----------
    def manual_check_update(self):
        if hasattr(self, 'updater'):
            self.updater.check_for_updates(show_no_update=True)
        else:
            messagebox.showerror("错误", "更新模块未初始化。")
