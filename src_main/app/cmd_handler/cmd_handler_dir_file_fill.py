import sys, os
import asyncio
import json
from typing import List, Dict, Any

from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from typedef.ai_data_types import ChatResponseStatus
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
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        # 使用新的 ICPChatHandler
        self.chat_handler = ICPChatHandler()
        self.role_name_1 = "4_dir_file_fill"
        self.role_name_2 = "4_dir_file_fill_plan_gen"
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行目录文件填充"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行目录文件填充...{Colors.ENDC}")
        
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
            print(f"{self.role_name_1}正在进行第 {attempt + 1} 次尝试...")
            response_content = asyncio.run(self._get_ai_response_1(user_prompt))
            
            # 如果响应为空，说明AI调用失败，继续下一次尝试
            if not response_content:
                print(f"{Colors.WARNING}警告: AI响应为空，将进行下一次尝试{Colors.ENDC}")
                continue
                
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
            
            # 检查并确保proj_root下有主入口文件
            self._ensure_main_entry_file(new_json_content)
            
            # 保存结果到icp_dir_content_with_files.json
            output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_files.json')
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    # 保存修改后的JSON内容，而不是原始的cleaned_content
                    json.dump(new_json_content, f, indent=2, ensure_ascii=False)
                print(f"目录文件填充完成，结果已保存到: {output_file}")
            except Exception as e:
                print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
                return
                
            # 使用第二个AI handler生成文件级别的实现规划描述
            print(f"{Colors.OKBLUE}开始生成文件级实现规划...{Colors.ENDC}")
            plan_output_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
            self._generate_implementation_plan_2(
                requirement_content, 
                cleaned_content, 
                plan_output_file
            )
            return  # 成功则退出循环
                
        print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的目录结构{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证目录文件填充命令的前置条件"""
        # 检查需求分析结果文件是否存在
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
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
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查角色1是否已加载
        if not self.chat_handler.has_role(self.role_name_1):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name_1} 未加载{Colors.ENDC}")
            return False
        
        # 检查角色2是否已加载
        if not self.chat_handler.has_role(self.role_name_2):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name_2} 未加载{Colors.ENDC}")
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
            return
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        # 优先检查是否有dir_file_fill_handler配置
        if 'dir_file_fill_handler' in config:
            chat_api_config = config['dir_file_fill_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少dir_file_fill_handler或coder_handler配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载两个角色的系统提示词
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name_1 = self.role_name_1 + ".md"
        prompt_file_name_2 = self.role_name_2 + ".md"
        sys_prompt_path_1 = os.path.join(prompt_dir, prompt_file_name_1)
        sys_prompt_path_2 = os.path.join(prompt_dir, prompt_file_name_2)
        
        # 从文件加载角色提示词
        self.chat_handler.load_role_from_file(self.role_name_1, sys_prompt_path_1)
        self.chat_handler.load_role_from_file(self.role_name_2, sys_prompt_path_2)
    
    def _ensure_main_entry_file(self, json_content: Dict) -> None:
        """检查并确保proj_root下有主入口文件"""
        import re
        
        if "proj_root" not in json_content:
            return
        
        proj_root = json_content["proj_root"]
        if not isinstance(proj_root, dict):
            return
        
        # 常见主入口文件命名模式（不区分大小写）
        main_patterns = [
            r'^main$',
            r'^Main$',
            r'^app$',
            r'^App$',
            r'^index$',
            r'^Index$',
            r'^run$',
            r'^Run$',
            r'^start$',
            r'^Start$',
            r'^launcher$',
            r'^Launcher$',
            r'^bootstrap$',
            r'^Bootstrap$'
        ]
        
        # 检查proj_root直接子节点是否有主入口文件
        has_main_entry = False
        for key, value in proj_root.items():
            # 只检查文件节点（值为字符串的节点）
            if isinstance(value, str):
                # 使用正则表达式匹配
                for pattern in main_patterns:
                    if re.match(pattern, key, re.IGNORECASE):
                        has_main_entry = True
                        print(f"{Colors.OKGREEN}检测到主入口文件: {key}{Colors.ENDC}")
                        break
            if has_main_entry:
                break
        
        # 如果没有找到主入口文件，添加一个
        if not has_main_entry:
            # 优先使用 'main' 作为主入口文件名
            main_file_name = 'main'
            
            # 如果 'main' 已经被用作目录名，尝试其他名称
            if main_file_name in proj_root and isinstance(proj_root[main_file_name], dict):
                for alt_name in ['app', 'index', 'run', 'start', 'launcher']:
                    if alt_name not in proj_root or not isinstance(proj_root[alt_name], dict):
                        main_file_name = alt_name
                        break
            
            # 添加主入口文件
            proj_root[main_file_name] = "主入口程序，执行初始化并启动程序"
            print(f"{Colors.OKGREEN}未检测到主入口文件，已自动添加: {main_file_name}{Colors.ENDC}")
    
    def _generate_implementation_plan_2(
        self,
        requirement_content: str,
        dir_file_content: str,
        output_file_path: str
    ) -> None:
        """生成文件级实现规划描述"""
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return
        
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'dir_file_fill_plan_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_ORIGINAL_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('REFINED_REQUIREMENTS_PLACEHOLDER', requirement_content)
        user_prompt = user_prompt.replace('DIR_FILE_CONTENT_PLACEHOLDER', dir_file_content)
        
        # 调用AI生成实现规划
        response_content = asyncio.run(self._get_ai_response_2(user_prompt))
        cleaned_content = response_content.strip()
        
        # 移除可能的代码块标记
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()
        
        # 保存实现规划
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKGREEN}文件级实现规划已生成并保存到: {output_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存实现规划失败: {e}{Colors.ENDC}")
    
    async def _get_ai_response_1(self, user_prompt: str) -> str:
        """异步获取AI响应（处理器1）"""
        print(f"{self.role_name_1}正在填充目录文件...")
        
        response_content, status = await self.chat_handler.get_role_response(
            role_name=self.role_name_1,
            user_prompt=user_prompt
        )
        
        if status == ChatResponseStatus.SUCCESS:
            print(f"\n{self.role_name_1}运行完毕。")
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
    
    async def _get_ai_response_2(self, user_prompt: str) -> str:
        """异步获取AI响应（处理器2）"""
        print(f"{self.role_name_2}正在生成实现规划...")
        
        response_content, status = await self.chat_handler.get_role_response(
            role_name=self.role_name_2,
            user_prompt=user_prompt
        )
        
        if status == ChatResponseStatus.SUCCESS:
            print(f"\n{self.role_name_2}运行完毕。")
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