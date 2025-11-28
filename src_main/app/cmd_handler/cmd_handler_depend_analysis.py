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



class CmdHandlerDependAnalysis(BaseCmdHandler):
    """依赖分析指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="depend_analysis",
            aliases=["DA"],
            description="分析项目依赖关系",
            help_text="根据目录结构分析并生成项目依赖关系",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir_path = proj_cfg_manager.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 使用新的 ICPChatHandler
        self.chat_handler = ICPChatHandler()
        self.role_name = "5_depend_analyzer"
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行依赖分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行依赖分析...{Colors.ENDC}")

        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_depend_analyzer()
        if not user_prompt:
            return
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
                
            # 清理代码块标记
            cleaned_json_str = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_json_str)
            if is_valid:
                break
        
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的依赖关系{Colors.ENDC}")
            return
        
        # 保存依赖分析结果到 icp_dir_content_with_depend.json
        output_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_json_str)
            print(f"{Colors.OKBLUE}依赖分析完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
            return

    def _build_user_prompt_for_depend_analyzer(self) -> str:
        """
        构建依赖分析的用户提示词
        
        从项目数据目录中读取所需文件，无需外部参数输入。
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            return ""
            
        if not implementation_plan_str:
            print(f"  {Colors.FAIL}错误: 文件级实现规划内容为空{Colors.ENDC}")
            return ""
            
        # 读取带文件描述的目录结构
        dir_with_files_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_files.json')
        try:
            with open(dir_with_files_file, 'r', encoding='utf-8') as f:
                dir_with_files_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取带文件描述的目录结构失败: {e}{Colors.ENDC}")
            return ""
            
        if not dir_with_files_str:
            print(f"  {Colors.FAIL}错误: 带文件描述的目录结构内容为空{Colors.ENDC}")
            return ""
        self.old_json_dict = json.loads(dir_with_files_str)
        
        # 生成完整路径列表
        file_paths = DirJsonFuncs.get_all_file_paths(self.old_json_dict.get("proj_root", {}))
        file_paths_text = "\n".join(file_paths)

        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        app_user_prompt_file_path = os.path.join(app_data_manager.get_user_prompt_dir(), 'depend_analysis_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        if not user_prompt_template_str:
            print(f"  {Colors.FAIL}错误: 用户提示词模板内容为空{Colors.ENDC}")
            return ""
            
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan_str)
        user_prompt_str = user_prompt_str.replace('JSON_STRUCTURE_PLACEHOLDER', dir_with_files_str)
        user_prompt_str = user_prompt_str.replace('FILE_PATHS_PLACEHOLDER', file_paths_text)
        
        return user_prompt_str

    def _validate_response(self, cleaned_json_str: str) -> tuple[bool, Dict[str, Any]]:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            
        Returns:
            tuple[bool, Dict[str, Any]]: (是否有效, JSON内容字典)
        """
        # 验证是否为有效的JSON
        try:
            new_json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_json_str}")
            return False
        
        # 检查新JSON内容是否包含必需的根节点
        if "proj_root" not in new_json_dict or "dependent_relation" not in new_json_dict:
            print(f"{Colors.WARNING}警告: 生成的JSON缺少必需的根节点 proj_root 或 dependent_relation{Colors.ENDC}")
            return False
        
        # 检查proj_root结构是否与原始结构一致
        if not DirJsonFuncs.compare_structure(self.old_json_dict["proj_root"], new_json_dict["proj_root"]):
            print(f"{Colors.WARNING}警告: proj_root结构与原始结构不一致{Colors.ENDC}")
            return False
            
        # 检查dependent_relation中的依赖路径是否都存在于proj_root中
        is_valid, validation_errors = DirJsonFuncs.validate_dependent_paths(new_json_dict["dependent_relation"], new_json_dict["proj_root"])
        if not is_valid:
            print(f"{Colors.WARNING}警告: 生成的 dependent_relation 出现了 proj_root 下不存在的路径{Colors.ENDC}")
            print(f"{Colors.WARNING}具体错误如下:{Colors.ENDC}")
            for error in validation_errors:
                print(f"  - {error}")
            return False
        
        return True

    def is_cmd_valid(self):
        """检查依赖分析命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证依赖分析命令的前置条件"""
        # 检查文件级实现规划文件是否存在
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        if not os.path.exists(implementation_plan_file):
            print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
            
        # 检查带文件描述的目录结构文件是否存在
        dir_with_files_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_files.json')
        if not os.path.exists(dir_with_files_file):
            print(f"  {Colors.WARNING}警告: 带文件描述的目录结构文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
        
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查角色是否已加载
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
            return False
            
        return True

    def _init_ai_handlers(self):
        """初始化AI处理器"""
        # 检查配置文件是否存在
        if not os.path.exists(self.work_api_config_file_path):
            print(f"错误: 配置文件 {self.work_api_config_file_path} 不存在，请创建该文件并填充必要内容")
            return
        
        try:
            with open(self.work_api_config_file_path, 'r', encoding='utf-8') as f:
                config_json_dict = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        # 优先检查是否有depend_analysis_handler配置
        if 'depend_analysis_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['depend_analysis_handler']
        elif 'coder_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['coder_handler']
        else:
            print("错误: 配置文件缺少depend_analysis_handler或coder_handler配置")
            return
        
        chat_handler_config = ChatApiConfig(
            base_url=chat_api_config_dict.get('api-url', ''),
            api_key=chat_api_config_dict.get('api-key', ''),
            model=chat_api_config_dict.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(chat_handler_config)
        
        # 加载角色的系统提示词
        app_data_manager = get_app_data_manager()
        app_prompt_dir_path = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        app_sys_prompt_file_path = os.path.join(app_prompt_dir_path, prompt_file_name)
        
        # 从文件加载角色提示词
        self.chat_handler.load_role_from_file(self.role_name, app_sys_prompt_file_path)