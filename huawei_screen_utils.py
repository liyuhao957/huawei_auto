#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huawei Screen Utilities
用于华为设备屏幕状态检测和唤醒的工具脚本
使用多种方法判断屏幕亮灭状态和尝试唤醒屏幕
"""

import subprocess
import time
import logging
import os
import argparse
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screen_utils.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ScreenUtils")

# 设备屏幕尺寸（可根据实际设备修改）
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2376

class ScreenUtils:
    """屏幕工具类，用于检测屏幕状态和唤醒屏幕"""
    
    def __init__(self):
        """初始化屏幕工具类"""
        logger.info("初始化屏幕工具类")
        
    def run_shell_command(self, command, capture_output=True):
        """运行shell命令并返回输出"""
        logger.info(f"运行命令: {command}")
        
        try:
            if capture_output:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.stdout:
                    logger.info(f"命令输出: {result.stdout[:200]}{'...' if len(result.stdout) > 200 else ''}")
                if result.stderr:
                    logger.warning(f"命令错误: {result.stderr[:200]}{'...' if len(result.stderr) > 200 else ''}")
                return result
            else:
                # 不捕获输出，直接执行
                subprocess.run(command, shell=True)
                return None
        except Exception as e:
            logger.error(f"执行命令出错: {str(e)}")
            return None
        
    def check_screen_power_state(self):
        """检测方法1: 使用Display Power state检查"""
        print("\n[检测方法1] 使用Display Power state...")
        cmd = "adb shell dumpsys power | grep 'Display Power' | grep -q 'state=ON'"
        result = self.run_shell_command(cmd)
        
        if result and result.returncode == 0:
            logger.info("检测方法1: 屏幕状态为亮屏 (Display Power state=ON)")
            print("✓ 结果: 屏幕处于亮屏状态")
            return True
        else:
            logger.info("检测方法1: 屏幕状态为熄屏或无法确定 (Display Power state≠ON)")
            print("✗ 结果: 屏幕处于熄屏状态或无法确定")
            return False
            
    def check_screen_on_flag(self):
        """检测方法2: 使用mScreenOn标志检查"""
        print("\n[检测方法2] 使用mScreenOn标志...")
        cmd = "adb shell dumpsys power | grep 'mScreenOn='"
        result = self.run_shell_command(cmd)
        
        if result and result.stdout:
            if "mScreenOn=true" in result.stdout:
                logger.info("检测方法2: 屏幕状态为亮屏 (mScreenOn=true)")
                print("✓ 结果: 屏幕处于亮屏状态")
                return True
            elif "mScreenOn=false" in result.stdout:
                logger.info("检测方法2: 屏幕状态为熄屏 (mScreenOn=false)")
                print("✗ 结果: 屏幕处于熄屏状态")
                return False
        
        logger.info("检测方法2: 无法确定屏幕状态 (未找到mScreenOn标志)")
        print("? 结果: 无法确定屏幕状态")
        return None
    
    def check_display_blocker(self):
        """检测方法3: 检查屏幕挂起阻止器"""
        print("\n[检测方法3] 检查mHoldingDisplaySuspendBlocker...")
        cmd = "adb shell dumpsys power | grep 'mHoldingDisplaySuspendBlocker'"
        result = self.run_shell_command(cmd)
        
        if result and result.stdout:
            if "true" in result.stdout.lower():
                logger.info("检测方法3: 屏幕状态为亮屏 (mHoldingDisplaySuspendBlocker=true)")
                print("✓ 结果: 屏幕处于亮屏状态")
                return True
            elif "false" in result.stdout.lower():
                logger.info("检测方法3: 屏幕状态为熄屏 (mHoldingDisplaySuspendBlocker=false)")
                print("✗ 结果: 屏幕处于熄屏状态")
                return False
        
        logger.info("检测方法3: 无法确定屏幕状态 (未找到mHoldingDisplaySuspendBlocker标志)")
        print("? 结果: 无法确定屏幕状态")
        return None
    
    def check_display_state(self):
        """检测方法4: 检查显示状态"""
        print("\n[检测方法4] 检查显示状态mState...")
        cmd = "adb shell dumpsys display | grep 'mState'"
        result = self.run_shell_command(cmd)
        
        if result and result.stdout:
            if "ON" in result.stdout:
                logger.info("检测方法4: 屏幕状态为亮屏 (Display State=ON)")
                print("✓ 结果: 屏幕处于亮屏状态")
                return True
            elif "OFF" in result.stdout:
                logger.info("检测方法4: 屏幕状态为熄屏 (Display State=OFF)")
                print("✗ 结果: 屏幕处于熄屏状态")
                return False
        
        logger.info("检测方法4: 无法确定屏幕状态 (未找到mState标志)")
        print("? 结果: 无法确定屏幕状态")
        return None
    
    def check_resumed_activity(self):
        """检测方法5: 检查前台活动"""
        print("\n[检测方法5] 检查前台应用活动...")
        cmd = "adb shell dumpsys activity activities | grep -A 3 'mResumedActivity'"
        result = self.run_shell_command(cmd)
        
        if result and result.stdout and len(result.stdout.strip()) > 10:
            # 如果能获取到前台应用信息，通常说明屏幕是亮的
            logger.info(f"检测到前台应用活动: {result.stdout.strip()[:50]}...")
            
            # 检查是否是锁屏界面
            if "Keyguard" in result.stdout or "StatusBar" in result.stdout:
                logger.info("检测方法5: 前台应用是锁屏或状态栏，屏幕可能是亮的但锁定状态")
                print("✓ 结果: 屏幕处于亮屏状态 (锁屏界面)")
                return True
            
            logger.info("检测方法5: 屏幕状态为亮屏 (有前台应用活动)")
            print("✓ 结果: 屏幕处于亮屏状态 (有前台应用)")
            return True
        else:
            logger.info("检测方法5: 未检测到前台应用活动，屏幕可能是熄屏状态")
            print("✗ 结果: 屏幕处于熄屏状态 (无前台应用)")
            return False
    
    def check_screen_state(self):
        """逐个尝试不同方法检查屏幕状态，并让用户按回车继续
        
        Returns:
            bool: 屏幕亮起返回True，熄屏返回False
        """
        logger.info("开始检查屏幕状态")
        print("\n=== 开始检查屏幕状态 ===")
        print("每个检测方法执行后请按回车继续...")
        
        # 结果计数
        on_count = 0
        off_count = 0
        methods_count = 0
        
        # 检测方法1: 使用Display Power state
        method1_result = self.check_screen_power_state()
        input("按回车继续下一个检测方法...")
        if method1_result is not None:
            methods_count += 1
            if method1_result:
                on_count += 1
            else:
                off_count += 1
        
        # 检测方法2: 使用mScreenOn标志
        method2_result = self.check_screen_on_flag()
        input("按回车继续下一个检测方法...")
        if method2_result is not None:
            methods_count += 1
            if method2_result:
                on_count += 1
            else:
                off_count += 1
        
        # 检测方法3: 检查mHoldingDisplaySuspendBlocker
        method3_result = self.check_display_blocker()
        input("按回车继续下一个检测方法...")
        if method3_result is not None:
            methods_count += 1
            if method3_result:
                on_count += 1
            else:
                off_count += 1
        
        # 检测方法4: 检查Display State
        method4_result = self.check_display_state()
        input("按回车继续下一个检测方法...")
        if method4_result is not None:
            methods_count += 1
            if method4_result:
                on_count += 1
            else:
                off_count += 1
        
        # 检测方法5: 检查前台活动
        method5_result = self.check_resumed_activity()
        input("按回车继续查看最终结果...")
        methods_count += 1
        if method5_result:
            on_count += 1
        else:
            off_count += 1
        
        # 综合判断
        print(f"\n=== 检测结果统计 ===")
        print(f"- 亮屏判断次数: {on_count}")
        print(f"- 熄屏判断次数: {off_count}")
        print(f"- 总有效方法数: {methods_count}")
        
        # 如果大多数方法认为屏幕是亮的
        is_screen_on = on_count > off_count
        
        if is_screen_on:
            logger.info("最终判断: 屏幕处于亮屏状态")
            print("\n最终判断: 屏幕处于亮屏状态 ✓")
        else:
            logger.info("最终判断: 屏幕处于熄屏状态")
            print("\n最终判断: 屏幕处于熄屏状态 ✗")
            
        return is_screen_on
    
    def press_key(self, keycode):
        """按下按键"""
        cmd = f"adb shell input keyevent {keycode}"
        logger.info(f"按下按键: {keycode}")
        self.run_shell_command(cmd, capture_output=False)
        
    def tap(self, x, y):
        """点击指定坐标"""
        cmd = f"adb shell input tap {x} {y}"
        logger.info(f"点击坐标: ({x}, {y})")
        self.run_shell_command(cmd, capture_output=False)
        
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动屏幕"""
        cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        self.run_shell_command(cmd, capture_output=False)
    
    def wake_screen(self):
        """尝试唤醒屏幕，每个方法尝试后等待用户按回车继续
        
        Returns:
            bool: 是否成功唤醒屏幕
        """
        logger.info("开始尝试唤醒屏幕...")
        print("\n=== 开始尝试唤醒屏幕 ===")
        print("每个唤醒方法执行后请按回车确认是否唤醒...")
        
        # 尝试多种唤醒方法
        methods = [
            ("电源键唤醒", "KEYCODE_POWER"),
            ("WAKEUP键码唤醒", "KEYCODE_WAKEUP"),
            ("HOME键唤醒", "KEYCODE_HOME"),
            ("双击屏幕唤醒", None),
            ("滑动屏幕唤醒", None)
        ]
        
        for i, (method_name, keycode) in enumerate(methods, 1):
            print(f"\n[唤醒方法{i}] {method_name}...")
            
            if keycode:
                # 使用按键唤醒
                self.press_key(keycode)
            elif method_name == "双击屏幕唤醒":
                # 双击屏幕
                center_x = SCREEN_WIDTH // 2
                center_y = SCREEN_HEIGHT // 2
                self.tap(center_x, center_y)
                time.sleep(0.3)
                self.tap(center_x, center_y)
            elif method_name == "滑动屏幕唤醒":
                # 滑动屏幕
                self.swipe(
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT * 3 // 4,
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 4,
                    300
                )
            
            # 等待屏幕响应
            time.sleep(1)
            
            # 检查是否成功唤醒
            print(f"执行{method_name}后，请观察手机是否唤醒")
            user_input = input("屏幕是否已亮起? (y/n，按回车默认为n): ").strip().lower()
            
            if user_input == 'y':
                logger.info(f"成功使用{method_name}")
                print(f"✓ 成功使用{method_name}")
                return True
            
            print(f"✗ {method_name}未能唤醒屏幕，尝试下一个方法...")
        
        logger.error("所有唤醒方法均失败")
        print("\n❌ 所有唤醒方法均失败")
        return False
    
    def unlock_screen(self):
        """简单解锁屏幕
        
        Returns:
            bool: 是否成功解锁
        """
        logger.info("尝试解锁屏幕")
        
        # 确保屏幕已亮起
        if not self.check_screen_state():
            logger.info("屏幕处于熄屏状态，先尝试唤醒")
            if not self.wake_screen():
                logger.error("无法唤醒屏幕，解锁失败")
                return False
        
        # 滑动解锁
        logger.info("执行滑动解锁操作")
        self.swipe(
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT * 3 // 4,
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 4,
            300
        )
        time.sleep(1)
        
        # 按Home键确认
        logger.info("按Home键确认解锁")
        self.press_key("KEYCODE_HOME")
        time.sleep(1)
        
        # 检查是否成功解锁到桌面
        cmd = "adb shell dumpsys activity activities | grep mResumedActivity"
        result = self.run_shell_command(cmd)
        
        if result and "Launcher" in result.stdout:
            logger.info("成功解锁到桌面")
            return True
        else:
            logger.info("简单解锁操作已执行，但未确认是否到达桌面")
            # 再次尝试Home键
            self.press_key("KEYCODE_HOME")
            return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='华为设备屏幕状态检测和唤醒工具')
    parser.add_argument('--check', action='store_true', help='仅检查屏幕状态')
    parser.add_argument('--wake', action='store_true', help='唤醒屏幕')
    parser.add_argument('--unlock', action='store_true', help='解锁屏幕')
    parser.add_argument('--loop', type=int, default=0, help='循环检测次数（0表示只执行一次）')
    parser.add_argument('--interval', type=int, default=5, help='循环检测间隔（秒）')
    
    args = parser.parse_args()
    
    screen_utils = ScreenUtils()
    
    # 默认行为：如果没有指定参数，则执行检查和唤醒
    if not (args.check or args.wake or args.unlock):
        args.check = True
        args.wake = True
    
    # 执行循环或单次检测
    loop_count = max(1, args.loop)
    for i in range(loop_count):
        if args.loop > 0:
            logger.info(f"执行第 {i+1}/{loop_count} 次检测")
            print(f"\n=== 执行第 {i+1}/{loop_count} 次检测 ===")
        
        # 检查屏幕状态
        is_screen_on = None
        if args.check:
            is_screen_on = screen_utils.check_screen_state()
            print(f"\n当前屏幕状态: {'亮屏' if is_screen_on else '熄屏'}")
        
        # 唤醒屏幕（仅当需要唤醒且屏幕当前为熄屏状态时）
        if args.wake:
            if is_screen_on is True:
                print("\n屏幕已经处于亮屏状态，无需唤醒")
            else:
                success = screen_utils.wake_screen()
                print(f"\n唤醒屏幕: {'成功' if success else '失败'}")
        
        # 解锁屏幕
        if args.unlock:
            success = screen_utils.unlock_screen()
            print(f"\n解锁屏幕: {'成功' if success else '失败'}")
        
        # 如果有更多循环，等待指定的间隔时间
        if args.loop > 0 and i < loop_count - 1:
            print(f"\n等待 {args.interval} 秒后继续下一次检测...")
            time.sleep(args.interval)

if __name__ == "__main__":
    main() 