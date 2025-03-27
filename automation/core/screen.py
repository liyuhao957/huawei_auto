#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
屏幕状态管理模块 - 处理屏幕检测、唤醒和解锁
"""

import subprocess
import time
import logging

class ScreenManager:
    """屏幕状态管理器，处理设备屏幕相关操作"""
    
    def __init__(self, device_controller, logger=None):
        """初始化屏幕管理器
        
        Args:
            device_controller: 设备控制器实例
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.device = device_controller
        self.logger = logger or logging.getLogger("screen")
    
    def check_screen_state(self):
        """检查屏幕状态，使用mHoldingDisplaySuspendBlocker标志
        
        Returns:
            bool: 屏幕亮起返回True，熄屏返回False
        """
        self.logger.info("检查屏幕状态")
        
        # 使用mHoldingDisplaySuspendBlocker检查
        cmd = "adb shell dumpsys power | grep 'mHoldingDisplaySuspendBlocker'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            if "true" in result.stdout.lower():
                self.logger.info("屏幕状态为亮屏 (mHoldingDisplaySuspendBlocker=true)")
                return True
            elif "false" in result.stdout.lower():
                self.logger.info("屏幕状态为熄屏 (mHoldingDisplaySuspendBlocker=false)")
                return False
            
        # 如果无法确定，尝试其他方法
        self.logger.warning("无法通过mHoldingDisplaySuspendBlocker确定屏幕状态，尝试其他方法")
        
        # 尝试检查前台应用活动
        cmd = "adb shell dumpsys activity activities | grep -A 3 'mResumedActivity'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout and len(result.stdout.strip()) > 10:
            self.logger.info("检测到前台应用活动，屏幕可能处于亮屏状态")
            return True
        else:
            self.logger.info("未检测到前台应用活动，屏幕可能处于熄屏状态")
            return False
            
    def wake_screen(self):
        """尝试唤醒屏幕
        
        Returns:
            bool: 是否成功唤醒屏幕
        """
        self.logger.info("尝试唤醒屏幕")
        
        # 使用电源键唤醒
        self.logger.info("使用电源键唤醒")
        self.device.press_key("KEYCODE_POWER")
        time.sleep(2)  # 等待屏幕响应
        
        # 检查是否成功唤醒
        if self.check_screen_state():
            self.logger.info("成功唤醒屏幕")
            return True
        
        self.logger.warning("电源键唤醒失败，尝试备用方法")
        
        # 备用方法：使用WAKEUP键码
        self.logger.info("使用WAKEUP键码唤醒")
        self.device.press_key("KEYCODE_WAKEUP")
        time.sleep(2)
        
        if self.check_screen_state():
            self.logger.info("成功使用WAKEUP键码唤醒屏幕")
            return True
            
        self.logger.warning("所有唤醒方法均失败")
        return False
    
    def simple_unlock(self):
        """简单解锁屏幕（适用于无密码设备）
        
        Returns:
            bool: 是否成功解锁
        """
        self.logger.info("尝试简单解锁屏幕")
        
        # 滑动解锁
        self.device.swipe_by_percent(0.5, 0.7, 0.5, 0.3)
        time.sleep(1)
        
        # 按Home键确认
        self.device.press_home()
        time.sleep(1)
        
        # 检查是否到达桌面
        cmd = "adb shell dumpsys activity activities | grep mResumedActivity"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout and "Launcher" in result.stdout:
            self.logger.info("成功解锁到桌面")
            return True
        else:
            self.logger.info("简单解锁操作已执行，但未确认是否到达桌面")
            return True
    
    def ensure_screen_on(self):
        """确保屏幕亮起并解锁
        
        Returns:
            bool: 屏幕是否成功亮起并解锁
        """
        self.logger.info("确保屏幕亮起并解锁")
        
        # 检查屏幕状态
        if not self.check_screen_state():
            self.logger.info("屏幕处于熄屏状态，尝试唤醒")
            if not self.wake_screen():
                self.logger.error("无法唤醒屏幕")
                return False
        else:
            self.logger.info("屏幕已处于亮屏状态")
            
        # 尝试解锁
        result = self.simple_unlock()
        
        return result
        
    def is_app_running(self, package_name=None):
        """检查应用是否在前台运行
        
        Args:
            package_name: 包名，如果为None则检查快应用
            对于快应用检测，忽略包名参数，始终检查com.huawei.fastapp
            
        Returns:
            bool: 如果应用在前台运行则返回True，否则返回False
        """
        self.logger.info(f"检查应用是否在前台运行: {package_name or '快应用'}")
        
        # 总是使用com.huawei.fastapp检查快应用，忽略传入的参数
        actual_package = "com.huawei.fastapp"
        
        # 使用经过测试的方法：检查前台应用状态
        cmd = "adb shell \"dumpsys activity activities | grep -A 1 'mResumedActivity'\""
        output = self.device.run_shell_command(cmd)
        
        # 只有处于Resumed状态的应用才是真正的前台应用
        is_foreground = actual_package in output and "Resumed" in output
        
        if is_foreground:
            self.logger.info(f"✅ 检测到华为快应用正在前台运行")
        else:
            self.logger.info(f"❌ 未检测到华为快应用在前台运行")
            
        return is_foreground 