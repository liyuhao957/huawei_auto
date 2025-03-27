#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
录制工具模块 - 处理scrcpy屏幕录制
"""

import subprocess
import time
import os
import signal
import logging
from datetime import datetime

class ScrcpyRecorder:
    """Scrcpy录制器，使用scrcpy进行屏幕录制"""
    
    def __init__(self, videos_dir, logger=None):
        """初始化Scrcpy录制器
        
        Args:
            videos_dir: 视频保存目录
            logger: 日志记录器，如果为None则创建新的logger
        """
        self.logger = logger or logging.getLogger("recording")
        self.videos_dir = videos_dir
        self.recording_process = None
        self.current_video_path = None
        
        # 确保视频目录存在
        os.makedirs(self.videos_dir, exist_ok=True)
        
    def check_device_connected(self):
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
            self.logger.error(f"检查设备连接时出错: {str(e)}")
            return False
        
    def kill_scrcpy_processes(self):
        """优雅地终止所有正在运行的scrcpy进程
        
        Returns:
            bool: 是否成功终止所有进程
        """
        try:
            self.logger.info("尝试优雅地终止所有scrcpy进程")
            
            # 直接使用信号终止scrcpy进程
            
            # 尝试使用pkill发送SIGINT信号 (等同于Ctrl+C)
            if os.name == 'nt':  # Windows
                # Windows没有SIGINT的直接方式，尝试taskkill /F
                self.logger.info("Windows平台：使用taskkill")
                subprocess.run("taskkill /IM scrcpy.exe", shell=True)  # 先不用/F，尝试优雅关闭
                time.sleep(2)
            else:  # Linux/Mac
                self.logger.info("Linux/Mac平台：先发送SIGINT信号")
                subprocess.run("pkill -2 scrcpy", shell=True)  # -2表示SIGINT
                time.sleep(3)  # 给进程3秒钟处理SIGINT
                
                # 检查是否还有进程存在
                check = subprocess.run("pgrep scrcpy", shell=True, capture_output=True)
                if check.returncode == 0:  # 有进程存在
                    self.logger.info("SIGINT未能终止全部进程，尝试SIGTERM")
                    subprocess.run("pkill scrcpy", shell=True)  # 默认是SIGTERM
                    time.sleep(2)
            
            # 3. 强制终止残留进程 - 最后手段
            if os.name == 'nt':  # Windows
                subprocess.run("taskkill /F /IM scrcpy.exe", shell=True)
            else:  # Linux/Mac
                # 检查是否还有残留进程
                check = subprocess.run("pgrep scrcpy", shell=True, capture_output=True)
                if check.returncode == 0:  # 有进程存在
                    self.logger.warning("使用SIGKILL强制终止残留进程")
                    subprocess.run("pkill -9 scrcpy", shell=True)
            
            # 4. 确保scrcpy-server也被终止，但不要发送HOME键
            try:
                subprocess.run("adb shell pkill scrcpy-server", shell=True, timeout=2)
            except Exception:
                pass
            
            # 5. 给进程一些时间完全退出
            time.sleep(2)
            
            self.logger.info("所有scrcpy进程已终止")
            return True
        except Exception as e:
            self.logger.warning(f"终止scrcpy进程出错: {str(e)}")
            return False
            
    def start_recording(self, filename=None):
        """
        开始使用scrcpy录制设备屏幕
        
        Args:
            filename: 输出文件名，不包含扩展名。如果为None，则使用时间戳
                
        Returns:
            str: 视频文件路径
        """
        # 确保之前的录制已停止
        self.kill_scrcpy_processes()
        
        # 确保设备连接正常
        try:
            self.logger.info("检查设备连接状态...")
            check_result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=5)
            device_output = check_result.stdout.strip()
            
            if "device" not in device_output or len(device_output.splitlines()) <= 1:
                self.logger.error("未检测到已连接的设备，无法开始录制")
                return None
            
            self.logger.info(f"设备连接正常: {device_output}")
        except Exception as e:
            self.logger.error(f"检查设备连接时出错: {e}")
            return None
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            filename = f"recording_{timestamp}"
        
        # 确保文件名有.mp4后缀
        if not filename.lower().endswith('.mp4'):
            filename += '.mp4'
        
        # 设置完整的输出路径
        output_path = os.path.join(self.videos_dir, filename)
        
        # 如果同名文件已存在，先删除
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                self.logger.info(f"已删除同名的旧文件: {output_path}")
            except Exception as e:
                self.logger.warning(f"删除旧文件时出错: {e}")
        
        self.current_video_path = output_path
        
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
            "--no-window",           # 完全禁用窗口，避免需要手动点击窗口来终止进程
            "--video-codec=h265",     # 使用H.265编码器(更好的质量)
            "--max-size=720",         # 限制分辨率
            "--max-fps=15",           # 帧率15fps提高稳定性
            "--time-limit=120",       # 限制录制时间为120秒(避免无法正常结束)
            "--video-bit-rate=8M",    # 使用8Mbps的比特率
            "--record-format=mp4",    # 确保使用mp4格式
            # 移除 "--power-off-on-close" 参数，避免录制结束时设备息屏
            "--no-audio"              # 禁用音频
        ]
        
        self.logger.info(f"开始录制，输出文件: {output_path}")
        self.logger.info(f"使用命令: {' '.join(cmd)}")
        
        # 启动录制进程
        try:
            self.recording_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 检查进程是否立即退出
            time.sleep(2)
            if self.recording_process.poll() is not None:
                stderr = self.recording_process.stderr.read() if self.recording_process.stderr else ""
                self.logger.error(f"scrcpy进程立即退出，退出码: {self.recording_process.returncode}")
                if stderr:
                    self.logger.error(f"错误输出: {stderr}")
                    # 尝试解析常见的错误，如参数问题
                    if "--no-display" in stderr and "--no-window" in cmd:
                        self.logger.error("检测到参数不兼容：您的scrcpy版本可能不支持--no-display，尝试使用--no-window")
                    elif "unrecognized option" in stderr:
                        self.logger.error("检测到不支持的选项，可能需要更新scrcpy或调整参数")
                
                self.recording_process = None
                self.current_video_path = None
                return None
                
            self.logger.info("录制已开始...")
            
            # 额外检查：确认录制进程是否稳定运行
            time.sleep(3)  # 再等待3秒
            if self.recording_process.poll() is not None:
                self.logger.error(f"scrcpy进程开始后不久退出，退出码: {self.recording_process.returncode}")
                stderr = self.recording_process.stderr.read() if self.recording_process.stderr else ""
                if stderr:
                    self.logger.error(f"错误输出: {stderr}")
                self.recording_process = None
                self.current_video_path = None
                return None
                
            # 开启一个后台线程监控录制状态
            def check_recording_status():
                start_time = time.time()
                while self.recording_process and self.recording_process.poll() is None:
                    elapsed = time.time() - start_time
                    # 每30秒记录一次状态
                    if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                        self.logger.info(f"录制进行中，已录制约 {int(elapsed)} 秒")
                    time.sleep(1)
                    
            import threading
            monitor_thread = threading.Thread(target=check_recording_status)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            self.logger.info("录制状态监控已启动")
            return output_path
        except Exception as e:
            self.logger.error(f"启动录制时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            if self.recording_process is not None and self.recording_process.poll() is None:
                self.logger.info("尝试清理失败的录制进程...")
                self.stop_recording(upload_func=None)
            return None
            
    def stop_recording(self, upload_func=None):
        """
        停止scrcpy录制并处理录制的视频
        
        Args:
            upload_func: 上传函数，接受文件路径参数并返回URL
        
        Returns:
            tuple: (视频文件路径, 视频URL)，如果失败则返回(None, None)
        """
        video_url = None
        
        if self.recording_process is None or self.current_video_path is None:
            self.logger.warning("没有正在进行的录制进程，无法停止")
            return None, None
        
        self.logger.info("停止录制...")
        
        try:
            # 检查进程是否已经退出
            if self.recording_process.poll() is not None:
                self.logger.info(f"录制进程已经退出，退出码: {self.recording_process.returncode}")
                stderr = self.recording_process.stderr.read() if self.recording_process.stderr else ""
                if stderr:
                    self.logger.info(f"stderr输出: {stderr}")
            else:
                # 直接使用SIGINT信号(等同于按Ctrl+C) - 这是最优雅的方式，允许scrcpy完成MP4文件的正确写入
                self.logger.info("发送SIGINT信号 (Ctrl+C)")
                self.recording_process.send_signal(signal.SIGINT)
                
                # 增加等待时间，给予更多时间处理SIGINT
                self.logger.info("等待SIGINT生效，这可能需要10-30秒...")
                max_wait = 30  # 从15秒增加到30秒
                wait_interval = 1
                
                for i in range(max_wait):
                    if self.recording_process.poll() is not None:
                        self.logger.info(f"进程在接收SIGINT后成功退出，用时{i+1}秒")
                        break
                    self.logger.info(f"等待进程退出... ({i+1}/{max_wait})")
                    time.sleep(wait_interval)
                
                # 如果SIGINT未能终止进程，尝试通过ADB命令停止server
                if self.recording_process.poll() is None:
                    self.logger.info("SIGINT未能终止进程，尝试通过ADB停止scrcpy服务端")
                    server_cmds = [
                        "adb shell am force-stop com.genymobile.scrcpy",  # 尝试停止scrcpy应用
                        "adb shell pkill -l 2 scrcpy-server",             # 发送INT信号给服务端
                        "adb shell pkill scrcpy-server"                   # 尝试终止服务端
                    ]
                    
                    for cmd in server_cmds:
                        self.logger.info(f"执行: {cmd}")
                        subprocess.run(cmd, shell=True, timeout=2)
                        time.sleep(2)
                        if self.recording_process.poll() is not None:
                            self.logger.info("服务端停止后，进程成功退出")
                            break
                
                # 6. 如果仍未退出，使用SIGTERM - 更温和的终止信号
                if self.recording_process.poll() is None:
                    self.logger.info("尝试通过SIGTERM终止进程")
                    self.recording_process.terminate()
                    
                    # 给SIGTERM更多时间生效
                    for i in range(10):  # 10秒等待
                        if self.recording_process.poll() is not None:
                            self.logger.info(f"进程在接收SIGTERM后成功退出，用时{i+1}秒")
                            break
                        self.logger.info(f"等待SIGTERM生效... ({i+1}/10)")
                        time.sleep(1)
                    
                    # 7. 仅在万不得已的情况下使用SIGKILL，因为它会导致录制文件损坏
                    if self.recording_process.poll() is None:
                        self.logger.warning("所有温和的尝试都失败，不得不使用SIGKILL强制终止进程")
                        self.logger.warning("这可能导致录制文件损坏(moov atom丢失)，录制可能无法播放")
                        self.recording_process.kill()
                        time.sleep(2)
                
                # 获取退出状态
                exit_code = self.recording_process.wait(timeout=1)
                self.logger.info(f"录制进程已退出，退出码: {exit_code}")
                
                stderr = self.recording_process.stderr.read() if self.recording_process.stderr else ""
                if stderr:
                    self.logger.info(f"stderr输出: {stderr}")
            
            # 8. 增加更长的等待时间，确保文件系统缓存刷新和文件写入完成
            self.logger.info("等待10秒确保文件写入完成...")
            time.sleep(10)  # 从5秒增加到10秒
            
            # 9. 检查文件是否存在及其完整性
            if os.path.exists(self.current_video_path):
                file_size = os.path.getsize(self.current_video_path) / (1024 * 1024)  # MB
                self.logger.info(f"录制文件: {self.current_video_path} (大小: {file_size:.2f}MB)")
                
                # 10. 使用ffmpeg快速检查文件完整性，如果不完整再尝试修复
                self.logger.info("预检查文件完整性...")
                probe_cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    self.current_video_path
                ]
                
                try:
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
                    if probe_result.returncode == 0:
                        duration = probe_result.stdout.strip()
                        self.logger.info(f"录制文件完整，时长: {duration}秒，无需修复")
                    else:
                        self.logger.warning(f"文件可能损坏: {probe_result.stderr}")
                        # 尝试使用ffmpeg修复
                        self.fix_mp4_file(self.current_video_path)
                except Exception as e:
                    self.logger.warning(f"预检查文件完整性时出错: {e}")
                    # 继续尝试修复
                    self.fix_mp4_file(self.current_video_path)
                
                # 11. 如果需要上传到Telegram
                if upload_func:
                    self.logger.info("上传视频...")
                    video_url = upload_func(self.current_video_path)
                    if video_url:
                        self.logger.info(f"视频已上传，URL: {video_url}")
                    else:
                        self.logger.warning("视频上传失败")
                
                return self.current_video_path, video_url
            else:
                self.logger.error(f"录制文件不存在: {self.current_video_path}")
                return None, None
        
        except Exception as e:
            self.logger.error(f"停止录制时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return None, None
        finally:
            # 确保杀死所有scrcpy进程，但在这之前先尝试优雅地关闭它们
            self.kill_scrcpy_processes()
            self.recording_process = None
            
    def fix_mp4_file(self, file_path):
        """尝试修复MP4文件
        
        Args:
            file_path: 要修复的MP4文件路径
            
        Returns:
            bool: 如果成功修复则返回True，否则返回False
        """
        try:
            # 检查ffmpeg是否可用
            if not self.check_ffmpeg_available():
                self.logger.warning("ffmpeg不可用，跳过文件修复")
                return False
            
            self.logger.info("使用ffmpeg分析文件")
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
                self.logger.info(f"文件正常，时长: {duration}秒")
                
                # 添加faststart标记
                fixed_path = f"{file_path}.fixed.mp4"
                self.logger.info("优化文件")
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
                    self.logger.info("文件优化完成")
                    return True
            else:
                # 文件损坏，尝试修复
                self.logger.warning(f"文件可能损坏: {probe_result.stderr}")
                
                # 尝试重编码
                fixed_path = f"{file_path}.fixed.mp4"
                self.logger.info("尝试重编码修复文件")
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
                    self.logger.info("文件修复完成")
                    
                    # 再次检查文件是否可用
                    check_result = subprocess.run([
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        file_path
                    ], capture_output=True, text=True)
                    
                    if check_result.returncode == 0:
                        duration = check_result.stdout.strip()
                        self.logger.info(f"修复成功，文件时长: {duration}秒")
                        return True
                    else:
                        self.logger.warning(f"修复后文件仍有问题: {check_result.stderr}")
                        return False
                else:
                    self.logger.error(f"修复失败: {result.stderr}")
                    return False
        
        except Exception as e:
            self.logger.error(f"修复文件时出错: {e}")
            return False
            
    def check_ffmpeg_available(self):
        """
        检查系统中是否安装了ffmpeg
        
        Returns:
            bool: 如果ffmpeg可用则返回True，否则返回False
        """
        try:
            # 检查ffmpeg版本
            result = subprocess.run(['ffmpeg', '-version'], 
                                   capture_output=True, 
                                   text=True, 
                                   check=True)
            self.logger.info(f"检测到ffmpeg: {result.stdout.splitlines()[0]}")
            return True
        except Exception as e:
            self.logger.warning(f"ffmpeg检测失败: {str(e)}")
            return False
            
    def test_recording(self, duration=15):
        """
        测试scrcpy录制功能
        
        Args:
            duration: 录制时长(秒)，0表示无限制(需要手动中断)
            
        Returns:
            tuple: (成功状态, 修复后的视频路径)
        """
        self.logger.info("="*50)
        self.logger.info("开始测试scrcpy录制功能")
        self.logger.info("="*50)
        
        # 确保设备已连接
        if not self.check_device_connected():
            self.logger.error("未找到已连接的设备，无法进行录制测试")
            return False, None
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_scrcpy_{timestamp}.mp4"
        
        # 开始录制
        self.logger.info(f"开始录制，时长: {duration if duration > 0 else '无限制'} 秒")
        video_path = self.start_recording(filename)
        
        if not video_path:
            self.logger.error("启动录制失败")
            return False, None
        
        try:
            if duration > 0:
                # 等待指定时长
                self.logger.info(f"录制中... {duration}秒")
                time.sleep(duration)
            else:
                # 无限录制，等待用户中断
                self.logger.info("无限录制中，按Ctrl+C停止...")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("用户中断，停止录制")
        finally:
            # 停止录制
            self.logger.info("停止录制")
            video_path, _ = self.stop_recording()
            
            if not video_path or not os.path.exists(video_path):
                self.logger.error("录制失败，未生成视频文件")
                return False, None
            
            # 获取录制文件信息
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            self.logger.info(f"录制完成: {video_path} (大小: {file_size_mb:.2f}MB)")
            
            # 使用ffmpeg修复视频
            self.logger.info("尝试使用ffmpeg修复视频...")
            
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
                
                self.logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, check=False, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(fixed_video_path):
                    fixed_size_mb = os.path.getsize(fixed_video_path) / (1024 * 1024)
                    self.logger.info(f"视频修复成功: {fixed_video_path} (大小: {fixed_size_mb:.2f}MB)")
                    self.logger.info("="*50)
                    self.logger.info("测试完成，scrcpy录制功能正常")
                    self.logger.info("="*50)
                    return True, fixed_video_path
                else:
                    self.logger.error(f"视频修复失败: {result.stderr}")
                    self.logger.info("="*50)
                    self.logger.info("测试完成，原始视频可用但修复失败")
                    self.logger.info("="*50)
                    return True, video_path
            except Exception as e:
                self.logger.error(f"视频修复过程出错: {str(e)}")
                self.logger.info("="*50)
                self.logger.info("测试完成，原始视频可用但修复出错")
                self.logger.info("="*50)
                return True, video_path
        
        return False, None