# -*- coding: utf-8 -*-
import time
import threading
import json
import os
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode
from pynput.mouse import Button


class PlaybackMixin:
    """键鼠脚本回放引擎"""

    # ---------- 热键 ----------
    def on_key_press(self, key):
        try:
            if hasattr(key, 'name') and key.name == 'esc':
                self.save_config()
                self.save_positions()
                self.save_history()
                os._exit(0)
                return True
        except AttributeError:
            pass
        return False

    # ---------- 脚本队列 ----------
    def play_script_by_name(self, name, loop=None, callback=None):
        if not name:
            return
        if loop is None:
            loop = self.loop_count
        filename = os.path.join(self.zbiao_dir, f"{name}.json")
        if not os.path.exists(filename):
            self.log(f"脚本文件不存在: {filename}")
            return
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception as e:
            self.log(f"读取脚本失败 {name}: {e}")
            return
        with self.queue_lock:
            self.script_queue.append((events, loop, callback))
            self.log(f"脚本 '{name}' 已加入播放队列")
            if not self.queue_processing:
                self.queue_processing = True
                self.root.after(0, self._process_script_queue)

    def _process_script_queue(self):
        with self.queue_lock:
            if not self.script_queue:
                self.queue_processing = False
                return
            events, loop, callback = self.script_queue.pop(0)

        self.playback_active = True
        self.stop_playback_flag = False
        self.log(f"开始回放，循环{loop}次")
        self.hide_window()
        threading.Thread(target=self._playback_thread, args=(events, loop, callback), daemon=True).start()

    def _playback_thread(self, events, loop, callback=None):
        try:
            for i in range(loop):
                if self.stop_playback_flag:
                    self.log("回放中断")
                    break
                if i>0:
                    time.sleep(1)
                start = time.perf_counter()
                for rel, etype, data in events:
                    if self.stop_playback_flag:
                        break
                    target = start + rel
                    now = time.perf_counter()
                    dt = target - now
                    if dt > 0:
                        if self.precision_mode.get() and dt < 0.01:
                            while time.perf_counter() < target:
                                pass
                        else:
                            time.sleep(dt)
                    self._execute_event(etype, data)
        except Exception as e:
            self.log(f"回放异常: {e}")
        finally:
            self.playback_active = False
            self.stop_playback_flag = False
            self.log("回放结束")
            self.show_window()
            if callback:
                self.root.after(0, callback)
            self.root.after(0, self._process_script_queue)

    def _execute_event(self, etype, data):
        try:
            if etype == 'kp':
                key = self._data_to_key(data)
                if key:
                    self.keyboard_controller.press(key)
            elif etype == 'kr':
                key = self._data_to_key(data)
                if key:
                    self.keyboard_controller.release(key)
            elif etype == 'mm':
                self.mouse_controller.position = data
            elif etype == 'mc':
                x,y,btn_str,pressed = data
                btn = getattr(Button, btn_str)
                self.mouse_controller.position = (x,y)
                if pressed: self.mouse_controller.press(btn)
                else: self.mouse_controller.release(btn)
            elif etype == 'ms':
                x,y,dx,dy = data
                self.mouse_controller.position = (x,y)
                self.mouse_controller.scroll(dx,dy)
        except Exception as e:
            self.log(f"事件执行失败 {etype}: {e}")

    def _data_to_key(self, key_info):
        typ, val = key_info
        try:
            if typ == 'special':
                try:
                    return getattr(Key, val)
                except AttributeError:
                    for k in Key:
                        if k.name == val:
                            return k
                    return None
            elif typ == 'vk':
                if isinstance(val, int) and 96 <= val <= 105:
                    return KeyCode(vk=val)
                else:
                    return KeyCode.from_vk(val)
            else:
                return KeyCode(char=val) if val else None
        except Exception as e:
            self.log(f"键转换失败: {typ}:{val} - {e}")
            return None

    # ---------- 窗口显隐 ----------
    def hide_window(self):
        self.root.after(0, self._do_hide)

    def _do_hide(self):
        self.root.withdraw()

    def show_window(self):
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
