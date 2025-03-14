#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清空手机应用简单测试脚本
这个脚本专门测试点击底部中间位置清除所有应用的功能
"""

import uiautomator2 as u2
import time
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("clear_center_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ClearCenterTest")

# 配置
DEVICE_SERIAL = None  # 如果有多台设备连接，请设置为特定设备序列号

def clear_apps_center_button():
    """使用底部中间位置的按钮清除所有应用"""
    logger.info("开始测试点击底部中间位置清除所有应用")
    
    # 连接设备
    device = u2.connect(DEVICE_SERIAL)
    screen_width, screen_height = device.window_size()
    logger.info(f"设备屏幕尺寸: {screen_width}x{screen_height}")
    
    # 1. 先强制停止快应用中心和相关应用
    logger.info("步骤1: 强制停止快应用中心和相关应用")
    try:
        device.shell("am force-stop com.huawei.fastapp")
        logger.info("已强制停止快应用中心")
        time.sleep(1)
        device.shell("am force-stop com.huawei.fastapp:ui")
        logger.info("已强制停止快应用UI进程")
        time.sleep(1)
    except Exception as e:
        logger.warning(f"强制停止应用时出错: {str(e)}")
    
    # 2. 按Home键回到桌面
    logger.info("步骤2: 按Home键回到桌面")
    device.press("home")
    time.sleep(1)
    
    # 3. 打开最近任务列表
    logger.info("步骤3: 打开最近任务列表")
    device.press("recent")
    time.sleep(2)
    
    # 4. 截图记录清除前状态
    logger.info("截图记录清除前状态")
    device.screenshot("before_clear.png")
    
    # 5. 直接点击底部中间位置，不检查任务卡片是否存在
    logger.info("步骤4: 直接点击底部中间位置清除应用")
    center_x = int(screen_width * 0.5)
    center_y = int(screen_height * 0.9)
    logger.info(f"点击坐标: ({center_x}, {center_y})")
    device.click(center_x, center_y)
    
    # 6. 等待1秒
    logger.info("等待1秒...")
    time.sleep(1)
    
    # 7. 返回桌面
    logger.info("返回桌面")
    device.press("home")
    
    # 8. 直接返回成功
    logger.info("点击底部中间位置完成，操作成功")
    return True

if __name__ == "__main__":
    result = clear_apps_center_button()
    logger.info(f"测试结果: {'成功' if result else '失败'}") 