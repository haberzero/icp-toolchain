import sys, os
import asyncio
import json
import re
from typing import List, Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.user_data_store import get_instance as get_user_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler.icp_chat_handler import ICPChatHandler
from utils.issue_recorder import TextIssueRecorder


class CmdHandlerModuleToDir(BaseCmdHandler):
    """目录结构生成命令处理器"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="module_to_dir",
            aliases=["MTD"],
            description="根据需求分析结果生成项目目录结构",
            help_text="基于需求分析生成标准化的项目目录结构",
        )
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 使用coder_handler单例
        self.chat_handler = ICPChatHandler(handler_key='coder_handler')
        
        # 系统提示词加载
        app_data_store = get_app_data_store()
        self.role_name = "3_module_to_dir"
        self.sys_prompt = app_data_store.get_sys_prompt_by_name(self.role_name) 
        self.sys_prompt_retry_part = app_data_store.get_sys_prompt_by_name('retry_sys_prompt')
        
        # 用户提示词在命令运行过程中，经由模板以及过程变量进行构建
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容


    def execute(self):
        """执行目录结构生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成目录结构...{Colors.ENDC}")
        
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
            
            # 根据是否是重试来组合提示词
            if attempt == 0:
                # 第一次尝试,使用基础提示词
                current_sys_prompt = self.sys_prompt
                current_user_prompt = self.user_prompt_base
            else:
                # 重试时,添加重试部分
                current_sys_prompt = self.sys_prompt + "\n\n" + self.sys_prompt_retry_part
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
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_content)
            if is_valid:
                break
            
            # 如果验证失败，保存当前生成的内容并构建重试提示词
            self.last_generated_content = cleaned_content
            self.user_prompt_retry_part = self._build_user_prompt_retry_part()

        if attempt == max_attempts - 1 and not is_valid:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的目录结构{Colors.ENDC}")
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

    def _build_user_prompt_base(self) -> str:
        """构建目录结构生成的用户提示词基础部分
        
        Returns:
            str: 基础用户提示词，失败时返回空字符串
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
    
    def _build_user_prompt_retry_part(self) -> str:
        """构建用户提示词重试部分
        
        Returns:
            str: 重试部分的用户提示词，失败时返回空字符串
        """
        if not self.issue_recorder.has_issues() or not self.last_generated_content:
            return ""
        
        # 读取重试提示词模板
        app_data_store = get_app_data_store()
        retry_template_path = os.path.join(app_data_store.get_user_prompt_dir(), 'retry_prompt_template.md')
        
        try:
            with open(retry_template_path, 'r', encoding='utf-8') as f:
                retry_template = f.read()
        except Exception as e:
            print(f"{Colors.FAIL}错误: 读取重试模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 格式化上一次生成的内容（用json代码块包裹）
        formatted_content = f"```json\n{self.last_generated_content}\n```"
        
        # 格式化问题列表
        issues_list = "\n".join([f"- {issue.issue_content}" for issue in self.issue_recorder.get_issues()])

        # 在控制台打印问题列表，提示其将用于下一次重试生成
        self.issue_recorder.print_issues_for_retry()
        
        # 替换占位符
        retry_prompt = retry_template.replace('PREVIOUS_CONTENT_PLACEHOLDER', formatted_content)
        retry_prompt = retry_prompt.replace('ISSUES_LIST_PLACEHOLDER', issues_list)
        
        return retry_prompt

    def _validate_response(self, cleaned_json_str: str) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            
        Returns:
            bool: 是否为有效的JSON
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

        # 检查key的存在性以及key内容的匹配，以及检查是否有其它多余字段
        required_key = "proj_root_dict"
        if required_key not in json_dict:
            error_msg = f"AI返回的内容缺少关键字段: {required_key}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        if not isinstance(json_dict[required_key], dict):
            error_msg = f"字段 {required_key} 的内容不是字典类型"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False

        for key in json_dict:
            if key != required_key:
                error_msg = f"存在多余字段: {key}"
                print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
                self.issue_recorder.record_issue(error_msg)
                return False
        
        # 检查目录结构中的所有键是否包含'.'（疑似后缀名或非法命名）
        def _has_dot_in_keys(node, path="proj_root_dict"):
            if isinstance(node, dict):
                for k, v in node.items():
                    current_path = f"{path}/{k}" if path else k
                    if "." in k:
                        error_msg = f"目录键包含'.'（疑似后缀或非法命名）: {current_path}"
                        print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
                        self.issue_recorder.record_issue(error_msg)
                        return True
                    if isinstance(v, dict):
                        if _has_dot_in_keys(v, current_path):
                            return True
            return False
        
        if _has_dot_in_keys(json_dict[required_key], "proj_root_dict"):
            return False
        
        # 检查文件夹命名是否使用了 main_xxx 形式
        error_msg = self._check_main_folder_naming(json_dict[required_key])
        if error_msg:
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        return True
    
    def _check_main_folder_naming(self, proj_root_dict: Dict) -> str:
        """
        检查文件夹命名是否使用了 main_xxx 形式
        
        Args:
            proj_root_dict: 项目根目录字典
            
        Returns:
            str: 错误信息，通过检查时返回None
        """
        # 检测 main_xxx 或 Main_xxx 形式的文件夹命名模式
        main_folder_patterns = [
            r'^main_',
            r'^Main_'
        ]
        
        def matches_main_folder_pattern(name: str) -> bool:
            """检查名称是否匹配 main_xxx 文件夹模式"""
            for pattern in main_folder_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True
            return False
        
        # 递归检查所有文件夹命名
        main_folders = []
        def collect_main_folders(node, path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    current_path = f"{path}/{key}" if path else key
                    # 只检查文件夹（值为dict的节点）
                    if isinstance(value, dict):
                        if matches_main_folder_pattern(key):
                            main_folders.append(current_path)
                        # 递归检查子节点
                        collect_main_folders(value, current_path)
        
        collect_main_folders(proj_root_dict)
        
        # 如果发现 main_xxx 文件夹，返回错误信息
        if main_folders:
            return f"检测到使用 main_xxx 形式的文件夹命名: {', '.join(main_folders)}。建议避免直接使用 main_xxx 作为文件夹名，可以改为其他更具体的命名"
        
        return None

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
        """验证AI处理器是否初始化成功"""
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查系统提示词是否加载
        if not self.sys_prompt:
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_name} 未加载{Colors.ENDC}")
            return False
            
        return True
