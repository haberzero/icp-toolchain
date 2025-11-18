import sys, os
import asyncio
import json
from typing import List

from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from libs.ai_interface.chat_interface import ChatInterface


DEBUG_FLAG = False


class CmdHandlerParaExtract(BaseCmdHandler):
    """用户需求分支指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="para_extract",
            aliases=["PE"],
            description="从用户初始编程需求中提取参数",
            help_text="对用户需求进行解析，并且从中提取出关键的参数，供后续步骤使用",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        self.ai_handler: ChatInterface
        self.role_name = "1_param_extractor"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行参数提取"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始提取参数...{Colors.ENDC}")
        requirement_content = get_user_data_manager().get_user_prompt()
        response_content = asyncio.run(self._get_ai_response(self.ai_handler, requirement_content))
        cleaned_content = response_content.strip()

        # 移除可能的代码块标记
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()

        if DEBUG_FLAG:
            print(f"{Colors.HEADER}{Colors.BOLD}参数提取结果:{Colors.ENDC}")
            print(cleaned_content)
        
        # 保存结果到extracted_params.json
        os.makedirs(self.proj_data_dir, exist_ok=True)
        output_file = os.path.join(self.proj_data_dir, 'extracted_params.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"参数提取完成，结果已保存到: {output_file}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证参数提取命令的前置条件"""
        # 检查用户需求内容是否存在
        requirement_content = get_user_data_manager().get_user_prompt()
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: {self.role_name} 未找到用户需求内容，请先提供需求内容{Colors.ENDC}")
            return False
            
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查AI处理器是否初始化成功
        if not hasattr(self, 'ai_handler') or self.ai_handler is None:
            print(f"  {Colors.FAIL}错误: {self.role_name} AI处理器未正确初始化{Colors.ENDC}")
            return False
            
        # 检查AI处理器是否连接成功
        if not hasattr(self.ai_handler, 'llm') or self.ai_handler.llm is None:
            print(f"  {Colors.FAIL}错误: {self.role_name} AI模型连接失败{Colors.ENDC}")
            return False
            
        return True

    def is_cmd_valid(self):
        """检查参数提取命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _init_ai_handlers(self):
        """初始化AI处理器"""
        
        # 检查配置文件是否存在
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在，请创建该文件并填充必要内容")
            return None
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return None
        
        # 优先检查是否有para-extract-handler配置
        if 'para_extract_handler' in config:
            chat_api_config = config['para_extract_handler']
            handler_config = ChatApiConfig(
                base_url=chat_api_config.get('api-url', ''),
                api_key=SecretStr(chat_api_config.get('api-key', '')),
                model=chat_api_config.get('model', '')
            )
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
            handler_config = ChatApiConfig(
                base_url=chat_api_config.get('api-url', ''),
                api_key=SecretStr(chat_api_config.get('api-key', '')),
                model=chat_api_config.get('model', '')
            )
        else:
            print("错误: 配置文件缺少para_extract_handler或coder_handler配置")
            return None

        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        sys_prompt_path = os.path.join(prompt_dir, prompt_file_name)

        return ChatInterface(handler_config, self.role_name, sys_prompt_path)

    async def _get_ai_response(self, handler: ChatInterface, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name}正在进行参数提取...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content