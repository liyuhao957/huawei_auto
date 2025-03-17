#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ADBKeyboard输入测试脚本
专门用于测试通过ADBKeyboard输入中文文本的功能
假设用户已将光标定位在输入框中
"""

import subprocess
import time
import logging
import os
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("adbkeyboard_input_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ADBKeyboardTester")

def press_key(keycode):
    """按下按键"""
    cmd = f"adb shell input keyevent {keycode}"
    logger.info(f"按下按键: {keycode}")
    subprocess.run(cmd, shell=True)

def clear_input_field():
    """清空当前输入框内容"""
    logger.info("清空输入框")
    press_key("KEYCODE_CTRL_LEFT")  # Ctrl键
    press_key("KEYCODE_A")  # A键 (Ctrl+A 全选)
    time.sleep(0.5)
    press_key("KEYCODE_DEL")  # 删除键
    time.sleep(0.5)

def check_adbkeyboard_installed():
    """检查ADBKeyboard是否已安装 - 改进的检测方法"""
    logger.info("检查ADBKeyboard是否已安装")
    
    # 方法1: 使用ime list检查
    ime_list_cmd = "adb shell ime list -a"
    result1 = subprocess.run(ime_list_cmd, shell=True, capture_output=True, text=True)
    if "com.android.adbkeyboard/.AdbIME" in result1.stdout:
        logger.info("检测到ADBKeyboard已安装（通过ime list确认）")
        return True
    
    # 方法2: 直接检查包是否存在
    package_cmd = "adb shell pm list packages"
    result2 = subprocess.run(package_cmd, shell=True, capture_output=True, text=True)
    if "package:com.android.adbkeyboard" in result2.stdout:
        logger.info("检测到ADBKeyboard已安装（通过package list确认）")
        return True
    
    # 方法3: 尝试设置为默认输入法
    try_set_cmd = "adb shell ime set com.android.adbkeyboard/.AdbIME"
    result3 = subprocess.run(try_set_cmd, shell=True, capture_output=True, text=True)
    if "error" not in result3.stdout.lower() and "unknown" not in result3.stdout.lower():
        # 验证是否真的设置成功
        check_current = "adb shell settings get secure default_input_method"
        result4 = subprocess.run(check_current, shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard" in result4.stdout:
            logger.info("检测到ADBKeyboard已安装（通过设置为默认输入法确认）")
            return True
    
    logger.info("未检测到ADBKeyboard")
    return False

def install_adbkeyboard(skip_check=False):
    """检查并安装ADBKeyboard"""
    if skip_check:
        logger.info("跳过安装检查，假设ADBKeyboard已安装")
        return True
        
    # 使用改进的方法检查是否已安装
    if check_adbkeyboard_installed():
        logger.info("ADBKeyboard已安装，无需重新安装")
        return True
        
    logger.info("尝试安装ADBKeyboard...")
    # 检查当前目录是否有APK文件
    if os.path.exists("ADBKeyboard.apk"):
        logger.info("找到APK文件，开始安装")
        result = subprocess.run("adb install -r ADBKeyboard.apk", shell=True, capture_output=True, text=True)
        
        # 检查安装结果
        if "Success" in result.stdout or "success" in result.stdout.lower():
            logger.info("ADBKeyboard安装成功")
            return True
        else:
            logger.warning(f"ADBKeyboard安装失败: {result.stdout} {result.stderr}")
            logger.info("如果您确定ADBKeyboard已安装，请使用--skip-install选项运行脚本")
            return False
    else:
        logger.warning("未找到ADBKeyboard.apk文件，请自行下载安装")
        logger.warning("可从 https://github.com/senzhk/ADBKeyBoard 下载")
        logger.info("如果您确定ADBKeyboard已安装，请使用--skip-install选项运行脚本")
        return False

def set_adbkeyboard_as_default():
    """设置ADBKeyboard为默认输入法"""
    logger.info("设置ADBKeyboard为默认输入法")
    # 保存当前输入法以便稍后恢复
    result = subprocess.run("adb shell settings get secure default_input_method", 
                           shell=True, capture_output=True, text=True)
    current_ime = result.stdout.strip()
    logger.info(f"当前输入法: {current_ime}")
    
    # 如果当前已经是ADBKeyboard，则无需更改
    if "com.android.adbkeyboard" in current_ime:
        logger.info("当前已经是ADBKeyboard输入法，无需切换")
        return current_ime
    
    # 设置ADBKeyboard为默认
    subprocess.run("adb shell ime set com.android.adbkeyboard/.AdbIME", shell=True)
    time.sleep(1)
    
    # 验证是否设置成功
    verify_result = subprocess.run("adb shell settings get secure default_input_method", 
                                  shell=True, capture_output=True, text=True)
    if "com.android.adbkeyboard" in verify_result.stdout:
        logger.info("成功设置ADBKeyboard为默认输入法")
    else:
        logger.warning(f"设置输入法可能失败，当前输入法: {verify_result.stdout.strip()}")
    
    return current_ime

def restore_input_method(input_method):
    """恢复之前的输入法"""
    if input_method and "com.android.adbkeyboard" not in input_method:
        logger.info(f"恢复之前的输入法: {input_method}")
        subprocess.run(f"adb shell ime set {input_method}", shell=True)
        time.sleep(1)

def input_text_with_adbkeyboard(text):
    """使用ADBKeyboard输入文本"""
    logger.info(f"使用ADBKeyboard输入文本: {text}")
    
    # 使用ADBKeyboard的广播机制输入文本
    # 处理转义字符
    escaped_text = text.replace('"', '\\"')
    cmd = f'adb shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped_text}"'
    logger.info(f"执行命令: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    logger.info(f"命令结果: {result.stdout}")
    
    if result.stderr:
        logger.error(f"命令错误: {result.stderr}")
    
    time.sleep(1)  # 等待输入完成
    
    # 如果结果中包含"Broadcast completed"，则表示成功
    if "Broadcast completed" in result.stdout:
        logger.info("文本输入广播命令成功发送")
        return True
    else:
        logger.warning("文本输入广播命令可能未成功发送，尝试备用方法")
        # 备用方法
        escaped_text = text.replace("'", "\\'")
        backup_cmd = f"adb shell am broadcast -a ADB_INPUT_TEXT --es msg '{escaped_text}'"
        logger.info(f"执行备用命令: {backup_cmd}")
        subprocess.run(backup_cmd, shell=True)
        time.sleep(1)
        return False

def test_adbkeyboard_input(text=None, skip_install=False):
    """测试ADBKeyboard输入"""
    if not text:
        text = "这是一个ADBKeyboard测试，输入中文内容：你好世界！"
    
    logger.info("===== 开始测试ADBKeyboard输入 =====")
    
    # 检查并安装ADBKeyboard
    if not install_adbkeyboard(skip_install):
        logger.error("ADBKeyboard未安装或安装失败，测试终止")
        logger.info("如果您确定ADBKeyboard已安装，请使用--skip-install选项运行脚本")
        return False
    
    # 备份当前输入法并设置ADBKeyboard
    original_ime = set_adbkeyboard_as_default()
    
    try:
        # 清空当前输入框
        clear_input_field()
        
        # 使用ADBKeyboard输入文本
        input_text_with_adbkeyboard(text)
        
        # 按回车确认（可选）
        # press_key("KEYCODE_ENTER")
        
        logger.info("输入完成")
        time.sleep(2)  # 等待查看结果
        
        return True
    
    finally:
        # 恢复原来的输入法
        restore_input_method(original_ime)
        logger.info("===== ADBKeyboard测试完成 =====")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='ADBKeyboard中文输入测试工具')
    parser.add_argument('--text', '-t', type=str, help='要输入的文本，默认为测试文本')
    parser.add_argument('--skip-install', '-s', action='store_true', 
                        help='跳过安装检查，假设ADBKeyboard已安装')
    args = parser.parse_args()
    
    # 运行测试
    test_adbkeyboard_input(args.text, args.skip_install) 