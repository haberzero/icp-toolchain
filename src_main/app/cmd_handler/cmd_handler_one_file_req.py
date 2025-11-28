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


class CmdHandlerOneFileReq(BaseCmdHandler):
    """IBC目录结构下创建单文件需求描述"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="one_file_req_gen",
            aliases=["OFR"],
            description="在文件系统中创建src_staging目录结构以及one_file_req.txt文件",
            help_text="根据已有的dir_content.json文件的内容在src_staging目录结构下创建单文件的编程需求描述, 为IBC的生成做准备",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir_path = proj_cfg_manager.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        self.chat_handler = ICPChatHandler()
        self.role_one_file_req = "7_one_file_req_gen"
        self._init_ai_handlers()

        self.accumulated_file_str_list: List[tuple[str, str]] = []  # File path and its content

    def execute(self):
        """执行IBC目录结构创建"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始创建IBC目录结构...{Colors.ENDC}")

        # 给后续代码运行准备所需信息
        self._build_pre_execution_variables()

        # 创建src_staging目录用于存储_one_file_req.txt文件
        work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
        try:
            os.makedirs(work_staging_dir_path, exist_ok=True)
            print(f"  {Colors.OKGREEN}src_staging目录创建成功: {work_staging_dir_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 创建src_staging目录失败: {e}{Colors.ENDC}")
            return

        # 按文件生成顺序遍历并生成后续文件
        for icp_json_file_path in self.file_creation_order_list:
            success = self._create_single_one_file_req(icp_json_file_path)
            if not success:
                print(f"{Colors.FAIL}单文件需求描述生成失败，终止执行{Colors.ENDC}")
                return

        # 使用前序依赖分析的结果，生成最终的目录内容文件
        dir_content_dict = {
            "proj_root": self.final_dir_json_dict['proj_root'],
            "dependent_relation": self.dependent_relation_dict
        }
        
        dir_content_file = os.path.join(self.work_data_dir_path, "icp_dir_content_final.json")
        try:
            with open(dir_content_file, 'w', encoding='utf-8') as f:
                json.dump(dir_content_dict, f, indent=2, ensure_ascii=False)
            print(f"  {Colors.OKGREEN}目录内容文件已保存: {dir_content_file}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存目录内容文件失败 {dir_content_file}: {e}{Colors.ENDC}")
            return

        print(f"{Colors.OKGREEN}IBC目录结构创建命令执行完毕!{Colors.ENDC}")

    def _build_pre_execution_variables(self) -> List[str]:
        """准备命令正式开始执行之前所需的变量内容"""
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements_str = user_data_manager.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.FAIL}错误: 读取用户需求失败{Colors.ENDC}")
            return ""
        
        # 读取经过依赖项修复的目录结构
        final_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_refined.json')
        try:
            with open(final_dir_file, 'r', encoding='utf-8') as f:
                final_dir_json_dict = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取最终目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not final_dir_json_dict:
            print(f"  {Colors.FAIL}错误: 最终目录结构内容为空{Colors.ENDC}")
            return

        # 检查是否包含必要的节点
        if "proj_root" not in final_dir_json_dict or "dependent_relation" not in final_dir_json_dict:
            print(f"  {Colors.FAIL}错误: 最终目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return
        
        # 从dependent_relation中获取文件创建顺序, 可以认为列表中靠近 index=0 的文件其层级低且被其它文件依赖
        dependent_relation_dict = final_dir_json_dict["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation_dict)
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            return

        # 构建可用的第三方库可用清单以及模块依赖建议, 来源 refined_requirements.json
        allowed_libs_text = "（不允许使用任何第三方库）"
        module_suggestions_text = "（无可用模块依赖建议）"
        allowed_lib_keys = set()

        refined_requirements_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(refined_requirements_file, 'r', encoding='utf-8') as rf:
                refined = json.load(rf)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取精炼要求文件失败: {e}{Colors.ENDC}")
            return

        # 处理外部库允许清单
        libs = refined.get('ExternalLibraryDependencies', {}) if isinstance(refined, dict) else {}
        if isinstance(libs, dict) and libs:
            allowed_libs_text = "\n".join(f"- {name}: {desc}" for name, desc in libs.items())
            allowed_lib_keys = set(libs.keys())

        # 生成模块依赖建议
        module_breakdown = refined.get('module_breakdown', {}) if isinstance(refined, dict) else {}
        if isinstance(module_breakdown, dict) and allowed_lib_keys:
            lines = []
            for mod_name, mod_obj in module_breakdown.items():
                deps = mod_obj.get('dependencies', []) if isinstance(mod_obj, dict) else []
                filtered = [dep for dep in deps if dep in allowed_lib_keys]
                if filtered:
                    lines.append(f"- {mod_name}: {', '.join(filtered)}")
            if lines:
                module_suggestions_text = "\n".join(lines)


        # 存储后续代码执行需要的实例变量
        self.user_requirements_str = user_requirements_str
        self.final_dir_json_dict = final_dir_json_dict
        self.dependent_relation_dict = dependent_relation_dict
        self.file_creation_order_list = file_creation_order_list
        self.implementation_plan_str = implementation_plan_str
        self.allowed_libs_text = allowed_libs_text
        self.module_suggestions_text = module_suggestions_text

        return

    def _create_single_one_file_req(self, icp_json_file_path: str) -> bool:
        """为当前选中路径生成单文件需求描述并保存"""
        max_attempts = 3
        response_content = None
        success = False

        for attempt in range(max_attempts):
            print(f"{self.role_one_file_req}正在进行第 {attempt + 1} 次尝试...")
            
            # 构建用户提示词
            user_prompt_ofr = self._build_user_prompt_for_one_file_req(icp_json_file_path)
            if not user_prompt_ofr:
                print(f"  {Colors.FAIL}错误: 无法构建用户提示词: {icp_json_file_path}{Colors.ENDC}")
                return False

            # 获取模型输出
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_one_file_req,
                user_prompt=user_prompt_ofr
            ))
            
            # 移除可能的代码块标记
            response_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            if success:
                break
            else:
                print(f"  {Colors.FAIL}错误: 生成文件依赖关系失败: {icp_json_file_path}{Colors.ENDC}")
                print(f"  {Colors.FAIL}重试当前文件的生成过程{Colors.ENDC}")
        
        # 循环已跳出，检查运行结果并进行相应操作
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，生成单文件需求描述失败: {icp_json_file_path}{Colors.ENDC}")
            return False

        # 累计保存目前已经生成的文件的路径以及其单文件编程需求描述
        self.accumulated_file_str_list.append((icp_json_file_path, response_content))

        # 保存需求描述至具体文件
        work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
        req_file_path = os.path.join(work_staging_dir_path, f"{icp_json_file_path}_one_file_req.txt")
    
        parent_dir = os.path.dirname(req_file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        try:
            with open(req_file_path, 'w', encoding='utf-8') as f:
                f.write(response_content)
            print(f"  {Colors.OKGREEN}文件需求描述已保存: {req_file_path}{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
            return False

    def _build_user_prompt_for_one_file_req(self, icp_json_file_path: str) -> str:
        """
        构建单文件需求生成的用户提示词
        Args:
            icp_json_file_path: 当前执行中的文件的路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 获取dir_json中的文件描述
        file_description = DirJsonFuncs.get_file_description(self.final_dir_json_dict['proj_root'], icp_json_file_path)
        if not file_description:
            print(f"  {Colors.FAIL}错误: 无法获取文件描述: {icp_json_file_path}{Colors.ENDC}")
            return ""
        
        # 遍历读取已生成的累积描述，仅获取当前文件依赖的文件的描述
        if self.dependent_relation_dict and isinstance(self.dependent_relation_dict, dict):
            current_file_dependencies = self.dependent_relation_dict.get(icp_json_file_path, [])
            print(f"  {Colors.OKGREEN}当前文件依赖: {current_file_dependencies}{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}错误: 无法获取当前文件依赖: {icp_json_file_path}{Colors.ENDC}")
            return ""
        accumulated_related_desc = []
        
        for _file_path, file_str in self.accumulated_file_str_list:
            # 只包含当前文件依赖的文件
            if _file_path not in current_file_dependencies:
                continue
                
            extracted_desc = self._extract_section_content(file_str, 'description')
            extracted_func = self._extract_section_content(file_str, 'function')
            extracted_class = self._extract_section_content(file_str, 'class')

            cleaned_file_path = _file_path.replace("_one_file_req.txt", "")
            normed_file_path = os.path.normpath(cleaned_file_path)
            formatted = f"文件 {normed_file_path} 的接口描述:\n"
            if extracted_class:
                formatted += f"类信息:\n{extracted_class}\n\n"
            if extracted_func:
                formatted += f"函数信息:\n{extracted_func}\n\n"
            if extracted_desc:
                formatted += f"描述信息:\n{extracted_desc}"
            
            accumulated_related_desc.append(formatted)

        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        app_user_prompt_file_path = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_gen_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 填充与文件描述相关的占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('USER_REQUIREMENTS_PLACEHOLDER', self.user_requirements_str)
        user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', self.implementation_plan_str)
        user_prompt_str = user_prompt_str.replace('FILE_DESCRIPTION_PLACEHOLDER', file_description)
        user_prompt_str = user_prompt_str.replace('RELATED_FILE_DESCRIPTIONS_PLACEHOLDER', 
                                        '\n\n'.join(accumulated_related_desc) if accumulated_related_desc else '暂无依赖的文件需求描述')
        
        # 填充与第三方库相关的占位符
        user_prompt_str = user_prompt_str.replace('EXTERNAL_LIB_ALLOWLIST_PLACEHOLDER', self.allowed_libs_text)
        user_prompt_str = user_prompt_str.replace('MODULE_DEPENDENCY_SUGGESTIONS_PLACEHOLDER', self.module_suggestions_text)
        
        return user_prompt_str

    def _extract_section_content(self, content: str, section_name: str) -> str:
        """从文件内容中提取指定section部分
        
        Args:
            content: 文件内容
            section_name: 要提取的section名称(如'description', 'func', 'class'等)
            
        Returns:
            str: 提取的section内容
        """
        lines = content.split('\n')
        section_lines = []
        found_section = False
        
        # 构建section标记
        section_marker = f'{section_name}:'
        
        for line in lines:
            # 查找section:开始的行
            if line.strip().startswith(section_marker):
                found_section = True
                continue

            # 检查是否应该结束section部分的提取
            elif found_section: 
                stripped_line = line.strip()
                
                # 如果是空行，继续添加（保持格式）
                if not stripped_line:
                    section_lines.append(line)
                    continue
                
                # 如果是注释行则跳过。注释行以#开头
                if stripped_line.startswith('#'):
                    continue
                
                # 检查是否是新的段落（以字母开头且没有缩进）
                is_new_paragraph = (
                    stripped_line and 
                    stripped_line[0].isalpha() and 
                    not line.startswith((' ', '\t'))  # 没有缩进
                )
                
                if is_new_paragraph:
                    break
                else:
                    # 添加section部分的内容行
                    section_lines.append(line)
    
        return '\n'.join(section_lines)

    def is_cmd_valid(self):
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查最终目录结构文件是否存在
        final_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_refined.json')
        if not os.path.exists(final_dir_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行循环依赖解决命令{Colors.ENDC}")
            return False
        
        # 检查文件级实现规划文件是否存在
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        if not os.path.exists(implementation_plan_file):
            print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
        
        # 检查用户原始需求是否存在
        user_data_manager = get_user_data_manager()
        user_requirements_str = user_data_manager.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.WARNING}警告: 用户原始需求不存在，请先加载用户需求{Colors.ENDC}")
            return False
        
        # 检查精炼需求文件是否存在（用于获取第三方库信息）
        refined_requirements_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        if not os.path.exists(refined_requirements_file):
            print(f"  {Colors.WARNING}警告: 精炼需求文件不存在，请先执行需求分析命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        if not self.chat_handler.has_role(self.role_one_file_req):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_one_file_req} 未加载{Colors.ENDC}")
            return False
        return True
    
    def _init_ai_handlers(self):
        """初始化AI处理器"""
        if not os.path.exists(self.work_api_config_file_path):
            print(f"错误: 配置文件 {self.work_api_config_file_path} 不存在")
            return
        
        try:
            with open(self.work_api_config_file_path, 'r', encoding='utf-8') as f:
                config_json_dict = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        if 'dependency_refine_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['dependency_refine_handler']
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
        
        app_data_manager = get_app_data_manager()
        app_prompt_dir_path = app_data_manager.get_prompt_dir()
        app_sys_prompt_file_path = os.path.join(app_prompt_dir_path, self.role_one_file_req + ".md")
        
        self.chat_handler.load_role_from_file(self.role_one_file_req, app_sys_prompt_file_path)
