import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


class PathSelector:
    def __init__(self, parent, proj_path = ""):
        self.parent = parent
        self.selected_path = proj_path
        self.create_window()
    
    def center_window(self, window, width, height):
        # 获取屏幕尺寸
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 设置窗口位置
        window.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("选择项目路径")
        self.window.resizable(False, False)
        
        # 设置窗口大小并居中
        self.center_window(self.window, 500, 150)
        
        # 居中显示窗口
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # 创建界面元素
        frame = tk.Frame(self.window)
        frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        label = tk.Label(frame, text="请选择项目根路径:")
        label.pack(anchor=tk.W)
        
        # 路径显示框
        path_frame = tk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.path_var = tk.StringVar()
        path_entry = tk.Entry(path_frame, textvariable=self.path_var, state="readonly")
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        if self.selected_path:
            self.path_var.set(self.selected_path)
        
        # 浏览按钮
        browse_button = tk.Button(path_frame, text="浏览...", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 确定和取消按钮 (交换位置)
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        cancel_button = tk.Button(button_frame, text="取消", command=self.cancel)
        cancel_button.pack(side=tk.RIGHT)
        
        ok_button = tk.Button(button_frame, text="确定", command=self.confirm_path)
        ok_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # 设置窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def browse_path(self):
        # 根据操作系统选择适当的初始目录
        initial_dir = os.path.expanduser("~")
        path = filedialog.askdirectory(
            parent=self.window,
            title="选择项目根目录",
            initialdir=initial_dir
        )
        
        if path:
            self.selected_path = path
            self.path_var.set(path)
    
    def confirm_path(self):
        if not self.selected_path:
            # 如果没有选择路径，提示用户
            messagebox.showwarning("警告", "请选择一个有效的路径")
            return
        
        self.window.destroy()

    def get_selected_path(self):
        return self.selected_path
    
    def cancel(self):
        self.selected_path = None
        self.window.destroy()