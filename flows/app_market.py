import time
import logging

# 获取logger
logger = logging.getLogger(__name__)

class AppMarket:
    """流程2: 通过应用市场管理快应用"""
    
    def __init__(self, adb_controller):
        """初始化
        
        Args:
            adb_controller: ADB控制器实例，提供基础操作方法
        """
        self.adb = adb_controller
    
    def execute(self):
        """执行通过应用市场管理快应用流程
        
        Returns:
            bool: 流程是否成功执行
        """
        logger.info("===== 开始执行流程2: 通过应用市场管理快应用 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.adb.press_home()
        time.sleep(1)
        
        # 2. 打开应用市场
        logger.info("步骤2: 打开应用市场")
        self.adb.run_shell_command("adb shell am start -n com.huawei.appmarket/.MainActivity")
        time.sleep(5)  # 应用市场加载可能需要更长时间
        
        # 3. 点击"我的"选项卡
        logger.info("步骤3: 点击'我的'选项卡")
        self.adb.tap_by_percent(0.904, 0.950)  # 坐标: (965, 2248)
        time.sleep(2)
        
        # 4. 点击"快应用管理"选项
        logger.info("步骤4: 点击'快应用管理'选项")
        self.adb.tap_by_percent(0.168, 0.711)  # 坐标: (172, 1654)
        time.sleep(5)  # 增加等待时间，从2秒增加到5秒，确保页面完全加载
        
        # 5. 点击"同意"按钮(如果出现)
        logger.info("步骤5: 检查并点击'同意'按钮(如果出现)")
        self.adb.tap_by_percent(0.715, 0.936)  # 坐标: (736, 2227)
        time.sleep(2)
        
        # 增加额外等待时间，确保应用市场稳定后再继续下一流程
        logger.info("等待应用市场稳定 (5秒)")
        time.sleep(5)  # 从3秒增加到5秒
        
        logger.info("流程2执行完成: 通过应用市场管理快应用")
        return True 