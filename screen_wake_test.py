#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
屏幕唤醒测试脚本
这个脚本用于测试设备屏幕唤醒功能，以确保定时任务能够在屏幕熄灭后正常执行。
假设设备已经处于熄屏状态且没有设置锁屏密码，脚本将尝试唤醒设备。
"""

import uiautomator2 as u2
import time
import logging
import os
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screen_wake_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ScreenWakeTest")

# 配置
DEVICE_SERIAL = None  # 如果有多台设备连接，请设置为特定设备序列号
SCREENSHOTS_DIR = "screenshots"  # 存储截图的目录

# 如果截图目录不存在，则创建
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)

class ScreenWakeTester:
    """屏幕唤醒测试类"""
    
    def __init__(self, device_serial=None):
        """初始化测试器"""
        logger.info("初始化ScreenWakeTester")
        self.device = u2.connect(device_serial)  # 连接设备
        self.screen_width, self.screen_height = self.device.window_size()
        logger.info(f"设备屏幕尺寸: {self.screen_width}x{self.screen_height}")
    
    def take_screenshot(self, name=None):
        """截取屏幕截图"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}"
        
        filename = f"{SCREENSHOTS_DIR}/{name}.png"
        self.device.screenshot(filename)
        logger.info(f"截图已保存: {filename}")
        return filename
    
    def check_screen_state(self):
        """检查屏幕状态"""
        try:
            # 尝试获取当前屏幕状态
            info = self.device.info
            screen_on = info.get('screenOn', None)
            if screen_on is not None:
                logger.info(f"屏幕状态: {'亮屏' if screen_on else '熄屏'}")
                return screen_on
            else:
                # 如果无法直接获取屏幕状态，尝试通过其他方式判断
                try:
                    # 尝试截图，如果成功则说明屏幕是亮的
                    self.device.screenshot()
                    logger.info("屏幕状态: 亮屏 (通过截图判断)")
                    return True
                except Exception as e:
                    logger.info(f"屏幕状态: 可能熄屏 (截图失败: {str(e)})")
                    return False
        except Exception as e:
            logger.warning(f"检查屏幕状态失败: {str(e)}")
            return None
    
    def wake_screen(self):
        """唤醒屏幕"""
        logger.info("开始唤醒屏幕...")
        
        # 检查当前屏幕状态
        screen_state = self.check_screen_state()
        
        # 如果屏幕已经亮起，直接返回成功
        if screen_state:
            logger.info("屏幕已经处于亮屏状态，无需唤醒")
            return True
        
        # 尝试唤醒屏幕
        logger.info("尝试唤醒屏幕")
        try:
            # 方法1: 使用uiautomator2的screen_on方法
            logger.info("尝试使用screen_on方法唤醒屏幕")
            self.device.screen_on()
            time.sleep(1)
            
            # 检查是否成功唤醒
            if self.check_screen_state():
                logger.info("成功使用screen_on方法唤醒屏幕")
                return True
            
            # 方法2: 使用按电源键唤醒
            logger.info("尝试使用按电源键方法唤醒屏幕")
            self.device.press("power")
            time.sleep(1)
            
            if self.check_screen_state():
                logger.info("成功使用电源键唤醒屏幕")
                return True
            
            # 方法3: 使用shell命令唤醒
            logger.info("尝试使用shell命令唤醒屏幕")
            self.device.shell("input keyevent KEYCODE_WAKEUP")
            time.sleep(1)
            
            if self.check_screen_state():
                logger.info("成功使用shell命令唤醒屏幕")
                return True
            
            logger.error("所有唤醒方法均失败")
            return False
        except Exception as e:
            logger.error(f"唤醒屏幕时出错: {str(e)}")
            return False
    
    def simple_unlock(self):
        """简单解锁（适用于无密码设备）"""
        logger.info("尝试简单解锁（适用于无密码设备）")
        
        try:
            # 对于无密码设备，通常只需要滑动一下即可解锁
            logger.info("尝试滑动解锁屏幕")
            self.device.swipe(self.screen_width * 0.5, self.screen_height * 0.8, 
                             self.screen_width * 0.5, self.screen_height * 0.2)
            time.sleep(0.5)
            
            # 按下Home键确保回到主屏幕
            logger.info("按下Home键确保回到主屏幕")
            self.device.press("home")
            time.sleep(0.5)
            
            # 验证是否成功解锁
            current_app = self.device.app_current()
            logger.info(f"当前应用信息: {current_app}")
            
            # 尝试截图
            self.take_screenshot("after_wake_unlock")
            
            logger.info("简单解锁完成")
            return True
        except Exception as e:
            logger.error(f"简单解锁时出错: {str(e)}")
            return False
    
    def run_test(self):
        """运行测试"""
        logger.info("开始屏幕唤醒测试")
        
        # 1. 检查屏幕状态
        logger.info("步骤1: 检查屏幕状态")
        screen_on = self.check_screen_state()
        logger.info(f"屏幕是否亮起: {screen_on}")
        
        # 2. 唤醒屏幕
        logger.info("步骤2: 唤醒屏幕")
        wake_result = self.wake_screen()
        
        if not wake_result:
            logger.error("唤醒屏幕失败")
            return False
        
        # 3. 简单解锁（适用于无密码设备）
        logger.info("步骤3: 简单解锁")
        unlock_result = self.simple_unlock()
        
        # 4. 验证结果
        logger.info("步骤4: 验证结果")
        if wake_result and unlock_result:
            logger.info("测试成功: 屏幕已成功唤醒并解锁")
            return True
        else:
            logger.error("测试失败: 屏幕唤醒或解锁失败")
            return False

def main():
    """主函数"""
    logger.info("启动屏幕唤醒测试")
    
    tester = ScreenWakeTester(device_serial=DEVICE_SERIAL)
    result = tester.run_test()
    
    logger.info(f"测试完成。结果: {'成功' if result else '失败'}")
    return result

if __name__ == "__main__":
    main() 