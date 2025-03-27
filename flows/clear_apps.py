import time
import logging

# 获取logger
logger = logging.getLogger(__name__)

class ClearApps:
    """流程4: 清空手机里的全部应用"""
    
    def __init__(self, adb_controller):
        """初始化
        
        Args:
            adb_controller: ADB控制器实例，提供基础操作方法
        """
        self.adb = adb_controller
    
    def execute(self):
        """执行清空手机里的全部应用流程
        
        Returns:
            bool: 流程是否成功执行
        """
        logger.info("===== 开始执行流程4: 清空手机里的全部应用 =====")
        
        # 1. 强制停止快应用
        logger.info("步骤1: 强制停止快应用")
        self.adb.run_shell_command("adb shell am force-stop com.huawei.fastapp")
        time.sleep(1)
        
        # 2. 按Home键
        logger.info("步骤2: 按Home键")
        self.adb.press_home()
        time.sleep(1)
        
        # 3. 打开最近任务列表
        logger.info("步骤3: 打开最近任务列表")
        self.adb.press_recent_apps()
        time.sleep(2)
        
        # 4. 点击底部中间清除按钮
        logger.info("步骤4: 点击底部中间清除按钮")
        self.adb.tap_by_percent(0.495, 0.909)  # 坐标: (540, 2147)
        time.sleep(1)
        
        # 5. 按Home键回到桌面
        logger.info("步骤5: 按Home键回到桌面")
        self.adb.press_home()
        time.sleep(1)
        
        logger.info("流程4执行完成: 清空手机里的全部应用")
        return True 