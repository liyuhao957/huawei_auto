#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通知工具模块 - 处理Telegram上传和飞书通知
"""

import subprocess
import time
import os
import requests
import json
import hashlib
import base64
import hmac
import logging
from datetime import datetime

class NotificationManager:
    """通知管理器，处理媒体上传和消息通知"""
    
    def __init__(self, telegram_bot_token=None, telegram_chat_id=None, 
                 feishu_webhook_url=None, feishu_secret=None, logger=None):
        """初始化通知管理器
        
        Args:
            telegram_bot_token: Telegram机器人Token
            telegram_chat_id: Telegram聊天ID
            feishu_webhook_url: 飞书Webhook URL
            feishu_secret: 飞书签名密钥
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.logger = logger or logging.getLogger("notification")
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.feishu_webhook_url = feishu_webhook_url
        self.feishu_secret = feishu_secret

    def upload_to_telegram(self, file_path):
        """
        上传文件(图片或视频)到Telegram
        
        Args:
            file_path: 文件路径
        
        Returns:
            str: 上传成功返回文件URL，失败返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        if not self.telegram_bot_token or not self.telegram_chat_id:
            self.logger.warning("Telegram配置不完整，无法上传")
            return None
        
        try:
            self.logger.info(f"开始上传文件到Telegram: {file_path}")
            
            # 判断是图片还是视频
            file_ext = os.path.splitext(file_path)[1].lower()
            is_video = file_ext in ['.mp4', '.avi', '.mov', '.3gp']
            
            # 构建API URL
            api_method = 'sendVideo' if is_video else 'sendPhoto'
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/{api_method}"
            
            # 准备请求参数
            param_name = 'video' if is_video else 'photo'
            
            with open(file_path, 'rb') as file:
                files = {param_name: file}
                data = {'chat_id': self.telegram_chat_id}
                
                # 发送POST请求
                self.logger.info(f"发送请求到 {api_method}...")
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
                    file_path_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/getFile?file_id={file_id}"
                    file_path_response = requests.get(file_path_url)
                    
                    if file_path_response.status_code == 200:
                        file_path_result = file_path_response.json()
                        if file_path_result.get("ok"):
                            file_path = file_path_result["result"]["file_path"]
                            # 构建下载URL
                            download_url = f"https://api.telegram.org/file/bot{self.telegram_bot_token}/{file_path}"
                            self.logger.info(f"文件上传成功! 下载URL: {download_url}")
                            return download_url
                
                self.logger.warning("文件上传成功，但无法获取URL")
                return None
            else:
                self.logger.warning(f"文件上传请求失败，状态码: {response.status_code}, 响应内容: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"上传文件到Telegram时出错: {str(e)}")
            
            # 打印更详细的错误信息以便调试
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            
            return None

    def send_feishu_notification(self, title, content, mention_user=None, mention_all=False, image_urls=None):
        """
        发送飞书机器人通知
        
        Args:
            title: 通知标题
            content: 通知内容
            mention_user: 要@的用户ID，如果为None则不@任何人
            mention_all: 是否@所有人
            image_urls: 媒体URL列表或带有类型标识的媒体项列表，如果为None则不发送媒体
        
        Returns:
            bool: 是否发送成功
        """
        if not self.feishu_webhook_url or self.feishu_webhook_url == "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL":
            self.logger.warning("飞书机器人webhook URL未配置，跳过通知发送")
            return False
        
        try:
            timestamp = str(int(time.time()))
            
            # 使用卡片消息格式
            self.logger.info("使用交互式卡片消息格式发送" + (f"，包含{len(image_urls)}张图片链接" if image_urls and len(image_urls) > 0 else ""))
            
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
            
            # 如果有媒体URL，添加分隔线和媒体链接部分
            if image_urls and len(image_urls) > 0:
                # 添加分隔线
                elements.append({"tag": "hr"})
                
                # 添加媒体标题
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**📷 测试截图和视频：**"
                    }
                })
                
                # 为每个媒体创建按钮
                image_buttons = []
                
                for i, item in enumerate(image_urls):
                    # 检查是否是带有类型标识的媒体项
                    if isinstance(item, dict) and 'url' in item:
                        url = item['url']
                        # 根据类型设置按钮文字
                        if 'type' in item:
                            if item['type'] == 'video':
                                button_text = "视频"
                            elif item['type'] == 'screenshot_swipe':
                                button_text = "防侧滑"
                            elif item['type'] == 'screenshot_home':
                                button_text = "拉回"
                            else:
                                button_text = f"媒体 {i+1}"
                        else:
                            button_text = f"媒体 {i+1}"
                    else:
                        # 向后兼容，如果只是字符串URL
                        url = item
                        button_text = "防侧滑" if i == 0 else "拉回" if i == 1 else "视频"
                    
                    if url:  # 确保URL不为空
                        image_buttons.append({
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": button_text
                            },
                            "type": "primary",
                            "url": url
                        })
                
                # 添加媒体按钮区域
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
            self.logger.info(f"构建的消息结构: {json.dumps(msg, ensure_ascii=False)}")
            
            # 如果设置了签名密钥，则计算签名
            headers = {"Content-Type": "application/json"}
            if self.feishu_secret and self.feishu_secret != "YOUR_SECRET":
                # 计算签名
                string_to_sign = f"{timestamp}\n{self.feishu_secret}"
                sign = base64.b64encode(hmac.new(self.feishu_secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()).decode('utf-8')
                
                # 添加签名到请求头
                headers.update({
                    "timestamp": timestamp,
                    "sign": sign
                })
            
            # 发送请求
            response = requests.post(self.feishu_webhook_url, headers=headers, data=json.dumps(msg))
            
            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    self.logger.info(f"飞书通知发送成功: {title}")
                    return True
                else:
                    self.logger.warning(f"飞书通知发送失败: {result.get('msg')}")
                    # 打印更多响应信息以便调试
                    self.logger.warning(f"响应详情: {json.dumps(result, ensure_ascii=False)}")
                    return False
            else:
                self.logger.warning(f"飞书通知发送失败，状态码: {response.status_code}")
                try:
                    error_info = response.json()
                    self.logger.warning(f"错误详情: {json.dumps(error_info, ensure_ascii=False)}")
                except:
                    self.logger.warning(f"响应内容: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"飞书通知发送异常: {str(e)}")
            # 打印详细的异常堆栈
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False 