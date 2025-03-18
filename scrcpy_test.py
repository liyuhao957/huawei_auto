#!/usr/bin/env python3
import subprocess
import time
import os
import signal
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
scrcpy_process = None
current_video_path = None
VIDEOS_DIR = "videos"

def start_recording():
    """开始使用scrcpy录制设备屏幕"""
    global scrcpy_process, current_video_path
    
    # 确保视频目录存在
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    
    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_recording_{timestamp}.mp4"
    output_path = os.path.join(VIDEOS_DIR, filename)
    current_video_path = output_path
    
    logger.info("按回车键开始录制...")
    input()
    
    # 构建scrcpy命令 - 使用官方文档推荐的参数
    cmd = [
        "scrcpy",
        f"--record={output_path}",
        "--no-playback",          # 只录制不显示
        "--video-codec=h265",     # 使用H.265编码器(更好的质量)
        "--max-size=720",         # 限制分辨率
        "--max-fps=15",           # 帧率15fps提高稳定性
        "--time-limit=120",       # 限制录制时间为120秒(避免无法正常结束)
        "--video-bit-rate=8M",    # 使用8Mbps的比特率(官方默认推荐)
        "--record-format=mp4",    # 确保使用mp4格式
        "--power-off-on-close",   # 关闭scrcpy时关闭设备屏幕
        "--no-audio"              # 禁用音频
    ]
    
    logger.info(f"开始录制，输出文件: {output_path}")
    logger.info(f"使用命令: {' '.join(cmd)}")
    
    # 启动录制进程
    try:
        scrcpy_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 检查进程是否立即退出
        time.sleep(2)
        if scrcpy_process.poll() is not None:
            logger.error(f"scrcpy进程立即退出，退出码: {scrcpy_process.returncode}")
            stderr = scrcpy_process.stderr.read()
            if stderr:
                logger.error(f"错误输出: {stderr}")
            return None
            
        logger.info("录制已开始...")
        
        # 如果设置了time-limit，等待录制自动完成
        # 否则等待用户按回车键停止
        if "--time-limit=" in " ".join(cmd):
            logger.info("录制将在指定时间后自动停止，或按回车键提前停止...")
            # 使用超时设置，避免永久等待
            max_wait = 130  # 比time-limit多等待10秒
            for i in range(max_wait):
                # 检查进程是否已经退出
                if scrcpy_process.poll() is not None:
                    logger.info("录制已自动完成")
                    break
                    
                # 每秒检查一次用户输入和进程状态
                user_input = input_with_timeout(1)
                if user_input:
                    logger.info("用户请求停止录制")
                    break
                
                # 显示进度
                if i % 10 == 0:
                    logger.info(f"录制中... {i}秒")
        else:
            logger.info("录制已开始，按回车键停止录制...")
            input()
        
        # 停止录制
        stop_recording()
        
        return output_path
    except Exception as e:
        logger.error(f"启动录制时出错: {e}")
        if scrcpy_process is not None and scrcpy_process.poll() is None:
            stop_recording()
        return None

def input_with_timeout(timeout):
    """带超时的输入检查"""
    import select
    import sys
    
    # 只在Unix系统上工作
    if os.name != 'posix':
        time.sleep(timeout)
        return False
        
    # 检查标准输入是否有数据
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        return sys.stdin.readline().strip()
    return False

def stop_recording():
    """停止scrcpy录制并确保文件正确写入"""
    global scrcpy_process, current_video_path
    
    if scrcpy_process is None:
        logger.warning("没有正在运行的录制进程")
        return
    
    logger.info("停止录制...")
    
    try:
        # 检查进程是否已经退出
        if scrcpy_process.poll() is not None:
            logger.info(f"录制进程已经退出，退出码: {scrcpy_process.returncode}")
            stderr = scrcpy_process.stderr.read() if scrcpy_process.stderr else ""
            if stderr:
                logger.info(f"stderr输出: {stderr}")
        else:
            # 尝试通过HOME键让scrcpy优雅退出
            logger.info("发送HOME键")
            subprocess.run("adb shell input keyevent KEYCODE_HOME", shell=True, timeout=2)
            time.sleep(1)
            
            # 使用SIGINT信号(等同于按Ctrl+C)
            logger.info("发送SIGINT信号 (Ctrl+C)")
            scrcpy_process.send_signal(signal.SIGINT)
            
            # 等待进程退出
            timeout = 5
            for i in range(timeout):
                if scrcpy_process.poll() is not None:
                    break
                logger.info(f"等待进程退出... ({i+1}/{timeout})")
                time.sleep(1)
            
            # 如果进程未退出，使用SIGTERM
            if scrcpy_process.poll() is None:
                logger.info("发送SIGTERM信号")
                scrcpy_process.terminate()
                time.sleep(2)
                
                # 如果仍未退出，使用SIGKILL
                if scrcpy_process.poll() is None:
                    logger.info("发送SIGKILL信号")
                    scrcpy_process.kill()
                    time.sleep(1)
            
            # 获取退出状态
            exit_code = scrcpy_process.wait(timeout=1)
            logger.info(f"录制进程已退出，退出码: {exit_code}")
            
            # 获取错误输出
            stderr = scrcpy_process.stderr.read() if scrcpy_process.stderr else ""
            if stderr:
                logger.info(f"stderr输出: {stderr}")
        
        # 等待确保文件写入完成
        logger.info("等待5秒确保文件写入完成...")
        time.sleep(5)
        
        # 检查文件是否存在
        if os.path.exists(current_video_path):
            file_size = os.path.getsize(current_video_path) / (1024 * 1024)  # MB
            logger.info(f"录制文件: {current_video_path} (大小: {file_size:.2f}MB)")
            
            # 尝试使用ffmpeg修复文件
            fix_mp4_file(current_video_path)
        else:
            logger.error(f"录制文件不存在: {current_video_path}")
    
    except Exception as e:
        logger.error(f"停止录制时出错: {e}")
    finally:
        # 确保杀死所有scrcpy进程
        kill_scrcpy_processes()
        scrcpy_process = None

def fix_mp4_file(file_path):
    """尝试修复MP4文件"""
    try:
        # 检查ffmpeg是否可用
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
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
            
            # 尝试重编码 - 使用自适应bitrate
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

def kill_scrcpy_processes():
    """终止所有scrcpy进程"""
    logger.info("终止所有scrcpy进程")
    try:
        if os.name == 'nt':  # Windows
            subprocess.run("taskkill /F /IM scrcpy.exe", shell=True)
        else:  # Linux/Mac
            subprocess.run("pkill -9 scrcpy", shell=True)
    except Exception as e:
        logger.warning(f"终止scrcpy进程时出错: {e}")

if __name__ == "__main__":
    try:
        # 先确保没有遗留的scrcpy进程
        kill_scrcpy_processes()
        
        # 开始录制
        output_file = start_recording()
        
        if output_file and os.path.exists(output_file):
            logger.info(f"测试完成，录制文件: {output_file}")
        else:
            logger.error("录制失败")
    
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        if scrcpy_process is not None:
            stop_recording()
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
    finally:
        # 确保所有scrcpy进程都被终止
        kill_scrcpy_processes() 