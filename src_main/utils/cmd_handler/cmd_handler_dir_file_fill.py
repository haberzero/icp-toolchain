import sys, os
import asyncio
import json
from typing import List, Dict, Any

from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.ai_handler.chat_handler import ChatHandler
from libs.dir_json_funcs import DirJsonFuncs


DEBUG_FLAG = False


class CmdHandlerDirFileFill(BaseCmdHandler):
    """目录文件填充指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="dir_file_fill",
            aliases=["DF"],
            description="在目录结构中添加功能文件描述",
            help_text="根据需求分析结果在目录结构中添加功能文件描述",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.proj_data_dir, 'icp_api_config.json')

        self.ai_handler: ChatHandler
        self.role_name = "4_dir_file_fill"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行目录文件填充"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行目录文件填充...{Colors.ENDC}")
        
        # 读取需求分析结果
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.md')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return
            
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: 需求分析结果为空{Colors.ENDC}")
            return
            
        # 读取目录结构
        dir_structure_file = os.path.join(self.proj_data_dir, 'icp_dir_content.json')
        try:
            with open(dir_structure_file, 'r', encoding='utf-8') as f:
                dir_structure_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录结构失败: {e}{Colors.ENDC}")
            return
            
        if not dir_structure_content:
            print(f"  {Colors.FAIL}错误: 目录结构内容为空{Colors.ENDC}")
            return
            
        # 读取原始目录结构用于后续比对
        try:
            old_json_content = json.loads(dir_structure_content)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 原始目录结构不是有效的JSON格式: {e}{Colors.ENDC}")
            return

        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'dir_file_fill_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return
            
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('PROGRAMMING_REQUIREMENT_PLACEHOLDER', requirement_content)
        user_prompt = user_prompt.replace('JSON_STRUCTURE_PLACEHOLDER', dir_structure_content)
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            response_content = asyncio.run(self._get_ai_response(self.ai_handler, user_prompt))
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
                new_json_content = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
                print(f"AI返回内容: {cleaned_content}")
                continue
            
            # 检查新JSON内容结构是否与旧JSON内容结构一致
            if not DirJsonFuncs.compare_structure(old_json_content, new_json_content):
                print(f"{Colors.WARNING}警告: 第 {attempt + 1} 次尝试生成的JSON结构不符合要求，正在重新生成...{Colors.ENDC}")
                continue
                
            # 检查新添加的节点是否都为字符串类型
            if not DirJsonFuncs.check_new_nodes_are_strings(new_json_content):
                print(f"{Colors.WARNING}警告: 第 {attempt + 1} 次尝试生成的JSON包含非字符串类型的叶子节点，正在重新生成...{Colors.ENDC}")
                continue
            
            # 保存结果到icp_dir_content_with_files.json
            output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_files.json')
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                print(f"目录文件填充完成，结果已保存到: {output_file}")
                return  # 成功则退出循环
            except Exception as e:
                print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
                return
                
        print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的目录结构{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证目录文件填充命令的前置条件"""
        # 检查需求分析结果文件是否存在
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.md')
        if not os.path.exists(requirement_analysis_file):
            print(f"  {Colors.WARNING}警告: 需求分析结果文件不存在，请先执行需求分析命令{Colors.ENDC}")
            return False
            
        # 检查目录结构文件是否存在
        dir_structure_file = os.path.join(self.proj_data_dir, 'icp_dir_content.json')
        if not os.path.exists(dir_structure_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行目录生成命令{Colors.ENDC}")
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
        """检查目录文件填充命令的必要条件是否满足"""
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
        
        # 优先检查是否有dir_file_fill_handler配置
        if 'dir_file_fill_handler' in config:
            chat_api_config = config['dir_file_fill_handler']
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
            print("错误: 配置文件缺少dir_file_fill_handler或coder_handler配置")
            return None

        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        sys_prompt_path = os.path.join(prompt_dir, prompt_file_name)

        return ChatHandler(handler_config, self.role_name, sys_prompt_path)
    
    async def _get_ai_response(self, handler: ChatHandler, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name}正在填充目录文件...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content