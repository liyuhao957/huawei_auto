import time
import logging
from datetime import datetime

# 获取logger
logger = logging.getLogger(__name__)

class QuickAppTesting:
    """流程3: 搜索并打开快应用进行测试"""
    
    def __init__(self, adb_controller):
        """初始化
        
        Args:
            adb_controller: ADB控制器实例，提供基础操作方法
        """
        self.adb = adb_controller
        # 保存截图路径和URL的属性
        self.swipe_screenshot_path = None
        self.swipe_screenshot_url = None
        self.home_screenshot_path = None
        self.home_screenshot_url = None
    
    def execute(self):
        """执行搜索并打开快应用进行测试流程
        
        Returns:
            dict: 测试结果字典，包含"防侧滑"和"拉回"两个键
        """
        logger.info("===== 开始执行流程3: 搜索并打开快应用进行测试 =====")
        
        # 用于存储测试结果
        test_results = {
            "防侧滑": False,
            "拉回": False
        }
        
        # 1. 点击搜索框
        logger.info("步骤1: 点击搜索框")
        self.adb.tap_by_percent(0.214, 0.164)  # 坐标: (326, 353)
        time.sleep(1)
        
        # 2. 输入"优购"
        logger.info("步骤2: 输入'买乐多'")
        self.adb.input_text("买乐多")
        time.sleep(1)
        
        # 3. 按下回车键
        logger.info("步骤3: 按下回车键")
        self.adb.press_enter()
        time.sleep(2)
        
        # 4. 点击搜索结果旁边的"打开"按钮
        logger.info("步骤4: 点击搜索结果旁边的'打开'按钮")
        self.adb.tap_by_percent(0.820, 0.168)  # 坐标: (861, 371)
        time.sleep(8)  # 应用打开需要更长时间
        
        # 5. 执行10次侧滑
        logger.info("步骤5: 准备执行10次侧滑")
        # 获取屏幕尺寸
        from config import SCREEN_WIDTH, SCREEN_HEIGHT
        start_x = int(SCREEN_WIDTH * 0.98)  # 起点X：屏幕宽度的98%
        end_x = int(SCREEN_WIDTH * 0.88)    # 终点X：屏幕宽度的88%
        y_pos = int(SCREEN_HEIGHT * 0.5)    # Y位置：屏幕高度的50%
        
        # 6. 执行侧滑操作
        logger.info("步骤6: 执行10次侧滑操作")
        for i in range(10):
            logger.info(f"第{i+1}次侧滑")
            self.adb.swipe(start_x, y_pos, end_x, y_pos, duration=15)  # 超快速侧滑
            time.sleep(0.1)  # 极短等待
        
        time.sleep(2)  # 等待界面稳定
        
        # 7. 检查当前应用
        logger.info("步骤7: 检查当前应用")
        is_quick_app = self.adb.is_quick_app_running("优购")
        
        if is_quick_app:
            logger.info("侧滑拦截成功：快应用仍在前台运行")
            test_results["防侧滑"] = True
        else:
            logger.warning("侧滑拦截失败：快应用已不在前台运行")
            test_results["防侧滑"] = False
        
        # 8. 截图记录状态
        logger.info("步骤8: 截图记录侧滑后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.swipe_screenshot_path, self.swipe_screenshot_url = self.adb.take_screenshot(f"after_swipe_{timestamp}", upload=True)
        
        # 9. 按Home键
        logger.info("步骤9: 按Home键")
        self.adb.press_home()
        time.sleep(10)  # 等待一段时间
        
        # 10. 再次检查当前应用
        logger.info("步骤10: 再次检查当前应用")
        is_quick_app = self.adb.is_quick_app_running("优购")
        
        if is_quick_app:
            logger.info("拉回成功：按Home键后快应用仍在前台运行")
            test_results["拉回"] = True
        else:
            logger.warning("拉回失败：按Home键后快应用已不在前台运行")
            test_results["拉回"] = False
        
        # 11. 再次截图记录状态
        logger.info("步骤11: 再次截图记录按Home后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.home_screenshot_path, self.home_screenshot_url = self.adb.take_screenshot(f"after_home_{timestamp}", upload=True)
        
        logger.info("流程3执行完成: 搜索并打开快应用进行测试")
        # 返回详细的测试结果，而不仅仅是布尔值
        return test_results 