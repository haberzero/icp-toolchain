# 信息交换层，当以命令行模式运行时，与外部命令行指令进行数据交互。
# 此文件不会涉及和另外几个app.thread的交互。会直接根据用户输入调用对应的cmd_handler.execute()功能
import sys
import os
import json
import asyncio
import time
import signal
import re
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass
from threading import Thread
from queue import Queue, Empty
from enum import Enum

from typedef.cmd_data_types import Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager
from .cmd_handler.command_manager import CommandManager


def signal_handler(sig, frame):
    """处理键盘中断信号"""
    print(f"\n{Colors.WARNING}程序被用户中断{Colors.ENDC}")
    sys.exit(0)


class IcpCmdCli:
    def __init__(self):
        # 初始化管理器和命令处理器
        self.proj_cfg_manager = get_proj_cfg_manager()
        self.command_manager = CommandManager()

    def start_cli(self):
        """启动CLI交互模式"""
        # 初始化命令内容
        print("初始化命令管理器，注册所有命令...")
        self.command_manager.register_all_commands()

        # 注册信号处理器来处理键盘中断
        signal.signal(signal.SIGINT, signal_handler)
        
        print("欢迎使用 ICP - Intent Code Protocol 命令行工具")
        print("当前工作目录:", self.proj_cfg_manager.get_work_dir())
        
        # 显示初始帮助和状态
        self._show_status()
        self._show_help()

        while True:
            try:
                user_input = input("\n请输入命令: ").strip()
                
                # 获取命令处理器
                cmd_handler = self.command_manager.get_command(user_input)
                
                if cmd_handler is None:
                    print("未知命令，请重新输入")
                    continue
                
                # 处理退出命令
                if self.command_manager.is_quit_command(user_input):
                    cmd_handler.execute()
                    break
                
                # 处理帮助命令
                elif self.command_manager.is_help_command(user_input):
                    cmd_handler.execute()
                    continue

                elif not cmd_handler.is_cmd_valid():
                    self._show_status()
                    self._show_help()
                    print(f"{Colors.FAIL}Command invalid. Please check command requirements.{Colors.ENDC}")

                elif cmd_handler.is_cmd_valid():
                    cmd_handler.execute()
                    self._show_status()
                    self._show_help()
                    print(f"\n{Colors.OKGREEN}{'>'*20} 命令执行完成 {'<'*20}{Colors.ENDC}")
                
                else:
                    print(f"{Colors.FAIL}提供给开发者：代码状态有误，请检查运行逻辑{Colors.ENDC}")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"退出运行: {e}")

    def _show_help(self):
        """显示帮助信息"""
        # 获取帮助命令处理器并执行
        help_cmd = self.command_manager.get_command("help")
        if help_cmd:
            help_cmd.execute()
    
    def _show_status(self):
        """显示当前状态"""
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
        
        print(f"{Colors.HEADER}{Colors.BOLD}项目状态:{Colors.ENDC}")
        work_dir = self.proj_cfg_manager.get_work_dir()
        print(f"  {Colors.OKBLUE}工作目录:{Colors.ENDC} {work_dir}")
        
        # 遍历所有命令，显示它们的状态
        for cmd_handler in self.command_manager.get_all_commands():
            cmd_info = cmd_handler.command_info
            # 跳过退出和帮助命令，因为它们的状态显示方式不同
            if cmd_info.name in ["quit", "help"]:
                continue
                
            if cmd_handler.is_cmd_valid():
                print(f"  {Colors.OKBLUE}{cmd_info.name}:{Colors.ENDC} {Colors.OKGREEN}已就绪{Colors.ENDC}")
            else:
                print(f"  {Colors.OKBLUE}{cmd_info.name}:{Colors.ENDC} {Colors.FAIL}未就绪{Colors.ENDC}")
        
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
