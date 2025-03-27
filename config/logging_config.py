import logging

def configure_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("quick_app_adb_test.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("QuickAppADBTester") 