from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

class AudioMonitor:
    def __init__(self):
        # 初始化音频计量器
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioMeterInformation._iid_, 
            CLSCTX_ALL, 
            None
        )
        self.meter = cast(interface, POINTER(IAudioMeterInformation))
        
        # 存储历史数据
        self.peak_history = []
        self.timestamps = []
        
    def get_peak_value(self):
        return self.meter.GetPeakValue()
    
    def monitor_audio(self, duration=10, interval=0.1):
        """监控音频并记录数据"""     
        while time.time() - start_time < duration:
            peak = self.get_peak_value()
            current_time = time.time() - start_time
            
            self.peak_history.append(peak)
            self.timestamps.append(current_time)
            
            # 实时显示当前峰值
            print(f"时间: {current_time:.2f}s, 峰值: {peak:.6f}")
            
            time.sleep(interval)
        
        print("监控结束")
    
    def plot_results(self):
        """绘制音频峰值变化图"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.timestamps, self.peak_history, 'b-', label='音频峰值')
        plt.xlabel('时间 (秒)')
        plt.ylabel('峰值 (0.0-1.0)')
        plt.title('系统音频输出峰值变化')
        plt.grid(True)
        plt.legend()
        plt.ylim(0, 1.1)  # 设置Y轴范围
        plt.savefig(f"audio_peak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.show()

# 使用示例
if __name__ == "__main__":
    monitor = AudioMonitor()
    
    # 测试1: 静音状态
    print("=== 测试1: 静音状态 ===")
    monitor.monitor_audio(duration=5000, interval=0.02)
    
    # 测试2: 播放音频
    print("\n=== 测试2: 请播放一些音频 ===")
    input("按回车键开始监控（请确保有音频播放）...")
    monitor.monitor_audio(duration=15, interval=0.1)
    
    # 绘制结果
    monitor.plot_results()