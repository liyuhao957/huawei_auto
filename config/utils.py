import subprocess
import time
import shutil
import logging

logger = logging.getLogger(__name__)

def check_command_exists(command):
    """
    检查系统是否安装了指定的命令
    
    Args:
        command: 要检查的命令名称
    
    Returns:
        bool: 如果命令存在则返回True，否则返回False
    """
    return shutil.which(command) is not None

def check_ffmpeg_available():
    """
    检查系统中是否安装了ffmpeg
    
    Returns:
        bool: 如果ffmpeg可用则返回True，否则返回False
    """
    if not check_command_exists('ffmpeg'):
        logger.warning("系统中未找到ffmpeg，视频修复功能将不可用")
        return False
    
    try:
        # 检查ffmpeg版本
        result = subprocess.run(['ffmpeg', '-version'], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        logger.info(f"检测到ffmpeg: {result.stdout.splitlines()[0]}")
        return True
    except Exception as e:
        logger.warning(f"ffmpeg检测失败: {str(e)}")
        return False 