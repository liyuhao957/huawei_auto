import subprocess
import time
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_screenrecord_available():
    """检查设备是否支持screenrecord命令"""
    try:
        result = subprocess.run(
            "adb shell which screenrecord",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error("设备上找不到screenrecord命令")
            logger.info("尝试使用完整路径: /system/bin/screenrecord")
            return "/system/bin/screenrecord"
        return "screenrecord"
    except Exception as e:
        logger.error(f"检查screenrecord时出错: {str(e)}")
        return None

def start_recording():
    """开始录制屏幕"""
    # 检查screenrecord命令
    screenrecord_cmd = check_screenrecord_available()
    if not screenrecord_cmd:
        logger.error("设备不支持screenrecord，无法进行录制")
        return
    
    # 确保输出目录存在
    os.makedirs("recordings", exist_ok=True)
    
    # 生成输出文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = f"/sdcard/recording_{timestamp}.mp4"
    
    # 检查sdcard目录是否可写
    try:
        subprocess.run(
            "adb shell touch /sdcard/test_write",
            shell=True,
            check=True
        )
        subprocess.run(
            "adb shell rm /sdcard/test_write",
            shell=True
        )
    except subprocess.CalledProcessError:
        logger.error("无法写入/sdcard目录，尝试使用/data/local/tmp目录")
        output_path = f"/data/local/tmp/recording_{timestamp}.mp4"
    
    # 开始录制
    logger.info("按回车键开始录制...")
    input()
    
    cmd = f"adb shell {screenrecord_cmd} {output_path}"
    logger.info(f"开始录制，输出文件: {output_path}")
    logger.info("按回车键停止录制...")
    
    # 启动录制进程
    process = subprocess.Popen(cmd, shell=True)
    
    # 等待用户按回车停止录制
    input()
    
    # 终止录制进程（使用更可靠的方式）
    try:
        # 先尝试使用SIGINT
        process.send_signal(subprocess.signal.SIGINT)
        time.sleep(1)
        
        # 如果进程还在运行，使用SIGTERM
        if process.poll() is None:
            process.terminate()
            time.sleep(1)
            
        # 如果还在运行，使用SIGKILL
        if process.poll() is None:
            process.kill()
            
        process.wait(timeout=5)
        logger.info("录制已停止")
    except Exception as e:
        logger.error(f"停止录制时出错: {str(e)}")
    
    # 等待一会确保文件写入完成
    time.sleep(3)
    
    # 检查文件是否存在
    check_cmd = f"adb shell ls {output_path}"
    if subprocess.run(check_cmd, shell=True, capture_output=True).returncode != 0:
        logger.error("录制文件未生成")
        return
    
    # 将录制文件拉取到本地
    local_path = os.path.join("recordings", f"recording_{timestamp}.mp4")
    logger.info(f"正在将录制文件拷贝到本地: {local_path}")
    
    # 使用-p参数保持文件权限
    pull_result = subprocess.run(f"adb pull {output_path} {local_path}", shell=True, capture_output=True, text=True)
    if pull_result.returncode != 0:
        logger.error(f"拷贝文件失败: {pull_result.stderr}")
        return
    
    # 检查本地文件是否存在且大小大于0
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        logger.info(f"录制完成，文件保存在: {local_path}")
        # 删除设备上的临时文件
        subprocess.run(f"adb shell rm {output_path}", shell=True)
    else:
        logger.error("录制文件保存失败")

if __name__ == "__main__":
    try:
        start_recording()
    except KeyboardInterrupt:
        logger.info("\n录制被用户中断")
    except Exception as e:
        logger.error(f"发生错误: {str(e)}") 