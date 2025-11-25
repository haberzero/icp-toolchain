import sys, os
import asyncio
import json
from typing import List, Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs



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
        self.role_dir_file_fill = "4_dir_file_fill"
        self.role_plan_gen = "4_dir_file_fill_plan_gen"
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行目录文件填充"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行目录文件填充...{Colors.ENDC}")

        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_dir_file_filler()
        if not user_prompt:
            return
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_dir_file_fill}正在进行第 {attempt + 1} 次尝试...")
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_dir_file_fill,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
                
            # 清理代码块标记
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid, new_json_content = self._validate_dir_fill_response(cleaned_content, self.old_json_content)
            if is_valid:
                break
        
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的目录结构{Colors.ENDC}")
            return

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

        #### 开始生成文件级别的实现规划描述 ####
        print(f"{Colors.OKBLUE}开始生成文件级实现规划...{Colors.ENDC}")

        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_plan_generator()
        if not user_prompt:
            return
        
        # 调用AI生成实现规划
        for attempt in range(max_attempts):
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_plan_gen,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
            
            # 清理代码块标记并退出运行
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            break
        
        # 保存实现规划
        output_file_path = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKGREEN}文件级实现规划已生成并保存到: {output_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存实现规划失败: {e}{Colors.ENDC}")

    def _build_user_prompt_for_dir_file_filler(self) -> str:
        """
        构建目录文件填充的用户提示词（role_name_1）
        
        从项目数据目录中读取所需文件，无需外部参数输入。
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取需求分析结果
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return ""
            
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: 需求分析结果为空{Colors.ENDC}")
            return ""
            
        # 读取目录结构
        dir_structure_file = os.path.join(self.proj_data_dir, 'icp_dir_content.json')
        try:
            with open(dir_structure_file, 'r', encoding='utf-8') as f:
                dir_structure_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录结构失败: {e}{Colors.ENDC}")
            return ""
            
        if not dir_structure_content:
            print(f"  {Colors.FAIL}错误: 目录结构内容为空{Colors.ENDC}")
            return ""
        self.old_json_content = json.loads(dir_structure_content)

        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'dir_file_fill_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('PROGRAMMING_REQUIREMENT_PLACEHOLDER', requirement_content)
        user_prompt = user_prompt.replace('JSON_STRUCTURE_PLACEHOLDER', dir_structure_content)
        
        return user_prompt

    def _build_user_prompt_for_plan_generator(self) -> str:
        """
        构建文件级实现规划生成的用户提示词（role_name_2）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return ""
        
        # 读取精炼需求内容
        requirement_analysis_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return ""
        
        # 读取目录文件内容
        dir_file_path = os.path.join(self.proj_data_dir, 'icp_dir_content_filled.json')
        try:
            with open(dir_file_path, 'r', encoding='utf-8') as f:
                dir_file_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录文件内容失败: {e}{Colors.ENDC}")
            return ""

        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'dir_file_fill_plan_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_ORIGINAL_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('REFINED_REQUIREMENTS_PLACEHOLDER', requirement_content)
        user_prompt = user_prompt.replace('DIR_FILE_CONTENT_PLACEHOLDER', dir_file_content)
        
        return user_prompt

    def _validate_dir_fill_response(self, cleaned_content: str, old_json_content: Dict[str, Any]) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_content: 清理后的AI响应内容
            old_json_content: 原始JSON内容，用于结构比较
            
        Returns:
            tuple[bool, Dict[str, Any]]: (是否有效, JSON内容字典)
        """
        # 验证是否为有效的JSON
        try:
            new_json_content = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_content}")
            return False
        
        # 检查新JSON内容结构是否与旧JSON内容结构一致
        if not DirJsonFuncs.compare_structure(old_json_content, new_json_content):
            print(f"{Colors.WARNING}警告: 生成的JSON结构不符合要求，正在重新生成...{Colors.ENDC}")
            return False
            
        # 检查新添加的节点是否都为字符串类型
        if not DirJsonFuncs.check_new_nodes_are_strings(new_json_content):
            print(f"{Colors.WARNING}警告: 生成的JSON包含非字符串类型的叶子节点，正在重新生成...{Colors.ENDC}")
            return False

        # 检查并确保 proj_root 下有主入口文件
        if not self._ensure_main_entry_file(new_json_content):
            print(f"{Colors.WARNING}警告: 目录结构中的主入口文件检查/填充未成功，正在重新生成...{Colors.ENDC}")
            return False

        return True

    def _ensure_main_entry_file(self, json_content: Dict) -> bool:
        """检查并确保proj_root下有主入口文件"""
        import re
        
        if "proj_root" not in json_content:
            return False
        
        proj_root = json_content["proj_root"]
        if not isinstance(proj_root, dict):
            return False
        
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
        
        return True

    def is_cmd_valid(self):
        """检查目录文件填充命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

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
        if not self.chat_handler.has_role(self.role_dir_file_fill):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_dir_file_fill} 未加载{Colors.ENDC}")
            return False
        
        # 检查角色2是否已加载
        if not self.chat_handler.has_role(self.role_plan_gen):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_plan_gen} 未加载{Colors.ENDC}")
            return False
            
        return True

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
            api_key=chat_api_config.get('api-key', ''),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载两个角色的系统提示词
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name_1 = self.role_dir_file_fill + ".md"
        prompt_file_name_2 = self.role_plan_gen + ".md"
        sys_prompt_path_1 = os.path.join(prompt_dir, prompt_file_name_1)
        sys_prompt_path_2 = os.path.join(prompt_dir, prompt_file_name_2)
        
        # 从文件加载角色提示词
        self.chat_handler.load_role_from_file(self.role_dir_file_fill, sys_prompt_path_1)
        self.chat_handler.load_role_from_file(self.role_plan_gen, sys_prompt_path_2)
    