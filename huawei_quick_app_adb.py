#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huawei Quick App ADB-based Automation Script
通过ADB命令和坐标点击实现的快应用自动化测试脚本
使用ADBKeyboard输入法实现中文输入
"""

import subprocess
import time
import logging
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_app_adb_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuickAppADBTester")

# 配置
SCREENSHOTS_DIR = "screenshots"  # 存储截图的目录

# 如果截图目录不存在，则创建
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)

# 设备屏幕尺寸
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2376

class QuickAppADBTester:
    """使用ADB命令和坐标点击的快应用测试器"""
    
    def __init__(self):
        """初始化测试器"""
        logger.info("初始化QuickAppADBTester")
        # 确保ADBKeyboard已安装并设置为默认输入法
        self.ensure_adbkeyboard_input_method()
        
    def check_adbkeyboard_installed(self):
        """检查ADBKeyboard是否已安装"""
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
        
        logger.warning("未检测到ADBKeyboard，某些功能可能无法正常工作")
        logger.warning("请安装ADBKeyboard: https://github.com/senzhk/ADBKeyBoard")
        return False
    
    def ensure_adbkeyboard_input_method(self):
        """确保ADBKeyboard被设置为当前输入法"""
        logger.info("确保ADBKeyboard被设置为默认输入法")
        
        # 首先检查ADBKeyboard是否已安装
        is_installed = self.check_adbkeyboard_installed()
        if not is_installed:
            logger.warning("ADBKeyboard未安装，将使用备用输入方法（可能不支持中文）")
            return False
        
        # 保存当前输入法以便稍后恢复
        result = subprocess.run("adb shell settings get secure default_input_method", 
                               shell=True, capture_output=True, text=True)
        self.original_ime = result.stdout.strip()
        logger.info(f"当前输入法: {self.original_ime}")
        
        # 如果当前已经是ADBKeyboard，则无需更改
        if "com.android.adbkeyboard" in self.original_ime:
            logger.info("当前已经是ADBKeyboard输入法，无需切换")
            return True
        
        # 设置ADBKeyboard为默认
        subprocess.run("adb shell ime set com.android.adbkeyboard/.AdbIME", shell=True)
        time.sleep(1)
        
        # 验证是否设置成功
        verify_result = subprocess.run("adb shell settings get secure default_input_method", 
                                      shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard" in verify_result.stdout:
            logger.info("成功设置ADBKeyboard为默认输入法")
            return True
        else:
            logger.warning(f"设置输入法可能失败，当前输入法: {verify_result.stdout.strip()}")
            return False
        
    def restore_original_input_method(self):
        """恢复原来的输入法"""
        if hasattr(self, 'original_ime') and self.original_ime and "com.android.adbkeyboard" not in self.original_ime:
            logger.info(f"恢复原来的输入法: {self.original_ime}")
            subprocess.run(f"adb shell ime set {self.original_ime}", shell=True)
            time.sleep(1)
        
    def tap(self, x, y):
        """点击指定坐标"""
        cmd = f"adb shell input tap {x} {y}"
        logger.info(f"点击坐标: ({x}, {y})")
        subprocess.run(cmd, shell=True)
        
    def tap_by_percent(self, x_percent, y_percent):
        """基于屏幕百分比位置点击"""
        x = int(SCREEN_WIDTH * x_percent)
        y = int(SCREEN_HEIGHT * y_percent)
        self.tap(x, y)
        
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动屏幕"""
        cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        subprocess.run(cmd, shell=True)
    
    def swipe_by_percent(self, start_x_percent, start_y_percent, end_x_percent, end_y_percent, duration=300):
        """基于屏幕百分比位置滑动"""
        start_x = int(SCREEN_WIDTH * start_x_percent)
        start_y = int(SCREEN_HEIGHT * start_y_percent)
        end_x = int(SCREEN_WIDTH * end_x_percent)
        end_y = int(SCREEN_HEIGHT * end_y_percent)
        self.swipe(start_x, start_y, end_x, end_y, duration)
        
    def press_key(self, keycode):
        """按下按键"""
        cmd = f"adb shell input keyevent {keycode}"
        logger.info(f"按下按键: {keycode}")
        subprocess.run(cmd, shell=True)
        
    def press_home(self):
        """按下Home键"""
        logger.info("按下Home键")
        self.press_key("KEYCODE_HOME")
        
    def press_enter(self):
        """按下回车键"""
        logger.info("按下回车键")
        self.press_key("66")
        
    def press_back(self):
        """按下返回键"""
        logger.info("按下返回键")
        self.press_key("KEYCODE_BACK")
        
    def press_recent_apps(self):
        """打开最近任务列表"""
        logger.info("打开最近任务列表")
        self.press_key("KEYCODE_APP_SWITCH")
        
    def take_screenshot(self, name=None):
        """截取屏幕截图"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}"
        
        filename = f"{SCREENSHOTS_DIR}/{name}.png"
        logger.info(f"截图: {filename}")
        
        # 使用ADB命令截图
        subprocess.run(f"adb shell screencap -p /sdcard/{name}.png", shell=True)
        subprocess.run(f"adb pull /sdcard/{name}.png {filename}", shell=True)
        subprocess.run(f"adb shell rm /sdcard/{name}.png", shell=True)
        
        return filename
        
    def run_shell_command(self, command):
        """运行shell命令并返回输出"""
        logger.info(f"运行命令: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        logger.info(f"命令输出: {result.stdout}")
        return result.stdout

    def input_text(self, text):
        """输入文本 - 使用ADBKeyboard输入中文或其他文本"""
        logger.info(f"输入文本: {text}")
        
        # 如果是英文或数字，可以直接使用标准输入法
        if all(ord(c) < 128 for c in text):
            logger.info("使用标准输入法输入ASCII文本")
            cmd = f'adb shell input text "{text}"'
            subprocess.run(cmd, shell=True)
            return
        
        # 对于中文或其他非ASCII文本，使用ADBKeyboard
        logger.info("使用ADBKeyboard输入非ASCII文本")
        
        # 处理转义字符
        escaped_text = text.replace('"', '\\"')
        cmd = f'adb shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped_text}"'
        logger.info(f"执行命令: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 检查是否成功
        if "Broadcast completed" in result.stdout:
            logger.info("文本输入广播命令成功发送")
        else:
            logger.warning("文本输入广播命令可能未成功发送，尝试备用方法")
            # 备用方法
            escaped_text = text.replace("'", "\\'")
            backup_cmd = f"adb shell am broadcast -a ADB_INPUT_TEXT --es msg '{escaped_text}'"
            logger.info(f"执行备用命令: {backup_cmd}")
            subprocess.run(backup_cmd, shell=True)
            
        time.sleep(1)  # 等待输入完成

    def clear_quick_app_center_data(self):
        """流程1: 清除快应用中心数据"""
        logger.info("===== 开始执行流程1: 清除快应用中心数据 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        # 2. 打开设置应用
        logger.info("步骤2: 打开设置应用")
        self.run_shell_command("adb shell am start -a android.settings.SETTINGS")
        time.sleep(2)
        
        # 3. 点击搜索框
        logger.info("步骤3: 点击搜索框")
        self.tap_by_percent(0.256, 0.217)  # 坐标: (276, 516)
        time.sleep(1)
        
        # 4. 输入"应用和服务"
        logger.info("步骤4: 输入'应用和服务'")
        self.input_text("应用和服务")
        time.sleep(1)
        
        # 5. 点击搜索结果"应用和服务"
        logger.info("步骤5: 点击搜索结果'应用和服务'")
        self.tap_by_percent(0.236, 0.176)  # 坐标: (255, 418)
        time.sleep(2)
        
        # 6. 点击"应用管理"
        logger.info("步骤6: 点击'应用管理'")
        self.tap_by_percent(0.222, 0.159)  # 坐标: (240, 377)
        time.sleep(2)
        
        # 7. 点击搜索框
        logger.info("步骤7: 点击搜索框")
        self.tap_by_percent(0.222, 0.149)  # 坐标: (240, 353)
        time.sleep(1)
        
        # 8. 输入"快应用中心"
        logger.info("步骤8: 输入'快应用中心'")
        self.input_text("快应用中心")
        time.sleep(1)
        
        # 9. 点击搜索结果"快应用中心"
        logger.info("步骤9: 点击搜索结果'快应用中心'") 
        self.tap_by_percent(0.242, 0.242)  # 坐标: (261, 576)
        time.sleep(2)
        
        # 10. 向上滑动显示更多内容 - 修正为从下往上滑
        logger.info("步骤10: 向上滑动显示更多内容")
        self.swipe_by_percent(0.454, 0.8, 0.454, 0.4)  # 从下部(约80%位置)滑动到上部(约40%位置)
        time.sleep(1)
        self.swipe_by_percent(0.454, 0.7, 0.454, 0.3)  # 再滑一次确保看到更多内容
        time.sleep(1)
        
        # 11. 点击"存储"
        logger.info("步骤11: 点击'存储'")
        self.tap_by_percent(0.145, 0.430)  # 坐标: (157, 1021)
        time.sleep(1)
        
        # 12. 点击"删除数据"
        logger.info("步骤12: 点击'删除数据'")
        self.tap_by_percent(0.514, 0.535)  # 坐标: (555, 1271)
        time.sleep(1)
        
        # 13. 点击确认对话框中的"确定"按钮
        logger.info("步骤13: 点击确认对话框中的'确定'按钮")
        self.tap_by_percent(0.701, 0.932)  # 坐标: (757, 2215)
        time.sleep(2)
        
        logger.info("流程1执行完成: 清除快应用中心数据")
        return True
        
    def manage_quick_apps_via_market(self):
        """流程2: 通过应用市场管理快应用"""
        logger.info("===== 开始执行流程2: 通过应用市场管理快应用 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        # 2. 打开应用市场
        logger.info("步骤2: 打开应用市场")
        self.run_shell_command("adb shell am start -n com.huawei.appmarket/.MainActivity")
        time.sleep(5)  # 应用市场加载可能需要更长时间
        
        # 3. 点击"我的"选项卡
        logger.info("步骤3: 点击'我的'选项卡")
        self.tap_by_percent(0.894, 0.946)  # 坐标: (965, 2248)
        time.sleep(2)
        
        # 4. 点击"快应用管理"选项
        logger.info("步骤4: 点击'快应用管理'选项")
        self.tap_by_percent(0.159, 0.696)  # 坐标: (172, 1654)
        time.sleep(2)
        
        # 5. 点击"同意"按钮(如果出现)
        logger.info("步骤5: 检查并点击'同意'按钮(如果出现)")
        self.tap_by_percent(0.681, 0.937)  # 坐标: (736, 2227)
        time.sleep(2)
        
        # 增加额外等待时间，确保应用市场稳定后再继续下一流程
        logger.info("等待应用市场稳定 (3秒)")
        time.sleep(3)
        
        logger.info("流程2执行完成: 通过应用市场管理快应用")
        return True
    
    def search_and_open_quick_app(self):
        """流程3: 搜索并打开快应用进行测试"""
        logger.info("===== 开始执行流程3: 搜索并打开快应用进行测试 =====")
        
        # 1. 点击搜索框
        logger.info("步骤1: 点击搜索框")
        self.tap_by_percent(0.302, 0.149)  # 坐标: (326, 353)
        time.sleep(1)
        
        # 2. 输入"优购"
        logger.info("步骤2: 输入'优购'")
        self.input_text("优购")
        time.sleep(1)
        
        # 3. 按下回车键
        logger.info("步骤3: 按下回车键")
        self.press_enter()
        time.sleep(2)
        
        # 4. 点击搜索结果旁边的"打开"按钮
        logger.info("步骤4: 点击搜索结果旁边的'打开'按钮")
        self.tap_by_percent(0.797, 0.156)  # 坐标: (861, 371)
        time.sleep(8)  # 应用打开需要更长时间
        
        # 5. 执行10次侧滑
        logger.info("步骤5: 准备执行10次侧滑")
        start_x = int(SCREEN_WIDTH * 0.98)  # 起点X：屏幕宽度的98%
        end_x = int(SCREEN_WIDTH * 0.88)    # 终点X：屏幕宽度的88%
        y_pos = int(SCREEN_HEIGHT * 0.5)    # Y位置：屏幕高度的50%
        
        # 6. 执行侧滑操作
        logger.info("步骤6: 执行10次侧滑操作")
        for i in range(10):
            logger.info(f"第{i+1}次侧滑")
            self.swipe(start_x, y_pos, end_x, y_pos, duration=15)  # 超快速侧滑
            time.sleep(0.1)  # 极短等待
        
        time.sleep(2)  # 等待界面稳定
        
        # 7. 检查当前应用
        logger.info("步骤7: 检查当前应用")
        current_app = self.run_shell_command("adb shell dumpsys window | grep mCurrentFocus")
        logger.info(f"当前应用: {current_app}")
        
        # 8. 截图记录状态
        logger.info("步骤8: 截图记录侧滑后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.take_screenshot(f"after_swipe_{timestamp}")
        
        # 9. 按Home键
        logger.info("步骤9: 按Home键")
        self.press_home()
        time.sleep(10)  # 等待一段时间
        
        # 10. 再次检查当前应用
        logger.info("步骤10: 再次检查当前应用")
        current_app = self.run_shell_command("adb shell dumpsys window | grep mCurrentFocus")
        logger.info(f"按Home后当前应用: {current_app}")
        
        # 11. 再次截图记录状态
        logger.info("步骤11: 再次截图记录按Home后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.take_screenshot(f"after_home_{timestamp}")
        
        logger.info("流程3执行完成: 搜索并打开快应用进行测试")
        return True
    
    def clear_all_apps(self):
        """流程4: 清空手机里的全部应用"""
        logger.info("===== 开始执行流程4: 清空手机里的全部应用 =====")
        
        # 1. 强制停止快应用
        logger.info("步骤1: 强制停止快应用")
        self.run_shell_command("adb shell am force-stop com.huawei.fastapp")
        time.sleep(1)
        
        # 2. 按Home键
        logger.info("步骤2: 按Home键")
        self.press_home()
        time.sleep(1)
        
        # 3. 打开最近任务列表
        logger.info("步骤3: 打开最近任务列表")
        self.press_recent_apps()
        time.sleep(2)
        
        # 4. 点击底部中间清除按钮
        logger.info("步骤4: 点击底部中间清除按钮")
        self.tap_by_percent(0.500, 0.904)  # 坐标: (540, 2147)
        time.sleep(1)
        
        # 5. 按Home键回到桌面
        logger.info("步骤5: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        logger.info("流程4执行完成: 清空手机里的全部应用")
        return True
    
    def run_all_flows(self):
        """执行所有流程"""
        logger.info("开始执行所有流程")
        
        try:
            # 流程1: 清除快应用中心数据
            result1 = self.clear_quick_app_center_data()
            
            # 流程2: 通过应用市场管理快应用
            result2 = self.manage_quick_apps_via_market()
            
            # 流程3: 搜索并打开快应用进行测试
            result3 = self.search_and_open_quick_app()
            
            # 流程4: 清空手机里的全部应用
            result4 = self.clear_all_apps()
            
            logger.info(f"所有流程执行完成。结果: 流程1: {result1}, 流程2: {result2}, 流程3: {result3}, 流程4: {result4}")
            return all([result1, result2, result3, result4])
        
        except Exception as e:
            logger.error(f"执行流程时出错: {str(e)}")
            return False
        
        finally:
            # 恢复原始输入法
            self.restore_original_input_method()

def main():
    """主函数"""
    logger.info("启动快应用ADB测试")
    
    tester = QuickAppADBTester()
    
    # 执行所有流程
    tester.run_all_flows()
    
    logger.info("测试完成")

if __name__ == "__main__":
    main() 