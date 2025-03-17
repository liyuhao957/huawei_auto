import subprocess
import re
import time
import os
import sys

def find_coordinates():
    """记录坐标的辅助脚本"""
    print("请在手机上点击需要记录坐标的位置")
    print("点击后按Ctrl+C结束记录")
    
    # 屏幕尺寸设置
    screen_width = 1080   # 请替换为您的屏幕宽度
    screen_height = 2376  # 请替换为您的屏幕高度
    
    # 添加文件保存功能
    coord_file = open("coordinates.txt", "w")
    coord_file.write("# 记录的坐标点\n")
    
    # 启动事件监听
    try:
        # 使用更简单的格式输出
        process = subprocess.Popen(
            "adb shell getevent -l", 
            shell=True, 
            stdout=subprocess.PIPE,
            text=True
        )
        
        x, y = None, None
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            # 更健壮的坐标提取
            if "ABS_MT_POSITION_X" in line:
                try:
                    # 尝试用正则表达式提取值
                    match = re.search(r'value\s+(\w+)', line)
                    if match:
                        x = int(match.group(1), 16)
                        print(f"X坐标: {x}")
                except Exception as e:
                    print(f"解析X坐标失败: {line} - {str(e)}")
                    
            elif "ABS_MT_POSITION_Y" in line:
                try:
                    match = re.search(r'value\s+(\w+)', line)
                    if match:
                        y = int(match.group(1), 16)
                        print(f"Y坐标: {y}")
                        
                        # 如果同时有X和Y坐标，则计算相对位置
                        if x is not None:
                            coord_info = f"坐标点: ({x}, {y})\n"
                            coord_info += f"相对坐标: x_percent={x/screen_width:.3f}, y_percent={y/screen_height:.3f}\n"
                            print(coord_info + "-" * 50)
                            
                            # 写入文件
                            coord_file.write(coord_info + "\n")
                            
                            # 重置坐标，准备下一次点击
                            x, y = None, None
                except Exception as e:
                    print(f"解析Y坐标失败: {line} - {str(e)}")
            
    except KeyboardInterrupt:
        print("\n坐标记录结束")
    finally:
        if process:
            process.terminate()
        coord_file.close()  # 关闭文件

# 提供备选方法 - 如果上面方法不能工作，尝试这个更简单的方法
def simple_coordinate_finder():
    """一个更简单的坐标查找工具，监控点击和触摸事件"""
    print("请在手机上点击需要记录坐标的位置")
    print("点击后查看最近的触摸事件坐标")
    print("按Ctrl+C结束记录")
    
    # 获取设备屏幕尺寸
    try:
        size_output = subprocess.check_output("adb shell wm size", shell=True, text=True)
        wm_size_match = re.search(r'(\d+)x(\d+)', size_output)
        if wm_size_match:
            screen_width = int(wm_size_match.group(1))
            screen_height = int(wm_size_match.group(2))
            print(f"检测到设备屏幕尺寸: {screen_width}x{screen_height}")
        else:
            screen_width = 1080
            screen_height = 2376
            print(f"未检测到设备尺寸，使用默认值: {screen_width}x{screen_height}")
    except Exception as e:
        screen_width = 1080
        screen_height = 2376
        print(f"获取屏幕尺寸失败，使用默认值: {screen_width}x{screen_height}")
    
    # 创建并打开文件保存坐标
    coord_file = open("coordinates.txt", "w")
    coord_file.write(f"# 记录的坐标点 (屏幕尺寸: {screen_width}x{screen_height})\n")
    
    # 清空旧的事件
    subprocess.run("adb shell input tap 10 10", shell=True)
    time.sleep(0.5)
    
    try:
        # 尝试不同的方法来获取坐标
        methods = [
            # Method 1: Using dumpsys input
            lambda: subprocess.check_output("adb shell dumpsys input | grep -A 5 'MotionEvent'", shell=True, text=True),
            # Method 2: Using getevent to get recent events
            lambda: subprocess.check_output("adb shell 'getevent -l | grep -A 2 -B 2 ABS_MT_POSITION'", shell=True, text=True),
            # Method 3: Use direct tap and record
            lambda: direct_tap_and_record()
        ]
        
        method_index = 0
        print(f"使用方法 {method_index+1} 尝试获取坐标...")
        
        counter = 0
        while True:
            try:
                if method_index < 2:  # 前两种方法使用命令行输出
                    output = methods[method_index]()
                    
                    # 查找坐标 - 尝试多种可能的格式
                    coord_patterns = [
                        r'x=(\d+\.\d+)\s+y=(\d+\.\d+)',   # dumpsys 格式 x=123.0 y=456.0
                        r'X:\s*(\d+).*Y:\s*(\d+)',        # 一些设备的格式
                        r'ABS_MT_POSITION_X\s+.*?(\w+).*?ABS_MT_POSITION_Y\s+.*?(\w+)'  # getevent格式
                    ]
                    
                    coordinates_found = False
                    for pattern in coord_patterns:
                        coord_match = re.search(pattern, output, re.DOTALL)
                        if coord_match:
                            coordinates_found = True
                            try:
                                x = float(coord_match.group(1))
                                y = float(coord_match.group(2))
                            except ValueError:
                                # 如果是十六进制
                                try:
                                    x = int(coord_match.group(1), 16)
                                    y = int(coord_match.group(2), 16)
                                except ValueError:
                                    continue
                                
                            # 避免记录相同的坐标
                            if counter == 0 or (counter > 0 and (last_x != x or last_y != y)):
                                record_coordinate(x, y, screen_width, screen_height, coord_file)
                                last_x, last_y = x, y
                                counter += 1
                            break
                    
                    if not coordinates_found:
                        counter += 1
                        if counter > 5:  # 如果多次尝试都未找到坐标
                            print(f"使用方法 {method_index+1} 未能获取坐标，尝试方法 {method_index+2}...")
                            method_index += 1
                            if method_index >= len(methods):
                                print("所有方法都已尝试，未能获取坐标。")
                                print("建议：在设备上启用'显示点按反馈'并手动记录坐标")
                                break
                            counter = 0
                else:
                    # 第三种方法：直接记录点击
                    methods[method_index]()
                
                time.sleep(1)  # 每秒检查一次
                
            except Exception as e:
                print(f"当前方法出错: {str(e)}")
                method_index += 1
                if method_index >= len(methods):
                    print("所有方法都已尝试，未能获取坐标。")
                    print("建议：在设备上启用'显示点按反馈'并手动记录坐标")
                    break
                print(f"尝试方法 {method_index+1}...")
                counter = 0
                
    except KeyboardInterrupt:
        print("\n坐标记录结束")
    finally:
        coord_file.close()
        print(f"坐标已保存到文件: {os.path.abspath('coordinates.txt')}")

def record_coordinate(x, y, width, height, file=None):
    """记录并显示坐标"""
    coord_info = f"坐标点: ({x}, {y})\n"
    coord_info += f"相对坐标: x_percent={x/width:.3f}, y_percent={y/height:.3f}\n"
    print(coord_info + "-" * 50)
    
    if file:
        file.write(coord_info + "\n")

def direct_tap_and_record():
    """通过截图和点击直接记录坐标"""
    print("使用截图方法获取坐标 - 请在手机上点击")
    # 拍一张屏幕截图
    subprocess.run("adb shell screencap -p /sdcard/screen.png", shell=True)
    subprocess.run("adb pull /sdcard/screen.png .", shell=True)
    print("已获取屏幕截图，请查看当前目录下的screen.png文件")
    print("请手动记录鼠标在图片上的位置坐标")
    return "使用直接截图方法"

def screenshot_coordinate_finder():
    """使用截图并点击方式获取坐标"""
    print("\n=== 截图坐标定位器 ===")
    print("此方法将：")
    print("1. 截取手机屏幕")
    print("2. 保存到本地")
    print("3. 您点击图片的位置将记录为坐标")
    
    try:
        # 获取屏幕尺寸
        size_output = subprocess.check_output("adb shell wm size", shell=True, text=True)
        wm_size_match = re.search(r'(\d+)x(\d+)', size_output)
        if wm_size_match:
            screen_width = int(wm_size_match.group(1))
            screen_height = int(wm_size_match.group(2))
            print(f"检测到设备屏幕尺寸: {screen_width}x{screen_height}")
        else:
            screen_width = 1080
            screen_height = 2376
            print(f"未检测到设备尺寸，使用默认值: {screen_width}x{screen_height}")
    except Exception as e:
        screen_width = 1080
        screen_height = 2376
        print(f"获取屏幕尺寸失败，使用默认值: {screen_width}x{screen_height}")
    
    # 保存坐标的文件
    coord_file = open("coordinates.txt", "w")
    coord_file.write(f"# 记录的坐标点 (屏幕尺寸: {screen_width}x{screen_height})\n")
    
    # 截图并拉取到本地
    try:
        print("正在截取屏幕...")
        subprocess.run("adb shell screencap -p /sdcard/screen.png", shell=True)
        subprocess.run("adb pull /sdcard/screen.png .", shell=True)
        print(f"截图已保存: {os.path.abspath('screen.png')}")
        
        # 检查是否有GUI环境
        try:
            # 尝试用Python的GUI库显示图片并获取点击坐标
            print("尝试打开图像查看器...")
            
            # 尝试导入tkinter
            try:
                import tkinter as tk
                from PIL import Image, ImageTk
                has_gui = True
            except ImportError:
                print("未安装tkinter或PIL库，无法显示图像")
                print("请手动打开screen.png，记住您点击的位置")
                print("然后输入坐标 (格式: x,y)：")
                has_gui = False
            
            if has_gui:
                # 创建窗口显示图像
                root = tk.Tk()
                root.title("点击图像记录坐标")
                
                # 加载图像
                img = Image.open("screen.png")
                img_width, img_height = img.size
                scale_factor = min(1.0, 800/img_width, 800/img_height)  # 缩放以适应屏幕
                
                # 创建画布
                canvas = tk.Canvas(root, width=img_width*scale_factor, height=img_height*scale_factor)
                canvas.pack()
                
                # 显示图像
                photo = ImageTk.PhotoImage(img.resize((int(img_width*scale_factor), int(img_height*scale_factor))))
                canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                
                def on_click(event):
                    # 计算实际坐标（考虑缩放）
                    x = int(event.x / scale_factor)
                    y = int(event.y / scale_factor)
                    
                    # 记录坐标
                    print(f"点击位置: ({x}, {y})")
                    print(f"相对坐标: x_percent={x/img_width:.3f}, y_percent={y/img_height:.3f}")
                    
                    # 写入文件
                    coord_info = f"坐标点: ({x}, {y})\n"
                    coord_info += f"相对坐标: x_percent={x/img_width:.3f}, y_percent={y/img_height:.3f}\n"
                    coord_file.write(coord_info + "\n")
                    
                    # 在图像上标记点击位置
                    canvas.create_oval(
                        event.x-5, event.y-5, event.x+5, event.y+5, 
                        fill="red", outline="white"
                    )
                
                # 绑定点击事件
                canvas.bind("<Button-1>", on_click)
                
                print("请点击图像上的目标位置...")
                print("点击后，坐标会记录下来，您可以多次点击记录多个位置")
                print("关闭窗口结束记录")
                
                # 显示窗口
                root.mainloop()
            else:
                # 手动输入模式
                while True:
                    coord_input = input("输入坐标 (x,y) 或 q 退出: ")
                    if coord_input.lower() == 'q':
                        break
                    
                    try:
                        x, y = map(int, coord_input.split(','))
                        print(f"记录坐标: ({x}, {y})")
                        print(f"相对坐标: x_percent={x/screen_width:.3f}, y_percent={y/screen_height:.3f}")
                        
                        # 写入文件
                        coord_info = f"坐标点: ({x}, {y})\n"
                        coord_info += f"相对坐标: x_percent={x/screen_width:.3f}, y_percent={y/screen_height:.3f}\n"
                        coord_file.write(coord_info + "\n")
                    except:
                        print("输入格式错误，请用逗号分隔x和y，例如: 500,600")
        
        except Exception as e:
            print(f"显示图像失败: {str(e)}")
            print("请手动查看screen.png并记录坐标")
    
    except Exception as e:
        print(f"截图失败: {str(e)}")
    
    finally:
        coord_file.close()
        print(f"坐标已保存到文件: {os.path.abspath('coordinates.txt')}")

# 执行简单截图方法，最直接可靠
print("使用截图方法获取坐标:")
screenshot_coordinate_finder()

# 如果截图方法失败，尝试其他方法
if not os.path.exists("coordinates.txt") or os.path.getsize("coordinates.txt") <= 30:
    print("\n尝试使用其他方法记录坐标:")
    try:
        simple_coordinate_finder()
    except Exception as e:
        print(f"simple_coordinate_finder方法失败: {str(e)}")
        try:
            find_coordinates()
        except Exception as e:
            print(f"find_coordinates方法失败: {str(e)}")
            print("请在设备上启用'显示点按反馈'选项，并手动记录坐标")