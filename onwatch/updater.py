# -*- coding: utf-8 -*-
import requests
import threading
import webbrowser
import os
import sys
from tkinter import messagebox, Toplevel, Button, Label, Frame
from packaging import version
from .version import VERSION, get_version

# 强制绕过 SSL 验证（解决 GitHub API 证书问题）
VERIFY_PATH = False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UpdateChecker:
    def __init__(self, app):
        self.app = app
        self.api_url = "https://api.github.com/repos/inxtoot/OnWatch/releases/latest"
        self.current_version = VERSION

        # ★ 所有镜像 URL 都改为指向 OnWatch_{}.exe（与 Release 中的实际文件名匹配）
        self.mirror_urls = [
            {
                "name": "ghproxy.net",
                "url": "https://ghproxy.net/https://github.com/inxtoot/OnWatch/releases/download/{}/OnWatch_{}.exe"
            },
            {
                "name": "ghproxy.cxkpro.top",
                "url": "https://ghproxy.cxkpro.top/https://github.com/inxtoot/OnWatch/releases/download/{}/OnWatch_{}.exe"
            },
            {
                "name": "gitclone.com",
                "url": "https://gitclone.com/inxtoot/OnWatch/releases/download/{}/OnWatch_{}.exe"
            },
            {
                "name": "GitHub 官方",
                "url": "https://github.com/inxtoot/OnWatch/releases/download/{}/OnWatch_{}.exe"
            }
        ]

    def check_for_updates(self, show_no_update=False):
        def _check():
            try:
                print("🔍 开始检查更新...")
                response = requests.get(
                    self.api_url,
                    timeout=10,
                    verify=VERIFY_PATH,
                    headers={'User-Agent': 'OnWatch/1.0'}
                )
                print(f"📡 HTTP 状态码: {response.status_code}")

                if response.status_code == 404:
                    print("⚠️ 404: 没有找到 Release")
                    return

                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get("tag_name", "")
                    print(f"📦 最新版本: {latest_version}")
                    print(f"📦 当前版本: {self.current_version}")

                    if latest_version and version.parse(latest_version) > version.parse(self.current_version):
                        print("✅ 检测到新版本！")
                        self.app.root.after(0, lambda: self._show_update_dialog(
                            latest_version,
                            self.current_version,
                            data.get("body", "暂无更新说明。")
                        ))
                        return

            except Exception as e:
                print(f"❌ 更新检查失败: {e}")

            if show_no_update:
                self.app.root.after(0, lambda: messagebox.showinfo("检查更新", "当前已是最新版本。"))

        threading.Thread(target=_check, daemon=True).start()

    def _show_update_dialog(self, latest_version, current_version, release_notes):
        dialog = Toplevel(self.app.root)
        dialog.title("发现新版本")
        dialog.geometry("450x250")
        dialog.minsize(450, 250)
        dialog.maxsize(450, 250)
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)

        main_frame = Frame(dialog, padx=20, pady=15)
        main_frame.pack(fill='both', expand=True)

        version_label = Label(
            main_frame,
            text=f"检测到新版本 {latest_version}（当前版本 {current_version}）",
            font=('微软雅黑', 10),
            anchor='w',
            justify='left'
        )
        version_label.pack(anchor='w', pady=(0, 5))

        hint_label = Label(
            main_frame,
            text="请选择下载镜像（若镜像失效请换另一个）：",
            font=('微软雅黑', 9),
            fg='#555555',
            anchor='w',
            justify='left'
        )
        hint_label.pack(anchor='w', pady=(0, 15))

        btn_frame = Frame(main_frame)
        btn_frame.pack(fill='x', pady=(0, 15))

        for i, mirror in enumerate(self.mirror_urls):
            row = i // 2
            col = i % 2
            btn = Button(
                btn_frame,
                text=mirror["name"],
                font=('微软雅黑', 9),
                bg='#f0f0f0',
                relief='raised',
                padx=15,
                pady=5,
                width=16,
                command=lambda url=mirror["url"], tag=latest_version: self._download_update(dialog, url, tag)
            )
            btn.grid(row=row, column=col, padx=10, pady=5, sticky='ew')

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        btn_bottom_frame = Frame(main_frame)
        btn_bottom_frame.pack(fill='x', pady=(10, 0))

        cancel_btn = Button(
            btn_bottom_frame,
            text="暂不更新",
            font=('微软雅黑', 9),
            bg='#e0e0e0',
            padx=20,
            pady=5,
            command=dialog.destroy
        )
        cancel_btn.pack(side='right')

    def _download_update(self, dialog, url_template, tag):
        # ★ 关键修改：两个 {} 占位符，分别替换为 tag（版本号）和 tag（文件名中的版本号）
        download_url = url_template.format(tag, tag)
        print(f"🌐 下载链接: {download_url}")
        webbrowser.open(download_url)
        dialog.destroy()

        messagebox.showinfo(
            "下载提示",
            "浏览器已打开下载页面。\n\n"
            "如果未自动开始下载，请点击页面中的 'Download' 或类似按钮。\n"
            "下载完成后，请关闭当前运行的程序，然后运行新版本。"
        )


# 为了兼容旧代码，保留 get_version 函数
def get_version():
    return VERSION
