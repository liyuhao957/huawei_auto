#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试管理器模块 - 集成所有组件并提供统一的测试接口
"""

import os
import time
import signal
import sys
import argparse
import logging
import schedule
from datetime import datetime

# 导入核心组件
from automation.core.device import DeviceController
from automation.core.screen import ScreenManager
from automation.core.input import InputMethodManager
from automation.core.media import MediaManager

# 导入工具组件
from automation.utils.notification import NotificationManager
from automation.utils.recording import ScrcpyRecorder

# 导入配置模块
from config import (
    configure_logging, SCREEN_WIDTH, SCREEN_HEIGHT, 
    FEISHU_WEBHOOK_URL, FEISHU_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    is_manually_interrupted, manual_interruption_video_url,
    SCHEDULE_INTERVAL_MINUTES, RUN_IMMEDIATELY_ON_START,
    SCREENSHOTS_DIR, VIDEOS_DIR
)

# 全局变量，用于在信号处理和测试流程间共享数据
is_manually_interrupted = False
manual_interruption_video_url = None

class TestManager:
    """测试管理器，集成所有组件并编排测试流程"""
    
    def __init__(self):
        """初始化测试管理器"""
        # 初始化日志
        self.logger = configure_logging()
        self.logger.info("初始化TestManager")
        
        # 初始化核心组件
        self.device = DeviceController(self.logger)
        self.device.set_screen_dimensions(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        self.input_manager = InputMethodManager(self.logger)
        self.screen_manager = ScreenManager(self.device, self.logger)
        self.media_manager = MediaManager(SCREENSHOTS_DIR, VIDEOS_DIR, self.logger)
        
        # 初始化通知管理器
        self.notification_manager = NotificationManager(
            telegram_bot_token=TELEGRAM_BOT_TOKEN,
            telegram_chat_id=TELEGRAM_CHAT_ID,
            feishu_webhook_url=FEISHU_WEBHOOK_URL,
            feishu_secret=FEISHU_SECRET,
            logger=self.logger
        )
        
        # 初始化录制管理器
        self.recorder = ScrcpyRecorder(VIDEOS_DIR, self.logger)
        
        # 确保ADBKeyboard已安装并设置为默认输入法
        self.input_manager.ensure_adbkeyboard_input_method()
        
        # 初始化流程模块
        from flows import ClearAppData, AppMarket, QuickAppTesting, ClearApps
        self._clear_app_data = ClearAppData(self)
        self._app_market = AppMarket(self)
        self._quick_app_testing = QuickAppTesting(self)
        self._clear_apps = ClearApps(self)
        
        # 测试结果数据
        self.swipe_screenshot_path = None
        self.swipe_screenshot_url = None
        self.home_screenshot_path = None
        self.home_screenshot_url = None
        self.test_video_url = None
        
    # 设备操作代理方法
    def tap(self, x, y):
        return self.device.tap(x, y)
        
    def tap_by_percent(self, x_percent, y_percent):
        return self.device.tap_by_percent(x_percent, y_percent)
        
    def swipe(self, start_x, start_y, end_x, end_y, duration=300):
        return self.device.swipe(start_x, start_y, end_x, end_y, duration)
    
    def swipe_by_percent(self, start_x_percent, start_y_percent, end_x_percent, end_y_percent, duration=300):
        return self.device.swipe_by_percent(start_x_percent, start_y_percent, end_x_percent, end_y_percent, duration)
        
    def press_key(self, keycode):
        return self.device.press_key(keycode)
        
    def press_home(self):
        return self.device.press_home()
        
    def press_enter(self):
        return self.device.press_enter()
        
    def press_back(self):
        return self.device.press_back()
        
    def press_recent_apps(self):
        return self.device.press_recent_apps()
        
    def run_shell_command(self, command):
        return self.device.run_shell_command(command)
    
    # 输入法操作代理方法
    def input_text(self, text):
        return self.input_manager.input_text(text)
        
    def restore_original_input_method(self):
        return self.input_manager.restore_original_input_method()
    
    # 屏幕管理代理方法
    def check_screen_state(self):
        return self.screen_manager.check_screen_state()
        
    def wake_screen(self):
        return self.screen_manager.wake_screen()
        
    def simple_unlock(self):
        return self.screen_manager.simple_unlock()
        
    def ensure_screen_on(self):
        return self.screen_manager.ensure_screen_on()
        
    def is_quick_app_running(self, app_name=None):
        return self.screen_manager.is_app_running(app_name)
    
    # 媒体操作代理方法
    def take_screenshot(self, name=None, upload=True):
        upload_func = self.notification_manager.upload_to_telegram if upload else None
        return self.media_manager.take_screenshot(name, upload_func)
        
    def record_screen(self, duration=90, name=None, upload=True):
        upload_func = self.notification_manager.upload_to_telegram if upload else None
        return self.media_manager.record_screen(duration, name, upload_func)
    
    # 录制相关方法
    def start_scrcpy_recording(self, filename=None):
        """开始使用scrcpy录制设备屏幕"""
        return self.recorder.start_recording(filename)
        
    def stop_scrcpy_recording(self, upload_to_tg=True):
        """停止scrcpy录制并处理录制的视频"""
        upload_func = self.notification_manager.upload_to_telegram if upload_to_tg else None
        return self.recorder.stop_recording(upload_func)
    
    # 测试流程方法
    def clear_quick_app_center_data(self):
        """流程1: 清除快应用中心数据"""
        return self._clear_app_data.execute()
        
    def manage_quick_apps_via_market(self):
        """流程2: 通过应用市场管理快应用"""
        return self._app_market.execute()
    
    def search_and_open_quick_app(self):
        """流程3: 搜索并打开快应用进行测试"""
        result = self._quick_app_testing.execute()
        # 保存截图路径以便在其他方法中访问
        self.swipe_screenshot_path = self._quick_app_testing.swipe_screenshot_path
        self.swipe_screenshot_url = self._quick_app_testing.swipe_screenshot_url
        self.home_screenshot_path = self._quick_app_testing.home_screenshot_path
        self.home_screenshot_url = self._quick_app_testing.home_screenshot_url
        return result
    
    def clear_all_apps(self):
        """流程4: 清空手机里的全部应用"""
        return self._clear_apps.execute()
    
    def run_all_flows(self, send_notification=True):
        """执行所有流程
        
        Args:
            send_notification: 是否在执行完成后发送飞书通知
            
        Returns:
            bool: 所有流程是否都成功执行
        """
        # 引用全局变量
        global is_manually_interrupted, manual_interruption_video_url
        
        self.logger.info("开始执行所有流程")
        
        # 用于记录测试截图URL和视频URL
        self.swipe_screenshot_url = None
        self.home_screenshot_url = None
        self.test_video_url = None
        test_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success = False
        error_msg = None
        
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
            # 检查是否手动中断
            if is_manually_interrupted:
                self.logger.info("检测到测试已被手动中断")
                return False
                
            # 确保屏幕处于亮屏状态
            self.logger.info("确保屏幕处于亮屏状态")
            screen_on = self.ensure_screen_on()
            detailed_results["屏幕唤醒"] = screen_on
            
            if not screen_on:
                self.logger.warning("无法确保屏幕处于亮屏状态，测试可能失败")
            
            # 流程1: 清除快应用中心数据
            result1 = self.clear_quick_app_center_data()
            detailed_results["流程1_清除快应用中心数据"] = result1
            
            # 流程2: 通过应用市场管理快应用
            result2 = self.manage_quick_apps_via_market()
            detailed_results["流程2_通过应用市场管理快应用"] = result2
            
            # ======= 流程3开始前启动录制 =======
            video_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_name = f"test_flow_{video_timestamp}"
            self.logger.info(f"开始使用scrcpy录制流程3视频: {video_name}.mp4")
            
            # 启动scrcpy录制，预留3秒稳定缓冲
            video_path = self.start_scrcpy_recording(video_name)
            if not video_path:
                self.logger.warning("无法启动scrcpy录制，将继续测试但没有录制")
            else:
                # 录制启动后，先延迟3秒再开始流程3，确保录制稳定
                self.logger.info("录制已启动，等待3秒确保录制稳定...")
                time.sleep(3)
            
            # 流程3: 搜索并打开快应用进行测试
            # 现在返回的是包含"防侧滑"和"拉回"结果的字典
            result3 = self.search_and_open_quick_app()
            detailed_results["流程3_防侧滑测试"] = result3["防侧滑"]
            detailed_results["流程3_拉回测试"] = result3["拉回"]
            
            # ======= 流程3结束后停止录制 =======
            self.logger.info("流程3完成，停止录制...")
            # 先按Home键回到桌面，以便更好地结束录制
            try:
                self.press_home()
                time.sleep(2)  # 等待一下确保回到桌面
            except Exception:
                pass
                
            video_path, video_url = self.stop_scrcpy_recording(upload_to_tg=True)
            if video_url:
                self.test_video_url = video_url
                self.logger.info(f"流程3视频已上传到Telegram，URL: {video_url}")
            else:
                self.logger.warning("无法获取流程3视频URL，可能是录制或上传失败")
            
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
            
            self.logger.info(f"所有流程执行完成。详细结果: {detailed_results}")
            
            return success
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"执行流程时出错: {error_msg}")
            # 如果在流程3中出错，确保停止录制
            if 'video_path' in locals():
                self.logger.info("错误发生时停止录制...")
                video_path, video_url = self.stop_scrcpy_recording(upload_to_tg=True)
                if video_url:
                    self.test_video_url = video_url
                    self.logger.info(f"错误时捕获的视频已上传，URL: {video_url}")
            
            # 详细的异常信息
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
        
        finally:
            # 恢复原始输入法
            self.restore_original_input_method()
            
            # 检查是否有手动中断上传的视频
            if is_manually_interrupted and manual_interruption_video_url:
                self.test_video_url = manual_interruption_video_url
                self.logger.info(f"使用中断时上传的视频URL: {manual_interruption_video_url}")
            
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
                    
                    # 如果是手动中断
                    if is_manually_interrupted:
                        failure_reasons.append("测试被手动中断")
                    else:
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
                    
                    # 为手动中断准备不同的内容
                    if is_manually_interrupted:
                        content = f"**快应用测试被手动中断！**\n\n" \
                                  f"- 开始时间: {test_start_time}\n" \
                                  f"- 中断时间: {test_end_time}\n" \
                                  f"- 测试设备: 华为设备\n\n" \
                                  f"**注意:** 测试过程被人为中断，未能完成全部测试流程。"
                    else:
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
                
                # 收集所有媒体URL，使用新的带类型标识的媒体项格式
                media_items = []
                if self.swipe_screenshot_url:
                    media_items.append({
                        "type": "screenshot_swipe",
                        "url": self.swipe_screenshot_url
                    })
                if self.home_screenshot_url:
                    media_items.append({
                        "type": "screenshot_home",
                        "url": self.home_screenshot_url
                    })
                if self.test_video_url:
                    media_items.append({
                        "type": "video",
                        "url": self.test_video_url
                    })
                
                # 发送飞书通知
                self.notification_manager.send_feishu_notification(title, content, mention_all=not success, image_urls=media_items)
                
                # 重置中断标志，以便下次测试正常进行
                if is_manually_interrupted:
                    # global声明已在函数开头，此处不需要重复
                    is_manually_interrupted = False
                    manual_interruption_video_url = None


def run_automated_test(no_notification=False, upload_screenshots=False):
    """执行自动化测试
    
    Args:
        no_notification: 是否禁用飞书通知
        upload_screenshots: 是否上传截图到图床
    """
    logger = logging.getLogger("main")
    logger.info("启动快应用ADB测试")
    
    tester = TestManager()
    
    # 确保屏幕处于亮屏状态
    screen_on = tester.ensure_screen_on()
    if not screen_on:
        logger.warning("无法确保屏幕处于亮屏状态，测试可能失败")
    
    # 执行所有流程
    tester.run_all_flows(send_notification=not no_notification)
    
    logger.info("测试完成")


def main():
    """主函数"""
    # 获取日志记录器
    logger = logging.getLogger("main")
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='Huawei快应用ADB自动化测试脚本')
    parser.add_argument('--no-notification', action='store_true', help='禁用飞书通知')
    parser.add_argument('--upload-screenshots', action='store_true', help='上传截图到图床')
    args = parser.parse_args()
    
    # 注册终止处理
    def signal_handler(sig, frame):
        global is_manually_interrupted, manual_interruption_video_url
        
        logger = logging.getLogger("main")
        logger.info("接收到终止信号，正在优雅退出...")
        is_manually_interrupted = True
        
        logger.info("脚本已终止")
        sys.exit(0)
    
    # 注册信号处理程序
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info(f"启动定时任务模式，每{SCHEDULE_INTERVAL_MINUTES}分钟执行一次测试")
    
    # 如果配置为启动时立即执行一次测试
    if RUN_IMMEDIATELY_ON_START:
        run_automated_test(no_notification=args.no_notification, upload_screenshots=args.upload_screenshots)
    
    # 设置定时任务，使用配置的间隔时间
    schedule.every(SCHEDULE_INTERVAL_MINUTES).minutes.do(
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
        logger = logging.getLogger("main")
        recorder = ScrcpyRecorder(VIDEOS_DIR, logger)
        recorder.kill_scrcpy_processes()
        logger.info("定时测试任务已结束")


if __name__ == "__main__":
    main() 