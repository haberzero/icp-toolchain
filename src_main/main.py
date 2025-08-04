import sys
import os
import json
import asyncio
from threading import Thread

from src_main.cfg import proj_cfg_manager
from src_main.cfg import ui_comm_inst

from src_main.ui.main_window import MainWindow

import tkinter as tk
from tkinter import ttk




    # def ai_processing_loop(self):
    #     """AI处理主循环"""
    #     while True:
    #         # 保存当前状态
    #         old_state = self.context.current_state
            
    #         # 更新状态
    #         self.context.update_state()
            
    #         # 如果状态发生变化，执行相应逻辑
    #         if old_state != self.context.current_state:
    #             self.execute_state_logic(old_state)
            
    #         # 如果是完成状态，通知UI启用控件
    #         if self.context.current_state == AppState.DONE:
    #             self.ui_queue.put(("UI_STATE", True))
    #             self.context.reset()
    #             self.context.update_state()  # 重置后更新状态



def main():
    top_proj_cfg_manager = proj_cfg_manager.get_instance()
    # 初始化

    # 初始化主界面
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()



        
        
        # self.ai_processor = AIProcessor(
        #     r"C:\myself\proj\mccp-toolchain\test_scripts\langchian_test_first\mccp_api_config.json",
        #     r"C:\myself\proj\mccp-toolchain\test_scripts\langchian_test_first\mccp_pre_prompt.json"
        # )

        # 启动AI处理线程
        # self.ai_thread = Thread(target=self.ai_processing_loop, daemon=True)
        # self.ai_thread.start()