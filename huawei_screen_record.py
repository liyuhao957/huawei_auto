#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import subprocess
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('huawei_screen_record.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('huawei_screen_record')

# 创建视频存储目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS_DIR = os.path.join(SCRIPT_DIR, "videos")
SCREENSHOTS_DIR = os.path.join(SCRIPT_DIR, "screenshots")
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Telegram配置
TELEGRAM_BOT_TOKEN = "7883072273:AAH0VO-o6O4-ZkY1KXLCiqT3xMqPgq--CXg"
TELEGRAM_CHAT_ID = "-1002505009144"

def upload_to_telegram(file_path):
    """
    上传文件(图片或视频)到Telegram
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: 上传成功返回文件URL，失败返回None
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return None
    
    try:
        logger.info(f"开始上传文件到Telegram: {file_path}")
        
        # 判断是图片还是视频
        file_ext = os.path.splitext(file_path)[1].lower()
        is_video = file_ext in ['.mp4', '.avi', '.mov', '.3gp']
        
        # 构建API URL
        api_method = 'sendVideo' if is_video else 'sendPhoto'
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{api_method}"
        
        # 准备请求参数
        param_name = 'video' if is_video else 'photo'
        
        with open(file_path, 'rb') as file:
            files = {param_name: file}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            
            # 发送POST请求
            logger.info(f"发送请求到 {api_method}...")
            response = requests.post(url, files=files, data=data)
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                # 获取文件ID
                file_id = None
                if is_video:
                    file_id = result["result"]["video"]["file_id"]
                else:
                    # 获取最大尺寸的图片
                    photo_sizes = result["result"]["photo"]
                    file_id = max(photo_sizes, key=lambda x: x["width"])["file_id"]
                
                # 获取文件路径
                file_path_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                file_path_response = requests.get(file_path_url)
                
                if file_path_response.status_code == 200:
                    file_path_result = file_path_response.json()
                    if file_path_result.get("ok"):
                        file_path = file_path_result["result"]["file_path"]
                        # 构建下载URL
                        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                        logger.info(f"文件上传成功! 下载URL: {download_url}")
                        return download_url
            
            logger.warning("文件上传成功，但无法获取URL")
            return None
        else:
            logger.warning(f"文件上传请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            return None
    except Exception as e:
        logger.error(f"上传文件到Telegram时出错: {str(e)}")
        
        # 打印更详细的错误信息以便调试
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        
        return None

def check_screen_record_available():
    """检查设备是否支持screenrecord命令"""
    logger.info("检查设备是否支持screenrecord命令...")
    result = subprocess.run(
        "adb shell which screenrecord", 
        shell=True, capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        logger.info(f"设备支持screenrecord命令: {result.stdout.strip()}")
        return True
    else:
        logger.warning("设备不支持标准的screenrecord命令")
        return False

def take_screenshot(name=None):
    """截图并保存到指定目录
    
    Args:
        name: 截图名称，不包含扩展名
        
    Returns:
        str: 截图文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name:
        screenshot_name = f"{name}_{timestamp}.png"
    else:
        screenshot_name = f"screenshot_{timestamp}.png"
    
    screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)
    device_path = f"/sdcard/{screenshot_name}"
    
    logger.info(f"开始截图: {screenshot_path}")
    
    try:
        # 执行截图命令
        subprocess.run(f"adb shell screencap -p {device_path}", shell=True, check=True)
        
        # 检查截图是否成功
        check_result = subprocess.run(
            f"adb shell ls {device_path}", 
            shell=True, capture_output=True, text=True
        )
        
        if "No such file" in check_result.stdout:
            logger.error(f"截图在设备上创建失败: {device_path}")
            return None
            
        # 拉取到本地
        subprocess.run(f"adb pull {device_path} {screenshot_path}", shell=True, check=True)
        
        # 清理设备上的文件
        subprocess.run(f"adb shell rm {device_path}", shell=True)
        
        logger.info(f"截图成功: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        logger.error(f"截图失败: {str(e)}")
        return None

def sequential_screenshots(duration=10, interval=1.0, name=None, upload=True):
    """通过连续截图模拟视频录制
    
    Args:
        duration: 总持续时间(秒)
        interval: 截图间隔时间(秒)
        name: 基础文件名
        upload: 是否上传其中一张截图
        
    Returns:
        tuple: (截图列表, 上传的URL)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name:
        base_name = f"{name}_{timestamp}"
    else:
        base_name = f"sequence_{timestamp}"
        
    logger.info(f"开始连续截图，持续{duration}秒，间隔{interval}秒")
    
    screenshots = []
    upload_url = None
    
    try:
        start_time = time.time()
        frame = 0
        
        while time.time() - start_time < duration:
            frame_name = f"{base_name}_frame{frame:03d}"
            screenshot_path = take_screenshot(frame_name)
            
            if screenshot_path:
                screenshots.append(screenshot_path)
                # 只上传第一张截图
                if upload and frame == 0:
                    logger.info("上传第一张截图...")
                    upload_url = upload_to_telegram(screenshot_path)
            
            frame += 1
            # 计算下一次截图的等待时间
            elapsed = time.time() - start_time
            next_capture = interval * frame
            wait_time = max(0, next_capture - elapsed)
            
            if wait_time > 0 and time.time() - start_time + wait_time < duration:
                time.sleep(wait_time)
        
        logger.info(f"连续截图完成，共{len(screenshots)}张截图")
        return screenshots, upload_url
    
    except Exception as e:
        logger.error(f"连续截图失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return screenshots, upload_url

def huawei_screen_record_alternative(duration=10, name=None, upload=True):
    """Huawei设备上的屏幕录制替代方法
    
    使用华为专用录屏方法或备用方法录制屏幕
    
    Args:
        duration: 录制时长(秒)
        name: 视频名称基础部分
        upload: 是否上传视频或截图
        
    Returns:
        tuple: (本地文件路径, 上传URL)
    """
    logger.info(f"使用华为设备替代屏幕录制方法，时长{duration}秒")
    
    # 尝试方法1: 检查华为设备是否有专用的录屏命令
    logger.info("尝试查找华为设备专用录屏命令...")
    huawei_commands = [
        "emui_screen_record",
        "huawei_screen_record",
        "hiscreen_record",
        "/system/bin/screenrecord",
        "/system/xbin/screenrecord"
    ]
    
    for cmd in huawei_commands:
        check_cmd = f"adb shell which {cmd}"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"找到可用的录屏命令: {cmd}")
            # 使用找到的命令录制
            return use_found_record_command(cmd, duration, name, upload)
    
    # 尝试方法2: 使用input keyevent触发系统录屏
    logger.info("尝试使用系统按键触发华为系统录屏...")
    try:
        trigger_system_screen_record(duration)
        # 检查录屏是否成功，并获取文件
        recording_file = find_system_recording()
        if recording_file:
            return recording_file, upload_to_telegram(recording_file) if upload else None
    except Exception as e:
        logger.error(f"系统录屏失败: {str(e)}")
    
    # 兜底方法: 使用连续截图替代
    logger.info("使用连续截图方法替代录屏...")
    screenshots, upload_url = sequential_screenshots(
        duration=duration, 
        interval=0.5,  # 每0.5秒一张截图
        name=name,
        upload=upload
    )
    
    if screenshots:
        logger.info(f"使用连续截图替代录屏成功，共{len(screenshots)}张截图")
        # 返回第一张截图作为结果
        return screenshots[0], upload_url
    
    logger.error("所有录屏方法均失败")
    return None, None

def use_found_record_command(cmd, duration, name, upload):
    """使用找到的录屏命令录制视频
    
    Args:
        cmd: 找到的录屏命令
        duration: 录制时长
        name: 视频名称
        upload: 是否上传
        
    Returns:
        tuple: (本地文件路径, 上传URL)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if name:
        video_name = f"{name}_{timestamp}.mp4"
    else:
        video_name = f"screen_record_{timestamp}.mp4"
    
    device_path = f"/sdcard/{video_name}"
    local_path = os.path.join(VIDEOS_DIR, video_name)
    
    logger.info(f"使用命令 {cmd} 开始录制到 {device_path}")
    
    try:
        # 清理可能存在的旧文件
        subprocess.run(f"adb shell rm -f {device_path}", shell=True)
        
        # 启动录制进程
        record_process = subprocess.Popen(
            f"adb shell {cmd} --time-limit {duration} {device_path}",
            shell=True
        )
        
        logger.info(f"录制进程已启动，等待{duration}秒...")
        
        # 等待录制完成
        try:
            record_process.wait(timeout=duration + 5)
        except subprocess.TimeoutExpired:
            logger.warning("录制进程超时，尝试终止")
            record_process.terminate()
        
        # 等待文件写入完成
        time.sleep(2)
        
        # 检查文件是否存在
        check_result = subprocess.run(
            f"adb shell ls -la {device_path}",
            shell=True, capture_output=True, text=True
        )
        
        if "No such file" in check_result.stdout:
            logger.error(f"录制的视频文件不存在: {device_path}")
            return None, None
        
        # 拉取文件到本地
        subprocess.run(f"adb pull {device_path} {local_path}", shell=True, check=True)
        
        # 删除设备上的文件
        subprocess.run(f"adb shell rm {device_path}", shell=True)
        
        if os.path.exists(local_path):
            logger.info(f"视频录制成功: {local_path}")
            
            # 上传视频
            if upload:
                url = upload_to_telegram(local_path)
                return local_path, url
            
            return local_path, None
        else:
            logger.error("视频拉取失败")
            return None, None
    
    except Exception as e:
        logger.error(f"使用命令{cmd}录制视频失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return None, None

def trigger_system_screen_record(duration):
    """尝试触发系统自带的录屏功能
    
    Args:
        duration: 录制时长(秒)
    """
    logger.info("尝试触发系统录屏...")
    
    # 不同华为设备可能有不同的快捷键组合
    # 尝试使用下拉通知栏和快捷开关
    try:
        # 下拉通知栏
        subprocess.run("adb shell input swipe 500 0 500 800", shell=True)
        time.sleep(0.5)
        
        # 再次下拉展开完整控制面板
        subprocess.run("adb shell input swipe 500 500 500 800", shell=True)
        time.sleep(1)
        
        # 这里需要根据实际设备上录屏按钮的位置调整坐标
        # 一般在控制面板中，录屏按钮位置不固定，可能需要滑动查找
        # 这里示例点击第3行第2个图标位置(假设是录屏)
        subprocess.run("adb shell input tap 350 600", shell=True)
        time.sleep(1)
        
        # 如果有确认对话框，点击确认
        subprocess.run("adb shell input tap 500 1000", shell=True)
        
        # 等待指定时长
        logger.info(f"等待系统录屏{duration}秒...")
        time.sleep(duration)
        
        # 点击停止录制(一般是通知栏中的停止按钮)
        subprocess.run("adb shell input tap 500 100", shell=True)
        time.sleep(1)
        
        logger.info("系统录屏过程已执行")
    except Exception as e:
        logger.error(f"触发系统录屏失败: {str(e)}")
        raise

def find_system_recording():
    """查找系统录制的视频文件
    
    返回:
        str: 找到的视频文件本地路径，未找到返回None
    """
    logger.info("查找系统录制的视频文件...")
    
    # 系统录屏一般保存在如下目录
    possible_dirs = [
        "/sdcard/DCIM/ScreenRecorder/",
        "/sdcard/Pictures/Screenshots/",
        "/sdcard/Movies/ScreenRecords/",
        "/sdcard/DCIM/Screenshots/",
        "/sdcard/Screencaps/"
    ]
    
    for directory in possible_dirs:
        logger.info(f"检查目录: {directory}")
        
        # 检查目录是否存在
        dir_check = subprocess.run(
            f"adb shell ls -la {directory} 2>/dev/null",
            shell=True, capture_output=True, text=True
        )
        
        if dir_check.returncode == 0 and "No such file" not in dir_check.stdout:
            # 寻找最近的mp4文件
            find_cmd = f"adb shell find {directory} -name '*.mp4' -mmin -2 | sort -r | head -1"
            result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout.strip():
                video_path = result.stdout.strip()
                logger.info(f"找到系统录制的视频: {video_path}")
                
                # 获取文件名
                filename = os.path.basename(video_path)
                local_path = os.path.join(VIDEOS_DIR, filename)
                
                # 拉取文件到本地
                subprocess.run(f"adb pull {video_path} {local_path}", shell=True, check=True)
                
                if os.path.exists(local_path):
                    logger.info(f"成功获取系统录制的视频: {local_path}")
                    return local_path
    
    logger.warning("未找到系统录制的视频文件")
    return None

def main():
    """主函数，测试华为设备上的屏幕录制功能"""
    logger.info("开始测试华为设备屏幕录制功能")
    
    # 检查ADB连接
    logger.info("检查ADB设备连接...")
    devices = subprocess.run(
        "adb devices", 
        shell=True, capture_output=True, text=True
    )
    logger.info(f"已连接设备:\n{devices.stdout}")
    
    if "device" not in devices.stdout:
        logger.error("没有发现已连接的设备，请确保设备已连接并启用USB调试")
        return
    
    # 检查设备信息
    logger.info("获取设备信息...")
    device_info = subprocess.run(
        "adb shell getprop | grep -e 'model' -e 'brand' -e 'manufacturer' -e 'version.sdk'", 
        shell=True, capture_output=True, text=True
    )
    logger.info(f"设备信息:\n{device_info.stdout}")
    
    # 测试标准的screenrecord是否可用
    has_screen_record = check_screen_record_available()
    
    # 测试录制
    logger.info("测试录制10秒视频")
    
    if has_screen_record:
        # 使用标准screenrecord命令
        logger.info("使用标准screenrecord命令录制")
        # 实现标准screenrecord的代码...
    else:
        # 使用替代方法
        logger.info("使用华为设备替代方法录制")
        video_path, video_url = huawei_screen_record_alternative(
            duration=10,
            name="huawei_test",
            upload=True
        )
        
        if video_path and os.path.exists(video_path):
            logger.info(f"视频/截图保存成功: {video_path}")
            if video_url:
                logger.info(f"媒体上传成功: {video_url}")
            else:
                logger.warning("媒体保存成功，但上传失败")
        else:
            logger.error("所有录制方法均失败")

if __name__ == "__main__":
    main() 