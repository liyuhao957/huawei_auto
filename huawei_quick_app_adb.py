#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huawei Quick App ADB-based Automation Script
通过ADB命令和坐标点击实现的快应用自动化测试脚本
使用ADBKeyboard输入法实现中文输入
支持飞书通知和图片上传功能
支持定时自动执行功能
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

# 配置
SCREENSHOTS_DIR = "screenshots"  # 存储截图的目录

# 如果截图目录不存在，则创建
if not os.path.exists(SCREENSHOTS_DIR):
    os.makedirs(SCREENSHOTS_DIR)

# 飞书机器人配置
FEISHU_WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/2e9f09a8-4cec-4475-a6a8-4da61c4a874c"  # 替换为您的飞书机器人webhook URL
FEISHU_SECRET = "YOUR_SECRET"  # 替换为您的飞书机器人签名密钥，如果没有设置签名可以留空

# Stardots图床配置
STARDOTS_API_KEY = "a4a15dc3-f394-4340-8749-311eb09cab9d"
STARDOTS_API_SECRET = "YJiDe7jRLEURX4HxD5PINBMBHJvxjNdMTzuK08GAnAAg68gKebanBFcIYPu5xZ1sd21c2Db7JS5dmF1T0v6GjuDAM2L6UDO46B54wdazIiJuHrbfqHZRKEE9Vjbz4QMkHvzK4gSyjZe88opI6fvfTvVbeiXffvuDqQUGNt5c8tzj0jnQvS0BRXQRezRy8cYWc4Z0zm4z1Ktmk5V70h4UVUrd3oIyxMBHxdYdzJUnERzXLZ9QXiq5xG3Sg5IIAmU"
STARDOTS_API_URL = "https://api.stardots.io"  # 基础URL
STARDOTS_SPACE = "huawei"  # 设置空间名称为huawei

# 设备屏幕尺寸
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 2376

def upload_image_to_stardots(image_path):
    """
    上传图片到Stardots图床
    
    Args:
        image_path: 图片文件路径
    
    Returns:
        str: 上传成功返回图片URL，失败返回None
    """
    if not os.path.exists(image_path):
        logger.error(f"图片文件不存在: {image_path}")
        return None
    
    try:
        logger.info(f"开始上传图片到Stardots空间'{STARDOTS_SPACE}': {image_path}")
        
        # 生成时间戳（秒）
        timestamp = str(int(time.time()))
        
        # 生成4-20个字符的随机字符串作为nonce
        nonce = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # 构建签名内容字符串：timestamp|secret|nonce
        sign_str = f"{timestamp}|{STARDOTS_API_SECRET}|{nonce}"
        
        # 计算MD5签名并转为大写
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
        
        # 准备请求头
        headers = {
            "x-stardots-timestamp": timestamp,
            "x-stardots-nonce": nonce,
            "x-stardots-key": STARDOTS_API_KEY,
            "x-stardots-sign": sign
        }
        
        # 准备文件和空间参数
        files = {
            'file': (os.path.basename(image_path), open(image_path, 'rb'), 'image/png')
        }
        
        data = {
            'space': STARDOTS_SPACE
        }
        
        # 完整的上传URL
        upload_url = f"{STARDOTS_API_URL}/openapi/file/upload"
        
        # 发送请求
        response = requests.put(upload_url, headers=headers, files=files, data=data)
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                image_url = result.get("data", {}).get("url")
                logger.info(f"图片上传成功: {image_url}")
                return image_url
            else:
                logger.warning(f"图片上传失败: {result.get('message')}")
                return None
        else:
            logger.warning(f"图片上传请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
            return None
    except Exception as e:
        logger.error(f"上传图片到Stardots时出错: {str(e)}")
        
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
                    "content": "**📷 测试截图：**"
                }
            })
            
            # 为每张图片创建按钮
            image_buttons = []
            
            for i, url in enumerate(image_urls):
                if url:  # 确保URL不为空
                    button_text = "防侧滑" if i == 0 else "拉回" if i == 1 else f"查看截图 {i+1}"
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
        
    def take_screenshot(self, name=None, upload=False):
        """截取屏幕截图，并可选择上传到图床
        
        Args:
            name: 截图文件名（不含扩展名），如果为None则使用时间戳
            upload: 是否上传截图到图床
            
        Returns:
            tuple: (本地文件路径, 如果上传则返回图床URL，否则为None)
        """
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}"
        
        filename = f"{SCREENSHOTS_DIR}/{name}.png"
        logger.info(f"截图: {filename}")
        
        # 使用ADB命令截图
        subprocess.run(f"adb shell screencap -p /sdcard/{name}.png", shell=True)
        subprocess.run(f"adb pull /sdcard/{name}.png {filename}", shell=True)
        subprocess.run(f"adb shell rm /sdcard/{name}.png", shell=True)
        
        # 如果需要上传到图床
        image_url = None
        if upload and os.path.exists(filename):
            logger.info(f"上传截图到图床: {filename}")
            image_url = upload_image_to_stardots(filename)
            
        return filename, image_url
        
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
        time.sleep(2)
        
        # 5. 点击"同意"按钮(如果出现)
        logger.info("步骤5: 检查并点击'同意'按钮(如果出现)")
        self.tap_by_percent(0.681, 0.937)  # 坐标: (736, 2227)
        time.sleep(2)
        
        # 增加额外等待时间，确保应用市场稳定后再继续下一流程
        logger.info("等待应用市场稳定 (3秒)")
        time.sleep(3)
        
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
        
        # 用于记录测试截图URL
        self.swipe_screenshot_url = None
        self.home_screenshot_url = None
        test_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = False
        error_msg = None
        
        # 详细测试结果
        detailed_results = {
            "流程1_清除快应用中心数据": False,
            "流程2_通过应用市场管理快应用": False,
            "流程3_防侧滑测试": False,
            "流程3_拉回测试": False, 
            "流程4_清空手机里的全部应用": False
        }
        
        try:
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
                detailed_results["流程1_清除快应用中心数据"],
                detailed_results["流程2_通过应用市场管理快应用"],
                detailed_results["流程3_防侧滑测试"],
                detailed_results["流程3_拉回测试"],
                detailed_results["流程4_清空手机里的全部应用"]
            ])
            
            logger.info(f"所有流程执行完成。详细结果: {detailed_results}")
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
            
            # 如果需要发送飞书通知
            if send_notification:
                test_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if success:
                    title = "✅ 快应用自动化测试成功"
                    content = f"**快应用防侧滑和拉回测试成功完成！**\n\n" \
                              f"- 开始时间: {test_start_time}\n" \
                              f"- 结束时间: {test_end_time}\n" \
                              f"- 测试设备: 华为设备\n\n" \
                              f"**✅ 成功执行了所有测试流程:**\n" \
                              f"1. 清除快应用中心数据: {'✅ 成功' if detailed_results['流程1_清除快应用中心数据'] else '❌ 失败'}\n" \
                              f"2. 通过应用市场管理快应用: {'✅ 成功' if detailed_results['流程2_通过应用市场管理快应用'] else '❌ 失败'}\n" \
                              f"3. 快应用功能测试: \n" \
                              f"   - 防侧滑测试: {'✅ 成功' if detailed_results['流程3_防侧滑测试'] else '❌ 失败'}\n" \
                              f"   - 拉回测试: {'✅ 成功' if detailed_results['流程3_拉回测试'] else '❌ 失败'}\n" \
                              f"4. 清空手机里的全部应用: {'✅ 成功' if detailed_results['流程4_清空手机里的全部应用'] else '❌ 失败'}"
                else:
                    # 确定哪个测试失败了
                    failure_reasons = []
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
                              f"1. 清除快应用中心数据: {'✅ 成功' if detailed_results['流程1_清除快应用中心数据'] else '❌ 失败'}\n" \
                              f"2. 通过应用市场管理快应用: {'✅ 成功' if detailed_results['流程2_通过应用市场管理快应用'] else '❌ 失败'}\n" \
                              f"3. 快应用功能测试: \n" \
                              f"   - 防侧滑测试: {'✅ 成功' if detailed_results['流程3_防侧滑测试'] else '❌ 失败'}\n" \
                              f"   - 拉回测试: {'✅ 成功' if detailed_results['流程3_拉回测试'] else '❌ 失败'}\n" \
                              f"4. 清空手机里的全部应用: {'✅ 成功' if detailed_results['流程4_清空手机里的全部应用'] else '❌ 失败'}\n\n" \
                              f"**{'❌ 错误信息:' if error_msg else ''}** {error_msg or ''}"
                
                # 收集截图URL
                image_urls = []
                if self.swipe_screenshot_url:
                    image_urls.append(self.swipe_screenshot_url)
                if self.home_screenshot_url:
                    image_urls.append(self.home_screenshot_url)
                
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
    
    logger.info("启动定时任务模式，每30分钟执行一次测试")
    
    # 先执行一次测试
    run_automated_test(no_notification=args.no_notification, upload_screenshots=args.upload_screenshots)
    
    # 设置定时任务，每30分钟执行一次
    schedule.every(30).minutes.do(
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
        logger.info("定时测试任务已结束")

if __name__ == "__main__":
    main() 