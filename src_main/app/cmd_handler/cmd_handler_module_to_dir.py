import sys, os
import asyncio
import json
from typing import List, Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.user_data_store import get_instance as get_user_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler



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
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        self.chat_handler = ICPChatHandler()
        self.role_name = "3_module_to_dir"
        self._init_ai_handlers()

    def execute(self):
        """执行目录结构生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成目录结构...{Colors.ENDC}")
        
        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_module_to_dir()
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
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_content)
            if is_valid:
                break

        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的依赖关系{Colors.ENDC}")
            return
        
        # 保存结果到icp_dir_content.json
        output_file = os.path.join(self.work_data_dir_path, 'icp_dir_content.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"目录结构生成完成，结果已保存到: {output_file}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
        return

    def _build_user_prompt_for_module_to_dir(self) -> str:
        """构建目录结构生成的用户提示词
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取需求分析结果
        requirement_analysis_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                requirement_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return ""
            
        if not requirement_str:
            print(f"  {Colors.FAIL}错误: 需求分析结果为空{Colors.ENDC}")
            return ""
        
        # 过滤掉ExternalLibraryDependencies字段，并移除module_breakdown下各模块的dependencies字段
        try:
            requirement_json_dict = json.loads(requirement_str)
            # 移除ExternalLibraryDependencies字段，因为module_to_dir只关注模块结构，不关注外部库
            if 'ExternalLibraryDependencies' in requirement_json_dict:
                del requirement_json_dict['ExternalLibraryDependencies']
            # 移除module_breakdown中各子模块的dependencies字段，避免干扰目录结构生成判断
            if 'module_breakdown' in requirement_json_dict and isinstance(requirement_json_dict['module_breakdown'], dict):
                for module in requirement_json_dict['module_breakdown'].values():
                    if isinstance(module, dict) and 'dependencies' in module:
                        del module['dependencies']
            # 将过滤后的内容转换回JSON字符串
            filtered_requirement_str = json.dumps(requirement_json_dict, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 需求分析结果不是有效的JSON格式: {e}{Colors.ENDC}")
            return ""
        
        return filtered_requirement_str

    def _validate_response(self, cleaned_json_str: str) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            
        Returns:
            bool: 是否为有效的JSON
        """
        # 验证是否为有效的JSON
        try:
            json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_json_str}")
            return False

        # 检查key的存在性以及key内容的匹配，以及检查是否有其它多余字段
        required_key = "proj_root_dict"
        if required_key not in json_dict:
            print(f"{Colors.FAIL}错误: AI返回的内容缺少关键字段: {required_key}{Colors.ENDC}")
            return False
        if not isinstance(json_dict[required_key], dict):
            print(f"{Colors.FAIL}错误: 字段 {required_key} 的内容不是字典类型{Colors.ENDC}")
            return False

        for key in json_dict:
            if key != required_key:
                print(f"{Colors.FAIL}错误: 存在多余字段: {key}{Colors.ENDC}")
                return False
        
        # 检查目录结构中的所有键是否包含'.'（疑似后缀名或非法命名）
        def _has_dot_in_keys(node, path="proj_root_dict"):
            if isinstance(node, dict):
                for k, v in node.items():
                    current_path = f"{path}/{k}" if path else k
                    if "." in k:
                        print(f"{Colors.FAIL}错误: 目录键包含'.'（疑似后缀或非法命名）: {current_path}{Colors.ENDC}")
                        return True
                    if isinstance(v, dict):
                        if _has_dot_in_keys(v, current_path):
                            return True
            return False
        
        if _has_dot_in_keys(json_dict[required_key], "proj_root_dict"):
            return False
        
        return True

    def is_cmd_valid(self):
        """检查目录生成命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证目录生成命令的前置条件"""
        # 检查需求分析结果文件是否存在
        requirement_analysis_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
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

    def _init_ai_handlers(self):
        if not os.path.exists(self.work_api_config_file_path):
            print(f"错误: 配置文件 {self.work_api_config_file_path} 不存在")
            return
        try:
            with open(self.work_api_config_file_path, 'r', encoding='utf-8') as f:
                config_json_dict = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        if 'dir_generate_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['dir_generate_handler']
        elif 'coder_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['coder_handler']
        else:
            print("错误: 配置文件缺少配置")
            return
        handler_config = ChatApiConfig(
            base_url=chat_api_config_dict.get('api-url', ''),
            api_key=chat_api_config_dict.get('api-key', ''),
            model=chat_api_config_dict.get('model', '')
        )
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        app_data_store = get_app_data_store()
        app_sys_prompt_file_path = os.path.join(app_data_store.get_prompt_dir(), self.role_name + ".md")
        self.chat_handler.load_role_from_file(self.role_name, app_sys_prompt_file_path)