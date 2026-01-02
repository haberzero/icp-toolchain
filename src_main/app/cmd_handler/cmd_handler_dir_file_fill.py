import asyncio
import json
import os
import re
import sys
from typing import Any, Dict, List

from data_store.app_data_store import get_instance as get_app_data_store
from data_store.user_data_store import get_instance as get_user_data_store
from libs.dir_json_funcs import DirJsonFuncs
from libs.text_funcs import ChatResponseCleaner
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from typedef.ai_data_types import ChatApiConfig
from typedef.cmd_data_types import CmdProcStatus, Colors, CommandInfo
from utils.icp_ai_handler.icp_chat_handler import ICPChatHandler
from utils.issue_recorder import TextIssueRecorder

from .base_cmd_handler import BaseCmdHandler


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

        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 获取coder_handler单例
        self.chat_handler = ICPChatHandler.get_instance(handler_key='coder_handler')
        self.role_dir_file_fill = "4_dir_file_fill"
        self.role_plan_gen = "4_dir_file_fill_plan_gen"

        # 系统提示词加载
        app_data_store = get_app_data_store()
        self.sys_prompt_dir_file_fill = app_data_store.get_sys_prompt_by_name(self.role_dir_file_fill)   
        self.sys_prompt_plan_gen = app_data_store.get_sys_prompt_by_name(self.role_plan_gen)
        self.sys_prompt_retry_part = app_data_store.get_sys_prompt_by_name('retry_sys_prompt')
        
        # 用户提示词在命令运行过程中，经由模板以及过程变量进行构建
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容
        
    def execute(self):
        """执行目录文件填充"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行目录文件填充...{Colors.ENDC}")

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
            print(f"{self.role_dir_file_fill}正在进行第 {attempt + 1} 次尝试...")
            
            # 根据是否是重试来组合提示词
            if attempt == 0:
                # 第一次尝试,使用基础提示词
                current_sys_prompt = self.sys_prompt_dir_file_fill
                current_user_prompt = self.user_prompt_base
            else:
                # 重试时,添加重试部分
                current_sys_prompt = self.sys_prompt_dir_file_fill + "\n\n" + self.sys_prompt_retry_part
                current_user_prompt = self.user_prompt_base + "\n\n" + self.user_prompt_retry_part
            
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_dir_file_fill,
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
            is_valid = self._validate_response(cleaned_content, self.old_json_dict)
            if is_valid:
                break
            
            # 如果验证失败，保存当前生成的内容并构建重试提示词
            self.last_generated_content = cleaned_content
            self.user_prompt_retry_part = self._build_user_prompt_retry_part()
        
        if attempt == max_attempts - 1 and not is_valid:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的目录结构{Colors.ENDC}")
            return

        # 解析最终的JSON数据
        try:
            new_json_dict = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: 解析最终JSON失败: {e}{Colors.ENDC}")
            return

        # 保存结果到icp_dir_content_with_files.json
        output_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_files.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(new_json_dict, f, indent=2, ensure_ascii=False)
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
            print(f"{self.role_plan_gen}正在进行第 {attempt + 1} 次尝试...")

            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_plan_gen,
                sys_prompt=self.sys_prompt_plan_gen,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
            
            # 清理代码块标记并退出运行
            cleaned_content = ChatResponseCleaner.clean_code_block_markers(response_content)
            break
        
        # 保存实现规划
        output_file_path = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKGREEN}文件级实现规划已生成并保存到: {output_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存实现规划失败: {e}{Colors.ENDC}")

    def _build_user_prompt_base(self) -> str:
        """
        构建目录文件填充的用户提示词基础部分
        
        从项目数据目录中读取所需文件，无需外部参数输入。
        
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
            
        # 读取目录结构
        dir_structure_file = os.path.join(self.work_data_dir_path, 'icp_dir_content.json')
        try:
            with open(dir_structure_file, 'r', encoding='utf-8') as f:
                dir_structure_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录结构失败: {e}{Colors.ENDC}")
            return ""
            
        if not dir_structure_str:
            print(f"  {Colors.FAIL}错误: 目录结构内容为空{Colors.ENDC}")
            return ""
        self.old_json_dict = json.loads(dir_structure_str)

        # 读取用户提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'dir_file_fill_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('PROGRAMMING_REQUIREMENT_PLACEHOLDER', requirement_str)
        user_prompt_str = user_prompt_str.replace('JSON_STRUCTURE_PLACEHOLDER', dir_structure_str)
        
        return user_prompt_str
    
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
        
        # 替换占位符
        retry_prompt = retry_template.replace('PREVIOUS_CONTENT_PLACEHOLDER', formatted_content)
        retry_prompt = retry_prompt.replace('ISSUES_LIST_PLACEHOLDER', issues_list)
        
        return retry_prompt

    def _build_user_prompt_for_plan_generator(self) -> str:
        """
        构建文件级实现规划生成的用户提示词（role_name_2）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户原始需求
        user_data_store = get_user_data_store()
        user_requirements_str = user_data_store.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return ""
        
        # 读取精炼需求内容
        requirement_analysis_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(requirement_analysis_file, 'r', encoding='utf-8') as f:
                refined_requirement_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取需求分析结果失败: {e}{Colors.ENDC}")
            return ""
        
        # 读取目录文件内容
        dir_file_path = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_files.json')
        try:
            with open(dir_file_path, 'r', encoding='utf-8') as f:
                dir_file_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录文件内容失败: {e}{Colors.ENDC}")
            return ""

        # 读取用户提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'dir_file_fill_plan_gen_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('USER_ORIGINAL_REQUIREMENTS_PLACEHOLDER', user_requirements_str)
        user_prompt_str = user_prompt_str.replace('REFINED_REQUIREMENTS_PLACEHOLDER', refined_requirement_str)
        user_prompt_str = user_prompt_str.replace('DIR_FILE_CONTENT_PLACEHOLDER', dir_file_str)
        
        return user_prompt_str

    def _validate_response(self, cleaned_json_str: str, old_json_dict: Dict[str, Any]) -> bool:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            old_json_dict: 原始JSON内容，用于结构比较
            
        Returns:
            bool: 是否有效
        """
        # 清空上一次验证的问题记录
        self.issue_recorder.clear()
        
        # 验证是否为有效的JSON
        try:
            new_json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            error_msg = f"AI返回的内容不是有效的JSON格式: {e}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检查新JSON内容结构是否与旧JSON内容结构一致
        structure_errors = DirJsonFuncs.compare_structure(old_json_dict, new_json_dict)
        if structure_errors:
            error_msg = "生成的JSON结构不符合要求，具体问题如下：\n" + "\n".join(f"  - {err}" for err in structure_errors)
            print(f"{Colors.WARNING}警告: 生成的JSON结构不符合要求{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
            
        # 检查新添加的节点是否都为字符串类型
        string_errors = DirJsonFuncs.check_new_nodes_are_strings(new_json_dict)
        if string_errors:
            error_msg = "生成的JSON包含非字符串类型的叶子节点，具体问题如下：\n" + "\n".join(f"  - {err}" for err in string_errors)
            print(f"{Colors.WARNING}警告: 生成的JSON包含非字符串类型的叶子节点{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False

        # 检查 proj_root_dict 下是否有主入口文件
        error_msg = self._check_main_entry_file_exists(new_json_dict)
        if error_msg:
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False

        return True

    def _check_main_entry_file_exists(self, json_dict: Dict) -> str:
        """
        检查proj_root_dict下是否存在主入口文件
        
        主入口文件可以在：
        1. proj_root_dict 直接子节点（文件）
        2. proj_root_dict 直接子节点中的文件夹内
        3. 文件夹名为 xxx_main 形式，其内包含合理的主入口文件
        
        Args:
            json_dict: 包含proj_root_dict的JSON字典
            
        Returns:
            str: 错误或警告信息，通过检查时返回None
        """
        proj_root_dict = json_dict["proj_root_dict"]
        
        # 标准主入口文件命名模式（以 main 或 Main 开头）
        standard_main_patterns = [
            r'^main',
            r'^Main'
        ]
        
        # 疑似主入口文件命名模式（包含 main 但不以 main 开头）
        suspicious_main_patterns = [
            r'.*_main$',
            r'.*_Main$',
            r'.*Main$'  # 如 AppMain
        ]
        
        def matches_standard_pattern(name: str) -> bool:
            """检查名称是否匹配标准主入口文件模式"""
            for pattern in standard_main_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True
            return False
        
        def matches_suspicious_pattern(name: str) -> bool:
            """检查名称是否匹配疑似主入口文件模式"""
            for pattern in suspicious_main_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True
            return False
        
        # 1. 检查proj_root_dict直接子节点中的文件（标准命名）
        for key, value in proj_root_dict.items():
            if isinstance(value, str):
                if matches_standard_pattern(key):
                    print(f"{Colors.OKGREEN}检测到主入口文件: {key}{Colors.ENDC}")
                    return None
        
        # 2. 检查proj_root_dict直接子节点中的文件夹内（包括 xxx_main 文件夹）
        for key, value in proj_root_dict.items():
            if isinstance(value, dict):
                # 检查文件夹内的文件
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        if matches_standard_pattern(sub_key):
                            # 如果文件夹名为 xxx_main 形式，也认为合理
                            print(f"{Colors.OKGREEN}检测到主入口文件: {key}/{sub_key}{Colors.ENDC}")
                            return None
        
        # 3. 检查是否有疑似主入口文件（直接子节点）
        suspicious_files = []
        for key, value in proj_root_dict.items():
            if isinstance(value, str):
                if matches_suspicious_pattern(key):
                    suspicious_files.append(key)
        
        # 4. 检查是否有疑似主入口文件（文件夹内）
        for key, value in proj_root_dict.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        if matches_suspicious_pattern(sub_key):
                            suspicious_files.append(f"{key}/{sub_key}")
        
        # 如果找到疑似主入口文件，返回警告信息
        if suspicious_files:
            return f"检测到疑似主入口文件: {', '.join(suspicious_files)}。如果是主入口文件，建议改名为 main_xxx 形式；如果不是，请在直接子节点下添加合理的主入口文件"
        
        # 未找到任何主入口文件
        return "未检测到主入口文件，请添加名为 main_xxx 形式的文件，优先放在 proj_root_dict 直接子节点下"

    def _build_retry_prompt(self, previous_content: str, issues: list, code_block_type: str = "") -> str:
        """
        构建重试提示词
        
        Args:
            previous_content: 上一次生成的内容
            issues: 问题列表
            code_block_type: 代码块类型(如"json", ""等)
            
        Returns:
            str: 重试提示词
        """
        # 读取重试提示词模板
        app_data_store = get_app_data_store()
        retry_template_path = os.path.join(app_data_store.get_user_prompt_dir(), 'retry_prompt_template.md')
        
        try:
            with open(retry_template_path, 'r', encoding='utf-8') as f:
                retry_template = f.read()
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取重试模板失败: {e}，使用默认格式{Colors.ENDC}")
            return self._build_default_retry_prompt(previous_content, issues, code_block_type)
        
        # 格式化上一次生成的内容
        if code_block_type:
            formatted_content = f"```{code_block_type}\n{previous_content}\n```"
        else:
            formatted_content = f"```\n{previous_content}\n```"
        
        # 格式化问题列表
        issues_list = "\n".join([f"- {issue.issue_content}" for issue in issues])
        
        # 替换占位符
        retry_prompt = retry_template.replace('PREVIOUS_CONTENT_PLACEHOLDER', formatted_content)
        retry_prompt = retry_prompt.replace('ISSUES_LIST_PLACEHOLDER', issues_list)
        
        return retry_prompt
    
    def _build_default_retry_prompt(self, previous_content: str, issues: list, code_block_type: str = "") -> str:
        """构建默认的重试提示词(作为模板读取失败时的后备)"""
        retry_prompt = "## 重试生成信息\n\n"
        retry_prompt += "这是一次重试生成，上一次生成的内容是:\n\n"
        if code_block_type:
            retry_prompt += f"```{code_block_type}\n{previous_content}\n```\n\n"
        else:
            retry_prompt += f"```\n{previous_content}\n```\n\n"
        retry_prompt += "其中检测到了生成的内容存在以下问题:\n\n"
        for issue in issues:
            retry_prompt += f"- {issue.issue_content}\n"
        retry_prompt += "\n请根据检测到的问题，修改上一次生成内容中的错误，使其符合系统提示词的要求\n"
        return retry_prompt

    def is_cmd_valid(self):
        """检查目录文件填充命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证目录文件填充命令的前置条件"""
        # 检查需求分析结果文件是否存在
        requirement_analysis_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        if not os.path.exists(requirement_analysis_file):
            print(f"  {Colors.WARNING}警告: 需求分析结果文件不存在，请先执行需求分析命令{Colors.ENDC}")
            return False
            
        # 检查目录结构文件是否存在
        dir_structure_file = os.path.join(self.work_data_dir_path, 'icp_dir_content.json')
        if not os.path.exists(dir_structure_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行目录生成命令{Colors.ENDC}")
            return False
        
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查handler实例是否已初始化
        if not self.chat_handler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查角色1的系统提示词是否加载
        if not self.sys_prompt_dir_file_fill:
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_dir_file_fill} 未加载{Colors.ENDC}")
            return False
        
        # 检查角色2的系统提示词是否加载
        if not self.sys_prompt_plan_gen:
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_plan_gen} 未加载{Colors.ENDC}")
            return False
            
        return True
