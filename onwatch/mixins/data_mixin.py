# -*- coding: utf-8 -*-
import json
import os
import threading
import time
import logging
import logging.handlers
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox


class DataMixin:
    """数据持久化、交易计算、手动买卖、日志（带轮转 + 备份恢复）"""

    # ---------- 日志（使用 logging 模块，自动轮转） ----------
    def _get_logger(self):
        """懒加载一个带轮转的日志记录器"""
        if not hasattr(self, '_rotating_logger'):
            self._rotating_logger = logging.getLogger('OnWatch')
            self._rotating_logger.setLevel(logging.INFO)
            if not self._rotating_logger.handlers:
                # 标准型配置：单文件 5MB，保留 20 个备份，总占用约 105 MB
                handler = logging.handlers.RotatingFileHandler(
                    self.log_file,
                    maxBytes=5 * 1024 * 1024,  # 5 MB
                    backupCount=20,            # 20 个备份
                    encoding='utf-8'
                )
                formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
                handler.setFormatter(formatter)
                self._rotating_logger.addHandler(handler)
        return self._rotating_logger

    def log(self, msg):
        """同时输出到 GUI 文本框和日志文件（文件部分自动轮转）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"{timestamp} - {msg}\n"

        def _add():
            if hasattr(self, 'log_text') and self.log_text:
                self.log_text.config(state='normal')
                self.log_text.insert('end', log_line)
                self.log_text.see('end')
                self.log_text.config(state='disabled')
            self._get_logger().info(msg)

        if threading.current_thread() is threading.main_thread():
            _add()
        else:
            self.root.after(0, _add)

    # ---------- 配置保存/加载（带备份恢复） ----------
    def save_config(self):
        """保存配置：原子写入 + 备份"""
        geometry = self.root.geometry()
        try:
            # 窗口几何配置单独保存
            self._save_json_atomically(self.window_geometry_file, {'window_geometry': geometry})
        except Exception as e:
            self.log(f"保存窗口几何失败: {e}")

        with self.data_lock:
            settings = {
                'stock_codes': self.stock_codes,
                'stock_pool': self.stock_pool,
                'shares_per_trade': self.shares_per_trade,
                'take_profit': self.take_profit,
                'stop_loss': self.stop_loss,
                'loop_count': self.loop_count,
                'sample_enabled': self.sample_enabled.get(),
                'sample_interval': self.sample_interval.get(),
                'precision_mode': self.precision_mode.get(),
                'password': self.password
            }
        try:
            self._save_json_atomically(self.settings_file, settings)
        except Exception as e:
            self.log(f"保存设置失败: {e}")

    def load_config(self):
        """加载配置：主文件损坏时自动从备份恢复"""
        # 加载窗口几何
        if os.path.exists(self.window_geometry_file):
            data = self._load_json_with_backup(self.window_geometry_file)
            if data and 'window_geometry' in data:
                self.root.geometry(data['window_geometry'])

        # 加载其他设置
        if os.path.exists(self.settings_file):
            data = self._load_json_with_backup(self.settings_file)
            if data:
                with self.data_lock:
                    self.stock_codes = data.get('stock_codes', self.stock_codes)
                    self.stock_pool = data.get('stock_pool', {})
                    for v in self.stock_pool.values():
                        v.setdefault('support_processed', [False, False, False])
                        v.setdefault('price_valid', False)
                        v.setdefault('buy_script', '')
                        v.setdefault('sell_script', '')
                    self.shares_per_trade = data.get('shares_per_trade', self.shares_per_trade)
                    self.take_profit = data.get('take_profit', 1.0)
                    self.stop_loss = data.get('stop_loss', 1.0)
                    self.loop_count = data.get('loop_count', 1)
                    self.sample_enabled.set(data.get('sample_enabled', False))
                    self.sample_interval.set(data.get('sample_interval', 10))
                    self.precision_mode.set(data.get('precision_mode', False))
                    self.password = data.get('password', '123')

    # ---------- 原子写入和备份恢复工具函数 ----------
    def _save_json_atomically(self, filepath, data):
        """原子方式保存 JSON：先写临时文件，再替换，同时备份"""
        temp_file = filepath + '.tmp'
        backup_file = filepath + '.bak'

        # 写入临时文件
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # 确保数据写入磁盘

        # 原子替换
        os.replace(temp_file, filepath)

        # 同时备份一份
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_json_with_backup(self, filepath):
        """加载 JSON：主文件失败时自动从备份恢复"""
        # 尝试加载主文件
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            self.log(f"加载 {filepath} 失败: {e}，尝试从备份恢复")

        # 尝试从备份恢复
        backup_file = filepath + '.bak'
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.log(f"✅ 从备份 {backup_file} 恢复成功")
                # 将恢复的数据写回主文件
                try:
                    self._save_json_atomically(filepath, data)
                except Exception as e2:
                    self.log(f"恢复后写入主文件失败: {e2}")
                return data
            except Exception as e:
                self.log(f"从备份恢复失败: {e}")

        self.log(f"⚠️ 无法恢复 {filepath}，使用默认值")
        return None

    # ---------- 持仓保存/加载（带备份恢复） ----------
    def _save_positions_snapshot(self, snapshot):
        """保存持仓快照（原子写入 + 备份）"""
        data = {'positions': snapshot, 'next_pos_id': self.next_pos_id}
        self._save_json_atomically(self.positions_file, data)

    def save_positions(self):
        with self.data_lock:
            data = {'positions': self.positions, 'next_pos_id': self.next_pos_id}
        self._save_json_atomically(self.positions_file, data)

    def load_positions(self):
        if not os.path.exists(self.positions_file):
            self.positions = []
            self.next_pos_id = 0
            return

        data = self._load_json_with_backup(self.positions_file)
        if data:
            with self.data_lock:
                self.positions = data.get('positions', [])
                self.next_pos_id = data.get('next_pos_id', 0)
                for p in self.positions:
                    p.setdefault('pos_id', 0)
                    p.setdefault('last_price', None)
                    p.setdefault('sold_price', 0.0)
                    p.setdefault('sold_time', '')
                    p.setdefault('buy_time', '')
                    p.setdefault('highest_price', p['buy_price'])
                    p.setdefault('support_index', None)
                    p.setdefault('sell_script', '')
                    p.setdefault('selling', False)
                if self.positions:
                    max_id = max(p['pos_id'] for p in self.positions)
                    if self.next_pos_id <= max_id:
                        self.next_pos_id = max_id + 1
            self.log(f"已加载 {len(self.positions)} 条持仓记录")
        else:
            self.positions = []
            self.next_pos_id = 0

    # ---------- 历史保存/加载（带备份恢复） ----------
    def _save_history_snapshot(self, snapshot):
        """保存历史快照（原子写入 + 备份）"""
        cutoff = datetime.now() - timedelta(days=35)
        filtered = []
        for h in snapshot:
            if 'type' not in h:
                t_str = h.get('sold_time') or h.get('buy_time')
            else:
                if h['type'] == 'buy':
                    t_str = h.get('buy_time')
                else:
                    t_str = h.get('sold_time') or h.get('buy_time')
            try:
                t = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S')
                if t >= cutoff:
                    filtered.append(h)
            except:
                filtered.append(h)
        self._save_json_atomically(self.history_file, filtered)

    def save_history(self):
        cutoff = datetime.now() - timedelta(days=35)
        filtered = []
        with self.data_lock:
            for h in self.history:
                if 'type' not in h:
                    t_str = h.get('sold_time') or h.get('buy_time')
                else:
                    if h['type'] == 'buy':
                        t_str = h.get('buy_time')
                    else:
                        t_str = h.get('sold_time') or h.get('buy_time')
                try:
                    t = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S')
                    if t >= cutoff:
                        filtered.append(h)
                except:
                    filtered.append(h)
            self.history = filtered
        self._save_json_atomically(self.history_file, filtered)

    def load_history(self):
        if not os.path.exists(self.history_file):
            self.history = []
            return

        data = self._load_json_with_backup(self.history_file)
        if data:
            with self.data_lock:
                self.history = data
            self.log(f"已加载 {len(self.history)} 条历史记录")
        else:
            self.history = []

    # ---------- 交易费用计算 ----------
    def calc_buy_cost(self, price, shares):
        return price * shares * (1 + self.commission_rate + self.transfer_fee_rate)

    def calc_sell_proceeds(self, price, shares):
        return price * shares * (1 - self.commission_rate - self.stamp_tax_rate - self.transfer_fee_rate)

    def calc_net_profit(self, buy_price, sell_price, shares):
        return self.calc_sell_proceeds(sell_price, shares) - self.calc_buy_cost(buy_price, shares)

    # ---------- 手动买卖 ----------
    def manual_buy(self, code, idx):
        with self.data_lock:
            if code not in self.stock_pool:
                return
            data = self.stock_pool[code]
            if data['support_processed'][idx]:
                return
            buy_price = data['support_prices'][idx]
            shares = self.shares_per_trade
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            pos_id = self._get_next_pos_id()
            sell_script = data.get('sell_script', '')
            self.positions.append({
                'pos_id': pos_id,
                'stock_code': code,
                'buy_price': buy_price,
                'shares': shares,
                'sold': False,
                'sold_pnl': None,
                'last_price': data.get('price', 0.0),
                'buy_time': now,
                'highest_price': buy_price,
                'support_index': idx,
                'sell_script': sell_script
            })
            self.history.append({
                'type': 'buy',
                'stock_code': code,
                'buy_price': buy_price,
                'shares': shares,
                'buy_time': now,
                'sell_price': None,
                'sold_time': None,
                'sold_pnl': None
            })
            data['support_processed'][idx] = True
            self.log(f"✅ 手动买入 {code} {buy_price:.2f} {shares}股")
            pos_snap = self.positions.copy()
            hist_snap = self.history.copy()
        self._save_positions_snapshot(pos_snap)
        self._save_history_snapshot(hist_snap)
        self.refresh_monitor_display(full_rebuild=False)
        self.refresh_position_display(full_rebuild=True)

    def manual_sell(self, pos_id):
        with self.data_lock:
            for pos in self.positions:
                if pos['pos_id'] == pos_id and not pos['sold']:
                    sell_price = pos.get('last_price')
                    if sell_price is None or sell_price <= 0:
                        self.root.after(0, lambda: self._ask_sell_without_price(pos_id))
                        return
                    pnl = self.calc_net_profit(pos['buy_price'], sell_price, pos['shares'])
                    pos['sold'] = True
                    pos['sold_pnl'] = pnl
                    pos['sold_price'] = sell_price
                    pos['sold_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    pos.pop('selling', None)
                    self.history.append({
                        'type': 'sell',
                        'stock_code': pos['stock_code'],
                        'buy_price': pos['buy_price'],
                        'shares': pos['shares'],
                        'buy_time': pos['buy_time'],
                        'sell_price': sell_price,
                        'sold_time': pos['sold_time'],
                        'sold_pnl': pnl
                    })
                    self.log(f"💰 手动卖出 {pos['stock_code']} 盈亏 {pnl:+.2f}")
                    pos_snap = self.positions.copy()
                    hist_snap = self.history.copy()
                    self.root.after(0, lambda: self._save_positions_snapshot(pos_snap))
                    self.root.after(0, lambda: self._save_history_snapshot(hist_snap))
                    self.root.after(0, self.refresh_position_display, True)
                    self.root.after(0, self.update_note)
                    self.root.after(0, self.refresh_monitor_display, False)
                    return
            self.log(f"⚠️ 手动卖出失败：持仓ID {pos_id} 不存在或已卖出")

    def _ask_sell_without_price(self, pos_id):
        if messagebox.askyesno("价格无效", "当前无有效价格，是否仍按0元卖出？"):
            with self.data_lock:
                for pos in self.positions:
                    if pos['pos_id'] == pos_id and not pos['sold']:
                        pnl = self.calc_net_profit(pos['buy_price'], 0.0, pos['shares'])
                        pos['sold'] = True
                        pos['sold_pnl'] = pnl
                        pos['sold_price'] = 0.0
                        pos['sold_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        pos.pop('selling', None)
                        self.history.append({
                            'type': 'sell',
                            'stock_code': pos['stock_code'],
                            'buy_price': pos['buy_price'],
                            'shares': pos['shares'],
                            'buy_time': pos['buy_time'],
                            'sell_price': 0.0,
                            'sold_time': pos['sold_time'],
                            'sold_pnl': pnl
                        })
                        self.log(f"💰 手动卖出 {pos['stock_code']}（无价格） 盈亏 {pnl:+.2f}")
                        pos_snap = self.positions.copy()
                        hist_snap = self.history.copy()
                        self.root.after(0, lambda: self._save_positions_snapshot(pos_snap))
                        self.root.after(0, lambda: self._save_history_snapshot(hist_snap))
                        self.root.after(0, self.refresh_position_display, True)
                        self.root.after(0, self.update_note)
                        self.root.after(0, self.refresh_monitor_display, False)
                        break

    # ---------- 清空已卖出 ----------
    def clear_sold_positions(self):
        with self.data_lock:
            if not any(p['sold'] for p in self.positions):
                messagebox.showinfo("提示", "当前持仓区没有已卖出的记录")
                return
            if not messagebox.askyesno("确认清空", "确定要清空持仓区所有已卖出的记录吗？\n（历史记录窗口仍会保留所有历史）"):
                return
            self.positions = [p for p in self.positions if not p['sold']]
            pos_snap = self.positions.copy()
        self._save_positions_snapshot(pos_snap)
        self.refresh_position_display(full_rebuild=True)
        self.update_note()
        self.log("已清空持仓区所有已卖出记录")

    # ---------- 辅助 ----------
    def _get_next_pos_id(self):
        self.next_pos_id += 1
        return self.next_pos_id

    def update_note(self):
        with self.data_lock:
            loss_count = sum(1 for p in self.positions if not p['sold'] and p.get('last_price') and self.calc_net_profit(p['buy_price'], p['last_price'], p['shares']) <= -self.stop_loss * self.calc_buy_cost(p['buy_price'], p['shares']) / 100)
        self.note_label.config(text=f"⏳ 亏损警戒:{loss_count}")

    # ---------- 关闭 ----------
    def on_closing(self):
        self.save_config()
        self.save_positions()
        self.save_history()
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.root.destroy()
