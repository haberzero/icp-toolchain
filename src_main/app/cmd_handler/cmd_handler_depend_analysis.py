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
from utils.issue_recorder import TextIssueRecorder



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
        self.sys_prompt = ""  # 系统提示词,在_init_ai_handlers中加载
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行依赖分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行依赖分析...{Colors.ENDC}")

        # 重置实例变量
        self.issue_recorder.clear()
        self.last_generated_content = None
        
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
                sys_prompt=self.sys_prompt,
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
            
            # 如果验证失败，保存当前生成的内容用于下一次重试
            self.last_generated_content = cleaned_json_str
            # 重新构建用户提示词（包含issue信息）
            user_prompt = self._build_user_prompt_for_depend_analyzer()
        
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
        
        # 如果是重试，添加上一次生成的内容和问题信息
        if self.issue_recorder.has_issues() and self.last_generated_content:
            user_prompt_str += "\n\n## 重试生成信息\n\n"
            user_prompt_str += "这是一次重试生成，上一次生成的内容是:\n\n"
            user_prompt_str += "``json\n" + self.last_generated_content + "\n```\n\n"
            user_prompt_str += "其中检测到了生成的内容存在以下问题:\n\n"
            for issue in self.issue_recorder.get_issues():
                user_prompt_str += f"- {issue.issue_content}\n"
            user_prompt_str += "\n请根据检测到的问题，修改上一次生成内容中的错误，使其符合系统提示词的要求\n"
        
        return user_prompt_str

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
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查系统提示词是否加载
        if not self.sys_prompt:
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_name} 未加载{Colors.ENDC}")
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
        
        # 读取系统提示词文件
        try:
            with open(app_sys_prompt_file_path, 'r', encoding='utf-8') as f:
                self.sys_prompt = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败: {e}")