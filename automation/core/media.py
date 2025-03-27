#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
媒体操作模块 - 处理截图和录屏操作
"""

import subprocess
import time
import os
import logging
from datetime import datetime

class MediaManager:
    """媒体管理器，处理截图和录屏操作"""
    
    def __init__(self, screenshots_dir, videos_dir, logger=None):
        """初始化媒体管理器
        
        Args:
            screenshots_dir: 截图保存目录
            videos_dir: 视频保存目录
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.logger = logger or logging.getLogger("media")
        self.screenshots_dir = screenshots_dir
        self.videos_dir = videos_dir
        
        # 确保目录存在
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)
        
    def take_screenshot(self, name=None, upload_func=None):
        """截图并保存到指定目录
        
        Args:
            name: 截图名称，不包含扩展名。如果为None，则使用时间戳
            upload_func: 上传函数，接受文件路径参数并返回URL
            
        Returns:
            tuple: (截图路径, 截图URL)，如果失败则返回(None, None)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            screenshot_name = f"{name}_{timestamp}.png"
        else:
            screenshot_name = f"screenshot_{timestamp}.png"
        
        screenshot_path = os.path.join(self.screenshots_dir, screenshot_name)
        self.logger.info(f"正在截图: {screenshot_path}")
        
        try:
            subprocess.run(f"adb shell screencap -p /sdcard/{screenshot_name}", shell=True, check=True)
            subprocess.run(f"adb pull /sdcard/{screenshot_name} {screenshot_path}", shell=True, check=True)
            subprocess.run(f"adb shell rm /sdcard/{screenshot_name}", shell=True)
            
            if upload_func and os.path.exists(screenshot_path):
                self.logger.info(f"上传截图: {screenshot_path}")
                url = upload_func(screenshot_path)
                self.logger.info(f"截图上传成功: {url}")
                return screenshot_path, url
            
            return screenshot_path, None
        except Exception as e:
            self.logger.error(f"截图失败: {e}")
            return None, None
    
    def record_screen(self, duration=90, name=None, upload_func=None):
        """录制屏幕视频并保存
        
        Args:
            duration: 录制时长(秒)，最大180秒
            name: 视频名称，不包含扩展名。如果为None，则使用时间戳
            upload_func: 上传函数，接受文件路径参数并返回URL
            
        Returns:
            tuple: (视频路径, 视频URL)，如果失败则返回(None, None)
        """
        # 限制最大录制时长为180秒（手机可能有限制）
        if duration > 180:
            duration = 180
            self.logger.warning(f"录制时长超过最大值，已调整为180秒")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            video_name = f"{name}_{timestamp}"
        else:
            video_name = f"screen_record_{timestamp}"
        
        device_video_path = f"/sdcard/{video_name}.mp4"
        local_video_path = os.path.join(self.videos_dir, f"{video_name}.mp4")
        
        self.logger.info(f"开始录制屏幕: {local_video_path}, 时长: {duration}秒")
        
        try:
            # 启动录屏进程
            record_process = subprocess.Popen(
                f"adb shell screenrecord --time-limit {duration} {device_video_path}", 
                shell=True
            )
            
            self.logger.info(f"录制进程已启动，等待{duration}秒完成...")
            
            # 等待录制完成
            try:
                record_process.wait(timeout=duration + 5)  # 等待稍长一点，确保录制完成
            except subprocess.TimeoutExpired:
                self.logger.warning("录制进程超时，尝试强制结束")
                subprocess.run("adb shell killall screenrecord", shell=True)
                record_process.terminate()
            
            # 等待一下确保文件写入完成
            time.sleep(2)
            
            # 检查录制文件是否存在
            check_result = subprocess.run(
                f"adb shell ls {device_video_path}", 
                shell=True, capture_output=True, text=True
            )
            
            if "No such file" in check_result.stdout or "not found" in check_result.stdout:
                self.logger.error(f"录制的视频文件在设备上不存在: {device_video_path}")
                return None, None
            
            # 将视频从设备复制到本地
            subprocess.run(f"adb pull {device_video_path} {local_video_path}", shell=True, check=True)
            subprocess.run(f"adb shell rm {device_video_path}", shell=True)
            
            self.logger.info(f"屏幕录制完成: {local_video_path}")
            
            # 如果需要上传视频
            if upload_func and os.path.exists(local_video_path) and os.path.getsize(local_video_path) > 0:
                self.logger.info(f"上传视频: {local_video_path}")
                url = upload_func(local_video_path)
                if url:
                    self.logger.info(f"视频上传成功: {url}")
                    return local_video_path, url
                else:
                    self.logger.error("视频上传失败")
                    return local_video_path, None
            
            return local_video_path, None
        
        except Exception as e:
            self.logger.error(f"录制屏幕失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return None, None 