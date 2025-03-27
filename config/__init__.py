"""配置模块，用于集中管理程序配置"""

# 导入各模块配置
from .default import *
from .device import *
from .recording import *
from .notification import *
from .logging_config import configure_logging
from .utils import check_command_exists, check_ffmpeg_available
from .quick_app import *
from .scheduler import *

# 全局变量用于处理scrcpy录制
scrcpy_recording_process = None
current_video_path = None

# 定义全局变量，用于在信号处理和测试流程间共享数据
is_manually_interrupted = False
manual_interruption_video_url = None

# 导出获取日志器函数
__all__ = [
    # 默认配置
    'SCRIPT_DIR', 'SCREENSHOTS_DIR', 'VIDEOS_DIR', 'DEFAULT_CONFIG',
    
    # 设备配置
    'SCREEN_WIDTH', 'SCREEN_HEIGHT',
    
    # 录制配置
    'SCRCPY_CONFIG', 'scrcpy_recording_process', 'current_video_path',
    
    # 通知配置
    'FEISHU_WEBHOOK_URL', 'FEISHU_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
    
    # 快应用配置
    'SEARCH_KEYWORD', 'QUICK_APP_PACKAGE', 'QUICK_APPS', 'APP_INTERVAL_SECONDS',
    
    # 定时任务配置
    'SCHEDULE_INTERVAL_MINUTES', 'RUN_IMMEDIATELY_ON_START',
    
    # 信号处理相关
    'is_manually_interrupted', 'manual_interruption_video_url',
    
    # 功能函数
    'configure_logging', 'check_command_exists', 'check_ffmpeg_available'
] 