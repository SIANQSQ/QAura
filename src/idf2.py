import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext
import requests
import threading
import socket
import time
import json

LED_Name = ["桌子下","显示器下","显示器上","桌子上","桌子侧","---","---","---"]
class MultiChannelLEDControlApp:
    def __init__(self, master):
        self.master = master
        master.title("QAura Master")
        master.geometry("1000x800")
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('TLabelframe', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        
        # 通道配置
        self.channels = []  # 存储每个通道的状态
        self.esp_ip = tk.StringVar(value="172.20.10.4")  # 默认IP
        self.connection_status = tk.BooleanVar(value=False)
        self.last_known_ip = ""
        self.color_previews = []
        self.ColorSYNC = tk.BooleanVar()  #
        # 创建UI
        self.create_widgets()
        
        # 启动连接监控
        self.monitor_connection()
    
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
                "pin": 4 + i,  # 假设引脚从4开始递增
                "count": 30, 
                "color": "#FFFFFF", 
                "brightness": 100, 
                "speed": 50,
                "mode": 2  # 0=关闭, 1=纯色, 2=彩虹, 3=呼吸
            })

        static_color_frame = ttk.LabelFrame(main_frame, text="静态颜色")
        static_color_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        checkbox1 = tk.Checkbutton(static_color_frame, text="同步颜色", variable=self.ColorSYNC)
        checkbox1.pack(anchor="w", padx=5)

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
        self.diag_text.insert(tk.END, "程序运行日志将显示在这里...\n")
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
        modes = [("关闭", 0), ("纯色", 1), ("彩虹", 2), ("呼吸", 3), ("声音", 4), ("屏幕", 5)]
        
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
        
        # 亮度控制
        brightness_frame = ttk.Frame(parent)
        brightness_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(brightness_frame, text="亮度:").pack(side=tk.LEFT)
        
        brightness = tk.Scale(
            brightness_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self.set_brightness(channel_idx, v)
        )
        brightness.set(100)
        brightness.pack(side=tk.LEFT, padx=5)
        
        # 速度控制
        speed_frame = ttk.Frame(parent)
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(speed_frame, text="速度:").pack(side=tk.LEFT)
        
        speed = tk.Scale(
            speed_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL,
            length=120,
            command=lambda v: self.set_speed(channel_idx, v)
        )
        speed.set(50)
        speed.pack(side=tk.LEFT, padx=5)
        
        # 通道信息
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(info_frame, text=f"引脚:{4+channel_idx} LED:30").pack(side=tk.LEFT)
    
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
                    self.status_bar.config(text=f"已连接到ESP32: {ip}")
                    self.log_diagnostic("连接成功！设备已准备就绪。")
                    
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
            self.log_diagnostic("开始扫描局域网查找ESP32设备...")
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
                self.log_diagnostic("扫描完成，未找到ESP32设备")
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
        if not self.connection_status.get():
            self.test_connection()
            return
            
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
    
    def choose_color(self, channel):
        # if not self.connection_status.get():
        #     self.test_connection()
        #     return
            
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
            if self.ColorSYNC.get():
                Color_sync = 1
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
    
    def set_brightness(self, channel, value):
        if not self.connection_status.get():
            self.test_connection()
            return
            
        try:
            # 更新本地通道状态
            self.channels[channel]["brightness"] = int(value)
            
            response = requests.get(
                f"http://{self.esp_ip.get()}/set_brightness", 
                params={
                    "channel": channel,
                    "value": value
                },
                timeout=2
            )
            self.status_bar.config(text=f"通道 {channel+1} 亮度设置成功: {value}%")
            self.log_diagnostic(f"设置通道 {channel+1} 亮度: {value}%")
        except Exception as e:
            self.status_bar.config(text=f"错误: {str(e)}")
    
    def set_speed(self, channel, value):
        if not self.connection_status.get():
            self.test_connection()
            return
            
        try:
            # 更新本地通道状态
            self.channels[channel]["speed"] = int(value)
            
            response = requests.get(
                f"http://{self.esp_ip.get()}/set_speed", 
                params={
                    "channel": channel,
                    "value": value
                },
                timeout=2
            )
            self.status_bar.config(text=f"通道 {channel+1} 速度设置成功: {value}%")
            self.log_diagnostic(f"设置通道 {channel+1} 速度: {value}%")
        except Exception as e:
            self.status_bar.config(text=f"错误: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiChannelLEDControlApp(root)
    root.mainloop()