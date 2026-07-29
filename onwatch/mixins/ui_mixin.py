# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import re


class UIMixin:
    """UI构建与界面刷新"""

    def setup_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # ---------- 收益参数 ----------
        profit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="收益参数", menu=profit_menu)
        profit_menu.add_command(label="拟持区设置", command=self.open_trade_params_window)

        # ---------- 参数设置 ----------
        param_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="参数设置", menu=param_menu)
        param_menu.add_command(label="条件区设置", command=self.open_settings_window)

        # ---------- 历史记录 ----------
        record_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="历史记录", menu=record_menu)
        record_menu.add_command(label="查看历史操作", command=self.open_profit_record_window)

        # ---------- 免责声明 ----------
        legal_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="免责声明", menu=legal_menu)
        legal_menu.add_command(label="查看法律声明", command=self.open_legal_notice)

        # ⭐ 新增：帮助菜单（检查更新）
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="检查更新", command=self.manual_check_update)

        # ---------- 工具栏 ----------
        toolbar = tk.Frame(self.root, bg='#f0f0f0', height=40)
        toolbar.pack(fill='x', padx=5, pady=5)
        tk.Label(toolbar, text="自动刷新(60s)", bg='#f0f0f0', font=('微软雅黑', 9)).pack(side='left', padx=10)
        self.auto_refresh_var = tk.BooleanVar(value=self.auto_refresh_enabled)
        self.auto_refresh_cb = tk.Checkbutton(toolbar, text="启用", variable=self.auto_refresh_var,
                                               command=self.toggle_auto_refresh, bg='#f0f0f0')
        self.auto_refresh_cb.pack(side='left', padx=5)
        self.refresh_btn = tk.Button(toolbar, text="手动刷新", command=self.manual_refresh, bg='#1c416c', fg='white', width=10)
        self.refresh_btn.pack(side='left', padx=5)

        # ---------- 监控区 ----------
        monitor_frame = tk.LabelFrame(self.root, text="📊 模拟条件区", font=('微软雅黑', 11, 'bold'), padx=5, pady=5)
        monitor_frame.pack(fill='x', padx=10, pady=5)

        header = tk.Frame(monitor_frame, bg='#f7fcff')
        header.pack(fill='x')
        cols = [("代码", 6), (" ", 1), ("现价", 7),
                ("参考1", 5), ("状态", 5), ("操作", 3),
                ("参考2", 5), ("状态", 5), ("操作", 3),
                ("参考3", 5), ("状态", 5), ("操作", 3)]
        col_idx = 0
        for text, width in cols:
            tk.Label(header, text=text, font=('微软雅黑', 9, 'bold'), bg='#f7fcff', width=width).grid(row=0, column=col_idx, padx=1)
            col_idx += 1

        self.monitor_cells.clear()
        for i in range(5):
            row = tk.Frame(monitor_frame, bg='#f7fcff')
            row.pack(fill='x', pady=2)
            cells = {}
            code_label = tk.Label(row, text="", font=('微软雅黑',9), width=6, anchor='w', bg='#f7fcff')
            code_label.pack(side='left', padx=1)
            cells['code'] = code_label
            led_label = tk.Label(row, text='●', font=('微软雅黑',9), fg='#95a5a6', bg='#f7fcff', width=1)
            led_label.pack(side='left', padx=1)
            cells['led'] = led_label
            price_var = tk.StringVar(value="--")
            price_entry = tk.Entry(row, textvariable=price_var, font=('微软雅黑',9), width=7, justify='left', bg='#f7fcff', state='readonly')
            price_entry.pack(side='left', padx=1)
            cells['price_var'] = price_var
            cells['price_entry'] = price_entry

            for j in range(3):
                ref_label = tk.Label(row, text="", font=('微软雅黑',9), width=5, anchor='w', bg='#f7fcff')
                ref_label.pack(side='left', padx=1)
                cells[f'ref{j}'] = ref_label
                status_label = tk.Label(row, text="", font=('微软雅黑',8), width=5, bg='#bdc3c7', fg='#2c3e50')
                status_label.pack(side='left', padx=1)
                cells[f'status{j}'] = status_label
                btn = tk.Button(row, text="记录买入", state='disabled', bg='#7f8c8d', fg='white', font=('微软雅黑',7), width=7)
                btn.pack(side='left', padx=1)
                cells[f'btn{j}'] = btn
            self.monitor_cells[i] = cells

        # ---------- 持仓区 ----------
        position_frame = tk.LabelFrame(self.root, text="📦 模拟持有区", font=('微软雅黑', 11, 'bold'), padx=5, pady=5)
        position_frame.pack(fill='both', expand=True, padx=10, pady=5)

        header_frame = tk.Frame(position_frame, bg='#f7fcff')
        header_frame.pack(fill='x')

        tk.Label(header_frame, text="持仓列表", font=('微软雅黑', 10, 'bold'), bg='#f7fcff').pack(side='left', padx=5)

        sort_frame = tk.Frame(header_frame, bg='#f7fcff')
        sort_frame.pack(side='left', padx=10)

        btn_code = tk.Button(sort_frame, text="代码", font=('微软雅黑', 8),
                             command=lambda: self.set_sort_field('stock_code'), width=4)
        btn_code.pack(side='left', padx=1)

        btn_status = tk.Button(sort_frame, text="状态", font=('微软雅黑', 8),
                               command=lambda: self.set_sort_field('status'), width=4)
        btn_status.pack(side='left', padx=1)

        btn_pnl = tk.Button(sort_frame, text="收益率", font=('微软雅黑', 8),
                            command=lambda: self.set_sort_field('pnl_pct'), width=4)
        btn_pnl.pack(side='left', padx=1)

        btn_oper = tk.Button(sort_frame, text="操作", font=('微软雅黑', 8),
                             command=lambda: self.set_sort_field('operable'), width=4)
        btn_oper.pack(side='left', padx=1)

        self.sort_indicator = tk.Label(sort_frame, text="↓", font=('微软雅黑', 8, 'bold'),
                                        bg='#f7fcff', fg='blue', width=2)
        self.sort_indicator.pack(side='left', padx=5)

        self.clear_btn = tk.Button(header_frame, text="清空已卖出", command=self.clear_sold_positions,
                                   bg='#d9534f', fg='white', font=('微软雅黑', 9), width=12)
        self.clear_btn.pack(side='right', padx=5)

        canvas = tk.Canvas(position_frame, bg='#f7fcff', highlightthickness=0)
        scrollbar = tk.Scrollbar(position_frame, orient='vertical', command=canvas.yview)
        self.position_inner = tk.Frame(canvas, bg='#f7fcff')
        self.position_inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0,0), window=self.position_inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        pos_header = tk.Frame(self.position_inner, bg='#f7fcff')
        pos_header.pack(fill='x')
        pos_cols = [("代码",6), ("买入价",8), ("数量",6), ("净收益(模拟)",10), ("净收益率",8), ("状态",8), ("操作",7)]
        for i,(text,w) in enumerate(pos_cols):
            tk.Label(pos_header, text=text, font=('微软雅黑',9,'bold'), bg='#f7fcff', width=w).grid(row=0, column=i, padx=1)

        self.position_rows.clear()

        # ---------- 提示条 ----------
        self.note_label = tk.Label(self.root, text="⏳ 无新触发", bg='#fff3cd', fg='#856404', font=('微软雅黑',9), anchor='w', padx=10)
        self.note_label.pack(fill='x', padx=10, pady=2)

        # ---------- 日志区 ----------
        log_frame = tk.Frame(self.root, bg='#1d2e42', height=80)
        log_frame.pack(fill='x', padx=10, pady=5)
        self.log_text = tk.Text(log_frame, bg='#1d2e42', fg='#cde3ff', font=('Consolas',8), wrap='word', height=4)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.insert('1.0', "⚙️ 就绪\n")
        self.log_text.config(state='disabled')

        # ---------- 页脚 ----------
        footer = tk.Frame(self.root)
        footer.pack(fill='x', padx=10, pady=2)
        tk.Label(footer, text="⚠️ 本软件仅用于模拟学习，数据仅供参考，不构成投资建议", 
                 font=('微软雅黑',7), fg='#a0a0a0').pack(side='right')

        # ---------- 首次填充数据 ----------
        self.refresh_monitor_display(full_rebuild=True)
        self.refresh_position_display(full_rebuild=True)

    # ---------- 排序 ----------
    def set_sort_field(self, field):
        if field == self.sort_field:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_field = field
            self.sort_reverse = True
        self.sort_indicator.config(text="↓" if self.sort_reverse else "↑")
        self.refresh_position_display(full_rebuild=True)

    # ---------- 监控区刷新 ----------
    def refresh_monitor_display(self, full_rebuild=False):
        if full_rebuild:
            for i in range(5):
                cells = self.monitor_cells[i]
                code = self.stock_codes[i] if i < len(self.stock_codes) else ""
                if not code.strip() or code not in self.stock_pool:
                    cells['code'].config(text="")
                    cells['led'].config(fg='#95a5a6')
                    cells['price_var'].set("--")
                    for j in range(3):
                        cells[f'ref{j}'].config(text="")
                        cells[f'status{j}'].config(text="", bg='#bdc3c7', fg='#2c3e50')
                        cells[f'btn{j}'].config(state='disabled', bg='#7f8c8d', text="记录买入")
                    continue

                digits = re.sub(r'\D', '', code)
                with self.data_lock:
                    data = self.stock_pool[digits]
                    price = data.get('price', 0.0)
                    price_valid = data.get('price_valid', False)
                    support_prices = data['support_prices'][:]
                    support_processed = data['support_processed'][:]
                cells['code'].config(text=digits)
                has_pos = any(p for p in self.positions if p['stock_code']==digits and not p['sold'])
                led_color = '#2ecc71' if has_pos else '#95a5a6'
                cells['led'].config(fg=led_color)
                price_text = f"{price:.2f}" if price_valid and price>0 else "--"
                cells['price_var'].set(price_text)

                for j in range(3):
                    sp = support_prices[j]
                    cells[f'ref{j}'].config(text=f"{sp:.2f}")
                    if support_processed[j]:
                        status_text = "已记录"
                        status_bg = '#27ae60'
                        status_fg = 'white'
                        btn_state = 'disabled'
                        btn_bg = '#7f8c8d'
                    elif price_valid and price > 0 and price <= sp:
                        status_text = "价格触及"
                        status_bg = '#e74c3c'
                        status_fg = 'white'
                        btn_state = 'normal'
                        btn_bg = '#3498db'
                    else:
                        status_text = "未触及"
                        status_bg = '#bdc3c7'
                        status_fg = '#2c3e50'
                        btn_state = 'disabled'
                        btn_bg = '#7f8c8d'
                    cells[f'status{j}'].config(text=status_text, bg=status_bg, fg=status_fg)
                    cells[f'btn{j}'].config(state=btn_state, bg=btn_bg,
                                           command=lambda c=digits, idx=j: self.manual_buy(c, idx))
        else:
            for i in range(5):
                cells = self.monitor_cells[i]
                code = self.stock_codes[i] if i < len(self.stock_codes) else ""
                if not code.strip() or code not in self.stock_pool:
                    continue
                digits = re.sub(r'\D', '', code)
                with self.data_lock:
                    data = self.stock_pool[digits]
                    price = data.get('price', 0.0)
                    price_valid = data.get('price_valid', False)
                    support_prices = data['support_prices'][:]
                    support_processed = data['support_processed'][:]
                has_pos = any(p for p in self.positions if p['stock_code']==digits and not p['sold'])
                led_color = '#2ecc71' if has_pos else '#95a5a6'
                cells['led'].config(fg=led_color)
                price_text = f"{price:.2f}" if price_valid and price>0 else "--"
                cells['price_var'].set(price_text)
                for j in range(3):
                    sp = support_prices[j]
                    cells[f'ref{j}'].config(text=f"{sp:.2f}")
                    if support_processed[j]:
                        status_text = "已记录"
                        status_bg = '#27ae60'
                        status_fg = 'white'
                        btn_state = 'disabled'
                        btn_bg = '#7f8c8d'
                    elif price_valid and price > 0 and price <= sp:
                        status_text = "价格触及"
                        status_bg = '#e74c3c'
                        status_fg = 'white'
                        btn_state = 'normal'
                        btn_bg = '#3498db'
                    else:
                        status_text = "未触及"
                        status_bg = '#bdc3c7'
                        status_fg = '#2c3e50'
                        btn_state = 'disabled'
                        btn_bg = '#7f8c8d'
                    cells[f'status{j}'].config(text=status_text, bg=status_bg, fg=status_fg)
                    cells[f'btn{j}'].config(state=btn_state, bg=btn_bg,
                                           command=lambda c=digits, idx=j: self.manual_buy(c, idx))

    # ---------- 持仓区刷新 ----------
    def refresh_position_display(self, full_rebuild=False):
        if full_rebuild:
            for row_info in self.position_rows.values():
                row_info[0].destroy()
            self.position_rows.clear()

            if not self.positions:
                frame = tk.Frame(self.position_inner, bg='#f7fcff')
                frame.pack(fill='x', pady=1)
                label = tk.Label(frame, text="暂无持仓", font=('微软雅黑',9), fg='#778fa5', bg='#f7fcff')
                label.pack()
                self.position_rows[None] = [frame, label]
                return

            sorted_positions = self._get_sorted_positions()
            for pos in sorted_positions:
                self._create_position_row(pos)
        else:
            if not self.positions:
                return
            sorted_positions = self._get_sorted_positions()
            current_ids = set(p['pos_id'] for p in sorted_positions)
            for pos in sorted_positions:
                pos_id = pos['pos_id']
                if pos_id in self.position_rows:
                    self._update_position_row(pos)
                else:
                    self._create_position_row(pos)
            for pos_id in list(self.position_rows.keys()):
                if pos_id is None:
                    if self.positions:
                        self.position_rows[None][0].destroy()
                        del self.position_rows[None]
                    continue
                if pos_id not in current_ids:
                    self.position_rows[pos_id][0].destroy()
                    del self.position_rows[pos_id]

    def _get_sorted_positions(self):
        with self.data_lock:
            positions_copy = self.positions.copy()
        def sort_key(pos):
            if self.sort_field == 'stock_code':
                return pos['stock_code']
            elif self.sort_field == 'status':
                status_map = {
                    "止盈卖出": 1,
                    "止损卖出": 2,
                    "持有": 3,
                    "等待价格": 4,
                    "已卖出": 5
                }
                if pos['sold']:
                    return status_map.get("已卖出", 5)
                else:
                    last = pos.get('last_price')
                    if last is None or last <= 0:
                        return status_map.get("等待价格", 4)
                    else:
                        pnl_pct = (self.calc_net_profit(pos['buy_price'], last, pos['shares']) /
                                   self.calc_buy_cost(pos['buy_price'], pos['shares']) * 100)
                        if pnl_pct >= self.take_profit:
                            return status_map.get("止盈卖出", 1)
                        elif pnl_pct <= -self.stop_loss:
                            return status_map.get("止损卖出", 2)
                        else:
                            return status_map.get("持有", 3)
            elif self.sort_field == 'pnl_pct':
                if pos['sold']:
                    return pos['sold_pnl'] / self.calc_buy_cost(pos['buy_price'], pos['shares']) * 100 if pos['sold_pnl'] is not None else -1e9
                else:
                    last = pos.get('last_price')
                    if last is None or last <= 0:
                        return -1e9
                    else:
                        return self.calc_net_profit(pos['buy_price'], last, pos['shares']) / self.calc_buy_cost(pos['buy_price'], pos['shares']) * 100
            elif self.sort_field == 'operable':
                if pos['sold']:
                    return 0
                else:
                    last = pos.get('last_price')
                    if last is None or last <= 0:
                        return 0
                    else:
                        return 1
            else:
                return pos.get('buy_time', '')
        return sorted(positions_copy, key=sort_key, reverse=self.sort_reverse)

    def _create_position_row(self, pos):
        frame = tk.Frame(self.position_inner, bg='#f7fcff')
        frame.pack(fill='x', pady=1)

        code = pos['stock_code']
        buy = pos['buy_price']
        shares = pos['shares']
        last = pos.get('last_price')

        label_code = tk.Label(frame, text=code, font=('微软雅黑',9), width=6, anchor='w', bg='#f7fcff')
        label_code.grid(row=0, column=0, padx=1)

        label_buy = tk.Label(frame, text=f"{buy:.2f}", font=('微软雅黑',9), width=8, anchor='w', bg='#f7fcff')
        label_buy.grid(row=0, column=1, padx=1)

        label_shares = tk.Label(frame, text=str(shares), font=('微软雅黑',9), width=6, anchor='w', bg='#f7fcff')
        label_shares.grid(row=0, column=2, padx=1)

        label_pnl = tk.Label(frame, text="", font=('微软雅黑',9), width=10, anchor='w', bg='#f7fcff')
        label_pnl.grid(row=0, column=3, padx=1)

        label_pnl_pct = tk.Label(frame, text="", font=('微软雅黑',9), width=8, anchor='w', bg='#f7fcff')
        label_pnl_pct.grid(row=0, column=4, padx=1)

        label_status = tk.Label(frame, text="", font=('微软雅黑',8), width=8)
        label_status.grid(row=0, column=5, padx=1)

        btn = tk.Button(frame, text="记录卖出", font=('微软雅黑',7), width=7,
                        command=lambda pid=pos['pos_id']: self.manual_sell(pid))
        btn.grid(row=0, column=6, padx=1)

        self.position_rows[pos['pos_id']] = [frame, label_code, label_buy, label_shares,
                                              label_pnl, label_pnl_pct, label_status, btn]
        self._update_position_row(pos)

    def _update_position_row(self, pos):
        row_info = self.position_rows[pos['pos_id']]
        (frame, label_code, label_buy, label_shares,
         label_pnl, label_pnl_pct, label_status, btn) = row_info

        code = pos['stock_code']
        buy = pos['buy_price']
        shares = pos['shares']
        last = pos.get('last_price')

        label_code.config(text=code)
        label_buy.config(text=f"{buy:.2f}")
        label_shares.config(text=str(shares))

        if pos['sold']:
            pnl = pos.get('sold_pnl', 0.0)
            pnl_text = f"{pnl:+.2f}"
            cost = self.calc_buy_cost(buy, shares)
            if cost != 0:
                pnl_pct = (pnl / cost) * 100
                pnl_pct_text = f"{pnl_pct:+.2f}%"
            else:
                pnl_pct_text = "--"
            status = "已卖出"
            status_bg = '#95a5a6'
            status_fg = 'white'
            btn_state = 'disabled'
            btn_bg = '#9fb8d4'
        else:
            if last is None or last <= 0:
                pnl_text = "--"
                pnl_pct_text = "--"
                status = "等待价格"
                status_bg = '#dee7f0'
                status_fg = '#314e72'
                btn_state = 'disabled'
                btn_bg = '#9fb8d4'
            else:
                pnl = self.calc_net_profit(buy, last, shares)
                pnl_text = f"{pnl:+.2f}"
                cost = self.calc_buy_cost(buy, shares)
                if cost != 0:
                    pnl_pct = (pnl / cost) * 100
                    pnl_pct_text = f"{pnl_pct:+.2f}%"
                else:
                    pnl_pct_text = "--"

                if pnl_pct >= self.take_profit:
                    status = "止盈卖出"
                    status_bg = '#b8e2b8'
                    status_fg = '#1d6b2b'
                elif pnl <= -self.stop_loss * cost / 100:
                    status = "止损卖出"
                    status_bg = '#f0b5b5'
                    status_fg = '#902d2d'
                else:
                    status = "持有"
                    status_bg = '#dee7f0'
                    status_fg = '#314e72'
                btn_state = 'normal'
                btn_bg = '#e5effa'

        label_pnl.config(text=pnl_text)
        label_pnl_pct.config(text=pnl_pct_text)
        label_status.config(text=status, bg=status_bg, fg=status_fg)
        btn.config(state=btn_state, bg=btn_bg)

    # ---------- 打开窗口（对话框） ----------
    def open_trade_params_window(self):
        from ..dialogs import TradeParamsWindow
        pwd = simpledialog.askstring("密码验证", "请输入密码:", show='*', parent=self.root)
        if pwd != self.password:
            messagebox.showerror("错误", "密码错误，无法打开设置")
            return
        TradeParamsWindow(self)

    def open_settings_window(self):
        from ..dialogs import SettingsWindow
        pwd = simpledialog.askstring("密码验证", "请输入密码:", show='*', parent=self.root)
        if pwd != self.password:
            messagebox.showerror("错误", "密码错误，无法打开设置")
            return
        SettingsWindow(self)

    def open_profit_record_window(self):
        from ..dialogs import ProfitRecordWindow
        ProfitRecordWindow(self)

    def open_legal_notice(self):
        from ..dialogs import LegalNoticeWindow
        LegalNoticeWindow(self)

    # ⭐ 新增：手动检查更新（调用主类的方法）
    def manual_check_update(self):
        """由菜单『检查更新』触发，通过主类实例调用更新检查器"""
        if hasattr(self, 'updater'):
            self.updater.check_for_updates(show_no_update=True)
        else:
            messagebox.showerror("错误", "更新模块未初始化。")
