import sys, os
import asyncio
import json
from typing import List

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler



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
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                user_prompt=requirement_content
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
            
            # 清理代码块标记
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_content)
            if is_valid:
                break
        
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的需求分析结果{Colors.ENDC}")
            return
        
        # 保存结果到refined_requirements.json
        os.makedirs(self.proj_data_dir, exist_ok=True)
        output_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKBLUE}需求分析完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
            return

    def _validate_response(self, cleaned_content: str) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_content: 清理后的AI响应内容
            
        Returns:
            bool: 是否有效
        """
        # 验证是否为有效的JSON
        try:
            json_content = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_content[:200]}...")  # 只显示前200个字符
            return False
        
        # 检查必需字段是否存在
        required_fields = ['main_goal', 'core_functions', 'module_breakdown', 'ExternalLibraryDependencies']
        for field in required_fields:
            if field not in json_content:
                print(f"{Colors.WARNING}警告: 生成的JSON缺少必需字段: {field}{Colors.ENDC}")
                return False
        
        # 验证 main_goal 是字符串
        if not isinstance(json_content['main_goal'], str) or not json_content['main_goal'].strip():
            print(f"{Colors.WARNING}警告: main_goal 字段必须是非空字符串{Colors.ENDC}")
            return False
        
        # 验证 core_functions 是列表且不为空
        if not isinstance(json_content['core_functions'], list) or len(json_content['core_functions']) == 0:
            print(f"{Colors.WARNING}警告: core_functions 字段必须是非空列表{Colors.ENDC}")
            return False
        
        # 验证 core_functions 中的每个元素都是字符串
        for func in json_content['core_functions']:
            if not isinstance(func, str) or not func.strip():
                print(f"{Colors.WARNING}警告: core_functions 中的元素必须是非空字符串{Colors.ENDC}")
                return False
        
        # 验证 module_breakdown 是字典且不为空
        if not isinstance(json_content['module_breakdown'], dict) or len(json_content['module_breakdown']) == 0:
            print(f"{Colors.WARNING}警告: module_breakdown 字段必须是非空字典{Colors.ENDC}")
            return False
        
        # 验证每个模块的结构
        for module_name, module_info in json_content['module_breakdown'].items():
            if not isinstance(module_info, dict):
                print(f"{Colors.WARNING}警告: 模块 {module_name} 的信息必须是字典{Colors.ENDC}")
                return False
            
            # 检查模块的必需字段
            if 'responsibilities' not in module_info or 'dependencies' not in module_info:
                print(f"{Colors.WARNING}警告: 模块 {module_name} 缺少 responsibilities 或 dependencies 字段{Colors.ENDC}")
                return False
            
            # 验证 responsibilities 是列表且不为空
            if not isinstance(module_info['responsibilities'], list) or len(module_info['responsibilities']) == 0:
                print(f"{Colors.WARNING}警告: 模块 {module_name} 的 responsibilities 必须是非空列表{Colors.ENDC}")
                return False
            
            # 验证 dependencies 是列表
            if not isinstance(module_info['dependencies'], list):
                print(f"{Colors.WARNING}警告: 模块 {module_name} 的 dependencies 必须是列表{Colors.ENDC}")
                return False
        
        # 验证 ExternalLibraryDependencies 是字典
        if not isinstance(json_content['ExternalLibraryDependencies'], dict):
            print(f"{Colors.WARNING}警告: ExternalLibraryDependencies 字段必须是字典{Colors.ENDC}")
            return False
        
        # 验证 ExternalLibraryDependencies 中的值都是字符串
        for lib_name, lib_desc in json_content['ExternalLibraryDependencies'].items():
            if not isinstance(lib_desc, str) or not lib_desc.strip():
                print(f"{Colors.WARNING}警告: 库 {lib_name} 的描述必须是非空字符串{Colors.ENDC}")
                return False
        
        print(f"{Colors.OKGREEN}需求分析结果验证通过{Colors.ENDC}")
        return True

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
            api_key=chat_api_config.get('api-key', ''),
            model=chat_api_config.get('model', '')
        )
        
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, self.role_name + ".md")
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)