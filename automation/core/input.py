#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
输入法管理模块 - 处理输入法设置和文本输入
"""

import subprocess
import time
import logging

class InputMethodManager:
    """输入法管理器，处理输入法切换和文本输入"""
    
    def __init__(self, logger=None):
        """初始化输入法管理器
        
        Args:
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.logger = logger or logging.getLogger("input")
        self.original_ime = None
        
    def check_adbkeyboard_installed(self):
        """检查ADBKeyboard是否已安装
        
        Returns:
            bool: 如果ADBKeyboard已安装则返回True，否则返回False
        """
        self.logger.info("检查ADBKeyboard是否已安装")
        
        # 方法1: 使用ime list检查
        ime_list_cmd = "adb shell ime list -a"
        result1 = subprocess.run(ime_list_cmd, shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard/.AdbIME" in result1.stdout:
            self.logger.info("检测到ADBKeyboard已安装（通过ime list确认）")
            return True
        
        # 方法2: 直接检查包是否存在
        package_cmd = "adb shell pm list packages"
        result2 = subprocess.run(package_cmd, shell=True, capture_output=True, text=True)
        if "package:com.android.adbkeyboard" in result2.stdout:
            self.logger.info("检测到ADBKeyboard已安装（通过package list确认）")
            return True
        
        # 方法3: 尝试设置为默认输入法
        try_set_cmd = "adb shell ime set com.android.adbkeyboard/.AdbIME"
        result3 = subprocess.run(try_set_cmd, shell=True, capture_output=True, text=True)
        if "error" not in result3.stdout.lower() and "unknown" not in result3.stdout.lower():
            # 验证是否真的设置成功
            check_current = "adb shell settings get secure default_input_method"
            result4 = subprocess.run(check_current, shell=True, capture_output=True, text=True)
            if "com.android.adbkeyboard" in result4.stdout:
                self.logger.info("检测到ADBKeyboard已安装（通过设置为默认输入法确认）")
                return True
        
        self.logger.warning("未检测到ADBKeyboard，某些功能可能无法正常工作")
        self.logger.warning("请安装ADBKeyboard: https://github.com/senzhk/ADBKeyBoard")
        return False
    
    def ensure_adbkeyboard_input_method(self):
        """确保ADBKeyboard被设置为当前输入法
        
        Returns:
            bool: 如果成功设置ADBKeyboard为默认输入法则返回True，否则返回False
        """
        self.logger.info("确保ADBKeyboard被设置为默认输入法")
        
        # 首先检查ADBKeyboard是否已安装
        is_installed = self.check_adbkeyboard_installed()
        if not is_installed:
            self.logger.warning("ADBKeyboard未安装，将使用备用输入方法（可能不支持中文）")
            return False
        
        # 保存当前输入法以便稍后恢复
        result = subprocess.run("adb shell settings get secure default_input_method", 
                               shell=True, capture_output=True, text=True)
        self.original_ime = result.stdout.strip()
        self.logger.info(f"当前输入法: {self.original_ime}")
        
        # 如果当前已经是ADBKeyboard，则无需更改
        if "com.android.adbkeyboard" in self.original_ime:
            self.logger.info("当前已经是ADBKeyboard输入法，无需切换")
            return True
        
        # 设置ADBKeyboard为默认
        subprocess.run("adb shell ime set com.android.adbkeyboard/.AdbIME", shell=True)
        time.sleep(1)
        
        # 验证是否设置成功
        verify_result = subprocess.run("adb shell settings get secure default_input_method", 
                                      shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard" in verify_result.stdout:
            self.logger.info("成功设置ADBKeyboard为默认输入法")
            return True
        else:
            self.logger.warning(f"设置输入法可能失败，当前输入法: {verify_result.stdout.strip()}")
            return False
        
    def restore_original_input_method(self):
        """恢复原来的输入法
        
        Returns:
            bool: 如果成功恢复原来的输入法则返回True，否则返回False
        """
        if hasattr(self, 'original_ime') and self.original_ime and "com.android.adbkeyboard" not in self.original_ime:
            self.logger.info(f"恢复原来的输入法: {self.original_ime}")
            subprocess.run(f"adb shell ime set {self.original_ime}", shell=True)
            time.sleep(1)
            return True
        return False
    
    def input_text(self, text):
        """输入文本 - 使用ADBKeyboard输入中文或其他文本
        
        Args:
            text: 要输入的文本
            
        Returns:
            bool: 如果成功输入文本则返回True，否则返回False
        """
        self.logger.info(f"输入文本: {text}")
        
        # 如果是英文或数字，可以直接使用标准输入法
        if all(ord(c) < 128 for c in text):
            self.logger.info("使用标准输入法输入ASCII文本")
            cmd = f'adb shell input text "{text}"'
            subprocess.run(cmd, shell=True)
            return True
        
        # 对于中文或其他非ASCII文本，使用ADBKeyboard
        self.logger.info("使用ADBKeyboard输入非ASCII文本")
        
        # 处理转义字符
        escaped_text = text.replace('"', '\\"')
        cmd = f'adb shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped_text}"'
        self.logger.info(f"执行命令: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 检查是否成功
        if "Broadcast completed" in result.stdout:
            self.logger.info("文本输入广播命令成功发送")
            time.sleep(1)  # 等待输入完成
            return True
        else:
            self.logger.warning("文本输入广播命令可能未成功发送，尝试备用方法")
            # 备用方法
            escaped_text = text.replace("'", "\\'")
            backup_cmd = f"adb shell am broadcast -a ADB_INPUT_TEXT --es msg '{escaped_text}'"
            self.logger.info(f"执行备用命令: {backup_cmd}")
            subprocess.run(backup_cmd, shell=True)
            time.sleep(1)  # 等待输入完成
            return True 