import sys, os
import asyncio
import json
import re
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
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 使用新的 ICPChatHandler
        self.chat_handler = ICPChatHandler()
        self.role_dir_file_fill = "4_dir_file_fill"
        self.role_plan_gen = "4_dir_file_fill_plan_gen"
        self.sys_prompt_dir_file_fill = ""  # 系统提示词,在_init_ai_handlers中加载
        self.sys_prompt_plan_gen = ""  # 系统提示词,在_init_ai_handlers中加载
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行目录文件填充"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行目录文件填充...{Colors.ENDC}")

        # 重置实例变量
        self.issue_recorder.clear()
        self.last_generated_content = None

        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_dir_file_filler()
        if not user_prompt:
            return
        
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_dir_file_fill}正在进行第 {attempt + 1} 次尝试...")
            
            # ===== 临时代码: 保存用户提示词 =====
            temp_prompt_file = os.path.join(self.work_data_dir_path, f'temp_user_prompt_attempt_{attempt + 1}.txt')
            try:
                with open(temp_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(user_prompt)
                print(f"{Colors.OKBLUE}[临时] 已保存第 {attempt + 1} 次尝试的用户提示词到: {temp_prompt_file}{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.WARNING}[临时] 保存用户提示词失败: {e}{Colors.ENDC}")
            # ===== 临时代码结束 =====
            
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_dir_file_fill,
                sys_prompt=self.sys_prompt_dir_file_fill,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
                
            # 清理代码块标记
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容
            is_valid = self._validate_response(cleaned_content, self.old_json_dict)
            if is_valid:
                break
            
            # 如果验证失败，保存当前生成的内容用于下一次重试
            self.last_generated_content = cleaned_content
            # 重新构建用户提示词（包含issue信息）
            user_prompt = self._build_user_prompt_for_dir_file_filler()
        
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
            
            # ===== 临时代码: 保存用户提示词 =====
            temp_prompt_file = os.path.join(self.work_data_dir_path, f'temp_plan_gen_prompt_attempt_{attempt + 1}.txt')
            try:
                with open(temp_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(user_prompt)
                print(f"{Colors.OKBLUE}[临时] 已保存第 {attempt + 1} 次实现规划提示词到: {temp_prompt_file}{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.WARNING}[临时] 保存实现规划提示词失败: {e}{Colors.ENDC}")
            # ===== 临时代码结束 =====
            
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
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            break
        
        # 保存实现规划
        output_file_path = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
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
        
        # 如果是重试，添加上一次生成的内容和问题信息
        if self.issue_recorder.has_issues() and self.last_generated_content:
            user_prompt_str += "\n\n## 重试生成信息\n\n"
            user_prompt_str += "这是一次重试生成，上一次生成的内容是:\n\n"
            user_prompt_str += "```json\n" + self.last_generated_content + "\n```\n\n"
            user_prompt_str += "其中检测到了生成的内容存在以下问题:\n\n"
            for issue in self.issue_recorder.get_issues():
                print("issue: ", issue.issue_content)
                user_prompt_str += f"- {issue.issue_content}\n"
            user_prompt_str += "\n请根据检测到的问题，修改上一次生成内容中的错误，使其符合系统提示词的要求\n"
        
        return user_prompt_str

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
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
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
        
        # 优先检查是否有dir_file_fill_handler配置
        if 'dir_file_fill_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['dir_file_fill_handler']
        elif 'coder_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['coder_handler']
        else:
            print("错误: 配置文件缺少dir_file_fill_handler或coder_handler配置")
            return
        
        chat_handler_config = ChatApiConfig(
            base_url=chat_api_config_dict.get('api-url', ''),
            api_key=chat_api_config_dict.get('api-key', ''),
            model=chat_api_config_dict.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(chat_handler_config)
        
        # 加载两个角色的系统提示词
        app_data_store = get_app_data_store()
        app_prompt_dir_path = app_data_store.get_prompt_dir()
        prompt_file_name_1 = self.role_dir_file_fill + ".md"
        prompt_file_name_2 = self.role_plan_gen + ".md"
        app_sys_prompt_file_path_1 = os.path.join(app_prompt_dir_path, prompt_file_name_1)
        app_sys_prompt_file_path_2 = os.path.join(app_prompt_dir_path, prompt_file_name_2)
        
        # 读取系统提示词文件
        try:
            with open(app_sys_prompt_file_path_1, 'r', encoding='utf-8') as f:
                self.sys_prompt_dir_file_fill = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败 ({self.role_dir_file_fill}): {e}")
        
        try:
            with open(app_sys_prompt_file_path_2, 'r', encoding='utf-8') as f:
                self.sys_prompt_plan_gen = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败 ({self.role_plan_gen}): {e}")
    