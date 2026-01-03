import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from data_store.sys_prompt_manager import get_instance as get_sys_prompt_manager
from data_store.user_prompt_manager import get_instance as get_user_prompt_manager
from data_store.user_data_store import get_instance as get_user_data_store
from libs.dir_json_funcs import DirJsonFuncs
from libs.text_funcs import ChatResponseCleaner
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from typedef.ai_data_types import ChatApiConfig
from typedef.cmd_data_types import CmdProcStatus, Colors, CommandInfo
from utils.icp_ai_utils.icp_chat_inst import ICPChatInsts
from utils.issue_recorder import TextIssueRecorder

from .base_cmd_handler import BaseCmdHandler


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

        # 关联系统提示词角色名
        self.role_name = "5_depend_analyzer"

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
        self.last_sys_prompt_used = ""  # 上一次调用时使用的系统提示词
        self.last_user_prompt_used = ""  # 上一次调用时使用的用户提示词

    def execute(self):
        """执行依赖分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行依赖分析...{Colors.ENDC}")

        # 重置实例变量
        self.issue_recorder.clear()
        self.last_generated_content = None
        self.last_sys_prompt_used = ""
        self.last_user_prompt_used = ""
        
        # 构建用户提示词基础部分
        self.user_prompt_base = self._build_user_prompt_base()
        if not self.user_prompt_base:
            print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
            return
        
        max_attempts = 3
        new_json_dict = None
        is_valid = False
        cleaned_json_str = ""
        
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
        
            base_sys_prompt = self.sys_prompt_manager.get_prompt(self.role_name)
            retry_sys_prompt = self.sys_prompt_manager.get_prompt('retry_sys_prompt')
        
            if attempt == 0:
                # 第一次尝试：直接使用基础提示词
                current_sys_prompt = base_sys_prompt
                current_user_prompt = self.user_prompt_base
        
                response_content, success = asyncio.run(self.chat_handler.get_role_response(
                    role_name=self.role_name,
                    sys_prompt=current_sys_prompt,
                    user_prompt=current_user_prompt
                ))
        
                # 如果响应失败，继续下一次尝试
                if not success:
                    print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                    continue
        
                # 记录本次调用使用的提示词
                self.last_sys_prompt_used = current_sys_prompt
                self.last_user_prompt_used = current_user_prompt
        
                # 清理代码块标记
                cleaned_json_str = ChatResponseCleaner.clean_code_block_markers(response_content)
        
                # 验证响应内容
                is_valid = self._validate_response(cleaned_json_str)
                if is_valid:
                    break
        
                # 如果验证失败，保存当前生成的内容，供后续诊断和修复使用
                self.last_generated_content = cleaned_json_str
        
            else:
                # 重试阶段：先调用「诊断与修复建议」角色，再根据修复建议进行结果修复
                if not self.last_generated_content or not self.issue_recorder.has_issues():
                    print(f"{Colors.WARNING}警告: 无可用的上一次输出或问题信息，无法执行重试修复{Colors.ENDC}")
                    continue
        
                # 将 issue_recorder 中的问题整理为文本列表
                issues_list = "\n".join([f"- {issue.issue_content}" for issue in self.issue_recorder.get_issues()])
        
                # 第一步：根据上一次提示词 / 输出 / 问题列表，生成修复建议
                # 替代 RetryPromptHelper.build_retry_analysis_prompts
                analysis_sys_prompt = self.sys_prompt_manager.get_prompt("retry_analysis_sys_prompt")
                
                analysis_mapping = {
                    "PREVIOUS_SYS_PROMPT_PLACEHOLDER": self.last_sys_prompt_used or "(无)",
                    "PREVIOUS_USER_PROMPT_PLACEHOLDER": self.last_user_prompt_used or "(无)",
                    "PREVIOUS_CONTENT_PLACEHOLDER": self.last_generated_content or "(无输出)",
                    "ISSUES_LIST_PLACEHOLDER": issues_list or "(未检测到问题描述)"
                }
                analysis_user_prompt = self.user_prompt_manager.build_prompt_from_template(
                    "retry_analysis_prompt_template", 
                    analysis_mapping
                )

                fix_suggestion_raw, success = asyncio.run(self.chat_handler.get_role_response(
                    role_name=self.role_name,
                    sys_prompt=analysis_sys_prompt,
                    user_prompt=analysis_user_prompt,
                ))
        
                if not success or not fix_suggestion_raw:
                    print(f"{Colors.WARNING}警告: 生成修复建议失败，将进行下一次尝试{Colors.ENDC}")
                    continue
        
                fix_suggestion = ChatResponseCleaner.clean_code_block_markers(fix_suggestion_raw)
        
                # 第二步：根据修复建议重新组织用户提示词，发起修复请求
                self.user_prompt_retry_part = self._build_user_prompt_retry_part(fix_suggestion)
        
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
        
                if not success:
                    print(f"{Colors.WARNING}警告: 修复阶段AI响应失败，将进行下一次尝试{Colors.ENDC}")
                    continue
        
                # 更新记录本次调用使用的提示词
                self.last_sys_prompt_used = current_sys_prompt
                self.last_user_prompt_used = current_user_prompt
        
                # 清理代码块标记
                cleaned_json_str = ChatResponseCleaner.clean_code_block_markers(response_content)
        
                # 再次验证修复后的响应内容
                is_valid = self._validate_response(cleaned_json_str)
                if is_valid:
                    break
        
                # 如果依然验证失败，保存当前生成的内容，供下一轮重试使用
                self.last_generated_content = cleaned_json_str
        
        if attempt == max_attempts - 1 and not is_valid:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的依赖关系{Colors.ENDC}")
            return
        
        # 解析最终的JSON数据
        try:
            new_json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: 解析最终JSON失败: {e}{Colors.ENDC}")
            return
        
        # 保存最终结果到 icp_dir_content_with_depend.json
        output_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(new_json_dict, f, indent=2, ensure_ascii=False)
            print(f"{Colors.OKBLUE}依赖分析完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
            return

    def _build_user_prompt_base(self) -> str:
        """
        构建依赖分析的用户提示词基础部分
        
        从项目数据目录中读取所需文件，无需外部参数输入。
        
        Returns:
            str: 基础用户提示词，失败时返回空字符串
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
        file_paths = DirJsonFuncs.get_all_file_paths(self.old_json_dict.get("proj_root_dict", {}))
        file_paths_text = "\n".join(file_paths)

        # 使用用户提示词模板管理器构建基础用户提示词
        placeholder_mapping = {
            'IMPLEMENTATION_PLAN_PLACEHOLDER': implementation_plan_str,
            'JSON_STRUCTURE_PLACEHOLDER': dir_with_files_str,
            'FILE_PATHS_PLACEHOLDER': file_paths_text,
        }
        user_prompt_str = self.user_prompt_manager.build_prompt_from_template(
            template_name='depend_analysis_user',
            placeholder_mapping=placeholder_mapping,
        )
        if not user_prompt_str:
            print(f"  {Colors.FAIL}错误: 依赖分析用户提示词模板构建失败{Colors.ENDC}")
            return ""
        
        return user_prompt_str
    
    def _build_user_prompt_retry_part(self, fix_suggestion: str) -> str:
        """构建用户提示词重试部分（基于修复建议的输出修复提示）
        
        Args:
            fix_suggestion: 上一步诊断阶段生成的修复建议
        
        Returns:
            str: 重试部分的用户提示词，失败时返回空字符串
        """
        if not self.issue_recorder.has_issues() or not self.last_generated_content:
            return ""
        
        # 将 issue_recorder 中的问题整理为文本列表
        issues_list = "\n".join([f"- {issue.issue_content}" for issue in self.issue_recorder.get_issues()])
        
        # 替代 RetryPromptHelper.build_fix_user_prompt_part
        # 格式化上一次生成的内容
        formatted_content = f"```json\n{self.last_generated_content}\n```"
        
        retry_mapping = {
            "PREVIOUS_CONTENT_PLACEHOLDER": formatted_content,
            "ISSUES_LIST_PLACEHOLDER": issues_list or ""
        }
        
        retry_prompt = self.user_prompt_manager.build_prompt_from_template("retry_prompt_template", retry_mapping)
        
        # 追加修复建议
        retry_prompt += "\n\n【修复建议】\n"
        retry_prompt += (fix_suggestion or "(无修复建议)")
        
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
            new_json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            error_msg = f"AI返回的内容不是有效的JSON格式: {e}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检查新JSON内容是否包含必需的根节点
        if "proj_root_dict" not in new_json_dict or "dependent_relation" not in new_json_dict:
            error_msg = "生成的JSON结构不符合要求，缺少必需的根节点 proj_root_dict 或 dependent_relation"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检查proj_root_dict结构是否与原始结构一致
        structure_errors = DirJsonFuncs.compare_structure(self.old_json_dict["proj_root_dict"], new_json_dict["proj_root_dict"])
        if structure_errors:
            error_msg = "proj_root_dict结构与原始结构不一致，具体问题如下：\n" + "\n".join(f"  - {err}" for err in structure_errors)
            print(f"{Colors.WARNING}警告: proj_root_dict结构与原始结构不一致{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检查是否有proj_root_dict中的文件在dependent_relation中缺失
        missing_files = DirJsonFuncs.find_missing_files_in_dependent_relation(new_json_dict)
        if missing_files:
            error_msg = "dependent_relation 中缺少以下文件的依赖关系条目，请为每个文件添加对应条目（即使该文件没有依赖其他文件，也需要添加空列表 []）：\n" + "\n".join(f"  - {file}" for file in missing_files)
            print(f"{Colors.WARNING}警告: dependent_relation 中缺少 {len(missing_files)} 个文件的条目{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
            
        # 检查dependent_relation中的依赖路径是否都存在于proj_root_dict中
        path_errors = DirJsonFuncs.check_dependent_paths_existence(new_json_dict["dependent_relation"], new_json_dict["proj_root_dict"])
        if path_errors:
            error_msg = "dependent_relation 中存在 proj_root_dict 下不存在的路径，具体问题如下：\n" + "\n".join(f"  - {err}" for err in path_errors)
            print(f"{Colors.WARNING}警告: dependent_relation 出现了 proj_root_dict 下不存在的路径{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 检测循环依赖
        dependent_relation = new_json_dict.get("dependent_relation", {})
        circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
        
        if circular_dependencies:
            error_msg = "检测到循环依赖，具体循环路径如下：\n" + "\n".join(f"  - {cycle}" for cycle in circular_dependencies)
            print(f"{Colors.WARNING}警告: 检测到循环依赖{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
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

        # 检查依赖分析用户提示词模板
        if not self.user_prompt_manager.has_template('depend_analysis_user'):
            print(f"  {Colors.FAIL}错误: 用户提示词模板 depend_analysis_user 未加载{Colors.ENDC}")
            return False
            
        return True
