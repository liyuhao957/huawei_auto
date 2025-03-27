#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快应用相关配置
"""

# 要测试的快应用列表，每个应用是一个字典
QUICK_APPS = [
    {
        "name": "优购",
        "package": "com.huawei.fastapp",
        "test_params": {}  # 可添加应用特定的测试参数
    },
    {
        "name": "买乐多",
        "package": "com.huawei.fastapp",
        "test_params": {}
    },
    {
        "name": "易折特惠",
        "package": "com.huawei.fastapp",
        "test_params": {}
    }
    # 可以添加更多应用...
]

# 应用之间的等待时间（秒）
APP_INTERVAL_SECONDS = 30

# 保留现有的单一应用配置，兼容旧代码
SEARCH_KEYWORD = QUICK_APPS[0]["name"]
QUICK_APP_PACKAGE = "com.huawei.fastapp" 