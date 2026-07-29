# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import re
import csv
from datetime import datetime, timedelta


class LegalNoticeWindow(tk.Toplevel):
    """专门显示法律声明与免责条款的窗口"""
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("法律声明与免责条款")
        self.geometry("600x500")
        self.minsize(600, 500)
        self.transient(app.root)
        self.grab_set()

        txt = tk.Text(self, wrap='word', font=('微软雅黑', 10))
        txt.pack(fill='both', expand=True, padx=10, pady=10)

        legal_text = """【法律声明与免责条款】

1. 软件性质
   本软件为开源学习项目，按“原样”提供，不附带任何明示或默示的担保。开发者不保证软件的准确性、可靠性、完整性或及时性。
   本软件**仅限用于模拟交易学习与研究**，不得用于任何实盘交易。

2. 数据来源
   本软件使用的股票数据来源于新浪、网易等公开网络接口，数据可能存在延迟、错误或中断。开发者不对数据的准确性、完整性、实时性作任何保证。**数据仅供参考，不构成任何投资建议。**

3. 自动化功能
   本软件的键鼠模拟、自动触发等功能，**仅用于辅助用户在模拟环境中进行自动化操作学习**。用户若将软件用于任何实盘交易或与实际券商软件交互，需自行确保相关行为符合券商的服务条款，并自行承担由此产生的一切风险与后果。

4. 投资决策
   本软件不提供任何投资建议，所有参考价位、买卖条件均由用户自行设置。任何基于软件信息的投资决策，均由用户独立作出并承担全部责任。金融市场有风险，投资需谨慎。

5. 禁止用途
   严禁将本软件用于：
   - 任何形式的实盘交易；
   - 操纵市场、内幕交易、非法证券活动；
   - 对任何网站、系统进行自动化攻击、爬取、干扰；
   - 任何违反所在国家/地区法律法规及券商交易规则的行为。

6. 用户义务
   用户使用本软件即表示已阅读并理解上述条款，并承诺：
   - 仅将软件用于模拟学习，不用于实盘；
   - 遵守所有适用法律法规；
   - 自行评估并承担使用本软件的全部风险；
   - 不得将本软件用于任何违法或未经授权的用途。

7. 修改与终止
   开发者保留随时修改、更新或终止本软件的权利，恕不另行通知。修改后的条款自发布之日起生效。

8. 其他
   本声明最终解释权归开发者所有。如有争议，开发者保留法律允许范围内的最终解释权。

【重要提示】本软件为开源项目，使用者需年满18周岁。若您不同意上述任何条款，请立即停止使用并删除本软件。"""
        txt.insert('1.0', legal_text)
        txt.config(state='disabled')


class TradeParamsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("持有区参数设置")
        self.geometry("400x250")
        self.minsize(400, 250)
        self.transient(app.root)
        self.grab_set()
        self.create_ui()

    def create_ui(self):
        main = tk.Frame(self)
        main.pack(fill='both', expand=True, padx=20, pady=15)

        row0 = tk.Frame(main)
        row0.pack(fill='x', pady=5)
        tk.Label(row0, text="数量:", width=12, anchor='w').pack(side='left')
        self.shares_var = tk.StringVar(value=str(self.app.shares_per_trade))
        tk.Entry(row0, textvariable=self.shares_var, width=10).pack(side='left')
        tk.Label(main, text="（实际数量以录制脚本时输入的数量为准）",
                font=('微软雅黑', 8), fg='gray').pack(anchor='w', pady=(0,10))

        row1 = tk.Frame(main)
        row1.pack(fill='x', pady=5)
        tk.Label(row1, text="拟赢卖出%:", width=12, anchor='w').pack(side='left')
        self.take_profit_var = tk.StringVar(value=str(self.app.take_profit))
        tk.Entry(row1, textvariable=self.take_profit_var, width=10).pack(side='left')

        row2 = tk.Frame(main)
        row2.pack(fill='x', pady=5)
        tk.Label(row2, text="拟损卖出%:", width=12, anchor='w').pack(side='left')
        self.stop_loss_var = tk.StringVar(value=str(self.app.stop_loss))
        tk.Entry(row2, textvariable=self.stop_loss_var, width=10).pack(side='left')

        btn_frame = tk.Frame(main)
        btn_frame.pack(fill='x', pady=15)
        tk.Button(btn_frame, text="保存", command=self.save, bg='#1c416c', fg='white', width=10).pack(side='left', padx=10)
        tk.Button(btn_frame, text="取消", command=self.destroy, width=10).pack(side='left')

    def save(self):
        try:
            self.app.shares_per_trade = int(self.shares_var.get())
            self.app.take_profit = float(self.take_profit_var.get())
            self.app.stop_loss = float(self.stop_loss_var.get())
        except ValueError:
            messagebox.showerror("错误", "所有参数必须为数字")
            return
        self.app.save_config()
        self.app.update_note()
        self.app.refresh_position_display(full_rebuild=True)
        self.destroy()


class SettingsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("模拟代码与播放参数设置")
        self.geometry("500x450")
        self.minsize(500, 450)
        self.transient(app.root)
        self.grab_set()
        self.create_ui()

    def get_script_names(self):
        if not os.path.exists(self.app.zbiao_dir):
            return []
        files = os.listdir(self.app.zbiao_dir)
        names = [os.path.splitext(f)[0] for f in files if f.endswith('.json')]
        return sorted(names)

    def create_ui(self):
        main = tk.Frame(self)
        main.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(main, text="代码池设置（最多5只）", font=('微软雅黑',10,'bold')).grid(row=0, column=0, columnspan=6, pady=5, sticky='w')
        headers = ["代码", "参考1", "参考2", "参考3", "买入脚本", "卖出脚本"]
        for i,h in enumerate(headers):
            tk.Label(main, text=h, font=('微软雅黑',9,'bold')).grid(row=1, column=i, padx=2, pady=2)

        script_names = ["无"] + self.get_script_names()
        self.row_vars = []
        for i in range(5):
            code = self.app.stock_codes[i] if i < len(self.app.stock_codes) else ""
            code_var = tk.StringVar(value=code)
            s1_var = tk.StringVar()
            s2_var = tk.StringVar()
            s3_var = tk.StringVar()
            buy_var = tk.StringVar()
            sell_var = tk.StringVar()

            if code and code in self.app.stock_pool:
                data = self.app.stock_pool[code]
                sp = data.get('support_prices', [1.0, 1.0, 1.0])
                s1_var.set(f"{sp[0]:.2f}")
                s2_var.set(f"{sp[1]:.2f}")
                s3_var.set(f"{sp[2]:.2f}")
                buy_var.set(data.get('buy_script','') if data.get('buy_script') else "无")
                sell_var.set(data.get('sell_script','') if data.get('sell_script') else "无")
            else:
                s1_var.set("1.00")
                s2_var.set("1.00")
                s3_var.set("1.00")
                buy_var.set("无")
                sell_var.set("无")

            tk.Entry(main, textvariable=code_var, width=8).grid(row=i+2, column=0, padx=2, pady=2)
            tk.Entry(main, textvariable=s1_var, width=6).grid(row=i+2, column=1, padx=2, pady=2)
            tk.Entry(main, textvariable=s2_var, width=6).grid(row=i+2, column=2, padx=2, pady=2)
            tk.Entry(main, textvariable=s3_var, width=6).grid(row=i+2, column=3, padx=2, pady=2)
            buy_cb = ttk.Combobox(main, textvariable=buy_var, values=script_names, width=12)
            buy_cb.grid(row=i+2, column=4, padx=2, pady=2)
            sell_cb = ttk.Combobox(main, textvariable=sell_var, values=script_names, width=12)
            sell_cb.grid(row=i+2, column=5, padx=2, pady=2)

            self.row_vars.append((code_var, s1_var, s2_var, s3_var, buy_var, sell_var))

        tk.Label(main, text="播放参数", font=('微软雅黑',10,'bold')).grid(row=7, column=0, columnspan=6, pady=(15,5), sticky='w')

        row_loop = tk.Frame(main)
        row_loop.grid(row=8, column=0, columnspan=6, pady=2, sticky='w')
        tk.Label(row_loop, text="循环次数:", font=('微软雅黑',9)).pack(side='left')
        self.loop_var = tk.IntVar(value=self.app.loop_count)
        tk.Entry(row_loop, textvariable=self.loop_var, width=4).pack(side='left', padx=5)

        row_sample = tk.Frame(main)
        row_sample.grid(row=9, column=0, columnspan=6, pady=2, sticky='w')
        self.sample_var = tk.BooleanVar(value=self.app.sample_enabled.get())
        tk.Checkbutton(row_sample, text="鼠标轨迹采样", variable=self.sample_var, font=('微软雅黑',9)).pack(side='left')
        tk.Label(row_sample, text="间隔(ms):", font=('微软雅黑',9)).pack(side='left', padx=(20,2))
        self.interval_var = tk.IntVar(value=self.app.sample_interval.get())
        tk.Spinbox(row_sample, from_=1, to=100, textvariable=self.interval_var, width=4).pack(side='left')

        row_precision = tk.Frame(main)
        row_precision.grid(row=10, column=0, columnspan=6, pady=2, sticky='w')
        self.precision_var = tk.BooleanVar(value=self.app.precision_mode.get())
        tk.Checkbutton(row_precision, text="高精度回放模式", variable=self.precision_var, font=('微软雅黑',9)).pack(side='left')

        btn_frame = tk.Frame(main)
        btn_frame.grid(row=11, column=0, columnspan=6, pady=20)

        tk.Button(btn_frame, text="保存", command=self.save, bg='#1c416c', fg='white', width=10).pack(side='left', padx=10)
        tk.Button(btn_frame, text="重置", command=self.reset_all, bg='#f0ad4e', fg='white', width=10).pack(side='left', padx=10)
        tk.Button(btn_frame, text="取消", command=self.destroy, width=10).pack(side='left', padx=10)

    def reset_all(self):
        if not messagebox.askyesno("确认重置", "确定要重置所有股票池数据为默认值吗？"):
            return
        for cv, s1, s2, s3, bv, sv in self.row_vars:
            cv.set("")
            s1.set("1.00")
            s2.set("1.00")
            s3.set("1.00")
            bv.set("无")
            sv.set("无")
        self.loop_var.set(1)
        self.sample_var.set(False)
        self.interval_var.set(10)
        self.precision_var.set(False)

    def save(self):
        new_codes = []
        for i, (cv, s1, s2, s3, bv, sv) in enumerate(self.row_vars):
            code = cv.get().strip()
            if code:
                digits = re.sub(r'\D', '', code)
                if len(digits) != 6:
                    messagebox.showerror("错误", f"第{i+1}行代码无效")
                    return
                try:
                    sp1 = float(s1.get())
                    sp2 = float(s2.get())
                    sp3 = float(s3.get())
                except:
                    messagebox.showerror("错误", f"第{i+1}行参考价必须为数字")
                    return
                buy_script = bv.get() if bv.get() != "无" else ""
                sell_script = sv.get() if sv.get() != "无" else ""
                new_codes.append(digits)
                if digits not in self.app.stock_pool:
                    self.app.stock_pool[digits] = {
                        'price': 0.0,
                        'price_valid': False,
                        'support_prices': [sp1, sp2, sp3],
                        'support_processed': [False,False,False],
                        'buy_script': buy_script,
                        'sell_script': sell_script
                    }
                else:
                    old = self.app.stock_pool[digits]
                    old_support = old.get('support_prices')
                    old['support_prices'] = [sp1, sp2, sp3]
                    old['buy_script'] = buy_script
                    old['sell_script'] = sell_script
                    if old_support != [sp1, sp2, sp3]:
                        old['support_processed'] = [False,False,False]
            else:
                new_codes.append("")
        non_empty = [c for c in new_codes if c]
        if len(non_empty) != len(set(non_empty)):
            messagebox.showerror("错误", "股票代码不能重复")
            return
        self.app.stock_codes = new_codes

        self.app.loop_count = self.loop_var.get()
        self.app.sample_enabled.set(self.sample_var.get())
        self.app.sample_interval.set(self.interval_var.get())
        self.app.precision_mode.set(self.precision_var.get())

        self.app.save_config()
        self.app.refresh_monitor_display(full_rebuild=True)
        self.app.refresh_position_display(full_rebuild=False)
        self.app.update_note()
        self.destroy()


class ProfitRecordWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("历史操作记录")
        self.geometry("700x600")
        self.minsize(700, 600)
        self.transient(app.root)
        self.grab_set()

        self.current_sort_col = "买入时间"
        self.current_sort_reverse = True

        self.create_ui()
        self.refresh_history()

    def create_ui(self):
        main = tk.Frame(self)
        main.pack(fill='both', expand=True, padx=10, pady=10)

        top_frame = tk.Frame(main)
        top_frame.pack(fill='x', pady=5)

        tk.Label(top_frame, text="📈 历史操作记录", font=('微软雅黑',12,'bold')).pack(side='left')

        export_frame = tk.Frame(top_frame)
        export_frame.pack(side='right')

        tk.Label(export_frame, text="时间范围:", font=('微软雅黑',9)).pack(side='left', padx=5)
        self.time_range = tk.StringVar(value="全部")
        range_combo = ttk.Combobox(export_frame, textvariable=self.time_range, values=["全部", "最近1周", "最近1个月"], width=10, state='readonly')
        range_combo.pack(side='left', padx=5)
        range_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_history())

        export_btn = tk.Button(export_frame, text="导出CSV", command=self.export_csv, bg='#1c416c', fg='white', width=8)
        export_btn.pack(side='left', padx=5)

        columns = ("股票代码", "买入价", "卖出价", "数量", "净收益(模拟)", "净收益率", "操作类型", "买入时间", "卖出时间")
        self.tree = ttk.Treeview(main, columns=columns, show='headings', height=18)
        col_widths = [80,70,70,50,100,80,60,140,140]
        for col, w in zip(columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=w, anchor='center')
        self.tree.pack(fill='both', expand=True)

        vsb = ttk.Scrollbar(main, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')

        self.stats_label = tk.Label(main, text="", font=('微软雅黑',9), fg='#1d6b2b', anchor='w')
        self.stats_label.pack(fill='x', pady=5)

    def sort_by_column(self, col):
        if col == self.current_sort_col:
            self.current_sort_reverse = not self.current_sort_reverse
        else:
            self.current_sort_col = col
            self.current_sort_reverse = False
        self.refresh_history()

    def refresh_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        history = self.app.history
        if self.time_range.get() == "最近1周":
            cutoff = datetime.now() - timedelta(days=7)
            history = [h for h in history if self._get_time(h) >= cutoff]
        elif self.time_range.get() == "最近1个月":
            cutoff = datetime.now() - timedelta(days=30)
            history = [h for h in history if self._get_time(h) >= cutoff]

        def sort_key(record):
            if self.current_sort_col == "股票代码":
                return record.get('stock_code', '')
            elif self.current_sort_col == "买入价":
                return record.get('buy_price', 0.0)
            elif self.current_sort_col == "卖出价":
                return record.get('sell_price', 0.0) if record.get('type') == 'sell' else -1e9
            elif self.current_sort_col == "数量":
                return record.get('shares', 0)
            elif self.current_sort_col == "净收益(模拟)":
                return record.get('sold_pnl', 0.0) if record.get('type') == 'sell' else -1e9
            elif self.current_sort_col == "净收益率":
                if record.get('type') == 'sell':
                    cost = self.app.calc_buy_cost(record.get('buy_price', 0), record.get('shares', 0))
                    pnl = record.get('sold_pnl', 0.0)
                    return (pnl / cost * 100) if cost != 0 else 0
                else:
                    return -1e9
            elif self.current_sort_col == "操作类型":
                return 0 if record.get('type') == 'buy' else 1
            elif self.current_sort_col == "买入时间":
                return record.get('buy_time', '')
            elif self.current_sort_col == "卖出时间":
                return record.get('sold_time', '') if record.get('type') == 'sell' else ''
            return ''

        history.sort(key=sort_key, reverse=self.current_sort_reverse)

        total_pnl = 0.0
        profit_cnt = loss_cnt = 0

        for h in history:
            record_type = h.get('type', 'sell')
            if record_type == 'buy':
                values = (
                    h.get('stock_code', ''),
                    f"{h.get('buy_price', 0):.2f}",
                    "--",
                    h.get('shares', 0),
                    "--",
                    "--",
                    "买入",
                    h.get('buy_time', ''),
                    "--"
                )
            else:
                pnl = h.get('sold_pnl', 0.0)
                cost = self.app.calc_buy_cost(h.get('buy_price', 0), h.get('shares', 0))
                pnl_pct = (pnl / cost) * 100 if cost != 0 else 0
                sell_price = h.get('sell_price')
                values = (
                    h.get('stock_code', ''),
                    f"{h.get('buy_price', 0):.2f}",
                    f"{sell_price:.2f}" if sell_price is not None else "--",
                    h.get('shares', 0),
                    f"{pnl:+.2f}",
                    f"{pnl_pct:+.2f}%" if cost != 0 else "--",
                    "卖出",
                    h.get('buy_time', ''),
                    h.get('sold_time', '') if h.get('sold_time') else "--"
                )
                total_pnl += pnl
                if pnl > 0:
                    profit_cnt += 1
                elif pnl < 0:
                    loss_cnt += 1

            self.tree.insert('', 'end', values=values)

        stats_text = f"显示记录数: {len(history)} 笔 | 累计模拟净收益: {total_pnl:+.2f} 元 | 盈利: {profit_cnt} 笔 | 亏损: {loss_cnt} 笔"
        self.stats_label.config(text=stats_text)

    def _get_time(self, record):
        if 'type' not in record:
            t = record.get('sold_time') or record.get('buy_time')
        else:
            if record['type'] == 'buy':
                t = record.get('buy_time')
            else:
                t = record.get('sold_time') or record.get('buy_time')
        try:
            return datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.min

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="保存历史记录"
        )
        if not file_path:
            return

        history = self.app.history
        if self.time_range.get() == "最近1周":
            cutoff = datetime.now() - timedelta(days=7)
            history = [h for h in history if self._get_time(h) >= cutoff]
        elif self.time_range.get() == "最近1个月":
            cutoff = datetime.now() - timedelta(days=30)
            history = [h for h in history if self._get_time(h) >= cutoff]

        def sort_key(record):
            if self.current_sort_col == "股票代码":
                return record.get('stock_code', '')
            elif self.current_sort_col == "买入价":
                return record.get('buy_price', 0.0)
            elif self.current_sort_col == "卖出价":
                return record.get('sell_price', 0.0) if record.get('type') == 'sell' else -1e9
            elif self.current_sort_col == "数量":
                return record.get('shares', 0)
            elif self.current_sort_col == "净收益(模拟)":
                return record.get('sold_pnl', 0.0) if record.get('type') == 'sell' else -1e9
            elif self.current_sort_col == "净收益率":
                if record.get('type') == 'sell':
                    cost = self.app.calc_buy_cost(record.get('buy_price', 0), record.get('shares', 0))
                    pnl = record.get('sold_pnl', 0.0)
                    return (pnl / cost * 100) if cost != 0 else 0
                else:
                    return -1e9
            elif self.current_sort_col == "操作类型":
                return 0 if record.get('type') == 'buy' else 1
            elif self.current_sort_col == "买入时间":
                return record.get('buy_time', '')
            elif self.current_sort_col == "卖出时间":
                return record.get('sold_time', '') if record.get('type') == 'sell' else ''
            return ''

        history.sort(key=sort_key, reverse=self.current_sort_reverse)

        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["股票代码", "买入价", "卖出价", "数量", "净收益(模拟)", "净收益率", "操作类型", "买入时间", "卖出时间"])
                for h in history:
                    record_type = h.get('type', 'sell')
                    if record_type == 'buy':
                        row = [
                            h.get('stock_code', ''),
                            f"{h.get('buy_price', 0):.2f}",
                            "",
                            h.get('shares', 0),
                            "",
                            "",
                            "买入",
                            h.get('buy_time', ''),
                            ""
                        ]
                    else:
                        pnl = h.get('sold_pnl', 0.0)
                        cost = self.app.calc_buy_cost(h.get('buy_price', 0), h.get('shares', 0))
                        pnl_pct = (pnl / cost) * 100 if cost != 0 else 0
                        sell_price = h.get('sell_price')
                        row = [
                            h.get('stock_code', ''),
                            f"{h.get('buy_price', 0):.2f}",
                            f"{sell_price:.2f}" if sell_price is not None else "",
                            h.get('shares', 0),
                            f"{pnl:+.2f}",
                            f"{pnl_pct:+.2f}%" if cost != 0 else "",
                            "卖出",
                            h.get('buy_time', ''),
                            h.get('sold_time', '') if h.get('sold_time') else ""
                        ]
                    writer.writerow(row)
            messagebox.showinfo("导出成功", f"已导出 {len(history)} 条记录到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))
