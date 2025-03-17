#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Huawei Quick App Automation Script
This script automates the process of clearing data for the Quick App Center on Huawei devices.
"""

import uiautomator2 as u2
import time
import logging
import os
import schedule
import requests
import json
import hashlib
import base64
import hmac
from datetime import datetime
import random
import string

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_app_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QuickAppTester")

# 配置
DEVICE_SERIAL = None  # 如果有多台设备连接，请设置为特定设备序列号
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

class QuickAppTester:
    """主类，用于执行快应用测试"""
    
    def __init__(self, device_serial=None):
        """初始化测试器"""
        logger.info("初始化QuickAppTester")
        self.device = u2.connect(device_serial)  # 连接设备
        self.screen_width, self.screen_height = self.device.window_size()
        logger.info(f"设备屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
    def check_screen_state(self):
        """检查屏幕状态"""
        try:
            # 尝试获取当前屏幕状态
            info = self.device.info
            screen_on = info.get('screenOn', None)
            if screen_on is not None:
                logger.info(f"屏幕状态: {'亮屏' if screen_on else '熄屏'}")
                return screen_on
            else:
                # 如果无法直接获取屏幕状态，尝试通过其他方式判断
                try:
                    # 尝试截图，如果成功则说明屏幕是亮的
                    self.device.screenshot()
                    logger.info("屏幕状态: 亮屏 (通过截图判断)")
                    return True
                except Exception as e:
                    logger.info(f"屏幕状态: 可能熄屏 (截图失败: {str(e)})")
                    return False
        except Exception as e:
            logger.warning(f"检查屏幕状态失败: {str(e)}")
            return None
    
    def wake_screen(self):
        """唤醒屏幕"""
        logger.info("开始唤醒屏幕...")
        
        # 检查当前屏幕状态
        screen_state = self.check_screen_state()
        
        # 如果屏幕已经亮起，直接返回成功
        if screen_state:
            logger.info("屏幕已经处于亮屏状态，无需唤醒")
            return True
        
        # 尝试唤醒屏幕
        logger.info("尝试唤醒屏幕")
        try:
            # 方法1: 使用uiautomator2的screen_on方法
            logger.info("尝试使用screen_on方法唤醒屏幕")
            self.device.screen_on()
            time.sleep(1)
            
            # 检查是否成功唤醒
            if self.check_screen_state():
                logger.info("成功使用screen_on方法唤醒屏幕")
                return True
            
            # 方法2: 使用按电源键唤醒
            logger.info("尝试使用按电源键方法唤醒屏幕")
            self.device.press("power")
            time.sleep(1)
            
            if self.check_screen_state():
                logger.info("成功使用电源键唤醒屏幕")
                return True
            
            # 方法3: 使用shell命令唤醒
            logger.info("尝试使用shell命令唤醒屏幕")
            self.device.shell("input keyevent KEYCODE_WAKEUP")
            time.sleep(1)
            
            if self.check_screen_state():
                logger.info("成功使用shell命令唤醒屏幕")
                return True
            
            logger.error("所有唤醒方法均失败")
            return False
        except Exception as e:
            logger.error(f"唤醒屏幕时出错: {str(e)}")
            return False
    
    def simple_unlock(self):
        """简单解锁（适用于无密码设备）"""
        logger.info("尝试简单解锁（适用于无密码设备）")
        
        try:
            # 对于无密码设备，通常只需要滑动一下即可解锁
            logger.info("尝试滑动解锁屏幕")
            self.device.swipe(self.screen_width * 0.5, self.screen_height * 0.8, 
                             self.screen_width * 0.5, self.screen_height * 0.2)
            time.sleep(0.5)
            
            # 按下Home键确保回到主屏幕
            logger.info("按下Home键确保回到主屏幕")
            self.device.press("home")
            time.sleep(0.5)
            
            # 验证是否成功解锁
            current_app = self.device.app_current()
            logger.info(f"当前应用信息: {current_app}")
            
            logger.info("简单解锁完成")
            return True
        except Exception as e:
            logger.error(f"简单解锁时出错: {str(e)}")
            return False
    
    def ensure_screen_on(self):
        """确保屏幕处于唤醒和解锁状态"""
        logger.info("确保屏幕处于唤醒和解锁状态")
        
        # 1. 检查屏幕状态
        logger.info("步骤1: 检查屏幕状态")
        screen_on = self.check_screen_state()
        logger.info(f"屏幕是否亮起: {screen_on}")
        
        # 如果屏幕已经亮起，直接返回成功
        if screen_on:
            logger.info("屏幕已经处于亮屏状态")
            return True
        
        # 2. 唤醒屏幕
        logger.info("步骤2: 唤醒屏幕")
        wake_result = self.wake_screen()
        
        if not wake_result:
            logger.error("唤醒屏幕失败")
            return False
        
        # 3. 简单解锁（适用于无密码设备）
        logger.info("步骤3: 简单解锁")
        unlock_result = self.simple_unlock()
        
        if wake_result and unlock_result:
            logger.info("屏幕已成功唤醒并解锁")
            return True
        else:
            logger.error("屏幕唤醒或解锁失败")
            return False
        
    def take_screenshot(self, name=None):
        """截取屏幕截图"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"screenshot_{timestamp}"
        
        filename = f"{SCREENSHOTS_DIR}/{name}.png"
        self.device.screenshot(filename)
        logger.info(f"截图已保存: {filename}")
        return filename
        
    def is_quick_app_running(self, app_name=None):
        """
        检查快应用是否在前台运行
        
        参数:
            app_name: 可选，指定要检查的快应用名称
        
        返回:
            bool: 如果快应用在前台运行则返回True，否则返回False
        """
        # 获取当前前台应用信息
        current_app = self.device.app_current()
        logger.info(f"当前前台应用信息: {current_app}")
        package_name = current_app.get('package', '')
        activity = current_app.get('activity', '')
        
        # 快应用相关包名
        quick_app_packages = [
            "com.huawei.fastapp",  # 华为快应用中心
            "com.huawei.fastapp:ui",  # 华为快应用UI进程
            "com.huawei.fastapp.dev",  # 华为快应用开发版
            "com.huawei.fastapp.dev:ui"  # 华为快应用开发版UI进程
        ]
        
        # 快应用特征
        quick_app_features = [
            "快应用",
            "fastapp",
            "quickapp"
        ]
        
        # 检查是否是已知的快应用包名
        if any(pkg in package_name for pkg in quick_app_packages):
            logger.info(f"检测到快应用中心在前台运行: {package_name}")
            
            # 如果指定了应用名称，则进一步检查UI元素
            if app_name:
                # 尝试在界面上查找应用名称
                if self.device(text=app_name).exists:
                    logger.info(f"在界面上找到指定的快应用: {app_name}")
                    return True
                else:
                    logger.info(f"未在界面上找到指定的快应用: {app_name}")
                    return False
            return True
        
        # 检查是否有快应用特征
        for feature in quick_app_features:
            if feature in package_name.lower() or feature in activity.lower():
                logger.info(f"根据特征检测到快应用在前台运行: {feature}")
                return True
        
        # 使用dumpsys检查更多信息
        try:
            window_info = self.device.shell("dumpsys window | grep mCurrentFocus")
            logger.debug(f"窗口信息: {window_info}")
            
            # 检查窗口信息中是否包含快应用特征
            for feature in quick_app_features:
                if feature in window_info.lower():
                    logger.info(f"通过窗口信息检测到快应用在前台运行: {feature}")
                    return True
                    
            # 检查是否是华为浏览器中的快应用
            if "com.huawei.browser" in window_info and any(feature in window_info.lower() for feature in quick_app_features):
                logger.info("检测到华为浏览器中的快应用在前台运行")
                return True
        except Exception as e:
            logger.warning(f"获取窗口信息失败: {str(e)}")
        
        # 如果指定了应用名称，尝试在界面上查找
        if app_name and self.device(text=app_name).exists:
            # 检查是否有快应用相关的UI元素
            if (self.device(text="快应用").exists or 
                self.device(resourceId="com.huawei.fastapp:id/container").exists):
                logger.info(f"通过UI元素检测到快应用 '{app_name}' 在前台运行")
                return True
        
        logger.info("未检测到快应用在前台运行")
        return False
        
    def search_and_open_quick_app(self):
        """流程3: 在快应用中心搜索并打开"买乐多"，然后进行侧滑、截图和前台检测"""
        logger.info("开始执行流程3: 在快应用中心搜索并打开'买乐多'...")
        
        # 用于存储测试结果
        test_results = {
            "防侧滑": False,
            "拉回": False
        }
        
        # 1. 点击搜索框
        logger.info("步骤1: 点击搜索框")
        search_box = self.device(resourceId="com.huawei.fastapp:id/search_src_text")
        
        if search_box.exists:
            logger.info("找到搜索框")
            search_box.click()
            time.sleep(2)
        else:
            logger.warning("未找到搜索框，尝试使用坐标点击")
            # 尝试使用坐标点击 - 通常搜索框在屏幕顶部中间位置
            self.device.click(self.screen_width * 0.5, self.screen_height * 0.1)
            time.sleep(2)
        
        # 2. 输入"买乐多"
        logger.info("步骤2: 输入'买乐多'")
        # 先清除可能存在的文本
        self.device.clear_text()
        time.sleep(0.5)
        
        # 输入搜索文本
        self.device.send_keys("买乐多")
        time.sleep(1)
        
        # 按下回车键执行搜索
        self.device.press("enter")
        time.sleep(3)
        
        # 3. 点击搜索结果旁边的"打开"按钮
        logger.info("步骤3: 点击第一个'买乐多'旁边的'打开'按钮")
        
        # 方法1: 使用精确的resourceId定位"打开"按钮
        try:
            # 根据您提供的信息，使用精确的resourceId
            open_button = self.device(resourceId="com.huawei.fastapp:id/downbtn", text="打开")
            if open_button.exists:
                logger.info("找到'打开'按钮 (通过resourceId和text)")
                open_button.click()
                time.sleep(10)  # 等待10秒让应用加载
            else:
                # 方法2: 使用XPath定位第一个"打开"按钮
                logger.info("尝试使用XPath定位'打开'按钮")
                xpath_selector = '//*[@resource-id="com.huawei.fastapp:id/applistview"]/android.widget.LinearLayout[1]/android.widget.FrameLayout[1]/android.widget.RelativeLayout[1]/android.widget.RelativeLayout[1]/android.widget.Button[1]'
                open_xpath = self.device.xpath(xpath_selector)
                if open_xpath.exists:
                    logger.info("找到'打开'按钮 (通过XPath)")
                    open_xpath.click()
                    time.sleep(10)
                else:
                    # 方法3: 使用精确坐标点击
                    logger.info("使用精确坐标点击'打开'按钮 (0.814, 0.16)")
                    self.device.click(self.screen_width * 0.814, self.screen_height * 0.16)
                    time.sleep(10)
        except Exception as e:
            logger.warning(f"点击'打开'按钮时出错: {str(e)}，尝试备选方法")
            # 备选方法: 使用精确坐标点击
            logger.info("使用精确坐标点击'打开'按钮 (0.814, 0.16)")
            self.device.click(self.screen_width * 0.814, self.screen_height * 0.16)
            time.sleep(10)
        
        # 4. 快速侧滑10次 - 使用超快速连续侧滑（从swipe_only_test.py的方法3）
        logger.info("步骤4: 超快速连续侧滑10次")
        for i in range(10):
            logger.info(f"第{i+1}次超快速侧滑")
            
            # 从屏幕最右边中间位置开始，中等距离侧滑 - 屏幕宽度的10%
            start_x = int(self.screen_width * 0.98)  # 屏幕最右边
            end_x = int(self.screen_width * 0.88)    # 向左滑动10%的屏幕宽度
            y_pos = int(self.screen_height * 0.5)    # 垂直位置在屏幕中间
            
            # 使用15毫秒的超快速持续时间
            try:
                self.device.shell(f"input swipe {start_x} {y_pos} {end_x} {y_pos} 15")
                logger.info(f"执行从最右边中间位置中等距离超快速侧滑: {start_x},{y_pos} -> {end_x},{y_pos}")
            except Exception as e:
                logger.warning(f"使用shell命令侧滑失败: {str(e)}")
                # 备选方法：使用SDK的swipe方法，但使用更短的持续时间
                self.device.swipe(start_x, y_pos, end_x, y_pos, duration=0.015)
            
            # 每次侧滑后极短等待
            time.sleep(0.1)  # 减少等待时间，提高连续性
        
        # 滑动完成后等待2秒，让界面稳定下来
        logger.info("滑动完成，等待2秒让界面稳定")
        time.sleep(2)
        
        # 滑动10次后检测快应用是否在前台
        logger.info("滑动10次后检测快应用是否在前台")
        
        # 获取当前前台应用信息
        current_app = self.device.app_current()
        logger.info(f"当前前台应用信息: {current_app}")
        package_name = current_app.get('package', '')
        activity = current_app.get('activity', '')
        
        # 检查是否是快应用相关包名
        is_quick_app = False
        if "com.huawei.fastapp" in package_name:
            logger.info(f"检测到快应用在前台运行: {package_name}")
            is_quick_app = True
            
            # 尝试使用dumpsys获取更多信息
            try:
                window_info = self.device.shell("dumpsys window | grep mCurrentFocus")
                logger.info(f"窗口信息: {window_info}")
                # 检查输出字符串而不是对象
                if isinstance(window_info, str):
                    if "买乐多" in window_info or "fastapp" in window_info.lower():
                        logger.info("通过窗口信息确认快应用在前台运行")
                        is_quick_app = True
                else:
                    # 如果是ShellResponse对象，获取其output属性
                    output = getattr(window_info, 'output', '')
                    if "买乐多" in output or "fastapp" in output.lower():
                        logger.info("通过窗口信息确认快应用在前台运行")
                        is_quick_app = True
            except Exception as e:
                logger.warning(f"获取窗口信息失败: {str(e)}")
        
        if is_quick_app:
            logger.info("侧滑拦截成功：快应用仍在前台运行")
            test_results["防侧滑"] = True
        else:
            logger.warning("侧滑拦截失败：快应用已不在前台运行")
            test_results["防侧滑"] = False
            # 侧滑拦截失败后，直接继续执行后续测试步骤，不添加额外的恢复逻辑
            logger.info("侧滑拦截失败，继续执行后续测试步骤")
        
        # 检测完成后等待2秒再继续后续操作
        logger.info("检测完成，等待2秒再继续后续操作")
        time.sleep(2)
        
        # 滑动10次后立即截图
        logger.info("滑动10次后立即截图")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        after_10_swipes_image_url = upload_image_to_stardots(self.take_screenshot(f"after_10_swipes_{timestamp}"))
        if after_10_swipes_image_url:
            logger.info(f"侧滑后截图上传成功: {after_10_swipes_image_url}")
        else:
            logger.error("侧滑后截图上传失败")
        
        # 6. 按Home键返回桌面
        logger.info("步骤6: 按Home键返回桌面")
        self.device.press("home")
        logger.info("等待10秒...")
        time.sleep(10)  # 等待10秒
        
        # 7. 判断快应用是否在前台
        logger.info("步骤7: 判断快应用是否在前台")
        
        # 获取当前前台应用信息
        current_app = self.device.app_current()
        logger.info(f"当前前台应用信息: {current_app}")
        package_name = current_app.get('package', '')
        activity = current_app.get('activity', '')
        
        # 检查是否是快应用相关包名
        is_quick_app = False
        if "com.huawei.fastapp" in package_name:
            logger.info(f"检测到快应用在前台运行: {package_name}")
            is_quick_app = True
            
            # 检查UI元素
            if self.device(text="买乐多").exists:
                logger.info("在界面上找到'买乐多'文本")
                is_quick_app = True
            else:
                # 尝试使用dumpsys获取更多信息
                try:
                    window_info = self.device.shell("dumpsys window | grep mCurrentFocus")
                    logger.info(f"窗口信息: {window_info}")
                    # 检查输出字符串而不是对象
                    if isinstance(window_info, str):
                        if "买乐多" in window_info or "fastapp" in window_info.lower():
                            logger.info("通过窗口信息确认快应用在前台运行")
                            is_quick_app = True
                    else:
                        # 如果是ShellResponse对象，获取其output属性
                        output = getattr(window_info, 'output', '')
                        if "买乐多" in output or "fastapp" in output.lower():
                            logger.info("通过窗口信息确认快应用在前台运行")
                            is_quick_app = True
                except Exception as e:
                    logger.warning(f"获取窗口信息失败: {str(e)}")
        
        logger.info(f"快应用'买乐多'是否在前台运行: {'是' if is_quick_app else '否'}")
        
        # 添加判断，明确标记是否成功拉回快应用
        if is_quick_app:
            logger.info("拉回成功：按Home键后快应用仍在前台运行")
            test_results["拉回"] = True
        else:
            logger.warning("拉回失败：按Home键后快应用已不在前台运行")
            test_results["拉回"] = False
        
        # 检测完快应用是否在前台运行后立即截图
        logger.info("检测完快应用是否在前台运行后立即截图")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        after_foreground_check_image_url = upload_image_to_stardots(self.take_screenshot(f"after_foreground_check_{timestamp}"))
        if after_foreground_check_image_url:
            logger.info(f"前台检测后截图上传成功: {after_foreground_check_image_url}")
        else:
            logger.error("前台检测后截图上传失败")
        
        logger.info("流程3执行完成")
        
        return test_results
        
    def manage_quick_apps_via_market(self):
        """通过应用市场进入快应用管理界面"""
        logger.info("开始通过应用市场管理快应用...")
        
        # 1. 按Home键
        logger.info("步骤1: 按下Home键")
        self.device.press("home")
        time.sleep(1)
        
        # 2. 打开应用市场 - 使用intent方式
        logger.info("步骤2: 打开应用市场")
        try:
            # 使用intent方式打开应用市场
            logger.info("尝试使用intent方式打开应用市场")
            self.device.shell("am start -n com.huawei.appmarket/.MainActivity")
            time.sleep(8)  # 等待8秒让应用市场完全加载
        except Exception as e:
            logger.warning(f"使用intent打开应用市场失败: {str(e)}，尝试备选方法")
            try:
                # 备选方法：直接使用包名启动
                logger.info("尝试直接使用包名启动应用市场")
                self.device.app_start("com.huawei.appmarket")
                time.sleep(8)
            except Exception as e2:
                logger.warning(f"使用包名启动应用市场失败: {str(e2)}，尝试点击应用市场图标")
                # 尝试点击应用市场图标
                market_icon = self.device(text="应用市场")
                if market_icon.exists:
                    market_icon.click()
                else:
                    logger.error("无法打开应用市场，测试终止")
                    return False
                time.sleep(8)
        
        # 3. 点击"我的"选项卡
        logger.info("步骤3: 点击'我的'选项卡")
        # 由于clickable为false，尝试多种方法
        my_tab = self.device(text="我的", resourceId="com.huawei.appmarket:id/content")
        
        if my_tab.exists:
            logger.info("找到'我的'选项卡")
            # 尝试点击元素
            my_tab.click()
            time.sleep(2)
            
            # 检查是否成功点击
            if not self.device(text="快应用管理").exists:
                logger.warning("点击'我的'选项卡可能失败，尝试使用坐标点击")
                # 尝试使用坐标点击 - 通常"我的"选项卡在屏幕右下角
                self.device.click(self.screen_width * 0.9, self.screen_height * 0.95)
                time.sleep(2)
        else:
            logger.warning("未找到'我的'选项卡，尝试使用坐标点击")
            # 尝试使用坐标点击 - 通常"我的"选项卡在屏幕右下角
            self.device.click(self.screen_width * 0.9, self.screen_height * 0.95)
            time.sleep(2)
        
        # 4. 点击"快应用管理"
        logger.info("步骤4: 点击'快应用管理'")
        # 由于clickable为false，尝试多种方法
        quick_app_mgmt = self.device(text="快应用管理", resourceId="com.huawei.appmarket:id/menu_title_textview")
        
        if quick_app_mgmt.exists:
            logger.info("找到'快应用管理'选项")
            # 获取元素位置信息
            bounds = quick_app_mgmt.info.get('bounds', {})
            if bounds:
                # 计算元素中心点
                center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                logger.info(f"'快应用管理'元素中心点: ({center_x}, {center_y})")
                # 点击中心点
                self.device.click(center_x, center_y)
            else:
                # 如果无法获取位置信息，直接点击元素
                quick_app_mgmt.click()
            time.sleep(3)
        else:
            logger.warning("未找到'快应用管理'选项，尝试滑动查找")
            # 尝试向下滑动查找
            for i in range(3):
                self.device.swipe(self.screen_width * 0.5, self.screen_height * 0.7, 
                                 self.screen_width * 0.5, self.screen_height * 0.3)
                time.sleep(1)
                if self.device(text="快应用管理").exists:
                    self.device(text="快应用管理").click()
                    break
                if i == 2:
                    logger.error("无法找到'快应用管理'选项，测试终止")
                    return False
            time.sleep(3)
        
        # 5. 点击"同意"（如果出现隐私协议对话框）
        logger.info("步骤5: 检查并点击'同意'按钮（如果出现）")
        agree_button = self.device(text="同意")
        if agree_button.exists:
            logger.info("找到'同意'按钮，点击")
            agree_button.click()
            time.sleep(2)
        else:
            logger.info("未出现需要点击'同意'的对话框，继续执行")
        
        logger.info("成功进入快应用管理界面")
        return True
        
    def clear_quick_app_center_data(self):
        """导航到设置并清除快应用中心数据"""
        logger.info("开始清理快应用中心数据...")
        
        # 1. 按Home键
        logger.info("步骤1: 按下Home键")
        self.device.press("home")
        time.sleep(1)
        input("按回车继续执行步骤2...")
        
        # 2. 打开设置应用 - 使用intent方式
        logger.info("步骤2: 打开设置应用")
        try:
            # 使用intent方式打开设置
            logger.info("尝试使用intent方式打开设置")
            self.device.shell("am start -a android.settings.SETTINGS")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"使用intent打开设置失败: {str(e)}，尝试备选方法")
            try:
                # 备选方法1：直接使用包名启动
                logger.info("尝试直接使用包名启动设置")
                self.device.app_start("com.android.settings", activity=".Settings")
                time.sleep(2)
            except Exception as e2:
                logger.warning(f"使用包名启动设置失败: {str(e2)}，尝试点击设置图标")
                # 备选方法2：点击设置图标
                logger.info("尝试点击设置图标")
                settings_icon = self.device(text="设置")
                if settings_icon.exists:
                    settings_icon.click()
                else:
                    # 最后尝试点击屏幕上可能的设置图标位置
                    logger.warning("未找到设置图标，尝试点击可能的位置")
                    self.device.click(self.screen_width * 0.5, self.screen_height * 0.2)
                time.sleep(2)
        input("按回车继续执行步骤3...")
        
        # 3. 点击搜索框（搜索设置项）
        logger.info("步骤3: 点击搜索框")
        search_box = self.device(resourceId="android:id/search_edit_frame")
        
        # 尝试多种方法点击搜索框
        search_clicked = False
        
        # 方法1: 尝试直接点击元素（即使clickable=false）
        if search_box.exists:
            logger.info("方法1: 尝试直接点击搜索框元素")
            try:
                search_box.click()
                time.sleep(1.5)
                if self.device(focused=True).exists:
                    logger.info("搜索框已获得焦点")
                    search_clicked = True
            except Exception as e:
                logger.warning(f"直接点击搜索框失败: {str(e)}")
        
        # 方法2: 尝试点击搜索框内的文本元素
        if not search_clicked:
            logger.info("方法2: 尝试点击搜索框内的文本元素")
            search_text = self.device(text="搜索设置项")
            if search_text.exists:
                try:
                    search_text.click()
                    time.sleep(1.5)
                    if self.device(focused=True).exists:
                        logger.info("通过点击文本元素，搜索框已获得焦点")
                        search_clicked = True
                except Exception as e:
                    logger.warning(f"点击搜索框文本失败: {str(e)}")
        
        # 方法3: 尝试使用坐标点击
        if not search_clicked:
            logger.info("方法3: 尝试使用精确坐标点击搜索框")
            try:
                # 点击屏幕顶部中间位置（通常是搜索框的位置）
                self.device.click(self.screen_width * 0.5, self.screen_height * 0.06)
                time.sleep(1.5)
                if self.device(focused=True).exists:
                    logger.info("通过坐标点击，搜索框已获得焦点")
                    search_clicked = True
                else:
                    # 尝试点击稍微下方一点的位置
                    self.device.click(self.screen_width * 0.5, self.screen_height * 0.1)
                    time.sleep(1.5)
                    if self.device(focused=True).exists:
                        logger.info("通过第二次坐标点击，搜索框已获得焦点")
                        search_clicked = True
            except Exception as e:
                logger.warning(f"使用坐标点击搜索框失败: {str(e)}")
        
        # 方法4: 尝试使用tap_center方法
        if not search_clicked and search_box.exists:
            logger.info("方法4: 尝试使用tap_center方法")
            try:
                bounds = search_box.info.get('bounds', {})
                center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                logger.info(f"搜索框中心点: ({center_x}, {center_y})")
                self.device.click(center_x, center_y)
                time.sleep(1.5)
                if self.device(focused=True).exists:
                    logger.info("通过点击中心点，搜索框已获得焦点")
                    search_clicked = True
            except Exception as e:
                logger.warning(f"使用tap_center方法失败: {str(e)}")
        
        # 方法5: 尝试使用XPath定位
        if not search_clicked:
            logger.info("方法5: 尝试使用XPath定位搜索框")
            try:
                self.device.xpath('//*[@resource-id="android:id/search_edit_frame"]').click()
                time.sleep(1.5)
                if self.device(focused=True).exists:
                    logger.info("通过XPath点击，搜索框已获得焦点")
                    search_clicked = True
            except Exception as e:
                logger.warning(f"XPath点击失败: {str(e)}")
        
        # 方法6: 尝试使用父元素或兄弟元素
        if not search_clicked:
            logger.info("方法6: 尝试查找并点击搜索图标")
            search_icon = self.device(resourceId="android:id/search_button")
            if search_icon.exists:
                try:
                    search_icon.click()
                    time.sleep(1.5)
                    if self.device(focused=True).exists:
                        logger.info("通过点击搜索图标，搜索框已获得焦点")
                        search_clicked = True
                except Exception as e:
                    logger.warning(f"点击搜索图标失败: {str(e)}")
        
        # 方法7: 尝试使用adb shell input tap命令
        if not search_clicked:
            logger.info("方法7: 尝试使用adb shell input tap命令")
            try:
                x = int(self.screen_width * 0.5)
                y = int(self.screen_height * 0.08)
                self.device.shell(f"input tap {x} {y}")
                time.sleep(1.5)
                if self.device(focused=True).exists:
                    logger.info("通过adb shell命令，搜索框已获得焦点")
                    search_clicked = True
            except Exception as e:
                logger.warning(f"使用adb shell命令失败: {str(e)}")
        
        # 检查是否成功点击了搜索框
        if not search_clicked:
            logger.warning("所有方法都未能使搜索框获得焦点，尝试直接输入文本")
            # 尝试直接点击屏幕顶部区域
            self.device.click(self.screen_width * 0.5, self.screen_height * 0.1)
            time.sleep(1.5)
        input("按回车继续执行步骤4...")
        
        # 4. 输入"应用和服务"
        logger.info("步骤4: 输入'应用和服务'")
        try:
            # 先清除可能存在的文本
            self.device.clear_text()
            time.sleep(0.5)
            
            # 输入搜索文本
            self.device.send_keys("应用和服务")
            time.sleep(1)
            
            # 按下回车键执行搜索
            self.device.press("enter")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"输入文本失败: {str(e)}，尝试使用adb shell命令")
            try:
                self.device.shell("input text '应用和服务'")
                time.sleep(1)
                self.device.shell("input keyevent 66")  # 回车键
                time.sleep(2)
            except Exception as e2:
                logger.error(f"使用adb shell命令输入文本也失败: {str(e2)}")
        input("按回车继续执行步骤5...")
        
        # 5. 点击搜索结果进入应用和服务界面
        logger.info("步骤5: 点击搜索结果进入应用和服务界面")
        logger.info("使用坐标点击'应用和服务'")
        # 使用更精确的坐标点击应用和服务选项
        self.device.click(self.screen_width * 0.196, self.screen_height * 0.163)
        time.sleep(3)  # 等待3秒确保界面加载完成
        
        # 6. 点击应用管理选项
        logger.info("步骤6: 点击'应用管理'选项")
        app_mgmt = self.device(text="应用管理")
        if app_mgmt.exists:
            logger.info("找到'应用管理'选项，点击")
            app_mgmt.click()
        else:
            logger.info("未找到'应用管理'，尝试使用坐标点击")
            # 使用更精确的坐标点击应用管理选项
            self.device.click(self.screen_width * 0.196, self.screen_height * 0.163)
        time.sleep(2)
        input("按回车继续执行步骤7...")
        
        # 7. 点击搜索框（搜索应用）
        logger.info("步骤7: 点击'搜索应用'框")
        # 由于clickable为false，尝试多种方法点击搜索框
        
        # 方法1: 尝试使用父元素点击
        logger.info("尝试方法1: 使用父元素点击搜索框")
        search_parent = self.device(resourceId="android:id/search_edit_frame")
        if search_parent.exists:
            logger.info("找到搜索框父元素")
            search_parent.click()
            time.sleep(1.5)
        
        # 方法2: 尝试使用文本定位
        if not self.device(focused=True).exists:
            logger.info("尝试方法2: 使用文本定位搜索框")
            search_text = self.device(text="搜索应用")
            if search_text.exists:
                logger.info("找到'搜索应用'文本")
                search_text.click()
                time.sleep(1.5)
        
        # 方法3: 尝试使用精确坐标点击
        if not self.device(focused=True).exists:
            logger.info("尝试方法3: 使用精确坐标点击搜索框")
            # 使用更精确的坐标
            self.device.click(self.screen_width * 0.167, self.screen_height * 0.155)
            time.sleep(1.5)
        
        # 方法4: 尝试使用XPath定位
        if not self.device(focused=True).exists:
            logger.info("尝试方法4: 使用XPath定位搜索框")
            try:
                self.device.xpath('//*[@resource-id="android:id/search_edit_frame"]').click()
                time.sleep(1.5)
            except Exception as e:
                logger.warning(f"XPath点击失败: {str(e)}")
        
        # 方法5: 尝试使用tap_center方法
        if not self.device(focused=True).exists:
            logger.info("尝试方法5: 使用tap_center方法")
            try:
                search_element = self.device(resourceId="android:id/search_edit_frame")
                if search_element.exists:
                    bounds = search_element.info.get('bounds', {})
                    center_x = (bounds.get('left', 0) + bounds.get('right', 0)) // 2
                    center_y = (bounds.get('top', 0) + bounds.get('bottom', 0)) // 2
                    logger.info(f"计算的中心点: ({center_x}, {center_y})")
                    self.device.click(center_x, center_y)
                    time.sleep(1.5)
            except Exception as e:
                logger.warning(f"tap_center方法失败: {str(e)}")
        
        # 验证搜索框是否获得焦点
        if self.device(focused=True).exists:
            logger.info("搜索框已获得焦点")
        else:
            logger.warning("所有方法都未能使搜索框获得焦点，尝试直接输入文本")
            # 尝试直接点击屏幕顶部区域
            self.device.click(self.screen_width * 0.5, self.screen_height * 0.1)
            time.sleep(1.5)
        input("按回车继续执行步骤8...")
        
        # 8. 输入"快应用中心"
        logger.info("步骤8: 输入'快应用中心'")
        # 先清除可能存在的文本
        self.device.clear_text()
        time.sleep(0.5)
        
        # 输入搜索文本
        self.device.send_keys("快应用中心")
        time.sleep(1)
        
        # 按下回车键执行搜索
        self.device.press("enter")
        time.sleep(2)
        input("按回车继续执行步骤9...")
        
        # 9. 直接使用intent跳转到快应用中心详情页面
        logger.info("步骤9: 使用intent跳转到快应用中心详情页面")
        try:
            # 执行intent跳转
            logger.info("执行intent命令: am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.huawei.fastapp")
            self.device.shell("am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.huawei.fastapp")
            time.sleep(3)
            
            # 检查是否成功进入详情页面
            if self.device(text="存储").exists or self.device(text="强行停止").exists or self.device(text="应用信息").exists:
                logger.info("成功使用intent进入快应用中心详情页面")
            else:
                # 如果intent方式失败，尝试点击搜索结果
                logger.warning("intent跳转可能失败，尝试点击搜索结果")
                
                # 尝试点击搜索结果
                quick_app = self.device(text="快应用中心")
                if quick_app.exists:
                    logger.info("找到'快应用中心'文本，尝试点击")
                    quick_app.click()
                    time.sleep(3)
                else:
                    # 如果找不到文本，尝试点击可能的位置
                    logger.warning("未找到'快应用中心'文本，尝试点击可能的位置")
                    self.device.click(self.screen_width * 0.5, self.screen_height * 0.38)
                    time.sleep(3)
        except Exception as e:
            logger.warning(f"使用intent跳转失败: {str(e)}，尝试常规点击方法")
            
            # 尝试点击搜索结果
            quick_app = self.device(text="快应用中心")
            if quick_app.exists:
                logger.info("找到'快应用中心'文本，尝试点击")
                quick_app.click()
                time.sleep(3)
            else:
                # 如果找不到文本，尝试点击可能的位置
                logger.warning("未找到'快应用中心'文本，尝试点击可能的位置")
                self.device.click(self.screen_width * 0.5, self.screen_height * 0.38)
                time.sleep(3)
        input("按回车继续执行步骤10...")
        
        # 10. 向下滑动到最底部
        logger.info("步骤10: 向下滑动查找'存储'")
        # 多次滑动以确保到达底部
        for i in range(4):  # 增加滑动次数
            logger.info(f"第{i+1}次滑动")
            self.device.swipe(self.screen_width * 0.5, self.screen_height * 0.8, 
                             self.screen_width * 0.5, self.screen_height * 0.2)
            time.sleep(1.5)  # 增加等待时间
            
            # 检查是否找到"存储"
            if self.device(text="存储").exists:
                logger.info("找到'存储'选项")
                break
            
            # 如果是最后一次滑动还没找到，记录日志
            if i == 3 and not self.device(text="存储").exists:
                logger.warning("多次滑动后仍未找到'存储'选项")
        input("按回车继续执行步骤11...")
        
        # 11. 点击存储
        logger.info("步骤11: 点击'存储'")
        storage = self.device(text="存储", resourceId="android:id/title")
        if storage.exists:
            storage.click()
        else:
            logger.warning("未找到'存储'，尝试使用文本搜索")
            self.device(text="存储").click()
        time.sleep(1)
        input("按回车继续执行步骤12...")
        
        # 12. 点击删除数据
        logger.info("步骤12: 点击'删除数据'")
        clear_data = self.device(text="删除数据", resourceId="com.android.settings:id/button_2")
        if clear_data.exists:
            clear_data.click()
        else:
            logger.warning("未找到'删除数据'，尝试使用文本搜索")
            self.device(text="删除数据").click()
        time.sleep(1)
        input("按回车继续执行步骤13...")
        
        # 13. 点击确定
        logger.info("步骤13: 点击确认对话框中的'确定'")
        confirm = self.device(text="确定", resourceId="android:id/button1")
        if confirm.exists:
            confirm.click()
        else:
            logger.warning("未找到'确定'按钮，尝试使用文本搜索")
            self.device(text="确定").click()
        time.sleep(2)
        
        logger.info("快应用中心数据清理完成")
        return True

    def clear_all_apps(self):
        """清空手机里的全部应用（简化版）"""
        logger.info("开始清空手机里的全部应用...")
        
        # 1. 先强制停止快应用中心和相关应用
        logger.info("步骤1: 强制停止快应用中心和相关应用")
        try:
            # 强制停止快应用中心
            self.device.shell("am force-stop com.huawei.fastapp")
            logger.info("已强制停止快应用中心")
            time.sleep(1)
            
            # 强制停止快应用UI进程
            self.device.shell("am force-stop com.huawei.fastapp:ui")
            logger.info("已强制停止快应用UI进程")
            time.sleep(1)
        except Exception as e:
            logger.warning(f"强制停止应用时出错: {str(e)}，继续执行后续步骤")
        
        # 2. 按Home键回到桌面
        logger.info("步骤2: 按Home键回到桌面")
        self.device.press("home")
        time.sleep(1)
        
        # 3. 打开最近任务列表
        logger.info("步骤3: 打开最近任务列表")
        self.device.press("recent")
        time.sleep(2)
        
        # 4. 直接点击底部中间位置，不检查任务卡片是否存在
        logger.info("步骤4: 直接点击底部中间位置清除应用")
        center_x = int(self.screen_width * 0.5)
        center_y = int(self.screen_height * 0.9)
        logger.info(f"点击坐标: ({center_x}, {center_y})")
        self.device.click(center_x, center_y)
        
        # 5. 等待1秒
        logger.info("等待1秒...")
        time.sleep(1)
        
        # 6. 返回桌面
        logger.info("返回桌面")
        self.device.press("home")
        
        # 7. 直接返回成功
        logger.info("点击底部中间位置完成，清空手机里的全部应用完成")
        return True


def run_test():
    """运行完整的测试序列"""
    try:
        logger.info("开始快应用测试序列")
        tester = QuickAppTester(device_serial=DEVICE_SERIAL)
        
        # 确保屏幕处于唤醒和解锁状态
        logger.info("===== 检查并确保屏幕处于唤醒状态 =====")
        screen_result = tester.ensure_screen_on()
        if not screen_result:
            logger.error("无法确保屏幕处于唤醒状态，测试终止")
            return False
        
        # 执行流程1: 清除快应用中心数据
        logger.info("===== 开始执行流程1: 通过设置清理快应用中心数据 =====")
        result1 = tester.clear_quick_app_center_data()
        logger.info(f"流程1完成。结果: {'成功' if result1 else '失败'}")
        
        # 短暂等待，确保两个流程之间有足够的间隔
        time.sleep(3)
        
        # 执行流程2: 通过应用市场管理快应用
        logger.info("===== 开始执行流程2: 通过应用市场管理快应用 =====")
        result2 = tester.manage_quick_apps_via_market()
        logger.info(f"流程2完成。结果: {'成功' if result2 else '失败'}")
        
        # 短暂等待，确保两个流程之间有足够的间隔
        time.sleep(3)
        
        # 执行流程3: 在快应用中心搜索并打开"买乐多"
        logger.info("===== 开始执行流程3: 在快应用中心搜索并打开'买乐多' =====")
        result3 = tester.search_and_open_quick_app()
        logger.info(f"流程3完成。结果: {'成功' if result3['防侧滑'] and result3['拉回'] else '失败'}")
        
        # 执行流程4: 清空手机里的全部应用
        logger.info("===== 开始执行流程4: 清空手机里的全部应用 =====")
        result4 = tester.clear_all_apps()
        logger.info(f"流程4完成。结果: {'成功' if result4 else '失败'}")
        
        # 总体结果取决于所有流程是否都成功
        final_result = result1 and result2 and result3['防侧滑'] and result3['拉回'] and result4
        logger.info(f"测试完成。总体结果: {'成功' if final_result else '失败'}")
        
        # 记录执行时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"本次测试执行时间: {current_time}")
        logger.info("下一次测试将在30分钟后执行")
        
        # 设置表情符号和状态
        防侧滑_success = result3['防侧滑']
        拉回_success = result3['拉回']
        
        # 设置状态图标和文字
        防侧滑_icon = "✅" if 防侧滑_success else "❌"
        拉回_icon = "✅" if 拉回_success else "❌"
        
        # 构建标题
        title = "快应用防侧滑与拉回测试"
        
        # 判断是否需要@所有人
        need_mention = not 防侧滑_success or not 拉回_success
        
        # 上传截图到Stardots图床
        image_urls = []
        try:
            # 查找最新的侧滑后截图
            swipe_screenshots = [file for file in os.listdir(SCREENSHOTS_DIR) if file.startswith("after_10_swipes_") and file.endswith(".png")]
            if swipe_screenshots:
                # 按文件名排序，取最新的一个
                latest_swipe_screenshot = sorted(swipe_screenshots)[-1]
                swipe_screenshot = f"{SCREENSHOTS_DIR}/{latest_swipe_screenshot}"
                if os.path.exists(swipe_screenshot):
                    swipe_image_url = upload_image_to_stardots(swipe_screenshot)
                    if swipe_image_url:
                        image_urls.append(swipe_image_url)
                        logger.info(f"侧滑后截图上传成功: {swipe_image_url}")
            
            # 查找最新的前台检测后截图
            foreground_screenshots = [file for file in os.listdir(SCREENSHOTS_DIR) if file.startswith("after_foreground_check_") and file.endswith(".png")]
            if foreground_screenshots:
                # 按文件名排序，取最新的一个
                latest_foreground_screenshot = sorted(foreground_screenshots)[-1]
                foreground_screenshot = f"{SCREENSHOTS_DIR}/{latest_foreground_screenshot}"
                if os.path.exists(foreground_screenshot):
                    foreground_image_url = upload_image_to_stardots(foreground_screenshot)
                    if foreground_image_url:
                        image_urls.append(foreground_image_url)
                        logger.info(f"前台检测后截图上传成功: {foreground_image_url}")
        except Exception as e:
            logger.error(f"上传截图时出错: {str(e)}")
        
        # 发送飞书通知，如果测试失败则@所有人
        if need_mention:
            # 构建简洁的失败通知内容
            if not 拉回_success and 防侧滑_success:
                content = "**拉回测试失败，请及时处理！**\n\n**防侧滑**: ✅ **成功**\n\n**拉回**: ❌ **失败**"
            elif not 防侧滑_success and 拉回_success:
                content = "**防侧滑测试失败，请及时处理！**\n\n**防侧滑**: ❌ **失败**\n\n**拉回**: ✅ **成功**"
            else:
                content = "**防侧滑和拉回测试均失败，请及时处理！**\n\n**防侧滑**: ❌ **失败**\n\n**拉回**: ❌ **失败**"
            
            # 使用卡片消息格式发送并@所有人，包含截图
            send_feishu_notification(title, content, mention_all=True, image_urls=image_urls)
        else:
            # 测试全部成功，使用卡片消息格式发送，包含截图
            content = f"""
**防侧滑**: {防侧滑_icon} **{('成功' if 防侧滑_success else '失败')}**

**拉回**: {拉回_icon} **{('成功' if 拉回_success else '失败')}**
"""
            send_feishu_notification(title, content, image_urls=image_urls)
        
        return final_result
    except Exception as e:
        logger.error(f"测试失败，错误: {str(e)}")
        
        # 发送错误通知并@所有人
        title = "快应用测试异常"
        content = f"**测试过程中发生异常，请及时处理！**\n\n**错误信息**: {str(e)}"
        send_feishu_notification(title, content, mention_all=True)
        
        return False


def main():
    """主函数 - 设置定时任务，每30分钟执行一次测试"""
    logger.info("启动定时测试任务，每30分钟执行一次完整测试流程")
    
    # 立即执行一次测试
    logger.info("立即执行第一次测试")
    run_test()
    
    # 设置定时任务，每30分钟执行一次
    schedule.every(30).minutes.do(run_test)
    
    # 持续运行定时任务
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)  # 短暂休眠，避免CPU占用过高
    except KeyboardInterrupt:
        logger.info("用户中断，定时测试任务已停止")
    except Exception as e:
        logger.error(f"定时任务异常: {str(e)}")
    finally:
        logger.info("定时测试任务已结束")


if __name__ == "__main__":
    main()
