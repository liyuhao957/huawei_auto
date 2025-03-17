#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
华为快应用前台检测脚本
使用前台应用状态检测方法判断华为快应用是否在前台运行
"""

import subprocess
import logging
import time
import os
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_app_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def run_shell_command(cmd):
    """
    运行shell命令并返回输出
    
    Args:
        cmd: 要执行的shell命令
    
    Returns:
        str: 命令的输出
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"执行命令时出错: {str(e)}")
        return ""

def check_quick_app_status():
    """检查前台应用状态
    
    使用dumpsys activity activities命令检查mResumedActivity
    只有处于Resumed状态的应用才是真正的前台应用
    
    Returns:
        tuple: (是否在前台, 命令输出)
    """
    cmd = "adb shell \"dumpsys activity activities | grep -A 1 'mResumedActivity'\""
    output = run_shell_command(cmd)
    logger.info(f"检查前台应用状态输出: {output}")
    # 只有处于Resumed状态的应用才是真正的前台应用
    is_foreground = "com.huawei.fastapp" in output and "Resumed" in output
    
    if is_foreground:
        logger.info("✅ 检测到华为快应用正在前台运行")
    else:
        logger.info("❌ 未检测到华为快应用在前台运行")
        
    return is_foreground, output

def main():
    """主函数"""
    logger.info("=== 华为快应用前台检测工具 ===")
    print("华为快应用前台检测工具")
    print("按Ctrl+C退出")
    
    try:
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # 显示当前使用的方法
            print("\n使用: 检查前台应用状态")
            
            # 执行检测
            is_running, details = check_quick_app_status()
            
            # 显示结果
            if is_running:
                print("\n✅ 快应用检测为前台运行")
            else:
                print("\n❌ 快应用未检测到前台运行")
            
            print(f"\n详细信息: {details}")
            
            # 每隔3秒检测一次
            print("\n3秒后自动重新检测，按Ctrl+C退出...")
            time.sleep(3)
            
    except KeyboardInterrupt:
        logger.info("用户中断检测")
        print("\n检测已停止")

if __name__ == "__main__":
    main() 