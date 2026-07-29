#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OnWatch v1.7.1（学习版） - 启动入口
"""

from onwatch.main_app import IntegratedApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = IntegratedApp(root)
    root.mainloop()
