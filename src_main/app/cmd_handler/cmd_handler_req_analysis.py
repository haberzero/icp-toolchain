import asyncio
import json
import os
import sys
from typing import List

from app.sys_prompt_manager import get_instance as get_sys_prompt_manager
from app.user_prompt_manager import get_instance as get_user_prompt_manager
from data_store.user_data_store import get_instance as get_user_data_store
from libs.text_funcs import ChatResponseCleaner
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from typedef.cmd_data_types import CmdProcStatus, Colors, CommandInfo
from utils.icp_ai_utils.icp_chat_inst import ICPChatInsts
from utils.issue_recorder import TextIssueRecorder

from .base_cmd_handler import BaseCmdHandler


class CmdHandlerReqAnalysis(BaseCmdHandler):
    """需求分析命令处理器"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="req_analysis",
            aliases=["RA"],
            description="对用户需求进行结构化分析",
            help_text="对用户需求进行深入分析，生成技术选型和模块拆解",
        )
        # 关联系统提示词角色名
        self.role_name = "2_req_to_module"
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 获取coder_handler单例
        self.chat_handler = ICPChatInsts.get_instance(handler_key='coder_handler')

        # 提示词管理器
        self.sys_prompt_manager = get_sys_prompt_manager()
        self.user_prompt_manager = get_user_prompt_manager()

        # 用户提示词在命令运行过程中，经由模板以及过程变量进行构建
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容

    def execute(self):
        """执行需求分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行需求分析...{Colors.ENDC}")
        
        # 重置实例变量
        self.issue_recorder.clear()
        self.last_generated_content = None
        
        # 构建用户提示词基础部分
        self.user_prompt_base = self._build_user_prompt_base()
        if not self.user_prompt_base:
            print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
            return
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")

            base_sys_prompt = self.sys_prompt_manager.get_prompt(self.role_name)
            retry_sys_prompt = self.sys_prompt_manager.get_prompt('retry_sys_prompt')
            
            # 根据是否是重试来组合提示词
            if attempt == 0:
                # 第一次尝试,使用基础提示词
                current_sys_prompt = base_sys_prompt
                current_user_prompt = self.user_prompt_base
            else:
                # 重试时,添加重试部分
                if retry_sys_prompt:
                    current_sys_prompt = base_sys_prompt + "\n\n" + retry_sys_prompt
                else:
                    current_sys_prompt = base_sys_prompt
                current_user_prompt = self.user_prompt_base + "\n\n" + self.user_prompt_retry_part
            
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                sys_prompt=current_sys_prompt,
                user_prompt=current_user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
            
            # 清理代码块标记
            cleaned_content = ChatResponseCleaner.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_content)
            if is_valid:
                break
            
            # 如果验证失败，保存当前生成的内容并构建重试提示词
            self.last_generated_content = cleaned_content
            self.user_prompt_retry_part = self._build_user_prompt_retry_part()
        
        if attempt == max_attempts - 1 and not is_valid:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的需求分析结果{Colors.ENDC}")
            return
        
        # 保存结果到refined_requirements.json
        os.makedirs(self.work_data_dir_path, exist_ok=True)
        output_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKBLUE}需求分析完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
            return

    def _build_user_prompt_base(self) -> str:
        """构建需求分析的用户提示词基础部分
        
        Returns:
            str: 基础用户提示词，失败时返回空字符串
        """
        user_data_store = get_user_data_store()
        requirement_content = user_data_store.get_user_prompt()
        if not requirement_content:
            print(f"  {Colors.FAIL}错误: 未找到用户需求内容{Colors.ENDC}")
            return ""
        
        return requirement_content
    
    def _build_user_prompt_retry_part(self) -> str:
        """构建用户提示词重试部分
        
        Returns:
            str: 重试部分的用户提示词，失败时返回空字符串
        """
        if not self.issue_recorder.has_issues() or not self.last_generated_content:
            return ""
        
        # 格式化上一次生成的内容（用json代码块包裹）
        formatted_content = f"```json\n{self.last_generated_content}\n```"
        
        # 格式化问题列表
        issues_list = "\n".join([f"- {issue.issue_content}" for issue in self.issue_recorder.get_issues()])

        # 在控制台打印问题列表，提示其将用于下一次重试生成
        self.issue_recorder.print_issues_for_retry()
        
        # 使用用户提示词模板管理器构建重试提示词
        placeholder_mapping = {
            'PREVIOUS_CONTENT_PLACEHOLDER': formatted_content,
            'ISSUES_LIST_PLACEHOLDER': issues_list,
        }
        retry_prompt = self.user_prompt_manager.build_prompt_from_template(
            template_name='retry_prompt_template',
            placeholder_mapping=placeholder_mapping,
        )
        if not retry_prompt:
            print(f"{Colors.FAIL}错误: 重试提示词模板构建失败{Colors.ENDC}")
            return ""
        
        return retry_prompt

    def _validate_response(self, cleaned_json_str: str) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            
        Returns:
            bool: 是否有效
        """
        # 清空上一次验证的问题记录
        self.issue_recorder.clear()
        
        # 验证是否为有效的JSON
        try:
            json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            error_msg = f"AI返回的内容不是有效的JSON格式: {e}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检查必需字段是否存在
        required_fields = ['main_goal', 'core_functions', 'module_breakdown', 'ExternalLibraryDependencies']
        for field in required_fields:
            if field not in json_dict:
                error_msg = f"生成的JSON缺少必需字段: {field}"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
        
        # 验证 main_goal 是字符串
        if not isinstance(json_dict['main_goal'], str) or not json_dict['main_goal'].strip():
            error_msg = "main_goal 字段必须是非空字符串"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 验证 core_functions 是列表且不为空
        if not isinstance(json_dict['core_functions'], list) or len(json_dict['core_functions']) == 0:
            error_msg = "core_functions 字段必须是非空列表"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 验证 core_functions 中的每个元素都是字符串
        for func in json_dict['core_functions']:
            if not isinstance(func, str) or not func.strip():
                error_msg = "core_functions 中的元素必须是非空字符串"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
        
        # 验证 module_breakdown 是字典且不为空
        if not isinstance(json_dict['module_breakdown'], dict) or len(json_dict['module_breakdown']) == 0:
            error_msg = "module_breakdown 字段必须是非空字典"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 验证每个模块的结构
        for module_name, module_info in json_dict['module_breakdown'].items():
            if not isinstance(module_info, dict):
                error_msg = f"模块 {module_name} 的信息必须是字典"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
            
            # 检查模块的必需字段
            if 'responsibilities' not in module_info or 'dependencies' not in module_info:
                error_msg = f"模块 {module_name} 缺少 responsibilities 或 dependencies 字段"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
            
            # 验证 responsibilities 是列表且不为空
            if not isinstance(module_info['responsibilities'], list) or len(module_info['responsibilities']) == 0:
                error_msg = f"模块 {module_name} 的 responsibilities 必须是非空列表"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
            
            # 验证 dependencies 是列表
            if not isinstance(module_info['dependencies'], list):
                error_msg = f"模块 {module_name} 的 dependencies 必须是列表"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
        
        # 验证 ExternalLibraryDependencies 是字典
        if not isinstance(json_dict['ExternalLibraryDependencies'], dict):
            error_msg = "ExternalLibraryDependencies 字段必须是字典"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 验证 ExternalLibraryDependencies 中的值都是字符串
        for lib_name, lib_desc in json_dict['ExternalLibraryDependencies'].items():
            if not isinstance(lib_desc, str) or not lib_desc.strip():
                error_msg = f"库 {lib_name} 的描述必须是非空字符串"
                print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
        
        print(f"  {Colors.OKGREEN}需求分析结果验证通过{Colors.ENDC}")
        return True

    def is_cmd_valid(self):
        """检查需求分析命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证需求分析命令的前置条件"""
        # 检查用户需求内容是否存在
        user_data_store = get_user_data_store()
        requirement_content = user_data_store.get_user_prompt()
        if not requirement_content:
            print(f"  {Colors.WARNING}警告: 未找到用户需求内容，请先提供需求内容{Colors.ENDC}")
            return False
            
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查handler实例是否已初始化
        if not self.chat_handler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查系统提示词是否加载
        if not self.sys_prompt_manager.has_prompt(self.role_name):
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_name} 未加载{Colors.ENDC}")
            return False

        if not self.sys_prompt_manager.has_prompt('retry_sys_prompt'):
            print(f"  {Colors.FAIL}错误: 重试系统提示词 retry_sys_prompt 未加载{Colors.ENDC}")
            return False

        # 检查重试用户提示词模板
        if not self.user_prompt_manager.has_template('retry_prompt_template'):
            print(f"  {Colors.FAIL}错误: 用户提示词模板 retry_prompt_template 未加载{Colors.ENDC}")
            return False
            
        return True