from abc import ABC, abstractmethod

from typedef.cmd_data_types import CommandInfo, CmdProcStatus


class BaseCmdHandler(ABC):
    """基础命令处理器抽象类"""
    
    def __init__(self):
        self.command_info: CommandInfo
    
    @abstractmethod
    def execute(self):
        """执行命令的抽象方法，子类必须实现"""
        pass
    
    def get_cmd_proc_status(self):
        """显示命令当前执行状态"""
        if self.is_cmd_valid():
            return CmdProcStatus.DEFAULT
    
    def is_cmd_valid(self):
        """检查命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证命令执行所需的文件存在性和内容有效性"""
        # 基类直接默认返回True，子类需根据需要验证自身执行所需的前置条件
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否正确初始化"""
        # 基类直接默认返回True，子类需根据需要验证AI处理器
        return True