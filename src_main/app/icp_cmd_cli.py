# 信息交换层，当以命令行模式运行时，与外部命令行指令进行数据交互。
# 使用状态机模式重构，降低代码复杂度，减少嵌套层级
import sys
import os
import time
import signal
import platform
from enum import Enum
from typing import Optional

from typedef.cmd_data_types import Colors
from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from .cmd_handler.command_manager import CommandManager
from .cmd_handler.base_cmd_handler import BaseCmdHandler

# ==================== 状态定义 ====================

class CliState(Enum):
    """CLI状态枚举"""
    WAITING_INPUT = "WAITING_INPUT"      # 等待用户输入
    EXECUTING_COMMAND = "EXECUTING_COMMAND"  # 执行命令中
    EXITING = "EXITING"                  # 退出中


# ==================== 全局状态变量 ====================

_current_cli_state = CliState.WAITING_INPUT
_should_exit = False


# ==================== 信号处理 ====================

def signal_handler(sig, frame):
    """处理键盘中断信号
    
    根据当前状态决定行为：
    - WAITING_INPUT：退出程序
    - EXECUTING_COMMAND：中断命令，返回等待输入
    """
    global _current_cli_state, _should_exit
    
    if _current_cli_state == CliState.EXECUTING_COMMAND:
        # 命令执行中，中断命令
        print(f"\n{Colors.WARNING}命令执行被用户中断{Colors.ENDC}")
        raise KeyboardInterrupt("命令被中断")
    else:
        # 等待输入中，退出程序
        print(f"\n{Colors.WARNING}程序被用户中断，正在退出...{Colors.ENDC}")
        _should_exit = True
        sys.exit(0)

# ==================== CLI主类 ====================

class IcpCmdCli:
    """ICP命令行交互工具
    
    使用状态机模式：
    1. WAITING_INPUT - 等待用户输入命令
    2. EXECUTING_COMMAND - 执行命令
    3. EXITING - 退出程序
    """
    
    def __init__(self):
        self.proj_run_time_cfg = get_proj_run_time_cfg()
        self.command_manager = CommandManager()
        self.current_state = CliState.WAITING_INPUT
        
    def start_cli(self):
        """启动CLI主循环"""
        self._initialize()
        self._run_main_loop()
        self._cleanup()
    
    def _initialize(self):
        """初始化CLI"""
        global _current_cli_state
        
        print("初始化命令管理器，注册所有命令...")
        self.command_manager.register_all_commands()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        
        print("欢迎使用 ICP - Intent Code Protocol 命令行工具")
        print("当前工作目录:", self.proj_run_time_cfg.get_work_dir_path())
        
        self._show_status()
        self._show_help()
        
        _current_cli_state = CliState.WAITING_INPUT
    
    def _run_main_loop(self):
        """运行主循环"""
        global _should_exit
        
        while not _should_exit:
            if self.current_state == CliState.WAITING_INPUT:
                self._handle_waiting_input()
            elif self.current_state == CliState.EXITING:
                break
    
    def _handle_waiting_input(self):
        """处理等待输入状态"""
        global _current_cli_state
        
        try:
            # 设置当前状态
            _current_cli_state = CliState.WAITING_INPUT
            self.current_state = CliState.WAITING_INPUT
            
            # 获取用户输入
            user_input = self._get_user_input()
            if user_input is None:
                return
            
            # 获取命令处理器
            cmd_handler = self.command_manager.get_command(user_input)
            if cmd_handler is None:
                print("未知命令，请重新输入")
                return
            
            # 处理命令
            self._process_command(user_input, cmd_handler)
            
        except KeyboardInterrupt:
            # 等待输入时被中断，退出
            self.current_state = CliState.EXITING
        except EOFError:
            # 处理EOF
            print(f"\n{Colors.WARNING}检测到EOF，正在退出...{Colors.ENDC}")
            self.current_state = CliState.EXITING
        except Exception as e:
            print(f"发生错误: {e}")
            print(f"{Colors.WARNING}返回命令行...{Colors.ENDC}")
    
    def _get_user_input(self) -> Optional[str]:
        """获取用户输入
        
        Returns:
            用户输入的命令，如果被中断则返回None
        """
        try:
            user_input = input("\n请输入命令: ").strip()
            return user_input
        except KeyboardInterrupt:
            # 在input阶段被中断
            raise
    
    def _process_command(self, user_input: str, cmd_handler: BaseCmdHandler):
        """处理命令执行
        
        Args:
            user_input: 用户输入的命令
            cmd_handler: 命令处理器
        """
        # 检查是否为退出命令
        if self.command_manager.is_quit_command(user_input):
            cmd_handler.execute()
            self.current_state = CliState.EXITING
            return
        
        # 检查是否为帮助命令
        if self.command_manager.is_help_command(user_input):
            cmd_handler.execute()
            return
        
        # 检查命令是否有效
        if not cmd_handler.is_cmd_valid():
            self._show_status()
            self._show_help()
            print(f"{Colors.FAIL}Command invalid. Please check command requirements.{Colors.ENDC}")
            return
        
        # 执行命令
        self._execute_command(cmd_handler)
    
    def _execute_command(self, cmd_handler: BaseCmdHandler):
        """执行命令
        
        Args:
            cmd_handler: 命令处理器
        """
        global _current_cli_state
        
        try:
            # 切换到执行状态
            _current_cli_state = CliState.EXECUTING_COMMAND
            self.current_state = CliState.EXECUTING_COMMAND
            
            # 执行命令
            cmd_handler.execute()
            
            # 命令执行成功
            self._show_status()
            self._show_help()
            print(f"\n{Colors.OKGREEN}{'>'*20} 命令执行完成 {'<'*20}{Colors.ENDC}")
            
        except KeyboardInterrupt:
            # 命令执行被中断
            print(f"\n{Colors.WARNING}命令执行被中断，返回命令行{Colors.ENDC}")
        finally:
            # 恢复等待输入状态
            _current_cli_state = CliState.WAITING_INPUT
            self.current_state = CliState.WAITING_INPUT
            time.sleep(0.1)
    
    def _cleanup(self):
        """清理资源"""
        pass

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
        work_dir = self.proj_run_time_cfg.get_work_dir_path()
        print(f"  {Colors.OKBLUE}工作目录:{Colors.ENDC} {work_dir}")
        print(f"  {Colors.OKBLUE}运行平台:{Colors.ENDC} {platform.system()} {platform.release()}")
        
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
