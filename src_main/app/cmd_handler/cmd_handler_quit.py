import sys
from typing import List

from typedef.cmd_data_types import CommandInfo, CmdProcStatus
from .base_cmd_handler import BaseCmdHandler


class CmdHandlerQuit(BaseCmdHandler):
    """退出指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="quit",
            aliases=["exit", "q"],
            description="退出程序 (或ctrl + c 以后按下回车)",
            help_text="使用此命令退出IBC工具",
        )
    
    def execute(self):
        """执行退出命令"""
        # TODO: 未来多线程？发送信号，等待所有线程处理信号并自行结束
        print("退出程序")
        sys.exit(0)