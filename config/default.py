import os

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 截图保存目录
SCREENSHOTS_DIR = os.path.join(SCRIPT_DIR, "screenshots")

# 视频保存目录
VIDEOS_DIR = os.path.join(SCRIPT_DIR, "videos")

# 确保目录存在
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# 全局配置
DEFAULT_CONFIG = {
    'duration': 0,  # 默认0表示无限录制，直到手动停止
    'upload_screenshots': True,
    'telegram_bot_token': '7883072273:AAH0VO-o6O4-ZkY1KXLCiqT3xMqPgq--CXg',
    'telegram_chat_id': '5748280607'
} 