import time
import logging

# 获取logger
logger = logging.getLogger(__name__)

class ClearAppData:
    """流程1: 清除快应用中心数据"""
    
    def __init__(self, adb_controller):
        """初始化
        
        Args:
            adb_controller: ADB控制器实例，提供基础操作方法
        """
        self.adb = adb_controller
    
    def execute(self):
        """执行清除快应用中心数据流程
        
        Returns:
            bool: 流程是否成功执行
        """
        logger.info("===== 开始执行流程1: 清除快应用中心数据 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.adb.press_home()
        time.sleep(1)
        
        # 2. 打开设置应用
        logger.info("步骤2: 打开设置应用")
        self.adb.run_shell_command("adb shell am start -a android.settings.SETTINGS")
        time.sleep(2)
        
        # 3. 点击搜索框
        logger.info("步骤3: 点击搜索框")
        self.adb.tap_by_percent(0.254, 0.237)  # 坐标: (276, 516)
        time.sleep(1)
        
        # 4. 输入"应用和服务"
        logger.info("步骤4: 输入'应用和服务'")
        self.adb.input_text("应用和服务")
        time.sleep(1)
        
        # 5. 点击搜索结果"应用和服务"
        logger.info("步骤5: 点击搜索结果'应用和服务'")
        self.adb.tap_by_percent(0.246, 0.183)  # 坐标: (255, 418)
        time.sleep(2)
        
        # 6. 点击"应用管理"
        logger.info("步骤6: 点击'应用管理'")
        self.adb.tap_by_percent(0.151, 0.174)  # 坐标: (240, 377)
        time.sleep(2)
        
        # 7. 点击搜索框
        logger.info("步骤7: 点击搜索框")
        self.adb.tap_by_percent(0.206, 0.164)  # 坐标: (240, 353)
        time.sleep(1)
        
        # 8. 输入"快应用中心"
        logger.info("步骤8: 输入'快应用中心'")
        self.adb.input_text("快应用中心")
        time.sleep(1)
        
        # 9. 点击搜索结果"快应用中心"
        logger.info("步骤9: 点击搜索结果'快应用中心'") 
        self.adb.tap_by_percent(0.273, 0.249)  # 坐标: (261, 576)
        time.sleep(2)
        
        # 10. 向上滑动显示更多内容 - 修正为从下往上滑
        logger.info("步骤10: 向上滑动显示更多内容")
        self.adb.swipe_by_percent(0.454, 0.8, 0.454, 0.4)  # 从下部(约80%位置)滑动到上部(约40%位置)
        time.sleep(1)
        
        # 11. 点击"存储"
        logger.info("步骤11: 点击'存储'")
        self.adb.tap_by_percent(0.124, 0.422)  # 坐标: (157, 1021)
        time.sleep(1)
        
        # 12. 点击"删除数据"
        logger.info("步骤12: 点击'删除数据'")
        self.adb.tap_by_percent(0.506, 0.556)  # 坐标: (555, 1271)
        time.sleep(1)
        
        # 13. 点击确认对话框中的"确定"按钮
        logger.info("步骤13: 点击确认对话框中的'确定'按钮")
        self.adb.tap_by_percent(0.739, 0.935)  # 坐标: (757, 2215)
        time.sleep(2)
        
        logger.info("流程1执行完成: 清除快应用中心数据")
        return True 