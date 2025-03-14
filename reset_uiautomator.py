#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重置uiautomator2服务脚本
此脚本用于完全重置设备上的uiautomator2服务
"""

import subprocess
import time
import sys
import os
import argparse

def run_command(cmd, desc=None):
    """运行命令并打印结果"""
    if desc:
        print(f"执行: {desc}")
    print(f"命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=False, 
                               capture_output=True, text=True)
        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"输出: {result.stdout}")
        if result.stderr:
            print(f"错误: {result.stderr}")
        return result.returncode == 0, result.stdout
    except Exception as e:
        print(f"执行命令时出错: {str(e)}")
        return False, str(e)

def reset_uiautomator(reboot_device=False):
    """重置uiautomator2服务"""
    print("===== 开始重置uiautomator2服务 =====")
    
    # 1. 检查ADB设备
    success, output = run_command("adb devices", "检查ADB设备")
    if "device" not in output:
        print("错误: 未检测到已连接的设备，请确保设备已正确连接并启用USB调试")
        return False
    
    # 2. 停止uiautomator服务
    run_command("adb shell am force-stop com.github.uiautomator", 
               "停止uiautomator服务")
    run_command("adb shell am force-stop com.github.uiautomator.test", 
               "停止uiautomator测试服务")
    
    # 3. 卸载uiautomator应用
    run_command("adb uninstall com.github.uiautomator", 
               "卸载uiautomator应用")
    run_command("adb uninstall com.github.uiautomator.test", 
               "卸载uiautomator测试应用")
    
    # 4. 清除临时文件
    run_command("adb shell rm -rf /data/local/tmp/minicap", 
               "清除minicap临时文件")
    run_command("adb shell rm -rf /data/local/tmp/minitouch", 
               "清除minitouch临时文件")
    
    # 5. 重启设备（如果指定）
    if reboot_device:
        print("\n===== 重启设备 =====")
        run_command("adb reboot", "重启设备")
        print("等待设备重启...")
        
        # 等待设备离线
        time.sleep(5)
        
        # 等待设备重新连接
        max_wait = 60  # 最多等待60秒
        for i in range(max_wait):
            success, output = run_command("adb devices", "检查设备状态")
            if "device" in output:
                print(f"设备已重新连接 (等待了{i+5}秒)")
                # 额外等待系统完全启动
                time.sleep(10)
                break
            time.sleep(1)
            if i % 5 == 0:  # 每5秒打印一次等待消息
                print(f"正在等待设备重新连接... ({i+5}秒)")
        else:
            print("设备重启超时，请手动确认设备已重启并连接")
            return False
    else:
        # 如果不重启设备，只重启ADB服务器
        run_command("adb kill-server", "停止ADB服务器")
        time.sleep(1)
        run_command("adb start-server", "启动ADB服务器")
        time.sleep(2)
    
    # 6. 重新初始化uiautomator2
    print("\n===== 重新初始化uiautomator2 =====")
    
    # 先检查uiautomator2版本
    success, version_output = run_command("python3 -m uiautomator2 version", 
                                        "检查uiautomator2版本")
    print(f"uiautomator2版本: {version_output.strip() if success else '未知'}")
    
    # 执行初始化命令（不使用--reinstall参数）
    success, init_output = run_command("python3 -m uiautomator2 init", 
                                     "初始化uiautomator2")
    
    if success:
        print("\n✅ uiautomator2服务重置成功！")
        print("请尝试重新运行您的脚本。")
    else:
        print("\n❌ uiautomator2服务重置可能不完整。")
        print("请尝试在设备上手动操作:")
        print("1. 打开设置 -> 应用 -> 找到并卸载'ATX'和'ATX Test'应用")
        print("2. 重启设备")
        print("3. 重新运行初始化命令: python3 -m uiautomator2 init")
    
    return success

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='重置uiautomator2服务')
    parser.add_argument('--reboot', action='store_true', 
                        help='重置后重启设备（需要设备已启用USB调试）')
    args = parser.parse_args()
    
    try:
        reset_uiautomator(reboot_device=args.reboot)
    except Exception as e:
        print(f"重置过程中出错: {str(e)}")
        return False

if __name__ == "__main__":
    main() 