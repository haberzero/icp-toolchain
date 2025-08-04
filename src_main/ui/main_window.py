import sys
import os
import json
import asyncio
from threading import Thread

from typing import Callable, Optional, Dict, List
from dataclasses import dataclass
from threading import Thread
from queue import Queue, Empty
from enum import Enum

from src_main.cfg import proj_cfg_manager
from src_main.cfg import ui_comm_inst

import tkinter as tk
from tkinter import ttk



# 主应用类
class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MCCP-Toolchain")
        self.root.geometry("1280x720")
        
        # 初始化ui组件
        self.setup_ui()
        
        # 初始化中间层实例
        self.config_manager = proj_cfg_manager.get_instance()
        self.ui_comm_inst = ui_comm_inst.get_instance()

        # 初始化队列
        self.ui_queue = Queue()
        
        # 启动UI更新
        self.update_display()

    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # 文本显示框
        self.text_display = tk.Text(main_frame, wrap=tk.WORD, state=tk.DISABLED)
        text_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.text_display.yview)
        self.text_display.configure(yscrollcommand=text_scrollbar.set)
        
        # 文本输入框
        self.text_input = ttk.Entry(main_frame)
        self.text_input.bind("<Return>", lambda event: self.send_message())
        
        # 确认按钮
        self.send_button = ttk.Button(main_frame, text="发送", command=self.send_message)
        
        # 布局
        self.text_display.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 5))
        text_scrollbar.grid(row=0, column=2, sticky="ns", pady=(0, 5))
        self.text_input.grid(row=1, column=0, sticky="we", pady=(0, 5))
        self.send_button.grid(row=1, column=1, pady=(0, 5), padx=(5, 0))
        
        # 配置列权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

    def send_message(self):
        pass
        # user_input = self.text_input.get()
        # if not user_input.strip():
        #     return
            
        # # 清空输入框
        # self.text_input.delete(0, tk.END)
        
        # # 在显示框中显示用户输入
        # self.append_to_display(f"用户: {user_input}\n\n")
        
        # # 设置上下文并启动处理
        # self.ui_comm_inst.user_input = user_input
        # self.ui_comm_inst.current_model_index = 0
        # self.ui_comm_inst.model_outputs = []
        # self.set_ui_state(False)

    def ai_processing_loop(self):
        """AI处理主循环"""
        while True:
            # 确定下一个状态
            next_state = self.ui_comm_inst.get_next_state()
            
            # 如果状态发生变化，执行相应逻辑
            if self.ui_comm_inst.current_state != self.ui_comm_inst.next_state:
                self.ui_comm_inst.current_state = self.ui_comm_inst.next_state
                self.state_machine.execute_state_logic()
            
            # 如果是完成状态，通知UI启用控件
            if self.ui_comm_inst.current_state == AppState.DONE:
                self.ui_queue.put(("UI_STATE", True))
                self.ui_comm_inst.current_state = AppState.IDLE

    def append_to_display(self, text: str):
        self.text_display.config(state=tk.NORMAL)
        self.text_display.insert(tk.END, text)
        self.text_display.config(state=tk.DISABLED)
        self.text_display.see(tk.END)

    def clear_display(self):
        """清空显示框"""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        self.text_display.config(state=tk.DISABLED)

    def set_ui_state(self, enabled: bool):
        """设置UI组件的启用/禁用状态"""
        state = 'normal' if enabled else 'disabled'
        self.text_input.config(state=state)
        self.send_button.config(state=state)

    def update_display(self):
        """更新UI显示"""
        while True:
            try:
                message = self.ui_queue.get_nowait()
                
                # 处理特殊消息
                if isinstance(message, tuple):
                    msg_type, msg_data = message
                    if msg_type == "CLEAR":
                        self.clear_display()
                    elif msg_type == "UI_STATE":
                        self.set_ui_state(msg_data)
                else:
                    # 普通文本消息
                    self.append_to_display(message)
            except Empty:
                break
                
        # 每100ms刷新一次
        self.root.after(100, self.update_display)

    def run(self):
        self.root.mainloop()
