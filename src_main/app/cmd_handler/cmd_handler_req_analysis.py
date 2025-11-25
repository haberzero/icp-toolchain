import sys, os
import asyncio
import json
from typing import List

from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from typedef.ai_data_types import ChatResponseStatus


DEBUG_FLAG = False


class CmdHandlerReqAnalysis(BaseCmdHandler):
    """需求分析指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="req_analysis",
            aliases=["RA"],
            description="对用户需求进行结构化分析",
            help_text="对用户需求进行深入分析，生成技术选型和模块拆解",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        self.chat_handler = ICPChatHandler()
        self.role_name = "2_req_to_module"
        self._init_ai_handlers()

    def execute(self):
        """执行需求分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行需求分析...{Colors.ENDC}")
        requirement_content = get_user_data_manager().get_user_prompt()
        response_content = asyncio.run(self._get_ai_response(requirement_content))
        
        if not response_content:
            print(f"{Colors.WARNING}警告: AI响应为空{Colors.ENDC}")
            return
            
        cleaned_content = response_content.strip()

        # 移除可能的代码块标记
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()

        if DEBUG_FLAG:
            print(f"{Colors.HEADER}{Colors.BOLD}需求分析结果:{Colors.ENDC}")
            print(cleaned_content)
        
        # 保存结果到refined_requirements.json
        os.makedirs(self.proj_data_dir, exist_ok=True)
        output_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"需求分析完成，结果已保存到: {output_file}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证需求分析命令的前置条件"""
        # 检查用户需求内容是否存在
        requirement_content = get_user_data_manager().get_user_prompt()
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: {self.role_name} 未找到用户需求内容，请先提供需求内容{Colors.ENDC}")
            return False
            
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
            return False
        return True

    def is_cmd_valid(self):
        """检查需求分析命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _init_ai_handlers(self):
        """初始化AI处理器"""
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在")
            return
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        if 'req_analysis_handler' in config:
            chat_api_config = config['req_analysis_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少req_analysis_handler或coder_handler配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, self.role_name + ".md")
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)

    async def _get_ai_response(self, user_prompt: str) -> str:
        """异步获取AI响应"""
        print(f"{self.role_name}正在进行需求分析...")
        
        response_content, status = await self.chat_handler.get_role_response(
            role_name=self.role_name,
            user_prompt=user_prompt
        )
        
        if status == ChatResponseStatus.SUCCESS:
            print(f"\n{self.role_name}运行完毕。")
            return response_content
        elif status == ChatResponseStatus.CLIENT_NOT_INITIALIZED:
            print(f"\n{Colors.FAIL}错误: ChatInterface未初始化{Colors.ENDC}")
            return ""
        elif status == ChatResponseStatus.STREAM_FAILED:
            print(f"\n{Colors.FAIL}错误: 流式响应失败{Colors.ENDC}")
            return ""
        else:
            print(f"\n{Colors.FAIL}错误: 未知状态 {status}{Colors.ENDC}")
            return ""