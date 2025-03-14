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
from datetime import datetime

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

class QuickAppTester:
    """主类，用于执行快应用测试"""
    
    def __init__(self, device_serial=None):
        """初始化测试器"""
        logger.info("初始化QuickAppTester")
        self.device = u2.connect(device_serial)  # 连接设备
        self.screen_width, self.screen_height = self.device.window_size()
        logger.info(f"设备屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
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
        
        # 滑动10次后立即截图
        logger.info("滑动10次后立即截图")
        self.take_screenshot("after_10_swipes")
        
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
        
        # 检测完快应用是否在前台运行后立即截图
        logger.info("检测完快应用是否在前台运行后立即截图")
        self.take_screenshot("after_foreground_check")
        
        logger.info("流程3执行完成")
        return True
        
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
                if bounds:
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
        
        # 5. 点击搜索结果"应用和服务"
        logger.info("步骤5: 点击搜索结果'应用和服务'")
        app_service = self.device(text="应用和服务")
        if app_service.exists:
            app_service.click()
        else:
            logger.warning("未找到'应用和服务'，尝试点击第一个搜索结果")
            self.device.click(self.screen_width * 0.5, self.screen_height * 0.25)
        time.sleep(2)
        
        # 6. 点击"应用管理"
        logger.info("步骤6: 点击'应用管理'")
        # 由于clickable为false，尝试多种方法
        app_mgmt = self.device(text="应用管理")
        if app_mgmt.exists:
            app_mgmt.click()
        else:
            logger.warning("未找到'应用管理'，尝试使用坐标点击")
            self.device.click(self.screen_width * 0.196, self.screen_height * 0.163)
        time.sleep(2)
        
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
        
        # 11. 点击存储
        logger.info("步骤11: 点击'存储'")
        storage = self.device(text="存储", resourceId="android:id/title")
        if storage.exists:
            storage.click()
        else:
            logger.warning("未找到'存储'，尝试使用文本搜索")
            self.device(text="存储").click()
        time.sleep(1)
        
        # 12. 点击删除数据
        logger.info("步骤12: 点击'删除数据'")
        clear_data = self.device(text="删除数据", resourceId="com.android.settings:id/button_2")
        if clear_data.exists:
            clear_data.click()
        else:
            logger.warning("未找到'删除数据'，尝试使用文本搜索")
            self.device(text="删除数据").click()
        time.sleep(1)
        
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


def run_test():
    """运行完整的测试序列"""
    try:
        logger.info("开始快应用测试序列")
        tester = QuickAppTester(device_serial=DEVICE_SERIAL)
        
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
        logger.info(f"流程3完成。结果: {'成功' if result3 else '失败'}")
        
        # 总体结果取决于三个流程是否都成功
        final_result = result1 and result2 and result3
        logger.info(f"测试完成。总体结果: {'成功' if final_result else '失败'}")
        return final_result
    except Exception as e:
        logger.error(f"测试失败，错误: {str(e)}")
        return False


def main():
    """主函数"""
    run_test()


if __name__ == "__main__":
    main()
