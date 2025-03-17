#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
单字符输入测试脚本
测试在华为设备上通过ADB逐个字符输入中文文本
"""

import subprocess
import time
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("char_input_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CharInputTester")

# 设备屏幕尺寸（请根据实际设备调整）
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2376

def tap(x, y):
    """点击指定坐标"""
    cmd = f"adb shell input tap {x} {y}"
    logger.info(f"点击坐标: ({x}, {y})")
    subprocess.run(cmd, shell=True)
    
def tap_by_percent(x_percent, y_percent):
    """基于屏幕百分比位置点击"""
    x = int(SCREEN_WIDTH * x_percent)
    y = int(SCREEN_HEIGHT * y_percent)
    tap(x, y)
    
def press_key(keycode):
    """按下按键"""
    cmd = f"adb shell input keyevent {keycode}"
    logger.info(f"按下按键: {keycode}")
    subprocess.run(cmd, shell=True)

def input_text_char_by_char(text):
    """分字符逐个输入文本"""
    logger.info(f"逐字符输入文本: {text}")
    
    # 逐个字符输入
    for char in text:
        logger.info(f"输入字符: {char}")
        if char == ' ':
            # 空格键
            press_key("KEYCODE_SPACE")
        elif '0' <= char <= '9':
            # 数字键
            keycode = f"KEYCODE_{char}"
            press_key(keycode)
        else:
            # 其他字符（包括中文）
            cmd = f'adb shell input text "{char}"'
            subprocess.run(cmd, shell=True)
        
        # 每个字符之间稍微暂停一下
        time.sleep(0.5)
    
    logger.info("文本输入完成")

def run_test():
    """运行测试"""
    logger.info("===== 开始测试字符逐个输入 =====")
    
    # 1. 按Home键回到桌面
    logger.info("步骤1: 按Home键回到桌面")
    press_key("KEYCODE_HOME")
    time.sleep(1)
    
    # 2. 打开设置应用
    logger.info("步骤2: 打开设置应用")
    subprocess.run("adb shell am start -a android.settings.SETTINGS", shell=True)
    time.sleep(2)
    
    # 3. 点击搜索框
    logger.info("步骤3: 点击搜索框")
    tap_by_percent(0.256, 0.217)  # 坐标: (276, 516)，根据实际情况调整
    time.sleep(1)
    
    # 4. 输入"应用和服务"
    logger.info("步骤4: 输入'应用和服务'")
    input_text_char_by_char("应用和服务")
    
    # 等待几秒观察结果
    logger.info("等待5秒钟观察结果...")
    time.sleep(5)
    
    logger.info("测试完成")

if __name__ == "__main__":
    run_test() 