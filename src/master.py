import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, scrolledtext
import requests
import threading
import socket
import time
from PIL import Image, ImageTk



esp32_ip = "172.20.10.2"

def send_color(r, g, b):
        try:
            response = requests.get(
                f"http://{esp32_ip}/set_color", 
                params={"r": r, "g": g, "b": b},
                timeout=2
            )
            print(f"颜色设置成功: RGB({r},{g},{b})")
            print(f"设置颜色: R={r}, G={g}, B={b}")
        except Exception as e:
            print(f"错误: {str(e)}")

if __name__ == "__main__":
    while(1):
        r=input("请输入r")
        g=input("请输入g")
        b=input("请输入b")
        send_color(r,g,b)


