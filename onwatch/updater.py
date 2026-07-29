# -*- coding: utf-8 -*-
import requests
import threading
import webbrowser
from tkinter import messagebox
from packaging import version

class UpdateChecker:
    def __init__(self, app):
        self.app = app
        # 定义你的 GitHub 仓库地址和当前版本
        self.repo_url = "https://api.github.com/repos/inxtoot/OnWatch/releases/latest"
        self.current_version = "v1.6"  # 与你的程序版本保持一致

    def check_for_updates(self, show_no_update=False):
        """在后台线程中检查更新"""
        def _check():
            try:
                response = requests.get(self.repo_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get("tag_name", "")
                    # 解析版本号并比较
                    if latest_version and version.parse(latest_version) > version.parse(self.current_version):
                        # 发现新版本，在主线程中弹出提示
                        self.app.root.after(0, lambda: self._prompt_update(data))
                        return
                
                # 没有新版本，且用户主动点击了“检查更新”
                if show_no_update:
                    self.app.root.after(0, lambda: messagebox.showinfo("检查更新", "当前已是最新版本。"))
            except Exception as e:
                print(f"更新检查失败: {e}")
                if show_no_update:
                    self.app.root.after(0, lambda: messagebox.showerror("检查更新", f"无法连接更新服务器:\n{e}"))

        # 启动一个后台线程执行检查，避免阻塞 GUI
        threading.Thread(target=_check, daemon=True).start()

    def _prompt_update(self, release_data):
        """弹出更新提示对话框"""
        latest_version = release_data.get("tag_name", "未知")
        body = release_data.get("body", "暂无更新说明。")
        # 截取更新说明的前200个字符作为预览
        preview = body[:200] + ("..." if len(body) > 200 else "")
        
        result = messagebox.askyesno(
            "发现新版本",
            f"发现新版本 {latest_version}！\n\n更新说明：\n{preview}\n\n是否前往 GitHub 查看并下载？"
        )
        if result:
            # 打开 GitHub Releases 页面
            webbrowser.open("https://github.com/inxtoot/OnWatch/releases/latest")