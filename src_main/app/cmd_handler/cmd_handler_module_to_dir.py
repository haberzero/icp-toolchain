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


class CmdHandlerModuleToDir(BaseCmdHandler):
    """目录结构生成指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="module_to_dir",
            aliases=["MTD"],
            description="根据需求分析结果生成项目目录结构",
            help_text="基于需求分析生成标准化的项目目录结构",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        self.chat_handler = ICPChatHandler()
        self.role_name = "3_module_to_dir"
        self._init_ai_handlers()

    def execute(self):
        """执行目录结构生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成目录结构...{Colors.ENDC}")
        
        # 读取需求分析结果
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return
            
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: 需求分析结果为空{Colors.ENDC}")
            return
        
        # 过滤掉ExternalLibraryDependencies字段，并移除module_breakdown下各模块的dependencies字段
        try:
            requirement_json = json.loads(requirement_content)
            # 移除ExternalLibraryDependencies字段，因为module_to_dir只关注模块结构，不关注外部库
            if 'ExternalLibraryDependencies' in requirement_json:
                del requirement_json['ExternalLibraryDependencies']
            # 移除module_breakdown中各子模块的dependencies字段，避免干扰目录结构生成判断
            if 'module_breakdown' in requirement_json and isinstance(requirement_json['module_breakdown'], dict):
                for module in requirement_json['module_breakdown'].values():
                    if isinstance(module, dict) and 'dependencies' in module:
                        del module['dependencies']
            # 将过滤后的内容转换回JSON字符串
            filtered_requirement_content = json.dumps(requirement_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 需求分析结果不是有效的JSON格式: {e}{Colors.ENDC}")
            return

        response_content = asyncio.run(self._get_ai_response(filtered_requirement_content))
        
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
        
        # 验证是否为有效的JSON
        try:
            json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_content}")
            return

        if DEBUG_FLAG:
            print(f"{Colors.HEADER}{Colors.BOLD}目录结构生成结果:{Colors.ENDC}")
            print(cleaned_content)
        
        # 保存结果到icp_dir_content.json
        output_file = os.path.join(self.proj_data_dir, 'icp_dir_content.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"目录结构生成完成，结果已保存到: {output_file}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证目录生成命令的前置条件"""
        # 检查需求分析结果文件是否存在
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        if not os.path.exists(requirement_analysis_file):
            print(f"  {Colors.WARNING}警告: 需求分析结果文件不存在，请先执行需求分析命令{Colors.ENDC}")
            return False
        
        return True

    def _check_ai_handler(self) -> bool:
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
            return False
        return True

    def is_cmd_valid(self):
        """检查目录生成命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _init_ai_handlers(self):
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在")
            return
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        if 'dir_generate_handler' in config:
            chat_api_config = config['dir_generate_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少配置")
            return
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        app_data_manager = get_app_data_manager()
        sys_prompt_path = os.path.join(app_data_manager.get_prompt_dir(), self.role_name + ".md")
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)
    
    async def _get_ai_response(self, user_prompt: str) -> str:
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            print(content, end="", flush=True)
        print(f"{self.role_name}正在生成目录结构...")
        status = await self.chat_handler.get_role_response(self.role_name, user_prompt, collect_response)
        if status == ChatResponseStatus.SUCCESS:
            print(f"\n{self.role_name}运行完毕。")
            return response_content
        print(f"\n{Colors.FAIL}错误: 响应失败 {status}{Colors.ENDC}")
        return ""