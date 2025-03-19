#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huawei Quick App ADB-based Automation Script
通过ADB命令和坐标点击实现的快应用自动化测试脚本
使用ADBKeyboard输入法实现中文输入
支持飞书通知和图片上传功能
支持定时自动执行功能
集成scrcpy录制功能
"""

import subprocess
import time
import logging
import os
import requests
import json
import hashlib
import base64
import hmac
from datetime import datetime
import random
import string
import argparse
import schedule
import signal
import sys
import shutil  # 用于检查命令是否存在

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 截图保存目录
SCREENSHOTS_DIR = os.path.join(SCRIPT_DIR, "screenshots")
# 视频保存目录
VIDEOS_DIR = os.path.join(SCRIPT_DIR, "videos")

# 确保目录存在
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_app_adb_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuickAppADBTester")

# 飞书机器人配置
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/2e9f09a8-4cec-4475-a6a8-4da61c4a874c"  # 替换为您的飞书机器人webhook URL
FEISHU_SECRET = "YOUR_SECRET"  # 替换为您的飞书机器人签名密钥，如果没有设置签名可以留空

# Telegram配置 (替换Stardots配置)
TELEGRAM_BOT_TOKEN = "7883072273:AAH0VO-o6O4-ZkY1KXLCiqT3xMqPgq--CXg"
TELEGRAM_CHAT_ID = "-1002505009144"  # 您的Telegram频道/群组ID

# 设备屏幕尺寸
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2376

# scrcpy录制相关配置
SCRCPY_CONFIG = {
    'display': False,         # 不显示屏幕
    'bitrate': '2M',          # 较低比特率，提高稳定性
    'max_size': '720',        # 最大分辨率
    'codec': 'h264',          # 使用H.264编码，更稳定
    'max_fps': '20'           # 限制帧率，确保稳定性
}

# 全局变量用于处理scrcpy录制
scrcpy_recording_process = None
current_video_path = None

# 全局配置
DEFAULT_CONFIG = {
    'duration': 0,  # 默认0表示无限录制，直到手动停止
    'upload_screenshots': True,
    'telegram_bot_token': '7883072273:AAH0VO-o6O4-ZkY1KXLCiqT3xMqPgq--CXg',
    'telegram_chat_id': '5748280607'
}

# 检查系统中是否安装了命令
def check_command_exists(command):
    """
    检查系统是否安装了指定的命令
    
    Args:
        command: 要检查的命令名称
    
    Returns:
        bool: 如果命令存在则返回True，否则返回False
    """
    return shutil.which(command) is not None

# 检查ffmpeg是否可用
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

def kill_scrcpy_processes():
    """优雅地终止所有正在运行的scrcpy进程"""
    try:
        logger.info("尝试优雅地终止所有scrcpy进程")
        
        # 1. 先尝试发送HOME键，帮助scrcpy能够优雅退出
        try:
            subprocess.run("adb shell input keyevent KEYCODE_HOME", shell=True, timeout=2)
            time.sleep(1)
        except Exception:
            pass
        
        # 2. 尝试使用pkill发送SIGINT信号 (等同于Ctrl+C)
        if os.name == 'nt':  # Windows
            # Windows没有SIGINT的直接方式，尝试taskkill /F
            logger.info("Windows平台：使用taskkill")
            subprocess.run("taskkill /IM scrcpy.exe", shell=True)  # 先不用/F，尝试优雅关闭
            time.sleep(2)
        else:  # Linux/Mac
            logger.info("Linux/Mac平台：先发送SIGINT信号")
            subprocess.run("pkill -2 scrcpy", shell=True)  # -2表示SIGINT
            time.sleep(3)  # 给进程3秒钟处理SIGINT
            
            # 检查是否还有进程存在
            check = subprocess.run("pgrep scrcpy", shell=True, capture_output=True)
            if check.returncode == 0:  # 有进程存在
                logger.info("SIGINT未能终止全部进程，尝试SIGTERM")
                subprocess.run("pkill scrcpy", shell=True)  # 默认是SIGTERM
                time.sleep(2)
        
        # 3. 强制终止残留进程 - 最后手段
        if os.name == 'nt':  # Windows
            subprocess.run("taskkill /F /IM scrcpy.exe", shell=True)
        else:  # Linux/Mac
            # 检查是否还有残留进程
            check = subprocess.run("pgrep scrcpy", shell=True, capture_output=True)
            if check.returncode == 0:  # 有进程存在
                logger.warning("使用SIGKILL强制终止残留进程")
                subprocess.run("pkill -9 scrcpy", shell=True)
        
        # 4. 确保scrcpy-server也被终止
        try:
            subprocess.run("adb shell pkill scrcpy-server", shell=True, timeout=2)
        except Exception:
            pass
        
        # 5. 给进程一些时间完全退出
        time.sleep(2)
        
        logger.info("所有scrcpy进程已终止")
        return True
    except Exception as e:
        logger.warning(f"终止scrcpy进程出错: {str(e)}")
        return False

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

def send_feishu_notification(title, content, mention_user=None, mention_all=False, image_urls=None):
    """
    发送飞书机器人通知
    
    Args:
        title: 通知标题
        content: 通知内容
        mention_user: 要@的用户ID，如果为None则不@任何人
        mention_all: 是否@所有人
        image_urls: 图片URL列表，如果为None则不发送图片
    
    Returns:
        bool: 是否发送成功
    """
    if not FEISHU_WEBHOOK_URL or FEISHU_WEBHOOK_URL == "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL":
        logger.warning("飞书机器人webhook URL未配置，跳过通知发送")
        return False
    
    try:
        timestamp = str(int(time.time()))
        
        # 使用卡片消息格式
        logger.info("使用交互式卡片消息格式发送" + (f"，包含{len(image_urls)}张图片链接" if image_urls and len(image_urls) > 0 else ""))
        
        # 确定卡片颜色模板 - 成功为绿色，失败为红色
        card_color = "green" if "成功" in content and "失败" not in content else "red"
        
        # 构建元素列表
        elements = []
        
        # 添加内容文本区域
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content
            }
        })
        
        # 如果有图片URL，添加分隔线和图片链接部分
        if image_urls and len(image_urls) > 0:
            # 添加分隔线
            elements.append({"tag": "hr"})
            
            # 添加图片标题
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📷 测试截图和视频：**"
                }
            })
            
            # 为每张图片创建按钮
            image_buttons = []
            
            for i, url in enumerate(image_urls):
                if url:  # 确保URL不为空
                    button_text = "防侧滑" if i == 0 else "拉回" if i == 1 else "视频"
                    image_buttons.append({
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": button_text
                        },
                        "type": "primary",
                        "url": url
                    })
            
            # 添加图片按钮区域
            elements.append({
                "tag": "action",
                "actions": image_buttons
            })
            
            # 添加提示文本
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "查看截图 or 视频，需要使用VPN"
                }
            })
        
        # 添加分隔线
        elements.append({"tag": "hr"})
        
        # 添加时间戳注释
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        # 如果需要@所有人，添加@所有人元素
        if mention_all:
            # 在最前面添加@所有人元素
            at_element = {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "<at id=all></at> 请注意："
                }
            }
            elements.insert(0, at_element)
        
        # 构建完整消息
        msg = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": card_color
                },
                "elements": elements
            }
        }
        
        # 打印构建的消息结构，用于调试
        logger.info(f"构建的消息结构: {json.dumps(msg, ensure_ascii=False)}")
        
        # 如果设置了签名密钥，则计算签名
        headers = {"Content-Type": "application/json"}
        if FEISHU_SECRET and FEISHU_SECRET != "YOUR_SECRET":
            # 计算签名
            string_to_sign = f"{timestamp}\n{FEISHU_SECRET}"
            sign = base64.b64encode(hmac.new(FEISHU_SECRET.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()).decode('utf-8')
            
            # 添加签名到请求头
            headers.update({
                "timestamp": timestamp,
                "sign": sign
            })
        
        # 发送请求
        response = requests.post(FEISHU_WEBHOOK_URL, headers=headers, data=json.dumps(msg))
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                logger.info(f"飞书通知发送成功: {title}")
                return True
            else:
                logger.warning(f"飞书通知发送失败: {result.get('msg')}")
                # 打印更多响应信息以便调试
                logger.warning(f"响应详情: {json.dumps(result, ensure_ascii=False)}")
                return False
        else:
            logger.warning(f"飞书通知发送失败，状态码: {response.status_code}")
            try:
                error_info = response.json()
                logger.warning(f"错误详情: {json.dumps(error_info, ensure_ascii=False)}")
            except:
                logger.warning(f"响应内容: {response.text}")
            return False
    except Exception as e:
        logger.error(f"飞书通知发送异常: {str(e)}")
        # 打印详细的异常堆栈
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

class QuickAppADBTester:
    """使用ADB命令和坐标点击的快应用测试器"""
    
    def __init__(self):
        """初始化测试器"""
        logger.info("初始化QuickAppADBTester")
        # 确保ADBKeyboard已安装并设置为默认输入法
        self.ensure_adbkeyboard_input_method()
        
    def check_adbkeyboard_installed(self):
        """检查ADBKeyboard是否已安装"""
        logger.info("检查ADBKeyboard是否已安装")
        
        # 方法1: 使用ime list检查
        ime_list_cmd = "adb shell ime list -a"
        result1 = subprocess.run(ime_list_cmd, shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard/.AdbIME" in result1.stdout:
            logger.info("检测到ADBKeyboard已安装（通过ime list确认）")
            return True
        
        # 方法2: 直接检查包是否存在
        package_cmd = "adb shell pm list packages"
        result2 = subprocess.run(package_cmd, shell=True, capture_output=True, text=True)
        if "package:com.android.adbkeyboard" in result2.stdout:
            logger.info("检测到ADBKeyboard已安装（通过package list确认）")
            return True
        
        # 方法3: 尝试设置为默认输入法
        try_set_cmd = "adb shell ime set com.android.adbkeyboard/.AdbIME"
        result3 = subprocess.run(try_set_cmd, shell=True, capture_output=True, text=True)
        if "error" not in result3.stdout.lower() and "unknown" not in result3.stdout.lower():
            # 验证是否真的设置成功
            check_current = "adb shell settings get secure default_input_method"
            result4 = subprocess.run(check_current, shell=True, capture_output=True, text=True)
            if "com.android.adbkeyboard" in result4.stdout:
                logger.info("检测到ADBKeyboard已安装（通过设置为默认输入法确认）")
                return True
        
        logger.warning("未检测到ADBKeyboard，某些功能可能无法正常工作")
        logger.warning("请安装ADBKeyboard: https://github.com/senzhk/ADBKeyBoard")
        return False
    
    def ensure_adbkeyboard_input_method(self):
        """确保ADBKeyboard被设置为当前输入法"""
        logger.info("确保ADBKeyboard被设置为默认输入法")
        
        # 首先检查ADBKeyboard是否已安装
        is_installed = self.check_adbkeyboard_installed()
        if not is_installed:
            logger.warning("ADBKeyboard未安装，将使用备用输入方法（可能不支持中文）")
            return False
        
        # 保存当前输入法以便稍后恢复
        result = subprocess.run("adb shell settings get secure default_input_method", 
                               shell=True, capture_output=True, text=True)
        self.original_ime = result.stdout.strip()
        logger.info(f"当前输入法: {self.original_ime}")
        
        # 如果当前已经是ADBKeyboard，则无需更改
        if "com.android.adbkeyboard" in self.original_ime:
            logger.info("当前已经是ADBKeyboard输入法，无需切换")
            return True
        
        # 设置ADBKeyboard为默认
        subprocess.run("adb shell ime set com.android.adbkeyboard/.AdbIME", shell=True)
        time.sleep(1)
        
        # 验证是否设置成功
        verify_result = subprocess.run("adb shell settings get secure default_input_method", 
                                      shell=True, capture_output=True, text=True)
        if "com.android.adbkeyboard" in verify_result.stdout:
            logger.info("成功设置ADBKeyboard为默认输入法")
            return True
        else:
            logger.warning(f"设置输入法可能失败，当前输入法: {verify_result.stdout.strip()}")
            return False
        
    def restore_original_input_method(self):
        """恢复原来的输入法"""
        if hasattr(self, 'original_ime') and self.original_ime and "com.android.adbkeyboard" not in self.original_ime:
            logger.info(f"恢复原来的输入法: {self.original_ime}")
            subprocess.run(f"adb shell ime set {self.original_ime}", shell=True)
            time.sleep(1)
        
    def tap(self, x, y):
        """点击指定坐标"""
        cmd = f"adb shell input tap {x} {y}"
        logger.info(f"点击坐标: ({x}, {y})")
        subprocess.run(cmd, shell=True)
        
    def tap_by_percent(self, x_percent, y_percent):
        """基于屏幕百分比位置点击"""
        x = int(SCREEN_WIDTH * x_percent)
        y = int(SCREEN_HEIGHT * y_percent)
        self.tap(x, y)
        
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        """滑动屏幕"""
        cmd = f"adb shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        subprocess.run(cmd, shell=True)
    
    def swipe_by_percent(self, start_x_percent, start_y_percent, end_x_percent, end_y_percent, duration=300):
        """基于屏幕百分比位置滑动"""
        start_x = int(SCREEN_WIDTH * start_x_percent)
        start_y = int(SCREEN_HEIGHT * start_y_percent)
        end_x = int(SCREEN_WIDTH * end_x_percent)
        end_y = int(SCREEN_HEIGHT * end_y_percent)
        self.swipe(start_x, start_y, end_x, end_y, duration)
        
    def press_key(self, keycode):
        """按下按键"""
        cmd = f"adb shell input keyevent {keycode}"
        logger.info(f"按下按键: {keycode}")
        subprocess.run(cmd, shell=True)
        
    def press_home(self):
        """按下Home键"""
        logger.info("按下Home键")
        self.press_key("KEYCODE_HOME")
        
    def press_enter(self):
        """按下回车键"""
        logger.info("按下回车键")
        self.press_key("66")
        
    def press_back(self):
        """按下返回键"""
        logger.info("按下返回键")
        self.press_key("KEYCODE_BACK")
        
    def press_recent_apps(self):
        """打开最近任务列表"""
        logger.info("打开最近任务列表")
        self.press_key("KEYCODE_APP_SWITCH")
        
    def check_screen_state(self):
        """检查屏幕状态，使用mHoldingDisplaySuspendBlocker标志
        
        Returns:
            bool: 屏幕亮起返回True，熄屏返回False
        """
        logger.info("检查屏幕状态")
        
        # 使用mHoldingDisplaySuspendBlocker检查
        cmd = "adb shell dumpsys power | grep 'mHoldingDisplaySuspendBlocker'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            if "true" in result.stdout.lower():
                logger.info("屏幕状态为亮屏 (mHoldingDisplaySuspendBlocker=true)")
                return True
            elif "false" in result.stdout.lower():
                logger.info("屏幕状态为熄屏 (mHoldingDisplaySuspendBlocker=false)")
                return False
            
        # 如果无法确定，尝试其他方法
        logger.warning("无法通过mHoldingDisplaySuspendBlocker确定屏幕状态，尝试其他方法")
        
        # 尝试检查前台应用活动
        cmd = "adb shell dumpsys activity activities | grep -A 3 'mResumedActivity'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout and len(result.stdout.strip()) > 10:
            logger.info("检测到前台应用活动，屏幕可能处于亮屏状态")
            return True
        else:
            logger.info("未检测到前台应用活动，屏幕可能处于熄屏状态")
            return False
            
    def wake_screen(self):
        """尝试唤醒屏幕
        
        Returns:
            bool: 是否成功唤醒屏幕
        """
        logger.info("尝试唤醒屏幕")
        
        # 使用电源键唤醒
        logger.info("使用电源键唤醒")
        self.press_key("KEYCODE_POWER")
        time.sleep(2)  # 等待屏幕响应
        
        # 检查是否成功唤醒
        if self.check_screen_state():
            logger.info("成功唤醒屏幕")
            return True
        
        logger.warning("电源键唤醒失败，尝试备用方法")
        
        # 备用方法：使用WAKEUP键码
        logger.info("使用WAKEUP键码唤醒")
        self.press_key("KEYCODE_WAKEUP")
        time.sleep(2)
        
        if self.check_screen_state():
            logger.info("成功使用WAKEUP键码唤醒屏幕")
            return True
            
        logger.warning("所有唤醒方法均失败")
        return False
    
    def simple_unlock(self):
        """简单解锁屏幕（适用于无密码设备）
        
        Returns:
            bool: 是否成功解锁
        """
        logger.info("尝试简单解锁屏幕")
        
        # 滑动解锁
        self.swipe_by_percent(0.5, 0.7, 0.5, 0.3)
        time.sleep(1)
        
        # 按Home键确认
        self.press_home()
        time.sleep(1)
        
        # 检查是否到达桌面
        cmd = "adb shell dumpsys activity activities | grep mResumedActivity"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout and "Launcher" in result.stdout:
            logger.info("成功解锁到桌面")
            return True
        else:
            logger.info("简单解锁操作已执行，但未确认是否到达桌面")
            return True
    
    def ensure_screen_on(self):
        """确保屏幕亮起并解锁
        
        Returns:
            bool: 屏幕是否成功亮起并解锁
        """
        logger.info("确保屏幕亮起并解锁")
        
        # 检查屏幕状态
        if not self.check_screen_state():
            logger.info("屏幕处于熄屏状态，尝试唤醒")
            if not self.wake_screen():
                logger.error("无法唤醒屏幕")
                return False
        else:
            logger.info("屏幕已处于亮屏状态")
            
        # 尝试解锁
        result = self.simple_unlock()
        
        return result
        
    def take_screenshot(self, name=None, upload=True):
        """截图并保存到指定目录
        
        Args:
            name: 截图名称，不包含扩展名。如果为None，则使用时间戳
            upload: 是否上传截图
            
        Returns:
            str: 截图保存的路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            screenshot_name = f"{name}_{timestamp}.png"
        else:
            screenshot_name = f"screenshot_{timestamp}.png"
        
        screenshot_path = os.path.join(SCREENSHOTS_DIR, screenshot_name)
        logger.info(f"正在截图: {screenshot_path}")
        
        try:
            subprocess.run(f"adb shell screencap -p /sdcard/{screenshot_name}", shell=True, check=True)
            subprocess.run(f"adb pull /sdcard/{screenshot_name} {screenshot_path}", shell=True, check=True)
            subprocess.run(f"adb shell rm /sdcard/{screenshot_name}", shell=True)
            
            if upload and os.path.exists(screenshot_path):
                logger.info(f"上传截图到Telegram: {screenshot_path}")
                url = upload_to_telegram(screenshot_path)
                logger.info(f"截图上传成功: {url}")
                return screenshot_path, url
            
            return screenshot_path, None
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None, None
    
    def record_screen(self, duration=90, name=None, upload=True):
        """录制屏幕视频并保存
        
        Args:
            duration: 录制时长(秒)，最大180秒
            name: 视频名称，不包含扩展名。如果为None，则使用时间戳
            upload: 是否上传视频
            
        Returns:
            tuple: (视频路径, 视频URL)，如果失败则返回(None, None)
        """
        # 限制最大录制时长为180秒（手机可能有限制）
        if duration > 180:
            duration = 180
            logger.warning(f"录制时长超过最大值，已调整为180秒")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            video_name = f"{name}_{timestamp}"
        else:
            video_name = f"screen_record_{timestamp}"
        
        device_video_path = f"/sdcard/{video_name}.mp4"
        local_video_path = os.path.join(VIDEOS_DIR, f"{video_name}.mp4")
        
        logger.info(f"开始录制屏幕: {local_video_path}, 时长: {duration}秒")
        
        try:
            # 启动录屏进程
            record_process = subprocess.Popen(
                f"adb shell screenrecord --time-limit {duration} {device_video_path}", 
                shell=True
            )
            
            logger.info(f"录制进程已启动，等待{duration}秒完成...")
            
            # 等待录制完成
            try:
                record_process.wait(timeout=duration + 5)  # 等待稍长一点，确保录制完成
            except subprocess.TimeoutExpired:
                logger.warning("录制进程超时，尝试强制结束")
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
                logger.error(f"录制的视频文件在设备上不存在: {device_video_path}")
                return None, None
            
            # 将视频从设备复制到本地
            subprocess.run(f"adb pull {device_video_path} {local_video_path}", shell=True, check=True)
            subprocess.run(f"adb shell rm {device_video_path}", shell=True)
            
            logger.info(f"屏幕录制完成: {local_video_path}")
            
            # 如果需要上传视频
            if upload and os.path.exists(local_video_path) and os.path.getsize(local_video_path) > 0:
                logger.info(f"上传视频到Telegram: {local_video_path}")
                url = upload_to_telegram(local_video_path)
                if url:
                    logger.info(f"视频上传成功: {url}")
                    return local_video_path, url
                else:
                    logger.error("视频上传失败")
                    return local_video_path, None
            
            return local_video_path, None
        
        except Exception as e:
            logger.error(f"录制屏幕失败: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None, None
            
    def run_shell_command(self, command):
        """运行shell命令并返回输出"""
        logger.info(f"运行命令: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        logger.info(f"命令输出: {result.stdout}")
        return result.stdout

    def input_text(self, text):
        """输入文本 - 使用ADBKeyboard输入中文或其他文本"""
        logger.info(f"输入文本: {text}")
        
        # 如果是英文或数字，可以直接使用标准输入法
        if all(ord(c) < 128 for c in text):
            logger.info("使用标准输入法输入ASCII文本")
            cmd = f'adb shell input text "{text}"'
            subprocess.run(cmd, shell=True)
            return
        
        # 对于中文或其他非ASCII文本，使用ADBKeyboard
        logger.info("使用ADBKeyboard输入非ASCII文本")
        
        # 处理转义字符
        escaped_text = text.replace('"', '\\"')
        cmd = f'adb shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped_text}"'
        logger.info(f"执行命令: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 检查是否成功
        if "Broadcast completed" in result.stdout:
            logger.info("文本输入广播命令成功发送")
        else:
            logger.warning("文本输入广播命令可能未成功发送，尝试备用方法")
            # 备用方法
            escaped_text = text.replace("'", "\\'")
            backup_cmd = f"adb shell am broadcast -a ADB_INPUT_TEXT --es msg '{escaped_text}'"
            logger.info(f"执行备用命令: {backup_cmd}")
            subprocess.run(backup_cmd, shell=True)
            
        time.sleep(1)  # 等待输入完成

    def clear_quick_app_center_data(self):
        """流程1: 清除快应用中心数据"""
        logger.info("===== 开始执行流程1: 清除快应用中心数据 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        # 2. 打开设置应用
        logger.info("步骤2: 打开设置应用")
        self.run_shell_command("adb shell am start -a android.settings.SETTINGS")
        time.sleep(2)
        
        # 3. 点击搜索框
        logger.info("步骤3: 点击搜索框")
        self.tap_by_percent(0.256, 0.217)  # 坐标: (276, 516)
        time.sleep(1)
        
        # 4. 输入"应用和服务"
        logger.info("步骤4: 输入'应用和服务'")
        self.input_text("应用和服务")
        time.sleep(1)
        
        # 5. 点击搜索结果"应用和服务"
        logger.info("步骤5: 点击搜索结果'应用和服务'")
        self.tap_by_percent(0.236, 0.176)  # 坐标: (255, 418)
        time.sleep(2)
        
        # 6. 点击"应用管理"
        logger.info("步骤6: 点击'应用管理'")
        self.tap_by_percent(0.222, 0.159)  # 坐标: (240, 377)
        time.sleep(2)
        
        # 7. 点击搜索框
        logger.info("步骤7: 点击搜索框")
        self.tap_by_percent(0.222, 0.149)  # 坐标: (240, 353)
        time.sleep(1)
        
        # 8. 输入"快应用中心"
        logger.info("步骤8: 输入'快应用中心'")
        self.input_text("快应用中心")
        time.sleep(1)
        
        # 9. 点击搜索结果"快应用中心"
        logger.info("步骤9: 点击搜索结果'快应用中心'") 
        self.tap_by_percent(0.242, 0.242)  # 坐标: (261, 576)
        time.sleep(2)
        
        # 10. 向上滑动显示更多内容 - 修正为从下往上滑
        logger.info("步骤10: 向上滑动显示更多内容")
        self.swipe_by_percent(0.454, 0.8, 0.454, 0.4)  # 从下部(约80%位置)滑动到上部(约40%位置)
        time.sleep(1)
        self.swipe_by_percent(0.454, 0.7, 0.454, 0.3)  # 再滑一次确保看到更多内容
        time.sleep(1)
        
        # 11. 点击"存储"
        logger.info("步骤11: 点击'存储'")
        self.tap_by_percent(0.145, 0.430)  # 坐标: (157, 1021)
        time.sleep(1)
        
        # 12. 点击"删除数据"
        logger.info("步骤12: 点击'删除数据'")
        self.tap_by_percent(0.514, 0.535)  # 坐标: (555, 1271)
        time.sleep(1)
        
        # 13. 点击确认对话框中的"确定"按钮
        logger.info("步骤13: 点击确认对话框中的'确定'按钮")
        self.tap_by_percent(0.701, 0.932)  # 坐标: (757, 2215)
        time.sleep(2)
        
        logger.info("流程1执行完成: 清除快应用中心数据")
        return True
        
    def manage_quick_apps_via_market(self):
        """流程2: 通过应用市场管理快应用"""
        logger.info("===== 开始执行流程2: 通过应用市场管理快应用 =====")
        
        # 1. 按Home键回到桌面
        logger.info("步骤1: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        # 2. 打开应用市场
        logger.info("步骤2: 打开应用市场")
        self.run_shell_command("adb shell am start -n com.huawei.appmarket/.MainActivity")
        time.sleep(5)  # 应用市场加载可能需要更长时间
        
        # 3. 点击"我的"选项卡
        logger.info("步骤3: 点击'我的'选项卡")
        self.tap_by_percent(0.894, 0.946)  # 坐标: (965, 2248)
        time.sleep(2)
        
        # 4. 点击"快应用管理"选项
        logger.info("步骤4: 点击'快应用管理'选项")
        self.tap_by_percent(0.159, 0.696)  # 坐标: (172, 1654)
        time.sleep(5)  # 增加等待时间，从2秒增加到5秒，确保页面完全加载
        
        # 5. 点击"同意"按钮(如果出现)
        logger.info("步骤5: 检查并点击'同意'按钮(如果出现)")
        self.tap_by_percent(0.681, 0.937)  # 坐标: (736, 2227)
        time.sleep(2)
        
        # 增加额外等待时间，确保应用市场稳定后再继续下一流程
        logger.info("等待应用市场稳定 (5秒)")
        time.sleep(5)  # 从3秒增加到5秒
        
        logger.info("流程2执行完成: 通过应用市场管理快应用")
        return True
    
    def search_and_open_quick_app(self):
        """流程3: 搜索并打开快应用进行测试"""
        logger.info("===== 开始执行流程3: 搜索并打开快应用进行测试 =====")
        
        # 用于存储测试结果
        test_results = {
            "防侧滑": False,
            "拉回": False
        }
        
        # 1. 点击搜索框
        logger.info("步骤1: 点击搜索框")
        self.tap_by_percent(0.302, 0.149)  # 坐标: (326, 353)
        time.sleep(1)
        
        # 2. 输入"优购"
        logger.info("步骤2: 输入'优购'")
        self.input_text("优购")
        time.sleep(1)
        
        # 3. 按下回车键
        logger.info("步骤3: 按下回车键")
        self.press_enter()
        time.sleep(2)
        
        # 4. 点击搜索结果旁边的"打开"按钮
        logger.info("步骤4: 点击搜索结果旁边的'打开'按钮")
        self.tap_by_percent(0.797, 0.156)  # 坐标: (861, 371)
        time.sleep(8)  # 应用打开需要更长时间
        
        # 5. 执行10次侧滑
        logger.info("步骤5: 准备执行10次侧滑")
        start_x = int(SCREEN_WIDTH * 0.98)  # 起点X：屏幕宽度的98%
        end_x = int(SCREEN_WIDTH * 0.88)    # 终点X：屏幕宽度的88%
        y_pos = int(SCREEN_HEIGHT * 0.5)    # Y位置：屏幕高度的50%
        
        # 6. 执行侧滑操作
        logger.info("步骤6: 执行10次侧滑操作")
        for i in range(10):
            logger.info(f"第{i+1}次侧滑")
            self.swipe(start_x, y_pos, end_x, y_pos, duration=15)  # 超快速侧滑
            time.sleep(0.1)  # 极短等待
        
        time.sleep(2)  # 等待界面稳定
        
        # 7. 检查当前应用
        logger.info("步骤7: 检查当前应用")
        is_quick_app = self.is_quick_app_running("优购")
        
        if is_quick_app:
            logger.info("侧滑拦截成功：快应用仍在前台运行")
            test_results["防侧滑"] = True
        else:
            logger.warning("侧滑拦截失败：快应用已不在前台运行")
            test_results["防侧滑"] = False
        
        # 8. 截图记录状态
        logger.info("步骤8: 截图记录侧滑后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.swipe_screenshot_path, self.swipe_screenshot_url = self.take_screenshot(f"after_swipe_{timestamp}", upload=True)
        
        # 9. 按Home键
        logger.info("步骤9: 按Home键")
        self.press_home()
        time.sleep(10)  # 等待一段时间
        
        # 10. 再次检查当前应用
        logger.info("步骤10: 再次检查当前应用")
        is_quick_app = self.is_quick_app_running("优购")
        
        if is_quick_app:
            logger.info("拉回成功：按Home键后快应用仍在前台运行")
            test_results["拉回"] = True
        else:
            logger.warning("拉回失败：按Home键后快应用已不在前台运行")
            test_results["拉回"] = False
        
        # 11. 再次截图记录状态
        logger.info("步骤11: 再次截图记录按Home后状态")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.home_screenshot_path, self.home_screenshot_url = self.take_screenshot(f"after_home_{timestamp}", upload=True)
        
        logger.info("流程3执行完成: 搜索并打开快应用进行测试")
        # 返回详细的测试结果，而不仅仅是布尔值
        return test_results
    
    def clear_all_apps(self):
        """流程4: 清空手机里的全部应用"""
        logger.info("===== 开始执行流程4: 清空手机里的全部应用 =====")
        
        # 1. 强制停止快应用
        logger.info("步骤1: 强制停止快应用")
        self.run_shell_command("adb shell am force-stop com.huawei.fastapp")
        time.sleep(1)
        
        # 2. 按Home键
        logger.info("步骤2: 按Home键")
        self.press_home()
        time.sleep(1)
        
        # 3. 打开最近任务列表
        logger.info("步骤3: 打开最近任务列表")
        self.press_recent_apps()
        time.sleep(2)
        
        # 4. 点击底部中间清除按钮
        logger.info("步骤4: 点击底部中间清除按钮")
        self.tap_by_percent(0.500, 0.904)  # 坐标: (540, 2147)
        time.sleep(1)
        
        # 5. 按Home键回到桌面
        logger.info("步骤5: 按Home键回到桌面")
        self.press_home()
        time.sleep(1)
        
        logger.info("流程4执行完成: 清空手机里的全部应用")
        return True
    
    def run_all_flows(self, send_notification=True):
        """执行所有流程
        
        Args:
            send_notification: 是否在执行完成后发送飞书通知
            
        Returns:
            bool: 所有流程是否都成功执行
        """
        logger.info("开始执行所有流程")
        
        # 用于记录测试截图URL和视频URL
        self.swipe_screenshot_url = None
        self.home_screenshot_url = None
        self.test_video_url = None
        test_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = False
        error_msg = None
        
        # 开始录屏 - 使用scrcpy代替原来的ADB screenrecord
        video_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_name = f"test_flow_{video_timestamp}"
        logger.info(f"开始使用scrcpy录制测试流程视频: {video_name}.mp4")
        
        # 启动前先确保设备处于唤醒状态
        self.ensure_screen_on()
        
        # 启动scrcpy录制，预留3秒稳定缓冲
        video_path = start_scrcpy_recording(video_name)
        if not video_path:
            logger.warning("无法启动scrcpy录制，将继续测试但没有录制")
        else:
            # 录制启动后，先延迟3秒再开始测试，确保录制稳定
            logger.info("录制已启动，等待3秒确保录制稳定...")
            time.sleep(3)
        
        # 详细测试结果
        detailed_results = {
            "屏幕唤醒": False,
            "流程1_清除快应用中心数据": False,
            "流程2_通过应用市场管理快应用": False,
            "流程3_防侧滑测试": False,
            "流程3_拉回测试": False, 
            "流程4_清空手机里的全部应用": False
        }
        
        try:
            # 确保屏幕处于亮屏状态
            logger.info("确保屏幕处于亮屏状态")
            screen_on = self.ensure_screen_on()
            detailed_results["屏幕唤醒"] = screen_on
            
            if not screen_on:
                logger.warning("无法确保屏幕处于亮屏状态，测试可能失败")
            
            # 流程1: 清除快应用中心数据
            result1 = self.clear_quick_app_center_data()
            detailed_results["流程1_清除快应用中心数据"] = result1
            
            # 流程2: 通过应用市场管理快应用
            result2 = self.manage_quick_apps_via_market()
            detailed_results["流程2_通过应用市场管理快应用"] = result2
            
            # 流程3: 搜索并打开快应用进行测试
            # 现在返回的是包含"防侧滑"和"拉回"结果的字典
            result3 = self.search_and_open_quick_app()
            detailed_results["流程3_防侧滑测试"] = result3["防侧滑"]
            detailed_results["流程3_拉回测试"] = result3["拉回"]
            
            # 流程4: 清空手机里的全部应用
            result4 = self.clear_all_apps()
            detailed_results["流程4_清空手机里的全部应用"] = result4
            
            # 判断整体测试是否成功
            success = all([
                detailed_results["屏幕唤醒"],
                detailed_results["流程1_清除快应用中心数据"],
                detailed_results["流程2_通过应用市场管理快应用"],
                detailed_results["流程3_防侧滑测试"],
                detailed_results["流程3_拉回测试"],
                detailed_results["流程4_清空手机里的全部应用"]
            ])
            
            logger.info(f"所有流程执行完成。详细结果: {detailed_results}")
            
            # 测试完成后，先按Home键回到桌面，然后等待5秒，确保录制内容完整
            # 这有助于scrcpy录制的正常结束
            logger.info("测试完成，按Home键回到桌面...")
            self.press_home()
            time.sleep(5)  # 测试结束后预留5秒安全缓冲
            
            return success
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"执行流程时出错: {error_msg}")
            # 详细的异常信息
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return False
        
        finally:
            # 恢复原始输入法
            self.restore_original_input_method()
            
            # 再次回到桌面，以确保录制能够干净地结束
            try:
                logger.info("测试完成，最后回到桌面...")
                self.press_home()
                time.sleep(2)
            except Exception:
                pass
            
            # 停止scrcpy录制并获取视频 - 先确保按了Home键
            logger.info("测试完成，停止scrcpy录制...")
            video_path, video_url = stop_scrcpy_recording(upload_to_tg=True)
            if video_url:
                self.test_video_url = video_url
                logger.info(f"测试视频已上传到Telegram，URL: {video_url}")
            else:
                logger.warning("无法获取测试视频URL，可能是录制或上传失败")
            
            # 如果需要发送飞书通知
            if send_notification:
                test_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if success:
                    title = "✅ 快应用自动化测试成功"
                    content = f"**快应用防侧滑和拉回测试成功完成！**\n\n" \
                              f"- 开始时间: {test_start_time}\n" \
                              f"- 结束时间: {test_end_time}\n" \
                              f"- 测试设备: 华为设备\n\n" \
                              f"**防侧滑:** {'✅ 成功' if detailed_results['流程3_防侧滑测试'] else '❌ 失败'}\n\n" \
                              f"**拉回:** {'✅ 成功' if detailed_results['流程3_拉回测试'] else '❌ 失败'}"
                else:
                    # 确定哪个测试失败了
                    failure_reasons = []
                    if not detailed_results["屏幕唤醒"]:
                        failure_reasons.append("屏幕唤醒失败")
                    if not detailed_results["流程1_清除快应用中心数据"]:
                        failure_reasons.append("清除快应用中心数据失败")
                    if not detailed_results["流程2_通过应用市场管理快应用"]:
                        failure_reasons.append("通过应用市场管理快应用失败")
                    if not detailed_results["流程3_防侧滑测试"]:
                        failure_reasons.append("快应用防侧滑测试失败")
                    if not detailed_results["流程3_拉回测试"]:
                        failure_reasons.append("快应用拉回测试失败")
                    if not detailed_results["流程4_清空手机里的全部应用"]:
                        failure_reasons.append("清空手机里的全部应用失败")
                    
                    failure_summary = "、".join(failure_reasons)
                    
                    title = "❌ 快应用自动化测试失败"
                    content = f"**快应用测试执行失败！失败项目：{failure_summary}**\n\n" \
                              f"- 开始时间: {test_start_time}\n" \
                              f"- 结束时间: {test_end_time}\n" \
                              f"- 测试设备: 华为设备\n\n" \
                              f"**测试结果详情:**\n" \
                              f"1. 屏幕唤醒: {'✅ 成功' if detailed_results['屏幕唤醒'] else '❌ 失败'}\n" \
                              f"2. 清除快应用中心数据: {'✅ 成功' if detailed_results['流程1_清除快应用中心数据'] else '❌ 失败'}\n" \
                              f"3. 通过应用市场管理快应用: {'✅ 成功' if detailed_results['流程2_通过应用市场管理快应用'] else '❌ 失败'}\n" \
                              f"4. 快应用功能测试: \n" \
                              f"   - 防侧滑测试: {'✅ 成功' if detailed_results['流程3_防侧滑测试'] else '❌ 失败'}\n" \
                              f"   - 拉回测试: {'✅ 成功' if detailed_results['流程3_拉回测试'] else '❌ 失败'}\n" \
                              f"5. 清空手机里的全部应用: {'✅ 成功' if detailed_results['流程4_清空手机里的全部应用'] else '❌ 失败'}\n\n" \
                              f"**{'❌ 错误信息:' if error_msg else ''}** {error_msg or ''}"
                
                # 收集所有媒体URL
                image_urls = []
                if self.swipe_screenshot_url:
                    image_urls.append(self.swipe_screenshot_url)
                if self.home_screenshot_url:
                    image_urls.append(self.home_screenshot_url)
                if self.test_video_url:
                    image_urls.append(self.test_video_url)
                
                # 发送飞书通知
                send_feishu_notification(title, content, mention_all=not success, image_urls=image_urls)

    def is_quick_app_running(self, app_name=None):
        """
        检查快应用是否在前台运行
        
        使用dumpsys activity activities命令检查mResumedActivity
        只有处于Resumed状态的应用才是真正的前台应用
        
        Args:
            app_name: 可选，指定要检查的快应用名称（此方法中不使用）
            
        Returns:
            bool: 如果快应用在前台运行则返回True，否则返回False
        """
        logger.info("检查快应用是否在前台运行")
        
        # 使用经过测试的方法：检查前台应用状态
        cmd = "adb shell \"dumpsys activity activities | grep -A 1 'mResumedActivity'\""
        output = self.run_shell_command(cmd)
        
        # 只有处于Resumed状态的应用才是真正的前台应用
        is_foreground = "com.huawei.fastapp" in output and "Resumed" in output
        
        if is_foreground:
            logger.info("✅ 检测到华为快应用正在前台运行")
        else:
            logger.info("❌ 未检测到华为快应用在前台运行")
            
        return is_foreground

def run_automated_test(no_notification=False, upload_screenshots=False):
    """执行自动化测试
    
    Args:
        no_notification: 是否禁用飞书通知
        upload_screenshots: 是否上传截图到图床
    """
    logger.info("启动快应用ADB测试")
    
    tester = QuickAppADBTester()
    
    # 确保屏幕处于亮屏状态
    screen_on = tester.ensure_screen_on()
    if not screen_on:
        logger.warning("无法确保屏幕处于亮屏状态，测试可能失败")
    
    # 执行所有流程
    tester.run_all_flows(send_notification=not no_notification)
    
    logger.info("测试完成")

def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Huawei快应用ADB自动化测试脚本')
    parser.add_argument('--no-notification', action='store_true', help='禁用飞书通知')
    parser.add_argument('--upload-screenshots', action='store_true', help='上传截图到图床')
    args = parser.parse_args()
    
    # 注册终止处理
    def signal_handler(sig, frame):
        logger.info("接收到终止信号，正在优雅退出...")
        if scrcpy_recording_process is not None:
            logger.info("终止录制进程...")
            video_path, video_url = stop_scrcpy_recording(upload_to_tg=True)
            
            # 如果成功获取视频URL，手动发送飞书通知
            if video_url:
                logger.info(f"上传的视频URL: {video_url}")
                test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                title = "❌ 测试被手动中断"
                content = f"**华为快应用测试被手动中断**\n\n" \
                         f"- 中断时间: {test_time}\n" \
                         f"- 测试设备: 华为设备\n\n" \
                         f"**注意:** 测试过程被人为中断，未能完成全部测试流程。"
                 
                # 发送包含视频URL的飞书通知
                send_feishu_notification(title, content, image_urls=[video_url])
                logger.info("已发送中断通知，包含录制视频")
        
        logger.info("脚本已终止")
        sys.exit(0)
    
    # 注册信号处理程序
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("启动定时任务模式，每30分钟执行一次测试")
    
    # 先执行一次测试
    run_automated_test(no_notification=args.no_notification, upload_screenshots=args.upload_screenshots)
    
    # 设置定时任务，每30分钟执行一次
    schedule.every(5).minutes.do(
        run_automated_test, 
        no_notification=args.no_notification, 
        upload_screenshots=args.upload_screenshots
    )
    
    # 持续运行定时任务
    try:
        logger.info("定时任务已启动，按Ctrl+C可停止")
        while True:
            schedule.run_pending()
            time.sleep(1)  # 短暂休眠，避免CPU占用过高
    except KeyboardInterrupt:
        logger.info("用户中断，定时测试任务已停止")
    except Exception as e:
        logger.error(f"定时任务异常: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
    finally:
        # 确保任何正在运行的录制进程都被正确关闭
        if scrcpy_recording_process is not None:
            logger.info("清理录制进程...")
            stop_scrcpy_recording(upload_to_tg=True)
        logger.info("定时测试任务已结束")

def start_scrcpy_recording(filename=None):
    """
    开始使用scrcpy录制设备屏幕
    
    Args:
        filename: 输出文件名，不包含扩展名。如果为None，则使用时间戳
            
    Returns:
        str: 视频文件路径
    """
    global scrcpy_recording_process, current_video_path
    
    # 确保之前的录制已停止
    kill_scrcpy_processes()
    
    # 确保视频目录存在
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # 确保设备连接正常
    try:
        logger.info("检查设备连接状态...")
        check_result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=5)
        device_output = check_result.stdout.strip()
        
        if "device" not in device_output or len(device_output.splitlines()) <= 1:
            logger.error("未检测到已连接的设备，无法开始录制")
            return None
        
        logger.info(f"设备连接正常: {device_output}")
    except Exception as e:
        logger.error(f"检查设备连接时出错: {e}")
        return None
    
    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not filename:
        filename = f"recording_{timestamp}"
    
    # 确保文件名有.mp4后缀
    if not filename.lower().endswith('.mp4'):
        filename += '.mp4'
    
    # 设置完整的输出路径
    output_path = os.path.join(VIDEOS_DIR, filename)
    
    # 如果同名文件已存在，先删除
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            logger.info(f"已删除同名的旧文件: {output_path}")
        except Exception as e:
            logger.warning(f"删除旧文件时出错: {e}")
    
    current_video_path = output_path
    
    # 使设备保持唤醒状态，避免录制过程中休眠
    try:
        subprocess.run("adb shell input keyevent KEYCODE_WAKEUP", shell=True, timeout=2)
        time.sleep(1)
    except Exception:
        pass
    
    # 构建scrcpy命令 - 使用经过验证的参数配置
    cmd = [
        "scrcpy",
        f"--record={output_path}",
        "--no-playback",          # 只录制不显示
        "--video-codec=h265",     # 使用H.265编码器(更好的质量)
        "--max-size=720",         # 限制分辨率
        "--max-fps=15",           # 帧率15fps提高稳定性
        "--time-limit=120",       # 限制录制时间为120秒(避免无法正常结束)
        "--video-bit-rate=8M",    # 使用8Mbps的比特率
        "--record-format=mp4",    # 确保使用mp4格式
        "--power-off-on-close",   # 关闭scrcpy时关闭设备屏幕
        "--no-audio"              # 禁用音频
    ]
    
    logger.info(f"开始录制，输出文件: {output_path}")
    logger.info(f"使用命令: {' '.join(cmd)}")
    
    # 启动录制进程
    try:
        scrcpy_recording_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 检查进程是否立即退出
        time.sleep(2)
        if scrcpy_recording_process.poll() is not None:
            stderr = scrcpy_recording_process.stderr.read() if scrcpy_recording_process.stderr else ""
            logger.error(f"scrcpy进程立即退出，退出码: {scrcpy_recording_process.returncode}")
            if stderr:
                logger.error(f"错误输出: {stderr}")
                # 尝试解析常见的错误，如参数问题
                if "--no-display" in stderr and "--no-playback" in cmd:
                    logger.error("检测到参数不兼容：您的scrcpy版本可能不支持--no-display，尝试使用--no-playback")
                elif "unrecognized option" in stderr:
                    logger.error("检测到不支持的选项，可能需要更新scrcpy或调整参数")
            
            scrcpy_recording_process = None
            current_video_path = None
            return None
            
        logger.info("录制已开始...")
        
        # 额外检查：确认录制进程是否稳定运行
        time.sleep(3)  # 再等待3秒
        if scrcpy_recording_process.poll() is not None:
            logger.error(f"scrcpy进程开始后不久退出，退出码: {scrcpy_recording_process.returncode}")
            stderr = scrcpy_recording_process.stderr.read() if scrcpy_recording_process.stderr else ""
            if stderr:
                logger.error(f"错误输出: {stderr}")
            scrcpy_recording_process = None
            current_video_path = None
            return None
            
        # 开启一个后台线程监控录制状态
        def check_recording_status():
            start_time = time.time()
            while scrcpy_recording_process and scrcpy_recording_process.poll() is None:
                elapsed = time.time() - start_time
                # 每30秒记录一次状态
                if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                    logger.info(f"录制进行中，已录制约 {int(elapsed)} 秒")
                time.sleep(1)
                
        import threading
        monitor_thread = threading.Thread(target=check_recording_status)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        logger.info("录制状态监控已启动")
        return output_path
    except Exception as e:
        logger.error(f"启动录制时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        if scrcpy_recording_process is not None and scrcpy_recording_process.poll() is None:
            logger.info("尝试清理失败的录制进程...")
            stop_scrcpy_recording(upload_to_tg=False)
        return None

def stop_scrcpy_recording(upload_to_tg=True):
    """
    停止scrcpy录制并处理录制的视频
    
    Args:
        upload_to_tg: 是否上传到Telegram
    
    Returns:
        tuple: (视频文件路径, 视频URL)，如果失败则返回(None, None)
    """
    global scrcpy_recording_process, current_video_path
    
    video_url = None
    
    if scrcpy_recording_process is None or current_video_path is None:
        logger.warning("没有正在进行的录制进程，无法停止")
        return None, None
    
    logger.info("停止录制...")
    
    try:
        # 检查进程是否已经退出
        if scrcpy_recording_process.poll() is not None:
            logger.info(f"录制进程已经退出，退出码: {scrcpy_recording_process.returncode}")
            stderr = scrcpy_recording_process.stderr.read() if scrcpy_recording_process.stderr else ""
            if stderr:
                logger.info(f"stderr输出: {stderr}")
        else:
            # 1. 先按多次HOME键以确保应用回到桌面状态，这有助于scrcpy正确结束录制
            logger.info("发送HOME键序列")
            for i in range(3):
                subprocess.run("adb shell input keyevent KEYCODE_HOME", shell=True, timeout=2)
                time.sleep(0.5)
            
            # 2. 让设备屏幕休眠，这也有助于scrcpy优雅地结束录制
            logger.info("让设备屏幕休眠")
            subprocess.run("adb shell input keyevent KEYCODE_POWER", shell=True, timeout=2)
            time.sleep(2)
            
            # 3. 使用SIGINT信号(等同于按Ctrl+C) - 这是最优雅的方式，允许scrcpy完成MP4文件的正确写入
            logger.info("发送SIGINT信号 (Ctrl+C)")
            scrcpy_recording_process.send_signal(signal.SIGINT)
            
            # 4. 增加等待时间，给予更多时间处理SIGINT
            logger.info("等待SIGINT生效，这可能需要10-15秒...")
            max_wait = 15  # 增加到15秒
            wait_interval = 1
            
            for i in range(max_wait):
                if scrcpy_recording_process.poll() is not None:
                    logger.info(f"进程在接收SIGINT后成功退出，用时{i+1}秒")
                    break
                logger.info(f"等待进程退出... ({i+1}/{max_wait})")
                time.sleep(wait_interval)
            
            # 5. 如果SIGINT未能终止进程，尝试通过ADB命令停止server
            if scrcpy_recording_process.poll() is None:
                logger.info("SIGINT未能终止进程，尝试通过ADB停止scrcpy服务端")
                server_cmds = [
                    "adb shell am force-stop com.genymobile.scrcpy",  # 尝试停止scrcpy应用
                    "adb shell pkill -l 2 scrcpy-server",             # 发送INT信号给服务端
                    "adb shell pkill scrcpy-server"                   # 尝试终止服务端
                ]
                
                for cmd in server_cmds:
                    logger.info(f"执行: {cmd}")
                    subprocess.run(cmd, shell=True, timeout=2)
                    time.sleep(2)
                    if scrcpy_recording_process.poll() is not None:
                        logger.info("服务端停止后，进程成功退出")
                        break
            
            # 6. 如果仍未退出，使用SIGTERM - 更温和的终止信号
            if scrcpy_recording_process.poll() is None:
                logger.info("尝试通过SIGTERM终止进程")
                scrcpy_recording_process.terminate()
                
                # 给SIGTERM更多时间生效
                for i in range(10):  # 10秒等待
                    if scrcpy_recording_process.poll() is not None:
                        logger.info(f"进程在接收SIGTERM后成功退出，用时{i+1}秒")
                        break
                    logger.info(f"等待SIGTERM生效... ({i+1}/10)")
                    time.sleep(1)
                
                # 7. 仅在万不得已的情况下使用SIGKILL，因为它会导致录制文件损坏
                if scrcpy_recording_process.poll() is None:
                    logger.warning("所有温和的尝试都失败，不得不使用SIGKILL强制终止进程")
                    logger.warning("这可能导致录制文件损坏(moov atom丢失)，录制可能无法播放")
                    scrcpy_recording_process.kill()
                    time.sleep(2)
            
            # 获取退出状态
            exit_code = scrcpy_recording_process.wait(timeout=1)
            logger.info(f"录制进程已退出，退出码: {exit_code}")
            
            stderr = scrcpy_recording_process.stderr.read() if scrcpy_recording_process.stderr else ""
            if stderr:
                logger.info(f"stderr输出: {stderr}")
        
        # 8. 增加更长的等待时间，确保文件系统缓存刷新和文件写入完成
        logger.info("等待10秒确保文件写入完成...")
        time.sleep(10)  # 从5秒增加到10秒
        
        # 9. 检查文件是否存在及其完整性
        if os.path.exists(current_video_path):
            file_size = os.path.getsize(current_video_path) / (1024 * 1024)  # MB
            logger.info(f"录制文件: {current_video_path} (大小: {file_size:.2f}MB)")
            
            # 10. 使用ffmpeg快速检查文件完整性，如果不完整再尝试修复
            logger.info("预检查文件完整性...")
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                current_video_path
            ]
            
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
                if probe_result.returncode == 0:
                    duration = probe_result.stdout.strip()
                    logger.info(f"录制文件完整，时长: {duration}秒，无需修复")
                else:
                    logger.warning(f"文件可能损坏: {probe_result.stderr}")
                    # 尝试使用ffmpeg修复
                    fix_mp4_file(current_video_path)
            except Exception as e:
                logger.warning(f"预检查文件完整性时出错: {e}")
                # 继续尝试修复
                fix_mp4_file(current_video_path)
            
            # 11. 如果需要上传到Telegram
            if upload_to_tg:
                logger.info("上传视频到Telegram...")
                video_url = upload_to_telegram(current_video_path)
                if video_url:
                    logger.info(f"视频已上传，URL: {video_url}")
                else:
                    logger.warning("视频上传失败")
            
            return current_video_path, video_url
        else:
            logger.error(f"录制文件不存在: {current_video_path}")
            return None, None
    
    except Exception as e:
        logger.error(f"停止录制时出错: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return None, None
    finally:
        # 确保杀死所有scrcpy进程，但在这之前先尝试优雅地关闭它们
        kill_scrcpy_processes()
        scrcpy_recording_process = None

def fix_mp4_file(file_path):
    """尝试修复MP4文件"""
    try:
        # 检查ffmpeg是否可用
        if not check_ffmpeg_available():
            logger.warning("ffmpeg不可用，跳过文件修复")
            return
        
        logger.info("使用ffmpeg分析文件")
        # 检查文件是否需要修复
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        if probe_result.returncode == 0:
            # 文件正常，只需优化
            duration = probe_result.stdout.strip()
            logger.info(f"文件正常，时长: {duration}秒")
            
            # 添加faststart标记
            fixed_path = f"{file_path}.fixed.mp4"
            logger.info("优化文件")
            subprocess.run([
                "ffmpeg", "-v", "warning",
                "-i", file_path,
                "-c", "copy",
                "-movflags", "faststart",
                "-y", fixed_path
            ])
            
            # 替换原文件
            if os.path.exists(fixed_path) and os.path.getsize(fixed_path) > 0:
                os.rename(file_path, f"{file_path}.bak")
                os.rename(fixed_path, file_path)
                logger.info("文件优化完成")
        else:
            # 文件损坏，尝试修复
            logger.warning(f"文件可能损坏: {probe_result.stderr}")
            
            # 尝试重编码
            fixed_path = f"{file_path}.fixed.mp4"
            logger.info("尝试重编码修复文件")
            result = subprocess.run([
                "ffmpeg", "-v", "warning",
                "-fflags", "+genpts+igndts",
                "-i", file_path,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "23",
                "-movflags", "+faststart",
                "-y", fixed_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(fixed_path) and os.path.getsize(fixed_path) > 0:
                os.rename(file_path, f"{file_path}.bak")
                os.rename(fixed_path, file_path)
                logger.info("文件修复完成")
                
                # 再次检查文件是否可用
                check_result = subprocess.run([
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    file_path
                ], capture_output=True, text=True)
                
                if check_result.returncode == 0:
                    duration = check_result.stdout.strip()
                    logger.info(f"修复成功，文件时长: {duration}秒")
                else:
                    logger.warning(f"修复后文件仍有问题: {check_result.stderr}")
            else:
                logger.error(f"修复失败: {result.stderr}")
    
    except Exception as e:
        logger.error(f"修复文件时出错: {e}")

def check_device_connected():
    """
    检查是否有Android设备连接
    
    Returns:
        bool: 如果有设备连接则返回True，否则返回False
    """
    try:
        result = subprocess.run(
            ['adb', 'devices'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        output = result.stdout
        
        # 检查输出中是否包含至少一个设备
        lines = output.strip().split('\n')
        if len(lines) <= 1:  # 只有标题行，没有设备
            return False
            
        for line in lines[1:]:  # 跳过第一行（标题行）
            if line.strip() and not line.endswith('offline') and not line.endswith('unauthorized'):
                return True
                
        return False
    except Exception as e:
        logger.error(f"检查设备连接时出错: {str(e)}")
        return False

def test_scrcpy_recording(duration=15):
    """
    测试scrcpy录制功能
    
    Args:
        duration: 录制时长(秒)，0表示无限制(需要手动Ctrl+C中断)
        
    Returns:
        tuple: (成功状态, 修复后的视频路径)
    """
    logger.info("="*50)
    logger.info("开始测试scrcpy录制功能")
    logger.info("="*50)
    
    # 确保设备已连接
    if not check_device_connected():
        logger.error("未找到已连接的设备，无法进行录制测试")
        return False, None
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_scrcpy_{timestamp}.mp4"
    
    # 开始录制
    logger.info(f"开始录制，时长: {duration if duration > 0 else '无限制'} 秒")
    video_path = start_scrcpy_recording(filename)
    
    if not video_path:
        logger.error("启动录制失败")
        return False, None
    
    try:
        if duration > 0:
            # 等待指定时长
            logger.info(f"录制中... {duration}秒")
            time.sleep(duration)
        else:
            # 无限录制，等待用户中断
            logger.info("无限录制中，按Ctrl+C停止...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logger.info("用户中断，停止录制")
    finally:
        # 停止录制
        logger.info("停止录制")
        video_path, video_url = stop_scrcpy_recording(upload_to_tg=False)
        
        if not video_path or not os.path.exists(video_path):
            logger.error("录制失败，未生成视频文件")
            return False, None
        
        # 获取录制文件信息
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"录制完成: {video_path} (大小: {file_size_mb:.2f}MB)")
        
        # 使用ffmpeg修复视频
        logger.info("尝试使用ffmpeg修复视频...")
        
        # 创建修复后的文件路径
        file_dir = os.path.dirname(video_path)
        file_name = os.path.basename(video_path)
        file_name_no_ext = os.path.splitext(file_name)[0]
        fixed_video_path = os.path.join(file_dir, f"{file_name_no_ext}_fixed.mp4")
        
        try:
            # 使用ffmpeg修复视频并添加faststart标志
            cmd = [
                "ffmpeg", "-v", "warning",
                "-i", video_path,
                "-c", "copy",
                "-movflags", "faststart",
                "-y", fixed_video_path
            ]
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(fixed_video_path):
                fixed_size_mb = os.path.getsize(fixed_video_path) / (1024 * 1024)
                logger.info(f"视频修复成功: {fixed_video_path} (大小: {fixed_size_mb:.2f}MB)")
                logger.info("="*50)
                logger.info("测试完成，scrcpy录制功能正常")
                logger.info("="*50)
                return True, fixed_video_path
            else:
                logger.error(f"视频修复失败: {result.stderr}")
                logger.info("="*50)
                logger.info("测试完成，原始视频可用但修复失败")
                logger.info("="*50)
                return True, video_path
        except Exception as e:
            logger.error(f"视频修复过程出错: {str(e)}")
            logger.info("="*50)
            logger.info("测试完成，原始视频可用但修复出错")
            logger.info("="*50)
            return True, video_path
    
    return False, None

# 如果直接运行该脚本，则测试scrcpy录制功能
if __name__ == "__main__":
    # 检查命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="华为快应用自动化测试工具")
    parser.add_argument("--test-scrcpy", action="store_true", help="测试scrcpy录制功能")
    parser.add_argument("-d", "--duration", type=int, default=15, help="录制时长(秒)，0表示无限制")
    args = parser.parse_args()
    
    if args.test_scrcpy:
        # 测试scrcpy录制功能
        test_scrcpy_recording(args.duration)
    else:
        # 启动定时任务
        main() 