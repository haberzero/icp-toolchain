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
from libs.dir_json_funcs import DirJsonFuncs
from data_store.issue_recoder_data_store import get_instance as get_issue_recorder_data_store



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
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 使用新的 ICPChatHandler
        self.chat_handler = ICPChatHandler()
        self.role_name = "5_depend_analyzer"
        self.role_refine_name = "5_depend_refine"
        
        # 用于循环依赖处理的实例变量
        self.circular_deps_content = None  # 循环依赖信息字符串
        self.dependency_structure_content = None  # 依赖结构内容
        self.first_refine_attempt = True  # 是否是第一次refine尝试
        self.original_json_dict = None  # 原始的JSON内容
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行依赖分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行依赖分析...{Colors.ENDC}")

        # 重置实例变量
        self.circular_deps_content = None
        self.dependency_structure_content = None
        self.first_refine_attempt = True
        self.original_json_dict = None
        
        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_depend_analyzer()
        if not user_prompt:
            return
        
        max_attempts = 3
        new_json_dict = None
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                # 记录错误到issue_recorder_data_store
                issue_data_store = get_issue_recorder_data_store()
                issue_data_store.append_issue_record(
                    work_dir=self.work_dir_path,
                    stage="depend_analysis",
                    attempt=attempt + 1,
                    error_type="ai_response_failed",
                    error_message="AI响应失败",
                    current_output=""
                )
                continue
                
            # 清理代码块标记
            cleaned_json_str = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid, new_json_dict = self._validate_response(cleaned_json_str)
            if is_valid:
                break
        
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的依赖关系{Colors.ENDC}")
            return
        
        # 检测循环依赖
        dependent_relation = new_json_dict.get("dependent_relation", {})
        circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
        
        if circular_dependencies:
            # 存在循环依赖，调用depend_refine流程
            print(f"{Colors.WARNING}检测到循环依赖，开始循环依赖修复流程...{Colors.ENDC}")
            for cycle in circular_dependencies:
                print(f"  {Colors.WARNING}{cycle}{Colors.ENDC}")
            
            # 保存原始JSON和循环依赖信息
            self.original_json_dict = new_json_dict
            self.circular_deps_content = '\n'.join(circular_dependencies)
            self.dependency_structure_content = cleaned_json_str
            
            # 执行循环依赖修复
            refined_json_dict = self._execute_depend_refine()
            if refined_json_dict:
                new_json_dict = refined_json_dict
            else:
                print(f"{Colors.FAIL}错误: 循环依赖修复失败{Colors.ENDC}")
                return
        
        # 保存最终结果到 icp_dir_content_with_depend.json（无论是否经过refine）
        output_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(new_json_dict, f, indent=2, ensure_ascii=False)
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
        file_paths = DirJsonFuncs.get_all_file_paths(self.old_json_dict.get("proj_root_dict", {}))
        file_paths_text = "\n".join(file_paths)

        # 读取用户提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'depend_analysis_user.md')
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

    def _execute_depend_refine(self) -> Dict[str, Any]:
        """
        执行循环依赖修复流程
        
        Returns:
            Dict[str, Any]: 修复后的JSON字典，失败时返回None
        """
        max_refine_attempts = 3
        new_json_dict = None
        
        for attempt in range(max_refine_attempts):
            print(f"{self.role_refine_name}正在进行第 {attempt + 1} 次尝试...")
            
            # 构建用户提示词
            user_prompt = self._build_user_prompt_for_depend_refiner(attempt + 1)
            if not user_prompt:
                print(f"{Colors.FAIL}错误: 构建refine用户提示词失败{Colors.ENDC}")
                return None
            
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_refine_name,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                # 记录错误到issue_recorder_data_store
                issue_data_store = get_issue_recorder_data_store()
                issue_data_store.append_issue_record(
                    work_dir=self.work_dir_path,
                    stage="depend_refine",
                    attempt=attempt + 1,
                    error_type="ai_response_failed",
                    error_message="AI响应失败",
                    current_output=""
                )
                continue
                
            # 清理代码块标记
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容（包含循环依赖检测）
            is_valid, new_json_dict = self._validate_refine_response(cleaned_content, attempt + 1)
            if is_valid:
                # 所有检查都通过，跳出循环
                break
        
        # 循环已跳出，检查运行结果
        if attempt == max_refine_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能成功消除循环依赖{Colors.ENDC}")
            return None

        print(f"{Colors.OKBLUE}循环依赖解决完成{Colors.ENDC}")
        return new_json_dict

    def _build_user_prompt_for_depend_refiner(self, attempt: int) -> str:
        """
        构建依赖修复的用户提示词
        
        Args:
            attempt: 当前重试次数
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'depend_refine_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('CIRCULAR_DEPENDENCIES_PLACEHOLDER', self.circular_deps_content)
        user_prompt_str = user_prompt_str.replace('DEPENDENCY_STRUCTURE_PLACEHOLDER', self.dependency_structure_content)
        
        # 如果是重试，从issue_recorder_data_store中获取历史错误信息并附加
        if attempt > 1:
            issue_data_store = get_issue_recorder_data_store()
            retry_info = issue_data_store.get_latest_issue(
                work_dir=self.work_dir_path,
                stage="depend_refine"
            )
            if retry_info:
                user_prompt_str += "\n\n## 上一次尝试的问题记录\n\n"
                user_prompt_str += "**上一次的错误类型:** " + retry_info.get("error_type", "") + "\n\n"
                user_prompt_str += "**上一次的错误信息:** " + retry_info.get("error_message", "") + "\n\n"
                user_prompt_str += "**上一次的输出内容:** \n```json\n" + retry_info.get("current_output", "") + "\n```\n\n"
                user_prompt_str += "请根据上述问题进行针对性修复。\n"
        
        return user_prompt_str

    def _validate_refine_response(self, cleaned_json_str: str, attempt: int) -> tuple[bool, Dict[str, Any]]:
        """
        验证refine后的AI响应内容是否符合要求
        
        Args:
            cleaned_json_str: 清理后的AI响应内容
            attempt: 当前尝试次数
            
        Returns:
            tuple[bool, Dict[str, Any]]: (是否有效, JSON内容字典)
        """
        # 验证是否为有效的JSON
        try:
            new_json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            error_msg = f"AI返回的内容不是有效的JSON格式: {e}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_json_str}")
            # 记录错误
            issue_data_store = get_issue_recorder_data_store()
            issue_data_store.append_issue_record(
                work_dir=self.work_dir_path,
                stage="depend_refine",
                attempt=attempt,
                error_type="invalid_json",
                error_message=error_msg,
                current_output=cleaned_json_str
            )
            return False, {}
        
        # 检查新JSON内容是否包含proj_root_dict和dependent_relation节点
        if "proj_root_dict" not in new_json_dict or "dependent_relation" not in new_json_dict:
            error_msg = "生成的JSON结构不符合要求，缺少必需的根节点"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            # 记录错误
            issue_data_store = get_issue_recorder_data_store()
            issue_data_store.append_issue_record(
                work_dir=self.work_dir_path,
                stage="depend_refine",
                attempt=attempt,
                error_type="missing_required_nodes",
                error_message=error_msg,
                current_output=cleaned_json_str
            )
            return False, {}
        
        # 确保dependent_relation中包含proj_root_dict下的所有文件路径
        DirJsonFuncs.ensure_all_files_in_dependent_relation(new_json_dict)
        
        # 检测循环依赖
        dependent_relation = new_json_dict.get("dependent_relation", {})
        circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
        
        if circular_dependencies:
            # 仍然存在循环依赖
            error_msg = "仍检测到循环依赖"
            print(f"{Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            for cycle in circular_dependencies:
                print(f"  {Colors.WARNING}{cycle}{Colors.ENDC}")
            
            # 记录错误到issue_recorder_data_store
            issue_data_store = get_issue_recorder_data_store()
            issue_data_store.append_issue_record(
                work_dir=self.work_dir_path,
                stage="depend_refine",
                attempt=attempt,
                error_type="circular_dependency_still_exists",
                error_message=error_msg + ": " + "; ".join(circular_dependencies),
                current_output=cleaned_json_str
            )
            
            # 更新实例变量，用于下一轮提示词构建
            self.circular_deps_content = '\n'.join(circular_dependencies)
            self.dependency_structure_content = cleaned_json_str
            self.first_refine_attempt = False
            
            return False, new_json_dict
        
        # 所有检查都通过
        return True, new_json_dict

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
            return False, {}
        
        # 检查新JSON内容是否包含必需的根节点
        if "proj_root_dict" not in new_json_dict or "dependent_relation" not in new_json_dict:
            print(f"{Colors.WARNING}警告: 生成的JSON缺少必需的根节点 proj_root_dict 或 dependent_relation{Colors.ENDC}")
            return False, {}
        
        # 检查proj_root_dict结构是否与原始结构一致
        if not DirJsonFuncs.compare_structure(self.old_json_dict["proj_root_dict"], new_json_dict["proj_root_dict"]):
            print(f"{Colors.WARNING}警告: proj_root_dict结构与原始结构不一致{Colors.ENDC}")
            return False, {}
            
        # 检查dependent_relation中的依赖路径是否都存在于proj_root_dict中
        is_valid, validation_errors = DirJsonFuncs.validate_dependent_paths(new_json_dict["dependent_relation"], new_json_dict["proj_root_dict"])
        if not is_valid:
            print(f"{Colors.WARNING}警告: 生成的 dependent_relation 出现了 proj_root_dict 下不存在的路径{Colors.ENDC}")
            print(f"{Colors.WARNING}具体错误如下:{Colors.ENDC}")
            for error in validation_errors:
                print(f"  - {error}")
            return False, {}
        
        return True, new_json_dict

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
        
        # 检查refine角色是否已加载
        if not self.chat_handler.has_role(self.role_refine_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_refine_name} 未加载{Colors.ENDC}")
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
        app_data_store = get_app_data_store()
        app_prompt_dir_path = app_data_store.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        app_sys_prompt_file_path = os.path.join(app_prompt_dir_path, prompt_file_name)
        
        # 从文件加载角色提示词
        self.chat_handler.load_role_from_file(self.role_name, app_sys_prompt_file_path)
        
        # 加载refine角色的系统提示词
        prompt_file_name_refine = self.role_refine_name + ".md"
        app_sys_prompt_file_path_refine = os.path.join(app_prompt_dir_path, prompt_file_name_refine)
        self.chat_handler.load_role_from_file(self.role_refine_name, app_sys_prompt_file_path_refine)