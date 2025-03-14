#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快应用前台检测脚本
此脚本用于检测指定的快应用是否在前台运行
"""

import uiautomator2 as u2
import time
import logging
import os
import argparse
import re
import sys
import subprocess
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_app_check.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuickAppChecker")

# 快应用相关包名
QUICK_APP_PACKAGES = [
    "com.huawei.fastapp",  # 华为快应用中心
    "com.huawei.fastapp:ui",  # 华为快应用UI进程
    "com.huawei.fastapp.dev",  # 华为快应用开发版
    "com.huawei.fastapp.dev:ui"  # 华为快应用开发版UI进程
]

# 快应用特征
QUICK_APP_FEATURES = [
    "快应用",
    "fastapp",
    "quickapp"
]

def check_adb_devices():
    """检查连接的ADB设备"""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        output = result.stdout
        logger.info(f"ADB设备列表:\n{output}")
        
        # 解析设备列表
        lines = output.strip().split('\n')
        if len(lines) <= 1:
            logger.error("没有检测到已连接的设备")
            return []
        
        devices = []
        for line in lines[1:]:  # 跳过第一行（标题行）
            if line.strip() and not line.strip().startswith('*') and '\tdevice' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        
        if not devices:
            logger.error("没有处于正常状态的设备")
        else:
            logger.info(f"检测到 {len(devices)} 个设备: {devices}")
        
        return devices
    except Exception as e:
        logger.error(f"检查ADB设备时出错: {str(e)}")
        return []

def restart_adb_server():
    """重启ADB服务器"""
    try:
        logger.info("正在重启ADB服务器...")
        subprocess.run(['adb', 'kill-server'], check=True)
        time.sleep(1)
        subprocess.run(['adb', 'start-server'], check=True)
        time.sleep(2)
        logger.info("ADB服务器已重启")
        return True
    except Exception as e:
        logger.error(f"重启ADB服务器失败: {str(e)}")
        return False

def init_uiautomator(device_serial=None):
    """初始化uiautomator2服务"""
    try:
        logger.info(f"正在初始化设备 {device_serial if device_serial else '(默认设备)'} 的uiautomator2服务...")
        # 使用weditor命令初始化设备
        cmd = ['python3', '-m', 'uiautomator2', 'init']
        if device_serial:
            cmd.append(device_serial)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        logger.info(f"初始化结果: {result.stdout}")
        if result.stderr:
            logger.warning(f"初始化警告/错误: {result.stderr}")
        
        return True
    except Exception as e:
        logger.error(f"初始化uiautomator2服务失败: {str(e)}")
        return False

class QuickAppChecker:
    """快应用前台检测类"""
    
    def __init__(self, device_serial=None):
        """初始化检测器"""
        logger.info("初始化QuickAppChecker")
        
        # 检查设备连接状态
        devices = check_adb_devices()
        if not devices:
            logger.info("尝试重启ADB服务器...")
            restart_adb_server()
            devices = check_adb_devices()
            if not devices:
                raise Exception("没有检测到已连接的设备，请确保设备已正确连接并启用USB调试")
        
        # 如果没有指定设备序列号但有多个设备，使用第一个设备
        if not device_serial and len(devices) > 1:
            device_serial = devices[0]
            logger.info(f"检测到多个设备，使用第一个设备: {device_serial}")
        
        # 初始化uiautomator2服务
        init_uiautomator(device_serial)
        
        # 尝试连接设备
        try:
            self.device = u2.connect(device_serial)
            logger.info("设备连接成功")
            
            # 等待uiautomator2服务启动
            time.sleep(2)
            
            # 获取屏幕尺寸
            try:
                self.screen_width, self.screen_height = self.device.window_size()
                logger.info(f"设备屏幕尺寸: {self.screen_width}x{self.screen_height}")
            except Exception as e:
                logger.warning(f"获取屏幕尺寸失败: {str(e)}")
                logger.info("尝试重新初始化uiautomator2服务...")
                init_uiautomator(device_serial)
                time.sleep(3)
                self.device = u2.connect(device_serial)
                self.screen_width, self.screen_height = self.device.window_size()
                logger.info(f"重试后获取的屏幕尺寸: {self.screen_width}x{self.screen_height}")
                
        except Exception as e:
            logger.error(f"连接设备失败: {str(e)}")
            raise Exception(f"无法连接到设备: {str(e)}")
    
    def take_screenshot(self, name=None):
        """截取屏幕截图"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}"
        
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            
        filename = f"{screenshots_dir}/{name}.png"
        try:
            self.device.screenshot(filename)
            logger.info(f"截图已保存: {filename}")
            return filename
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None
    
    def get_current_package(self):
        """获取当前前台应用的包名"""
        try:
            current_app = self.device.app_current()
            logger.info(f"当前前台应用信息: {current_app}")
            return current_app
        except Exception as e:
            logger.error(f"获取当前应用信息失败: {str(e)}")
            # 尝试使用shell命令获取
            try:
                dumpsys = self.device.shell("dumpsys window | grep mCurrentFocus")
                logger.info(f"通过shell命令获取的窗口信息: {dumpsys}")
                # 解析包名和活动名
                match = re.search(r'mCurrentFocus=.*{([^/]+)/([^}]+)}', dumpsys)
                if match:
                    package_name = match.group(1)
                    activity = match.group(2)
                    return {'package': package_name, 'activity': activity}
                return {'package': '', 'activity': ''}
            except Exception as e2:
                logger.error(f"通过shell命令获取应用信息也失败: {str(e2)}")
                return {'package': '', 'activity': ''}
    
    def is_quick_app_running(self, app_name=None):
        """
        检查快应用是否在前台运行
        
        参数:
            app_name: 可选，指定要检查的快应用名称
        
        返回:
            bool: 如果快应用在前台运行则返回True，否则返回False
        """
        # 获取当前前台应用信息
        current_app = self.get_current_package()
        package_name = current_app.get('package', '')
        activity = current_app.get('activity', '')
        
        # 检查是否是已知的快应用包名
        if any(pkg in package_name for pkg in QUICK_APP_PACKAGES):
            logger.info(f"检测到快应用中心在前台运行: {package_name}")
            
            # 如果指定了应用名称，则进一步检查UI元素
            if app_name:
                # 尝试在界面上查找应用名称
                try:
                    if self.device(text=app_name).exists:
                        logger.info(f"在界面上找到指定的快应用: {app_name}")
                        return True
                    else:
                        logger.info(f"未在界面上找到指定的快应用: {app_name}")
                        return False
                except Exception as e:
                    logger.warning(f"检查UI元素时出错: {str(e)}")
            return True
        
        # 检查是否有快应用特征
        for feature in QUICK_APP_FEATURES:
            if feature in package_name.lower() or feature in activity.lower():
                logger.info(f"根据特征检测到快应用在前台运行: {feature}")
                return True
        
        # 使用dumpsys检查更多信息
        try:
            window_info = self.device.shell("dumpsys window | grep mCurrentFocus")
            logger.debug(f"窗口信息: {window_info}")
            
            # 检查窗口信息中是否包含快应用特征
            for feature in QUICK_APP_FEATURES:
                if feature in window_info.lower():
                    logger.info(f"通过窗口信息检测到快应用在前台运行: {feature}")
                    return True
                    
            # 检查是否是华为浏览器中的快应用
            if "com.huawei.browser" in window_info and any(feature in window_info.lower() for feature in QUICK_APP_FEATURES):
                logger.info("检测到华为浏览器中的快应用在前台运行")
                return True
        except Exception as e:
            logger.warning(f"获取窗口信息失败: {str(e)}")
        
        # 如果指定了应用名称，尝试在界面上查找
        if app_name:
            try:
                if self.device(text=app_name).exists:
                    # 检查是否有快应用相关的UI元素
                    if (self.device(text="快应用").exists or 
                        self.device(resourceId="com.huawei.fastapp:id/container").exists):
                        logger.info(f"通过UI元素检测到快应用 '{app_name}' 在前台运行")
                        return True
            except Exception as e:
                logger.warning(f"检查UI元素时出错: {str(e)}")
        
        logger.info("未检测到快应用在前台运行")
        return False
    
    def monitor_quick_app(self, app_name=None, interval=1, duration=60):
        """
        持续监控快应用是否在前台运行
        
        参数:
            app_name: 可选，指定要监控的快应用名称
            interval: 检查间隔时间（秒）
            duration: 监控持续时间（秒），设为0表示持续监控直到手动中断
        
        返回:
            None
        """
        logger.info(f"开始监控快应用 {app_name if app_name else '(任意)'} 是否在前台运行")
        logger.info(f"监控间隔: {interval}秒, 持续时间: {'无限' if duration == 0 else f'{duration}秒'}")
        
        start_time = time.time()
        running_count = 0
        not_running_count = 0
        
        try:
            while duration == 0 or time.time() - start_time < duration:
                try:
                    is_running = self.is_quick_app_running(app_name)
                    
                    if is_running:
                        running_count += 1
                    else:
                        not_running_count += 1
                    
                    total_checks = running_count + not_running_count
                    running_percentage = (running_count / total_checks) * 100 if total_checks > 0 else 0
                    
                    logger.info(f"快应用状态: {'运行中' if is_running else '未运行'} "
                               f"(运行次数: {running_count}, 未运行次数: {not_running_count}, "
                               f"运行比例: {running_percentage:.2f}%)")
                    
                    # 如果状态发生变化，截图记录
                    if (running_count == 1 and is_running) or (not_running_count == 1 and not is_running):
                        self.take_screenshot(f"quick_app_{'running' if is_running else 'not_running'}")
                except Exception as e:
                    logger.error(f"监控过程中出错: {str(e)}")
                
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("监控被手动中断")
        
        # 总结监控结果
        total_time = time.time() - start_time
        total_checks = running_count + not_running_count
        running_percentage = (running_count / total_checks) * 100 if total_checks > 0 else 0
        
        logger.info(f"监控结束，总结:")
        logger.info(f"- 总检查次数: {total_checks}")
        logger.info(f"- 检测到运行次数: {running_count} ({running_percentage:.2f}%)")
        logger.info(f"- 检测到未运行次数: {not_running_count} ({100-running_percentage:.2f}%)")
        logger.info(f"- 总监控时间: {total_time:.2f}秒")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='检测快应用是否在前台运行')
    parser.add_argument('-d', '--device', help='设备序列号，如果有多台设备连接')
    parser.add_argument('-a', '--app', help='指定要检查的快应用名称')
    parser.add_argument('-m', '--monitor', action='store_true', help='持续监控模式')
    parser.add_argument('-i', '--interval', type=float, default=1.0, help='监控模式下的检查间隔（秒）')
    parser.add_argument('-t', '--time', type=int, default=60, help='监控持续时间（秒），0表示持续监控直到手动中断')
    parser.add_argument('--init', action='store_true', help='初始化uiautomator2服务')
    
    args = parser.parse_args()
    
    # 如果指定了初始化选项，先初始化uiautomator2服务
    if args.init:
        logger.info("初始化uiautomator2服务...")
        if init_uiautomator(args.device):
            logger.info("初始化完成，退出")
            return True
        else:
            logger.error("初始化失败")
            return False
    
    # 检查设备连接状态
    devices = check_adb_devices()
    if not devices:
        logger.info("尝试重启ADB服务器...")
        restart_adb_server()
        devices = check_adb_devices()
        if not devices:
            logger.error("没有检测到已连接的设备，请确保设备已正确连接并启用USB调试")
            return False
    
    try:
        checker = QuickAppChecker(device_serial=args.device)
        
        if args.monitor:
            checker.monitor_quick_app(app_name=args.app, interval=args.interval, duration=args.time)
        else:
            is_running = checker.is_quick_app_running(app_name=args.app)
            print(f"快应用 {args.app if args.app else '(任意)'} 是否在前台运行: {'是' if is_running else '否'}")
            return is_running
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        print(f"错误: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"程序异常终止: {str(e)}")
        print(f"程序异常终止: {str(e)}")
        sys.exit(1) 