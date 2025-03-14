#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
侧滑功能测试脚本
这个脚本专门用于测试不同参数的侧滑操作，不包含应用打开流程
假设应用已经打开，直接进行侧滑测试
"""

import uiautomator2 as u2
import time
import logging
import os
import sys
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("swipe_only_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SwipeOnlyTest")

# 配置
DEVICE_SERIAL = None  # 如果有多台设备连接，请设置为特定设备序列号
SCREENSHOTS_DIR = "swipe_screenshots"  # 存储截图的目录

# 如果截图目录不存在，则创建
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)


class SwipeOnlyTest:
    """侧滑测试类"""
    
    def __init__(self, device_serial=None):
        """初始化测试器"""
        logger.info("初始化SwipeOnlyTest")
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
    
    def test_swipe_method3(self):
        """测试方法3: 从屏幕最右边中间位置中等距离、超快速连续侧滑"""
        logger.info("测试方法3: 从屏幕最右边中间位置中等距离、超快速连续侧滑")
        
        # 截图记录侧滑前状态
        self.take_screenshot("before_swipe_method3")
        
        # 执行10次连续超快速侧滑
        for i in range(10):
            logger.info(f"方法3 - 第{i+1}次超快速侧滑")
            
            # 从屏幕最右边中间位置开始，中等距离侧滑 - 屏幕宽度的10%
            start_x = int(self.screen_width * 0.98)  # 屏幕最右边
            end_x = int(self.screen_width * 0.88)    # 向左滑动10%的屏幕宽度
            y_pos = int(self.screen_height * 0.5)    # 垂直位置在屏幕中间
            
            # 使用15毫秒的超快速持续时间（原来是50毫秒）
            try:
                self.device.shell(f"input swipe {start_x} {y_pos} {end_x} {y_pos} 15")
                logger.info(f"执行从最右边中间位置中等距离超快速侧滑: {start_x},{y_pos} -> {end_x},{y_pos}")
            except Exception as e:
                logger.warning(f"使用shell命令侧滑失败: {str(e)}")
                self.device.swipe(start_x, y_pos, end_x, y_pos, duration=0.015)
            
            # 每次侧滑后极短等待
            time.sleep(0.1)  # 减少等待时间，提高连续性
            
            # 每3次侧滑后截图
            if (i+1) % 3 == 0:
                self.take_screenshot(f"method3_swipe_{i+1}")
        
        # 截图记录侧滑后状态
        self.take_screenshot("after_swipe_method3")
        return True
    
    def test_swipe_method5(self):
        """测试方法5: 从屏幕最右边中间位置较长距离、超极速连续侧滑"""
        logger.info("测试方法5: 从屏幕最右边中间位置较长距离、超极速连续侧滑")
        
        # 截图记录侧滑前状态
        self.take_screenshot("before_swipe_method5")
        
        # 执行10次连续超极速侧滑
        for i in range(10):
            logger.info(f"方法5 - 第{i+1}次超极速侧滑")
            
            # 从屏幕最右边中间位置开始，较长距离侧滑 - 屏幕宽度的15%
            start_x = int(self.screen_width * 0.99)  # 屏幕最右边
            end_x = int(self.screen_width * 0.84)    # 向左滑动15%的屏幕宽度
            y_pos = int(self.screen_height * 0.5)    # 垂直位置在屏幕中间
            
            # 使用10毫秒的超极速持续时间（原来是20毫秒）
            try:
                self.device.shell(f"input swipe {start_x} {y_pos} {end_x} {y_pos} 10")
                logger.info(f"执行从最右边中间位置较长距离超极速侧滑: {start_x},{y_pos} -> {end_x},{y_pos}")
            except Exception as e:
                logger.warning(f"使用shell命令侧滑失败: {str(e)}")
                self.device.swipe(start_x, y_pos, end_x, y_pos, duration=0.01)
            
            # 每次侧滑后极短等待
            time.sleep(0.1)  # 减少等待时间，提高连续性
            
            # 每3次侧滑后截图
            if (i+1) % 3 == 0:
                self.take_screenshot(f"method5_swipe_{i+1}")
        
        # 截图记录侧滑后状态
        self.take_screenshot("after_swipe_method5")
        return True
    
    def test_single_method(self, method_num):
        """测试单个方法"""
        method_map = {
            3: self.test_swipe_method3,
            5: self.test_swipe_method5
        }
        
        if method_num in method_map:
            logger.info(f"仅测试方法{method_num}")
            return method_map[method_num]()
        else:
            logger.error(f"无效的方法编号: {method_num}，只支持方法3和方法5")
            return False
    
    def run_all_tests(self):
        """运行所有测试方法"""
        logger.info("开始运行所有侧滑测试方法")
        
        # 运行测试方法3
        logger.info("===== 开始测试方法3: 从屏幕最右边中间位置中等距离、超快速连续侧滑 =====")
        result3 = self.test_swipe_method3()
        logger.info(f"方法3测试完成。结果: {'成功' if result3 else '失败'}")
        time.sleep(1)
        
        # 运行测试方法5
        logger.info("===== 开始测试方法5: 从屏幕最右边中间位置较长距离、超极速连续侧滑 =====")
        result5 = self.test_swipe_method5()
        logger.info(f"方法5测试完成。结果: {'成功' if result5 else '失败'}")
        
        logger.info("所有侧滑测试方法已完成")
        return True


def main():
    """主函数"""
    try:
        logger.info("开始侧滑测试")
        tester = SwipeOnlyTest(device_serial=DEVICE_SERIAL)
        
        # 检查是否指定了特定的测试方法
        if len(sys.argv) > 1:
            try:
                method_num = int(sys.argv[1])
                if method_num not in [3, 5]:
                    logger.error(f"无效的方法编号: {method_num}，只支持方法3和方法5")
                    print("用法: python swipe_only_test.py [方法编号]")
                    print("方法编号: 3或5，不提供则测试所有方法")
                    return False
                tester.test_single_method(method_num)
            except ValueError:
                logger.error(f"无效的参数: {sys.argv[1]}")
                print("用法: python swipe_only_test.py [方法编号]")
                print("方法编号: 3或5，不提供则测试所有方法")
                return False
        else:
            # 运行所有测试
            tester.run_all_tests()
        
        logger.info("侧滑测试完成")
        return True
    except Exception as e:
        logger.error(f"测试失败，错误: {str(e)}")
        return False


if __name__ == "__main__":
    main() 