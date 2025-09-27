from typing import List

from typedef.data_types import CommandInfo, Colors, CmdProcStatus
from utils.cmd_handler.base_cmd_handler import BaseCmdHandler


class CmdHandlerHelp(BaseCmdHandler):
    """帮助指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="help",
            aliases=["h", "?"],
            description="显示帮助信息",
            help_text="显示所有可用命令及其描述",
        )
        self.command_list = []
    
    def execute(self):
        """显示帮助信息"""
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}可用命令:{Colors.ENDC}")

        for cmd_handler in self.command_list:
            cmd_info = cmd_handler.command_info
            aliases_str = ' / '.join([cmd_info.name] + cmd_info.aliases)
            print(f"  {Colors.OKGREEN}{aliases_str:<20}{Colors.ENDC} {cmd_info.description}")
        
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
    
    def set_help_command_list(self, command_list: List[BaseCmdHandler]):
        """设置命令列表"""
        self.command_list = command_list