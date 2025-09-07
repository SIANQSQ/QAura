import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext
import requests
import websocket
import threading
import socket
import time
import sys
import winreg
import pyautogui
import serial
import serial.tools.list_ports
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, IPropertyStore
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import json
import comtypes
import warnings
LED_Name = ["桌子下","显示器下","显示器上","桌子上","桌子侧","---","---","---"]
modes = [("关闭", 0), ("纯色", 1), ("彩虹", 2), ("呼吸", 3), ("声音", 4), ("屏幕", 5),("渐变",6)]
WS2812B_Pin = [4,18,19,21,22,23,25,26]
LED_Num = [53,22,28,39,33,0,0,0]


class MultiChannelLEDControlApp:
    def __init__(self, master):
        self.master = master
        master.title("QAura Master")
        master.geometry("1000x1000")
        self.master.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.master.iconbitmap('icon.ico')
        # 托盘相关变量
        self.tray = None
        self.tray_running = False

        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('vista')
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TLabelframe', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        
        # 通道配置
        self.channels = []  # 存储每个通道的状态
        self.mode_combos = []  # 存储每个通道的模式下拉框
        self.esp_ip = tk.StringVar(value="192.168.31.105")  # 默认IP
        self.connection_status = tk.BooleanVar(value=False)
        self.last_known_ip = ""
        self.color_previews = []
        self.ColorSYNC = tk.BooleanVar(value=True)  #
        self.ColorSystemTheme = tk.BooleanVar()  # 使用系统主题颜色
        #音频模式参数
        self.audio_color_preview = None
        self.audio_use_specific_color = tk.BooleanVar(value=False)
        self.audio_r = 128  #默认声音模式特定颜色
        self.audio_g = 128
        self.audio_b = 128
        self.audio_gain = tk.DoubleVar(value=1.0) #增益
        self.audio_running = False
        self.speed_frame = None
        self.peak = 0   # 音频峰值
        self.audio_device_name = None
        #屏幕捕获模式参数
        self.screen_x = tk.IntVar(value=100)
        self.screen_y = tk.IntVar(value=100)
        self.screen_r = 0
        self.screen_g = 0
        self.screen_b = 0
        self.screen_running = False
        self.ws = None
        self.ws_running = False
        self.ws_thread = None
        # 串口控制
        self.serial_port = None
        self.serial_connected = tk.BooleanVar(value=False)
        self.serial_port_name = tk.StringVar()
        self.serial_thread = None

        self.region_size = tk.IntVar(value=10)  # 监测区域大小
        # 创建UI
        self.create_widgets()
        
        # 启动连接监控
        self.monitor_connection()
        
        self.create_tray_icon()
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部控制面板
        control_frame = ttk.LabelFrame(main_frame, text="连接控制")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # IP地址设置
        ip_frame = ttk.Frame(control_frame)
        ip_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(ip_frame, text="QAura IP:").pack(side=tk.LEFT, padx=5)
        ip_entry = ttk.Entry(ip_frame, textvariable=self.esp_ip, width=15)
        ip_entry.pack(side=tk.LEFT, padx=5)
        
        # 连接按钮
        ttk.Button(ip_frame, text="连接至设备", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(ip_frame, text="扫描网络", command=self.scan_network).pack(side=tk.LEFT, padx=5)
        
        # 状态指示器
        self.status_indicator = tk.Label(ip_frame, text="●", font=("Arial", 14), fg="red")
        self.status_indicator.pack(side=tk.LEFT, padx=10)
        
        # 状态文本
        self.status_label = ttk.Label(ip_frame, text="未连接")
        self.status_label.pack(side=tk.LEFT)
        
        serial_frame = ttk.LabelFrame(control_frame, text="串口连接")
        serial_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(serial_frame, text="串口:").pack(side=tk.LEFT, padx=5)
        self.serial_ports_combo = ttk.Combobox(serial_frame, width=12, textvariable=self.serial_port_name, state="readonly")
        self.serial_ports_combo.pack(side=tk.LEFT, padx=5)
        self.refresh_serial_ports()

        ttk.Button(serial_frame, text="刷新", command=self.refresh_serial_ports).pack(side=tk.LEFT, padx=5)
        ttk.Button(serial_frame, text="连接串口", command=self.connect_serial).pack(side=tk.LEFT, padx=5)
        ttk.Button(serial_frame, text="断开串口", command=self.disconnect_serial).pack(side=tk.LEFT, padx=5)
        self.serial_status_label = ttk.Label(serial_frame, text="未连接")
        self.serial_status_label.pack(side=tk.LEFT, padx=10)
            
        color_setting_frame = ttk.LabelFrame(main_frame, text="颜色设置")
        color_setting_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        # 新建一行用于勾选框
        check_frame = ttk.Frame(color_setting_frame)
        check_frame.pack(fill=tk.X, padx=5, pady=5)
        color_sync_check = tk.Checkbutton(check_frame, text="同步颜色", variable=self.ColorSYNC)
        color_sync_check.pack(side=tk.LEFT, padx=5)
        color_system_theme_check = tk.Checkbutton(check_frame, text="使用系统主题颜色", variable=self.ColorSystemTheme, command=self.get_windows_theme_color)
        color_system_theme_check.pack(side=tk.LEFT, padx=5)

        ttk.Label(check_frame, text="监测屏幕颜色坐标 X:").pack(side=tk.LEFT, padx=5)
        self.screen_x = tk.IntVar(value=1280)
        x_entry = ttk.Entry(check_frame, textvariable=self.screen_x, width=6)
        x_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(check_frame, text="Y:").pack(side=tk.LEFT, padx=2)
        self.screen_y = tk.IntVar(value=1200)
        y_entry = ttk.Entry(check_frame, textvariable=self.screen_y, width=6)
        y_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(check_frame, text="监测范围px:").pack(side=tk.LEFT, padx=5)
        self.region_size = tk.IntVar(value=50)
        detectsize = ttk.Entry(check_frame, textvariable=self.region_size, width=6)
        detectsize.pack(side=tk.LEFT, padx=2)

        # 新建一行用于两个滑动条
        slider_frame = ttk.Frame(color_setting_frame)
        slider_frame.pack(fill=tk.X, padx=5, pady=5)

        brightness_frame = ttk.Frame(slider_frame)
        brightness_frame.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(brightness_frame, text="亮度:").pack(side=tk.LEFT)
        brightness = tk.Scale(
            brightness_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self.set_brightness(v)
        )
        brightness.set(100)
        brightness.pack(side=tk.LEFT, padx=5)

        self.speed_frame = ttk.Frame(slider_frame)
        self.speed_frame.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(self.speed_frame, text="速度:").pack(anchor=tk.W, side=tk.LEFT)
        speed = tk.Scale(
            self.speed_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self.set_speed(v)
            )
        speed.set(50)
        speed.pack(side=tk.LEFT, padx=5)

        audio_specify_color_check = tk.Checkbutton(self.speed_frame, text="音频模式下使用特定颜色", variable=self.audio_use_specific_color)
        audio_specify_color_check.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.speed_frame, text="颜色:").pack(side=tk.LEFT)

        self.color_btn = tk.Button(
            self.speed_frame, 
            text="选择", 
            bg="#FFFFFF", 
            command=lambda: self.choose_audio_color(),
            width=6,
            height=1
        )
        self.color_btn.pack(side=tk.LEFT, padx=5)

        # 新增：颜色预览标签
        self.audio_color_preview = tk.Label(self.speed_frame, bg="#FFFFFF", width=3, height=1, relief=tk.SUNKEN)
        self.audio_color_preview.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.speed_frame, text="音频信号增益:").pack(side=tk.LEFT, padx=5)
        audio_gain_Input = ttk.Entry(self.speed_frame, textvariable=self.audio_gain, width=6)
        audio_gain_Input.pack(side=tk.LEFT, padx=2)

        # 通道控制区域
        channels_frame = ttk.LabelFrame(main_frame, text="通道控制")        
        channels_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建8个通道的控制面板
        self.channel_frames = []
        for i in range(8):
            # 每行两个通道
            if i % 4 == 0:
                row_frame = tk.Frame(channels_frame)
                row_frame.pack(fill=tk.X, padx=5, pady=5)

            channel_frame = tk.LabelFrame(row_frame, text=f"通道 {i+1}        "+LED_Name[i])
            channel_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.channel_frames.append(channel_frame)
            self.create_channel_controls(channel_frame, i)

            # 初始化通道状态
            self.channels.append({
                "pin": WS2812B_Pin[i],  
                "count": LED_Num[i], 
                "color": "#FFFFFF", 
                "mode": 2  # 0=关闭, 1=纯色, 2=彩虹, 3=呼吸
            })
        # 网络诊断面板
        diag_frame = ttk.LabelFrame(main_frame, text="日志")
        diag_frame.pack(fill=tk.BOTH, padx=5, pady=5)

        # 诊断输出
        self.diag_text = scrolledtext.ScrolledText(
            diag_frame, 
            height=8,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.diag_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.diag_text.insert(tk.END, "欢迎使用QAura\n")
        self.diag_text.config(state=tk.DISABLED)

        # 诊断按钮
        btn_frame = ttk.Frame(diag_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="Ping ESP32", command=self.ping_device).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="显示网络信息", command=self.show_network_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清除日志", command=self.clear_diagnostic).pack(side=tk.LEFT, padx=5)

        # 状态栏
        self.status_bar = ttk.Label(
            self.master, 
            text="就绪", 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=3
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_channel_controls(self, parent, channel_idx):
        # 模式选择
        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="模式:").pack(side=tk.LEFT)
        
        mode_var = tk.StringVar(value="关闭")
        
        
        mode_combo = ttk.Combobox(
            mode_frame, 
            values=[m[0] for m in modes],
            state="readonly",
            width=8
        )
        mode_combo.set("彩虹")
        mode_combo.pack(side=tk.LEFT, padx=5)
        mode_combo.bind("<<ComboboxSelected>>", 
                       lambda e: self.set_mode(channel_idx, 
                                             [m[1] for m in modes if m[0] == mode_combo.get()][0]))
        self.mode_combos.append(mode_combo)
        # 颜色选择
        color_frame = ttk.Frame(parent)
        color_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(color_frame, text="颜色:").pack(side=tk.LEFT)

        self.color_btn = tk.Button(
            color_frame, 
            text="选择", 
            bg="#FFFFFF", 
            command=lambda: self.choose_color(channel_idx),
            width=6,
            height=1
        )
        self.color_btn.pack(side=tk.LEFT, padx=5)

        # 新增：颜色预览标签
        color_preview = tk.Label(color_frame, bg="#FFFFFF", width=3, height=1, relief=tk.SUNKEN)
        color_preview.pack(side=tk.LEFT, padx=5)
        self.color_previews.append(color_preview)
        
        # 通道信息
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text=f"引脚:{WS2812B_Pin[channel_idx]}    LED数目:{LED_Num[channel_idx]}").pack(side=tk.LEFT)

    def log_diagnostic(self, message):
        """记录诊断信息"""
        self.diag_text.config(state=tk.NORMAL)
        self.diag_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.diag_text.see(tk.END)  # 滚动到底部
        self.diag_text.config(state=tk.DISABLED)
    
    def clear_diagnostic(self):
        """清除诊断日志"""
        self.diag_text.config(state=tk.NORMAL)
        self.diag_text.delete(1.0, tk.END)
        self.diag_text.insert(tk.END, "日志已清除\n")
        self.diag_text.see(tk.END)
        self.diag_text.config(state=tk.DISABLED)
    
    def monitor_connection(self):
        """监控连接状态"""
        if not self.connection_status.get():
            self.test_connection()
        
        # 每10秒检查一次连接状态
        self.master.after(10000, self.monitor_connection)
    
    def test_connection(self):
        """测试与ESP32的连接"""
        def test():
            ip = self.esp_ip.get()
            self.log_diagnostic(f"正在测试连接到 {ip}...")
            
            try:
                response = requests.get(
                    f"http://{ip}/", 
                    timeout=2
                )
                if "QAura" in response.text:
                    self.connection_status.set(True)
                    self.status_indicator.config(fg="green")
                    self.status_label.config(text=f"已连接到: {ip}")
                    self.last_known_ip = ip
                    self.status_bar.config(text=f"已连接到QAura: {ip}")
                    self.log_diagnostic("连接成功！QAura已准备就绪。")
                    
                else:
                    self.connection_status.set(False)
                    self.status_indicator.config(fg="red")
                    self.status_label.config(text="设备响应异常")
                    self.log_diagnostic(f"错误: 设备响应异常 ({response.status_code} - {response.text[:50]})")
            except requests.exceptions.Timeout:
                self.connection_status.set(False)
                self.status_indicator.config(fg="red")
                self.status_label.config(text="连接超时")
                self.log_diagnostic(f"错误: 连接 {ip} 超时")
                self.status_bar.config(text=f"连接超时: {ip}")
            except requests.exceptions.ConnectionError:
                self.connection_status.set(False)
                self.status_indicator.config(fg="red")
                self.status_label.config(text="无法连接")
                self.log_diagnostic(f"错误: 无法连接到 {ip}")
                self.status_bar.config(text=f"无法连接到: {ip}")
            except Exception as e:
                self.connection_status.set(False)
                self.status_indicator.config(fg="red")
                self.status_label.config(text="连接错误")
                self.log_diagnostic(f"错误: {str(e)}")
                self.status_bar.config(text=f"连接错误: {str(e)}")
        
        threading.Thread(target=test, daemon=True).start()
    
    
    
    def scan_network(self):
        """扫描局域网查找ESP32设备"""
        def scan():
            self.log_diagnostic("开始扫描局域网查找QAura设备...")
            base_ip = self.get_base_ip()
            
            if not base_ip:
                self.log_diagnostic("错误: 无法确定本地网络地址")
                return
                
            self.log_diagnostic(f"扫描范围: {base_ip}1-255")
            
            found = False
            for i in range(1, 255):
                ip = f"{base_ip}{i}"
                self.status_bar.config(text=f"扫描中: {ip}")
                
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.1)
                    result = s.connect_ex((ip, 80))
                    s.close()
                    
                    if result == 0:
                        try:
                            response = requests.get(f"http://{ip}/", timeout=1)
                            if "Multi-Channel" in response.text:
                                self.esp_ip.set(ip)
                                self.log_diagnostic(f"发现设备: {ip}")
                                self.test_connection()
                                found = True
                                break
                        except:
                            continue
                except:
                    continue
            
            if not found:
                self.log_diagnostic("扫描完成，未找到QAura设备")
                self.status_bar.config(text="扫描完成，未找到设备")
            else:
                self.status_bar.config(text=f"发现设备: {ip}")
        
        threading.Thread(target=scan, daemon=True).start()
    
    def get_base_ip(self):
        """获取本地网络IP地址前缀"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            
            # 获取IP地址前缀 (如192.168.1.)
            parts = ip.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}."
            return None
        except:
            return None
    
    def ping_device(self):
        """Ping ESP32设备"""
        def ping():
            ip = self.esp_ip.get()
            self.log_diagnostic(f"Pinging {ip}...")
            
            try:
                # 使用系统ping命令
                import subprocess
                result = subprocess.run(
                    ["ping", "-n", "2", ip], 
                    capture_output=True, 
                    text=True
                )
                
                self.log_diagnostic(result.stdout)
                if "TTL=" in result.stdout:
                    self.log_diagnostic(f"Ping {ip} 成功！")
                    self.status_bar.config(text=f"Ping {ip} 成功")
                else:
                    self.log_diagnostic(f"Ping {ip} 失败")
                    self.status_bar.config(text=f"Ping {ip} 失败")
            except Exception as e:
                self.log_diagnostic(f"Ping错误: {str(e)}")
                self.status_bar.config(text=f"Ping错误: {str(e)}")
        
        threading.Thread(target=ping, daemon=True).start()
    
    def show_network_info(self):
        """显示网络信息"""
        try:
            import netifaces
            self.log_diagnostic("网络接口信息:")
            
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    self.log_diagnostic(f"接口: {interface}")
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get('addr', '')
                        mask = addr_info.get('netmask', '')
                        self.log_diagnostic(f"  IP地址: {ip}")
                        self.log_diagnostic(f"  子网掩码: {mask}")
        except ImportError:
            self.log_diagnostic("错误: 需要安装netifaces库 (pip install netifaces)")
            self.status_bar.config(text="需要安装netifaces库")
    
    def set_mode(self, channel, mode_id):
        # if not self.connection_status.get():
        #     self.test_connection()
        #     return
        
        if self.ColorSYNC.get():
            requests.get(
                        f"http://{self.esp_ip.get()}/set_mode",
                        params={
                            "channel": channel+1,
                            "mode": mode_id,
                            "sync": 1
                        },
                        timeout=2
                    )
            for i in range(8):
                try:
                    self.channels[i]["mode"] = mode_id
                    self.mode_combos[i].set(modes[mode_id][0])
                except Exception as e:
                    self.status_bar.config(text=f"错误: {str(e)}")
            #self.status_bar.config(text="所有通道已同步")
            #self.log_diagnostic("同步所有通道")
        else:
            try:
                response = requests.get(
                    f"http://{self.esp_ip.get()}/set_mode", 
                    params={
                        "channel": channel+1,
                        "mode": mode_id
                    },
                    timeout=2
                )
                self.status_bar.config(text=f"通道 {channel+1} 模式设置成功")
                self.log_diagnostic(f"设置通道 {channel+1} 模式: {mode_id}")
                
                # 更新本地状态
                self.channels[channel]["mode"] = mode_id
            except Exception as e:
                self.status_bar.config(text=f"错误: {str(e)}")

        # 根据模式启动或停止相关线程
        OnSCREEN = False
        OnAUDIO = False
        if(mode_id == 5):
            OnSCREEN = True
            if not self.screen_running:
                self.start_screen_thread()
            if not self.ws_running:
                self.start_websocket_thread()
        else:
            for i in range(8):  
                print
                if int(self.channels[i]["mode"]) == 5:
                    OnSCREEN = True
            if not OnSCREEN :
                self.stop_screen_thread()
        if(mode_id == 4):
            OnAUDIO = True
            if not self.audio_running:
                self.start_audio_thread()
            if not self.ws_running:
                self.start_websocket_thread()
        else:
            for i in range(8):  
                if int(self.channels[i]["mode"]) == 4:
                    OnAUDIO = True
            if not OnAUDIO :
                self.stop_audio_thread()
        if not OnSCREEN and not OnAUDIO:
            self.stop_websocket_thread()
    
    def choose_audio_color(self):
        if not self.connection_status.get():
            self.test_connection()
            return
            
        color = colorchooser.askcolor(title=f"选择音频模式的灯带颜色")[0]
        if color:
            r, g, b = [int(c) for c in color]
            self.audio_r = r
            self.audio_g = g
            self.audio_b = b
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # 新增：更新预览标签颜色
            self.audio_color_preview.config(bg=hex_color)

    def choose_color(self, channel):
        if not self.connection_status.get():
            #self.test_connection()
            self.status_bar.config(text="未连接到QAura设备")    
            return
            
        color = colorchooser.askcolor(title=f"选择通道 {channel+1} 的颜色")[0]
        if color:
            r, g, b = [int(c) for c in color]
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            # 更新按钮颜色
            for widget in self.channel_frames[channel].winfo_children():
                if isinstance(widget, tk.Button) and widget.cget("text") == "选择":
                    widget.config(bg=hex_color)
                    break

            # 新增：更新预览标签颜色
            self.color_previews[channel].config(bg=hex_color)

            # 更新本地通道状态
            self.channels[channel]["color"] = hex_color
            self.send_color(channel, r, g, b)
    
    def send_color(self, channel, r, g, b):
        try:
            if self.ColorSYNC.get() or channel == -1:
                Color_sync = 1
                for i in range(8):
                    self.channels[i]["color"] = f"#{r:02x}{g:02x}{b:02x}"
                    self.channels[i]["mode"] = 1  # 全部切换到纯色模式
                    self.color_previews[i].config(bg=f"#{r:02x}{g:02x}{b:02x}")
                    self.mode_combos[i].set(modes[1][0])
            else:
                Color_sync = 0
            response = requests.get(
                f"http://{self.esp_ip.get()}/set_color", 
                params={
                    "channel": channel+1,
                    "r": r, 
                    "g": g, 
                    "b": b,
                    "sync": Color_sync
                },
                timeout=2
            )
            self.status_bar.config(text=f"通道 {channel+1} 颜色设置成功: RGB({r},{g},{b})")
            self.log_diagnostic(f"设置通道 {channel+1} 颜色: R={r}, G={g}, B={b}, SYNC={Color_sync}")
        except Exception as e:
            self.status_bar.config(text=f"错误: {str(e)}")
    
    def set_brightness(self, value):
        if not self.connection_status.get():
            #self.test_connection()
            self.status_bar.config(text="未连接到QAura设备")    
            return
            
        try:
            # 更新本地通道状态
            response = requests.get(
                f"http://{self.esp_ip.get()}/set_brightness", 
                params={
                    "value": value
                },
                timeout=2
            )
            self.status_bar.config(text=f"亮度设置成功: {value}%")
            self.log_diagnostic(f"设置亮度: {value}%")
        except Exception as e:
            self.status_bar.config(text=f"错误: {str(e)}")
    
    def set_speed(self, value):
        if not self.connection_status.get():
            #self.test_connection()
            self.status_bar.config(text="未连接到QAura设备")    
            return
            
        try:            
            response = requests.get(
                f"http://{self.esp_ip.get()}/set_speed", 
                params={
                    "value": value
                },
                timeout=2
            )
            self.status_bar.config(text=f"速度设置成功: {value}%")
            self.log_diagnostic(f"设置速度: {value}%")
        except Exception as e:
            self.status_bar.config(text=f"错误: {str(e)}")

    def get_windows_theme_color(self):
        if self.ColorSystemTheme.get():
            try:
                # 打开注册表键
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")

                # 读取 ColorizationColor 值
                color_value, _ = winreg.QueryValueEx(key, "ColorizationColor")

                # 关闭注册表键
                winreg.CloseKey(key)

                # 将颜色值转换为十六进制格式
                alpha = (color_value >> 24) & 0xFF
                red = (color_value >> 16) & 0xFF
                green = (color_value >> 8) & 0xFF
                blue = color_value & 0xFF

                Dred = int(str(red),10)
                Dgreen = int(str(green),10)
                Dblue = int(str(blue),10)
                self.send_color(-1, Dred, Dgreen, Dblue) #通道-1也发送到所有通道

            except Exception as e:
                print(f"Error accessing registry: {e}")
                return None
    
    def start_websocket_thread(self):
        """启动WebSocket线程，定时发送屏幕颜色"""
        def ws_worker():
            self.ws_running = True
            try:
                self.ws = websocket.create_connection(f"ws://{self.esp_ip.get()}:81")
                while self.ws_running:
                    if self.audio_use_specific_color.get() == True:
                        useSpecific = 1
                    else:    
                        useSpecific = 0
                    rgb_data = {
                    "type": "AC_pack",
                    "specific_color": int(useSpecific),
                    "r": int(self.screen_r),
                    "g": int(self.screen_g),
                    "b": int(self.screen_b),
                    "a_r": int(self.audio_r),
                    "a_g": int(self.audio_g),  
                    "a_b": int(self.audio_b),
                    "peak": self.peak
                    }
        
                    # 将字典转换为JSON字符串并发送
                    json_data = json.dumps(rgb_data)
                    self.ws.send(json_data)
                    time.sleep(1/30)  # 30hz
            except Exception as e:
                print(f"WebSocket错误: {e}")
            finally:
                if self.ws:
                    self.ws.close()
        self.ws_thread = threading.Thread(target=ws_worker, daemon=True)
        self.ws_thread.start()

    def stop_websocket_thread(self):
        print("Stopping WebSocket thread")
        self.ws_running = False
        if self.ws:
            self.ws.close()
    
    def refresh_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serial_ports_combo['values'] = ports
        if ports:
            self.serial_port_name.set(ports[0])
        else:
            self.serial_port_name.set("")

    def connect_serial(self):
        port = self.serial_port_name.get()
        try:
            self.serial_port = serial.Serial(port, baudrate=115200, timeout=0.3)
            self.serial_connected.set(True)
            self.serial_status_label.config(text=f"已连接: {port}")
            self.log_diagnostic(f"串口已连接: {port}")
        except Exception as e:
            self.serial_connected.set(False)
            self.serial_status_label.config(text="连接失败")
            self.log_diagnostic(f"串口连接失败: {str(e)}")

    def disconnect_serial(self):
        if self.serial_port:
            try:
                self.serial_port.close()
                self.serial_connected.set(False)
                self.serial_status_label.config(text="未连接")
                self.log_diagnostic("串口已断开")
            except Exception as e:
                self.log_diagnostic(f"串口断开失败: {str(e)}")
        else:
            self.serial_status_label.config(text="未连接")
    def send_command(self, mode, r, g, b, peak):
        """
        发送模式和数据到ESP32，带颜色平滑过渡
        """
        if not hasattr(self, 'last_r'):
            self.last_r, self.last_g, self.last_b = r, g, b

        # 计算颜色差值
        diff_r = r - self.last_r
        diff_g = g - self.last_g
        diff_b = b - self.last_b

        # 设置过渡步数
        steps = 10

        # 逐步过渡颜色
        for i in range(1, steps + 1):
            if not self.serial_running:  # 如果中途停止，则退出
                break

            # 计算当前步的颜色
            current_r = self.last_r + int(diff_r * i / steps)
            current_g = self.last_g + int(diff_g * i / steps)
            current_b = self.last_b + int(diff_b * i / steps)

            # 构建命令字符串
            command = f"{mode},{current_r},{current_g},{current_b},{peak}\n"
            self.screen_r = current_r
            self.screen_g = current_g   
            self.screen_b = current_b
            try:
                # 发送命令
                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.write(command.encode('utf-8'))
                    #print(f"已发送过渡颜色: {command.strip()}")
            except Exception as e:
                #print(f"发送命令时出错: {e}")
                self.status_bar.config(text=f"串口发送错误: {e}")
                break
            
            time.sleep(0.05)  # 短暂延迟，控制过渡速度

        # 更新最后颜色
        self.last_r, self.last_g, self.last_b = r, g, b

        return True
    
    def send_audio_command(self,mode,r,g,b,peak):
        command = f"{mode},{r},{g},{b},{peak}\n"
        try:
            # 发送命令
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(command.encode('utf-8'))
                #print(f"已发送声音数据: {command.strip()}")
        except Exception as e:
            self.status_bar.config(text=f"串口发送错误: {e}")
            #print(f"发送命令时出错: {e}")
            
    def start_screen_thread(self):
        """启动串口线程，定时发送屏幕颜色"""
        self.status_bar.config(text=f"正在启动屏幕颜色捕获线程")
        def screen_worker():
            self.screen_running = True
            self.status_bar.config(text=f"成功启动屏幕颜色捕获线程")
            while self.screen_running:
                x = self.screen_x.get()
                y = self.screen_y.get()
                try:
                    region = self.region_size.get()
                    if(region < 1):
                        region = 1
                        self.region_size.set(1)
                        self.log_diagnostic("监测区域大小过小，已调整为1")
                    elif(region > 500):
                        region = 500
                        self.region_size.set(500)
                        self.log_diagnostic("监测区域大小过大，已调整为500")
                except:
                    region = 10
                    self.log_diagnostic("监测区域数值异常，已调整为默认值: 10px")
                    self.region_size.set(10)
                # 获取小区域的平均颜色而不是单点
                screenshot = pyautogui.screenshot(region=(
                    x - region//2,
                    y - region//2,
                    region,
                    region
                ))

                # 计算平均颜色
                r_total, g_total, b_total = 0, 0, 0
                pixel_count = region * region

                for pixel_x in range(region):
                    for pixel_y in range(region):
                        r, g, b = screenshot.getpixel((pixel_x, pixel_y))
                        r_total += r
                        g_total += g
                        b_total += b

                self.screen_r = r_total // pixel_count
                self.screen_g = g_total // pixel_count
                self.screen_b = b_total // pixel_count

                if not hasattr(self, 'last_r'):
                    self.last_r, self.last_g, self.last_b = self.screen_r, self.screen_g, self.screen_b

                # 计算颜色差值
                diff_r = r - self.last_r
                diff_g = g - self.last_g
                diff_b = b - self.last_b
        
                # 设置过渡步数
                steps = 20
        
                # 逐步过渡颜色
                for i in range(1, steps + 1):
                    if not self.screen_running:  # 如果中途停止，则退出
                        break
        
                    # 计算当前步的颜色
                    current_r = self.last_r + int(diff_r * i / steps)
                    current_g = self.last_g + int(diff_g * i / steps)
                    current_b = self.last_b + int(diff_b * i / steps)
        
                    self.screen_r = current_r
                    self.screen_g = current_g   
                    self.screen_b = current_b
                    
                    time.sleep(0.001)  # 短暂延迟，控制过渡速度

                self.last_r, self.last_g, self.last_b = self.screen_r, self.screen_g, self.screen_b
                time.sleep(0.01)
        self.serial_thread = threading.Thread(target=screen_worker, daemon=True)
        self.serial_thread.start()
       

    def stop_screen_thread(self):
        self.status_bar.config(text=f"成功停止屏幕颜色捕获线程")
        self.screen_running = False
    
    def get_friendly_name(self, dev) -> str:
        with warnings.catch_warnings():
            # suppress deprecation warning for GetAllDevices
            warnings.simplefilter("ignore", UserWarning)

            # get the unique endpoint ID
            dev_id = dev.GetId()

            # AudioUtilities.GetAllDevices() yields AudioDevice wrappers
            for d in AudioUtilities.GetAllDevices():
                if d.id == dev_id:
                    return d.FriendlyName
            return "Unknown Device"

    def set_meter(self):
        try:
            devices = AudioUtilities.GetSpeakers()
            self.audio_device_name = self.get_friendly_name(devices)
            interface = devices.Activate(
                            IAudioMeterInformation._iid_, 
                            CLSCTX_ALL, 
                            None
                        )
            self.status_bar.config(text=f"音频监听设备已切换为: {self.audio_device_name}")
            self.meter = cast(interface, POINTER(IAudioMeterInformation))  # 重新初始化音频设备
            
        except Exception as e:
            self.status_bar.config(text=f"音频初始化错误: {e},请检查音频设备")
            self.log_diagnostic(f"音频初始化错误: {e}")
    def start_audio_thread(self):
        self.status_bar.config(text=f"正在启动音频监听线程")
        self.set_meter()
        def audio_worker():
            self.audio_running = True
            self.status_bar.config(text=f"成功启动音频监听线程,监听设备: {self.audio_device_name}")

            # 视觉效果增强参数
            peak_hold = 0.0  # 用于峰值保持效果
            peak_decay = 0.95  # 峰值衰减速率 (值越小衰减越快)
            min_threshold = 0.02  # 最小阈值，过滤微小声音
            response_curve = 1.5  # 响应曲线指数，值越大对强信号越敏感
            comtypes.CoInitialize()
            while self.audio_running:
                try:
                    try:
                        if self.audio_gain.get() < 0:
                            self.audio_gain.set(0)
                    except:
                        self.audio_gain.set(1.0)

                    # 获取原始音频峰值
                    raw_peak = float(self.audio_gain.get()) * self.meter.GetPeakValue()

                    # 应用响应曲线，增强视觉动态范围
                    processed_peak = raw_peak ** response_curve

                    # 峰值保持
                    if processed_peak > peak_hold:
                        peak_hold = processed_peak
                    else:
                        peak_hold *= peak_decay 

                    if peak_hold < min_threshold:
                        peak_hold = 0.0

                    final_peak = round(min(peak_hold, 0.999), 5)
                    self.peak = final_peak

                except Exception as e:
                    self.status_bar.config(text=f"音频线程错误: {e},请尝试重新切换至音频模式")
                    if "设备已被删除" in str(e):
                        self.set_meter()
                time.sleep(1/60)  # 60Hz更新频率

        self.audio_thread = threading.Thread(target=audio_worker, daemon=True)
        self.audio_thread.start()

    def stop_audio_thread(self):
        self.status_bar.config(text=f"成功停止音频监听线程")
        # print("Stopping audio thread")
        self.audio_running = False
    
    def create_tray_icon(self):
        # 确保只创建一个托盘图标实例
        if self.tray is None:
            # 创建一个简单的图标
            image = Image.open("icon.ico")

            # 创建托盘菜单
            menu = (
                item('显示主窗口', self.show_window),
                item('关闭灯光', self.stray_close_lights),
                item('彩虹', self.stray_rainbow),
                item('纯色', self.stray_static_color),
                item('呼吸', self.stray_breathing),
                item('音频', self.stray_audio),
                item('屏幕', self.stray_screen),
                item('退出', self.exit_app)
            )
            
            # 创建托盘图标
            self.tray = pystray.Icon("QAura", image, "QAura Master", menu)

    def minimize_to_tray(self):
        # 隐藏主窗口
        self.master.withdraw()
        
        # 检查托盘是否在运行，如果没有则启动
        if not self.tray_running:
            self.tray_running = True
            # 在单独线程中运行托盘，避免阻塞
            threading.Thread(target=self.run_tray, daemon=True).start()
        else:
            self.tray.visible = True

    def run_tray(self):
        # 运行托盘图标
        if self.tray:
            self.tray.run()
            self.tray_running = False

    def show_window(self, icon=None, item=None):
        # 显示主窗口
        self.master.deiconify()
        # 将窗口提到最前
        self.master.lift()
        self.master.attributes('-topmost', True)
        self.master.attributes('-topmost', False)

        # 不停止托盘，只隐藏图标
        if icon:
            icon.visible = False

    def exit_app(self, icon=None, item=None):
        # 停止托盘服务
        if self.tray:
            self.tray.stop()
            self.tray = None
        
        # 销毁主窗口
        self.master.destroy()
        # 退出程序
        sys.exit()
    
    def stray_close_lights(self, icon=None, item=None):
        self.set_mode(-1, 0)

    def stray_static_color(self, icon=None, item=None):
        self.set_mode(-1, 1)

    def stray_rainbow(self, icon=None, item=None):
        self.set_mode(-1, 2)
    
    def stray_breathing(self, icon=None, item=None):
        self.set_mode(-1, 3)
    
    def stray_audio(self, icon=None, item=None):
        self.set_mode(-1, 4)

    def stray_screen(self, icon=None, item=None):
        self.set_mode(-1, 5)
    
    
if __name__ == "__main__":
    root = tk.Tk()
    app = MultiChannelLEDControlApp(root)
    root.mainloop()