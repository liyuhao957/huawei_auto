#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ATX服务重装脚本
用于解决ATX服务连接问题，包括：
1. 重启ADB服务器
2. 卸载设备上的ATX Agent
3. 重新安装ATX Agent
4. 检查ATX服务是否正常运行
"""

import os
import sys
import time
import logging
import subprocess
import uiautomator2 as u2

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("atx_reinstall.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ATXReinstaller")

def get_connected_devices():
    """获取已连接的设备列表"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = []
        for line in result.stdout.split('\n')[1:]:  # 跳过第一行（标题行）
            if '\tdevice' in line:
                devices.append(line.split('\t')[0])
        return devices
    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        return []

def restart_adb_server():
    """重启ADB服务器"""
    try:
        logger.info("正在重启ADB服务器...")
        # 杀死ADB服务器
        subprocess.run(['adb', 'kill-server'], check=True)
        time.sleep(2)
        # 启动ADB服务器
        subprocess.run(['adb', 'start-server'], check=True)
        time.sleep(3)
        logger.info("ADB服务器重启成功")
        return True
    except Exception as e:
        logger.error(f"重启ADB服务器失败: {str(e)}")
        return False

def uninstall_atx_agent(device_serial=None):
    """卸载ATX Agent"""
    try:
        logger.info("正在卸载ATX Agent...")
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        
        # 卸载ATX应用
        cmd_uninstall = cmd + ['uninstall', 'com.github.uiautomator']
        subprocess.run(cmd_uninstall, check=False)
        
        # 停止ATX服务
        cmd_stop = cmd + ['shell', 'am', 'force-stop', 'com.github.uiautomator']
        subprocess.run(cmd_stop, check=False)
        
        logger.info("ATX Agent卸载完成")
        return True
    except Exception as e:
        logger.error(f"卸载ATX Agent失败: {str(e)}")
        return False

def install_atx_agent(device_serial=None):
    """安装ATX Agent"""
    try:
        logger.info("正在安装ATX Agent...")
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        
        # 1. 确保没有遗留的进程
        logger.info("确保清理所有遗留进程...")
        subprocess.run(cmd + ['shell', 'pm', 'clear', 'com.github.uiautomator'], check=False)
        subprocess.run(cmd + ['shell', 'pm', 'clear', 'com.github.uiautomator.test'], check=False)
        time.sleep(2)
        
        # 2. 使用weditor命令安装（这会安装所有必要的组件）
        logger.info("使用weditor命令安装ATX组件...")
        subprocess.run([sys.executable, '-m', 'weditor', 'install'], check=False)
        time.sleep(5)
        
        # 3. 初始化设备
        logger.info("初始化设备...")
        d = u2.connect(device_serial)
        d.healthcheck()  # 进行健康检查
        time.sleep(3)
        
        # 4. 启动UIAutomator服务
        logger.info("启动UIAutomator服务...")
        subprocess.run(cmd + ['shell', 'am', 'start', '-n', 'com.github.uiautomator/.MainActivity'], check=False)
        time.sleep(2)
        
        # 5. 启动UIAutomator测试服务
        logger.info("启动UIAutomator测试服务...")
        subprocess.run(cmd + ['shell', 'am', 'instrument', '-w', 'com.github.uiautomator.test/android.support.test.runner.AndroidJUnitRunner'], check=False)
        time.sleep(2)
        
        # 6. 检查ATX-Agent是否正在运行
        logger.info("检查ATX-Agent是否正在运行...")
        result = subprocess.run(cmd + ['shell', 'ps | grep atx-agent'], capture_output=True, text=True)
        if 'atx-agent' not in result.stdout:
            logger.info("ATX-Agent未运行，尝试启动...")
            # 启动atx-agent
            subprocess.run(cmd + ['shell', '/data/local/tmp/atx-agent', 'server', '--stop'], check=False)
            time.sleep(1)
            subprocess.run(cmd + ['shell', '/data/local/tmp/atx-agent', 'server', '--nouia', '-d'], check=False)
            time.sleep(3)
        
        # 7. 等待服务完全启动
        logger.info("等待服务完全启动...")
        time.sleep(10)
        
        logger.info("ATX Agent安装成功")
        return True
    except Exception as e:
        logger.error(f"安装ATX Agent失败: {str(e)}")
        return False

def check_atx_service(device_serial=None):
    """检查ATX服务是否正常运行"""
    try:
        logger.info("正在检查ATX服务...")
        
        # 1. 首先检查设备连接状态
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        
        # 2. 检查ATX-Agent进程
        result = subprocess.run(cmd + ['shell', 'ps | grep atx-agent'], capture_output=True, text=True)
        if 'atx-agent' not in result.stdout:
            logger.error("ATX-Agent进程未运行")
            return False
        
        # 3. 检查UIAutomator服务
        result = subprocess.run(cmd + ['shell', 'ps | grep uiautomator'], capture_output=True, text=True)
        if 'uiautomator' not in result.stdout:
            logger.error("UIAutomator服务未运行")
            return False
        
        # 4. 尝试连接并获取设备信息
        d = u2.connect(device_serial)
        time.sleep(2)  # 给连接一些时间
        
        # 5. 执行简单的UI操作来验证服务是否正常
        d.info
        d.window_size()
        
        logger.info("ATX服务正常运行")
        return True
    except Exception as e:
        logger.error(f"ATX服务检查失败: {str(e)}")
        return False

def restart_device(device_serial=None):
    """重启设备"""
    try:
        logger.info("正在重启设备...")
        cmd = ['adb']
        if device_serial:
            cmd.extend(['-s', device_serial])
        
        # 1. 先停止所有相关服务
        logger.info("停止所有相关服务...")
        subprocess.run(cmd + ['shell', 'am', 'force-stop', 'com.github.uiautomator'], check=False)
        subprocess.run(cmd + ['shell', 'am', 'force-stop', 'com.github.uiautomator.test'], check=False)
        subprocess.run(cmd + ['shell', '/data/local/tmp/atx-agent', 'server', '--stop'], check=False)
        time.sleep(2)
        
        # 2. 执行重启命令
        logger.info("执行重启命令...")
        subprocess.run(cmd + ['reboot'], check=True)
        logger.info("重启命令已发送，等待设备重启...")
        
        # 3. 等待设备离线
        time.sleep(5)
        
        # 4. 等待设备重新连接
        max_wait = 60  # 最多等待60秒
        start_time = time.time()
        while time.time() - start_time < max_wait:
            devices = get_connected_devices()
            if device_serial:
                if device_serial in devices:
                    break
            elif devices:
                break
            time.sleep(5)
        
        # 5. 等待系统完全启动
        logger.info("等待系统完全启动...")
        time.sleep(30)  # 增加等待时间
        
        # 6. 等待包管理器准备就绪
        logger.info("等待包管理器准备就绪...")
        max_attempts = 10
        for i in range(max_attempts):
            try:
                result = subprocess.run(cmd + ['shell', 'pm', 'list', 'packages'], capture_output=True, text=True)
                if result.returncode == 0 and 'package:' in result.stdout:
                    break
            except:
                pass
            time.sleep(3)
        
        logger.info("设备重启完成")
        return True
    except Exception as e:
        logger.error(f"重启设备失败: {str(e)}")
        return False

def reinstall_atx(device_serial=None, max_retry=3):
    """重新安装ATX服务的主函数"""
    logger.info(f"开始重装ATX服务{'（指定设备：' + device_serial + '）' if device_serial else ''}")
    
    # 重启ADB服务器
    if not restart_adb_server():
        logger.error("重启ADB服务器失败，终止重装")
        return False
    
    # 获取连接的设备
    devices = get_connected_devices()
    if not devices:
        logger.error("未找到已连接的设备，终止重装")
        return False
    
    if device_serial and device_serial not in devices:
        logger.error(f"指定的设备 {device_serial} 未连接，终止重装")
        return False
    
    # 对每个设备执行重装（如果指定了设备序列号，则只处理该设备）
    target_devices = [device_serial] if device_serial else devices
    
    for device in target_devices:
        logger.info(f"正在处理设备: {device}")
        
        # 卸载现有的ATX Agent
        if not uninstall_atx_agent(device):
            logger.warning(f"设备 {device} 卸载ATX Agent失败，继续安装新版本")
        
        # 尝试安装ATX Agent
        retry_count = 0
        success = False
        
        while retry_count < max_retry and not success:
            if retry_count > 0:
                logger.info(f"第 {retry_count + 1} 次重试安装...")
            
            # 安装ATX Agent
            if install_atx_agent(device):
                # 检查服务是否正常运行
                if check_atx_service(device):
                    logger.info(f"设备 {device} ATX服务安装并运行成功")
                    success = True
                    break
            
            # 如果安装失败且还有重试机会，尝试重启设备
            if retry_count < max_retry - 1:
                logger.warning(f"设备 {device} 安装失败，尝试重启设备后重试")
                restart_device(device)
            
            retry_count += 1
        
        if not success:
            logger.error(f"设备 {device} 在 {max_retry} 次尝试后仍未能成功安装ATX服务")
            return False
    
    logger.info("ATX服务重装完成")
    return True

def main():
    """主函数"""
    try:
        # 获取命令行参数中的设备序列号（如果有）
        device_serial = sys.argv[1] if len(sys.argv) > 1 else None
        
        # 执行ATX重装
        success = reinstall_atx(device_serial)
        
        if success:
            logger.info("ATX服务重装成功完成")
            sys.exit(0)
        else:
            logger.error("ATX服务重装失败")
            sys.exit(1)
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 