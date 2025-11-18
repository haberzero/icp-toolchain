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
        self.icp_api_config_file = os.path.join(self.proj_data_dir, 'icp_api_config.json')

        self.ai_handler: ChatInterface
        self.role_name = "3_module_to_dir"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

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
        
        # 过滤掉ExternalLibraryDependencies字段
        try:
            requirement_json = json.loads(requirement_content)
            # 移除ExternalLibraryDependencies字段，因为module_to_dir只关注模块结构，不关注外部库
            if 'ExternalLibraryDependencies' in requirement_json:
                del requirement_json['ExternalLibraryDependencies']
            # 将过滤后的内容转换回JSON字符串
            filtered_requirement_content = json.dumps(requirement_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 需求分析结果不是有效的JSON格式: {e}{Colors.ENDC}")
            return

        response_content = asyncio.run(self._get_ai_response(self.ai_handler, filtered_requirement_content))
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
        """检查目录生成命令的必要条件是否满足"""
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
        
        # 优先检查是否有dir_generate_handler配置
        if 'dir_generate_handler' in config:
            chat_api_config = config['dir_generate_handler']
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
            print("错误: 配置文件缺少dir_generate_handler或coder_handler配置")
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
            
        print(f"{self.role_name}正在生成目录结构...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content