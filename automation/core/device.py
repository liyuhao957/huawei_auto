#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设备控制模块 - 包含与设备交互的基本操作
"""

import subprocess
import time
import logging

class DeviceController:
    """设备基础操作控制器，封装ADB命令操作"""
    
    def __init__(self, logger=None):
        """初始化设备控制器
        
        Args:
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.logger = logger or logging.getLogger("device")
        self.screen_width = None
        self.screen_height = None
    
    def set_screen_dimensions(self, width, height):
        """设置屏幕尺寸
        
        Args:
            width: 屏幕宽度
            height: 屏幕高度
        """
        self.screen_width = width
        self.screen_height = height
        self.logger.info(f"设置屏幕尺寸: {width}x{height}")
    
    def tap(self, x, y):
        """点击指定坐标
        
        Args:
            x: X坐标
            y: Y坐标
        """
        cmd = f"adb shell input tap {x} {y}"
        self.logger.info(f"点击坐标: ({x}, {y})")
        subprocess.run(cmd, shell=True)
        
    def tap_by_percent(self, x_percent, y_percent):
        """基于屏幕百分比位置点击
        
        Args:
            x_percent: X坐标的百分比 (0.0-1.0)
            y_percent: Y坐标的百分比 (0.0-1.0)
        """
        if not self.screen_width or not self.screen_height:
            self.logger.warning("屏幕尺寸未设置，无法使用百分比点击")
            return
            
        x = int(self.screen_width * x_percent)
        y = int(self.screen_height * y_percent)
        self.tap(x, y)
        
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动屏幕
        
        Args:
            start_x: 起始X坐标
            start_y: 起始Y坐标
            end_x: 结束X坐标
            end_y: 结束Y坐标
            duration: 滑动持续时间(毫秒)
        """
        cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        self.logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        subprocess.run(cmd, shell=True)
    
    def swipe_by_percent(self, start_x_percent, start_y_percent, end_x_percent, end_y_percent, duration=300):
        """基于屏幕百分比位置滑动
        
        Args:
            start_x_percent: 起始X坐标的百分比 (0.0-1.0)
            start_y_percent: 起始Y坐标的百分比 (0.0-1.0)
            end_x_percent: 结束X坐标的百分比 (0.0-1.0)
            end_y_percent: 结束Y坐标的百分比 (0.0-1.0)
            duration: 滑动持续时间(毫秒)
        """
        if not self.screen_width or not self.screen_height:
            self.logger.warning("屏幕尺寸未设置，无法使用百分比滑动")
            return
            
        start_x = int(self.screen_width * start_x_percent)
        start_y = int(self.screen_height * start_y_percent)
        end_x = int(self.screen_width * end_x_percent)
        end_y = int(self.screen_height * end_y_percent)
        self.swipe(start_x, start_y, end_x, end_y, duration)
        
    def press_key(self, keycode):
        """按下按键
        
        Args:
            keycode: 按键码或按键名称
        """
        cmd = f"adb shell input keyevent {keycode}"
        self.logger.info(f"按下按键: {keycode}")
        subprocess.run(cmd, shell=True)
        
    def press_home(self):
        """按下Home键"""
        self.logger.info("按下Home键")
        self.press_key("KEYCODE_HOME")
        
    def press_enter(self):
        """按下回车键"""
        self.logger.info("按下回车键")
        self.press_key("66")
        
    def press_back(self):
        """按下返回键"""
        self.logger.info("按下返回键")
        self.press_key("KEYCODE_BACK")
        
    def press_recent_apps(self):
        """打开最近任务列表"""
        self.logger.info("打开最近任务列表")
        self.press_key("KEYCODE_APP_SWITCH")
        
    def run_shell_command(self, command):
        """运行shell命令并返回输出
        
        Args:
            command: 要执行的shell命令
            
        Returns:
            str: 命令的标准输出
        """
        self.logger.info(f"运行命令: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        self.logger.info(f"命令输出: {result.stdout}")
        return result.stdout 