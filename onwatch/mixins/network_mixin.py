# -*- coding: utf-8 -*-
import re
import time
import threading
import os
import requests
from datetime import datetime
from concurrent.futures import as_completed


class NetworkMixin:
    """网络请求与价格刷新（读写分离）"""

    def fetch_single_price(self, code_digits):
        market = 'sh' if code_digits.startswith('6') or code_digits.startswith('688') else 'sz'
        try:
            full = market + code_digits
            url = f"http://hq.sinajs.cn/list={full}"
            resp = requests.get(url, headers={'Referer':'http://finance.sina.com.cn'}, timeout=8)
            resp.encoding = 'gbk'
            text = resp.text
            m = re.search(r'\"([^\"]+)\"', text)
            if m:
                parts = m.group(1).split(',')
                if len(parts) >= 4:
                    price = float(parts[3])
                    if price > 0:
                        return code_digits, price
        except:
            pass
        try:
            market_num = '0' if market == 'sh' else '1'
            full = market_num + code_digits
            url = f"http://api.money.126.net/data/feed/{full}"
            resp = requests.get(url, headers={'Referer':'http://money.163.com'}, timeout=8)
            data = resp.json()
            stock = data.get(full, {})
            price = float(stock.get('price', 0))
            if price > 0:
                return code_digits, price
        except:
            pass
        return code_digits, 0.0

    def update_all_prices(self):
        if not self.price_update_lock.acquire(blocking=False):
            self.log("已有刷新任务，跳过")
            return
        try:
            # ---- 快照 ----
            with self.data_lock:
                positions_snapshot = self.positions.copy()
                pool_snapshot = {}
                for code, data in self.stock_pool.items():
                    pool_snapshot[code] = {
                        'price': data.get('price', 0.0),
                        'price_valid': data.get('price_valid', False),
                        'support_prices': data['support_prices'][:],
                        'support_processed': data['support_processed'][:],
                        'buy_script': data.get('buy_script', ''),
                        'sell_script': data.get('sell_script', '')
                    }
                monitor_codes = [re.sub(r'\D', '', c) for c in self.stock_codes if c.strip()]

            # ---- 网络请求（锁外） ----
            all_codes = set(monitor_codes)
            for pos in positions_snapshot:
                if not pos['sold']:
                    all_codes.add(pos['stock_code'])
            if not all_codes:
                self.root.after(0, self.refresh_monitor_display, False)
                self.root.after(0, self.refresh_position_display, False)
                return

            self.log(f"开始并发获取 {len(all_codes)} 只股票价格")
            futures = {self.executor.submit(self.fetch_single_price, code): code for code in all_codes}
            price_results = {}
            for future in as_completed(futures):
                code, price = future.result()
                if price > 0:
                    price_results[code] = price

            # ---- 计算触发动作（锁外） ----
            buy_actions = []
            for code in monitor_codes:
                if code in pool_snapshot and code in price_results:
                    price = price_results[code]
                    data = pool_snapshot[code]
                    for idx, sp in enumerate(data['support_prices']):
                        if not data['support_processed'][idx] and price <= sp:
                            buy_actions.append((code, idx, price, sp))

            # ★★★ 修改一：卖出动作收集增加 price_valid 检查 ★★★
            # 只有本次成功获取价格的股票才检查卖出条件
            sell_actions = []
            for pos in positions_snapshot:
                if pos['sold'] or pos.get('selling', False):
                    continue
                code = pos['stock_code']
                # ★ 关键：如果本次刷新没有获取到该股票的价格，跳过卖出检查
                if code not in price_results:
                    continue
                last_price = price_results[code]
                buy_price = pos['buy_price']
                shares = pos['shares']
                pnl = self.calc_net_profit(buy_price, last_price, shares)
                cost = self.calc_buy_cost(buy_price, shares)
                pnl_pct = (pnl / cost) * 100 if cost != 0 else 0
                sell_script = pos.get('sell_script', '')
                if sell_script and (pnl <= -self.stop_loss * cost / 100 or pnl_pct >= self.take_profit):
                    sell_actions.append((pos['pos_id'], last_price, pnl, sell_script))

            # ---- 应用修改（短时加锁） ----
            with self.data_lock:
                # ★★★ 修改一：先将监控股票的价格有效性全部重置为 False ★★★
                for code in monitor_codes:
                    if code in self.stock_pool:
                        self.stock_pool[code]['price_valid'] = False

                # ★★★ 修改一：只将成功获取的股票标记为有效并更新价格 ★★★
                for code, price in price_results.items():
                    if code in self.stock_pool:
                        self.stock_pool[code]['price'] = price
                        self.stock_pool[code]['price_valid'] = True
                    else:
                        self.stock_pool[code] = {
                            'price': price,
                            'price_valid': True,
                            'support_prices': [1.0, 1.0, 1.0],
                            'support_processed': [False, False, False],
                            'buy_script': '',
                            'sell_script': ''
                        }

                # 更新持仓的最新价格（只更新成功获取的股票）
                for pos in self.positions:
                    if not pos['sold'] and pos['stock_code'] in price_results:
                        pos['last_price'] = price_results[pos['stock_code']]
                        if pos['last_price'] > pos.get('highest_price', pos['buy_price']):
                            pos['highest_price'] = pos['last_price']

                # 处理买入标记
                pending_buy = []
                for code, idx, price, sp in buy_actions:
                    if code in self.stock_pool:
                        if not self.stock_pool[code]['support_processed'][idx]:
                            self.stock_pool[code]['support_processed'][idx] = True
                            pending_buy.append((code, idx, price, sp))

                # 处理卖出标记
                pending_sell = []
                for pos_id, last_price, pnl, sell_script in sell_actions:
                    for pos in self.positions:
                        if pos['pos_id'] == pos_id and not pos['sold'] and not pos.get('selling', False):
                            pos['selling'] = True
                            pos['sell_start_time'] = time.time()
                            pending_sell.append((pos_id, last_price, pnl, sell_script))
                            break

            # ---- 触发脚本（锁外） ----
            for code, idx, price, sp in pending_buy:
                data = self.stock_pool.get(code)
                if data:
                    script = data.get('buy_script', '')
                    if script:
                        def make_buy_callback(code=code, idx=idx, price=price, sp=sp):
                            def callback():
                                with self.data_lock:
                                    if code in self.stock_pool and self.stock_pool[code]['support_processed'][idx]:
                                        shares = self.shares_per_trade
                                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        pos_id = self._get_next_pos_id()
                                        sell_script = self.stock_pool[code].get('sell_script', '')
                                        self.positions.append({
                                            'pos_id': pos_id,
                                            'stock_code': code,
                                            'buy_price': sp,
                                            'shares': shares,
                                            'sold': False,
                                            'sold_pnl': None,
                                            'last_price': price,
                                            'buy_time': now,
                                            'highest_price': sp,
                                            'support_index': idx,
                                            'sell_script': sell_script
                                        })
                                        self.history.append({
                                            'type': 'buy',
                                            'stock_code': code,
                                            'buy_price': sp,
                                            'shares': shares,
                                            'buy_time': now,
                                            'sell_price': None,
                                            'sold_time': None,
                                            'sold_pnl': None
                                        })
                                        self.log(f"✅ 自动买入 {code} {sp:.2f} {shares}股")
                                        pos_snap = self.positions.copy()
                                        hist_snap = self.history.copy()
                                        self.root.after(0, lambda: self._save_positions_snapshot(pos_snap))
                                        self.root.after(0, lambda: self._save_history_snapshot(hist_snap))
                                        self.root.after(0, self.refresh_monitor_display, False)
                                        self.root.after(0, self.refresh_position_display, True)
                                    else:
                                        self.log(f"⚠️ 买入回调: {code} 参考位已失效")
                            return callback
                        self.log(f"🎬 触发买入: {code} 价格{price:.2f}≤{sp:.2f}，加入队列: {script}")
                        self.play_script_by_name(script, callback=make_buy_callback())
                    else:
                        self.log(f"⚠️ {code} 触及参考{sp:.2f}，但未配置买入脚本")

            for pos_id, last_price, pnl, sell_script in pending_sell:
                def make_sell_callback(pos_id=pos_id, last_price=last_price, pnl=pnl):
                    def callback():
                        with self.data_lock:
                            for p in self.positions:
                                if p['pos_id'] == pos_id and not p['sold']:
                                    pnl_final = self.calc_net_profit(p['buy_price'], last_price, p['shares'])
                                    p['sold'] = True
                                    p['sold_pnl'] = pnl_final
                                    p['sold_price'] = last_price
                                    p['sold_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    p.pop('selling', None)
                                    self.history.append({
                                        'type': 'sell',
                                        'stock_code': p['stock_code'],
                                        'buy_price': p['buy_price'],
                                        'shares': p['shares'],
                                        'buy_time': p['buy_time'],
                                        'sell_price': last_price,
                                        'sold_time': p['sold_time'],
                                        'sold_pnl': pnl_final
                                    })
                                    self.log(f"💰 自动卖出 {p['stock_code']} 盈亏 {pnl_final:+.2f}")
                                    pos_snap = self.positions.copy()
                                    hist_snap = self.history.copy()
                                    self.root.after(0, lambda: self._save_positions_snapshot(pos_snap))
                                    self.root.after(0, lambda: self._save_history_snapshot(hist_snap))
                                    self.root.after(0, self.refresh_position_display, True)
                                    self.root.after(0, self.update_note)
                                    self.root.after(0, self.refresh_monitor_display, False)
                                    break
                            else:
                                for p in self.positions:
                                    if p['pos_id'] == pos_id:
                                        p.pop('selling', None)
                                        break
                                self.log(f"⚠️ 自动卖出失败：持仓 {pos_id} 已不存在或已卖出")
                    return callback

                script_path = os.path.join(self.zbiao_dir, f"{sell_script}.json")
                if not os.path.exists(script_path):
                    self.log(f"⚠️ 卖出脚本 {sell_script} 不存在，直接执行卖出操作")
                    make_sell_callback()()
                else:
                    self.log(f"🎬 触发卖出: 持仓 {pos_id} 盈亏{pnl:+.2f}，加入队列: {sell_script}")
                    self.play_script_by_name(sell_script, callback=make_sell_callback())

            self.root.after(0, self.refresh_monitor_display, False)
            self.root.after(0, self.refresh_position_display, False)

        finally:
            self.price_update_lock.release()

    def manual_refresh(self):
        threading.Thread(target=self.update_all_prices, daemon=True).start()

    def schedule_auto_refresh(self):
        if not self.auto_refresh_enabled:
            return
        self.root.after(60000, self.auto_refresh)

    def auto_refresh(self):
        if not self.auto_refresh_enabled:
            return
        threading.Thread(target=self.update_all_prices, daemon=True).start()
        self.schedule_auto_refresh()

    def toggle_auto_refresh(self):
        self.auto_refresh_enabled = self.auto_refresh_var.get()
        if self.auto_refresh_enabled:
            self.schedule_auto_refresh()
            self.log("自动刷新已启用")
        else:
            self.log("自动刷新已禁用")
