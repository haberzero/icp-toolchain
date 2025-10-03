from typing import Dict, List, Optional

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.cmd_handler.cmd_handler_quit import CmdHandlerQuit
from utils.cmd_handler.cmd_handler_help import CmdHandlerHelp
from utils.cmd_handler.cmd_handler_para_extract import CmdHandlerParaExtract
from utils.cmd_handler.cmd_handler_req_analysis import CmdHandlerReqAnalysis
from utils.cmd_handler.cmd_handler_module_to_dir import CmdHandlerModuleToDir
from utils.cmd_handler.cmd_handler_dir_file_fill import CmdHandlerDirFileFill
from utils.cmd_handler.cmd_handler_depend_analysis import CmdHandlerDependAnalysis
from utils.cmd_handler.cmd_handler_depend_refine import CmdHandlerDependRefine
from utils.cmd_handler.cmd_handler_one_file_req_gen import CmdHandlerOneFileReqGen
from utils.cmd_handler.cmd_handler_icb_gen import CmdHandlerIcbGen
from utils.cmd_handler.cmd_handler_icb_to_target_code import CmdHandlerIcbToTargetCode

# TODO: 是否有必要进行倒置？给CommandManager实现一个register_command()方法，让各个CmdHandler注册自己？随后单独做一个工厂类放一个文件？

class CommandManager:
    def __init__(self):
        self.commands_map: Dict[str, BaseCmdHandler] = {}
        self.commands_list: List[BaseCmdHandler] = []
    
    def register_all_commands(self):
        """注册命令全写和所有别名"""
        self.commands_list = self._create_all_commands()
        for _cmd_handler in self.commands_list:
            _cmd_name = _cmd_handler.command_info.name
            _alisas = _cmd_handler.command_info.aliases
            self.commands_map[_cmd_name] = _cmd_handler
            for _alias in _alisas:
                self.commands_map[_alias] = _cmd_handler
    
    def get_command(self, command_name: str) -> Optional[BaseCmdHandler]:
        """根据命令名称获取命令处理器"""
        return self.commands_map.get(command_name)
    
    def get_all_commands(self) -> List[BaseCmdHandler]:
        """获取所有命令处理器"""
        return self.commands_list
    
    def is_quit_command(self, command_name: str) -> bool:
        """判断是否为退出命令"""
        cmd_handler = self.commands_map.get(command_name)
        if cmd_handler:
            return isinstance(cmd_handler, CmdHandlerQuit)
        return False
    
    def is_help_command(self, command_name: str) -> bool:
        """判断是否为帮助命令"""
        cmd_handler = self.commands_map.get(command_name)
        if cmd_handler:
            return isinstance(cmd_handler, CmdHandlerHelp)
        return False
    
    @staticmethod
    def _create_all_commands() -> List[BaseCmdHandler]:
        """创建所有命令处理器实例"""
        commands = []
        
        # 退出命令
        quit_cmd = CmdHandlerQuit()
        commands.append(quit_cmd)
        
        # 帮助命令
        help_cmd = CmdHandlerHelp()
        commands.append(help_cmd)
        
        # 参数提取命令
        para_extract_cmd = CmdHandlerParaExtract()
        commands.append(para_extract_cmd)
        
        # 需求分析命令
        req_analysis_cmd = CmdHandlerReqAnalysis()
        commands.append(req_analysis_cmd)
        
        # 目录生成命令
        dir_generate_cmd = CmdHandlerModuleToDir()
        commands.append(dir_generate_cmd)

        # 目录文件描述填充命令
        dir_file_fill_cmd = CmdHandlerDirFileFill()
        commands.append(dir_file_fill_cmd)
        
        # 依赖分析命令
        depend_analysis_cmd = CmdHandlerDependAnalysis()
        commands.append(depend_analysis_cmd)
        
        # 依赖重构命令
        dependency_refine_cmd = CmdHandlerDependRefine()
        commands.append(dependency_refine_cmd)

        # 单文件需求描述创建命令
        one_file_req_cmd = CmdHandlerOneFileReqGen()
        commands.append(one_file_req_cmd)

        # 半自然语言行为描述代码生成命令
        intent_code_behavior_gen_cmd = CmdHandlerIcbGen()
        commands.append(intent_code_behavior_gen_cmd)

        # ICB到目标代码转换命令
        icb_to_target_code_cmd = CmdHandlerIcbToTargetCode()
        commands.append(icb_to_target_code_cmd)

        # 设置帮助命令的命令列表
        help_cmd.set_help_command_list(commands)
        
        return commands