# -*- coding: utf-8 -*-
"""
OnWatch 版本号管理（集中管理）
所有版本号统一从此文件读取，修改版本号只需修改此处。
"""

VERSION = "v1.8.0"


def get_version():
    """返回当前版本号"""
    return VERSION
