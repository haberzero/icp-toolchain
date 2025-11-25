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
    """IBC目录结构下创建单文件需求描述并生成最新依赖关系"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="one_file_req_gen",
            aliases=["OFR"],
            description="在文件系统中创建src_staging目录结构以及one_file_req.txt文件",
            help_text="根据已有的dir_content.json文件的内容在src_staging目录结构下创建单文件的编程需求描述, 为IBC的生成做准备",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        self.chat_handler = ICPChatHandler()
        self.role_one_file_req = "7_one_file_req_gen"
        self.role_one_file_req_depend = "7_one_file_req_depend_analyzer"
        self._init_ai_handlers()

        self.accumulated_file_str_content: List[tuple[str, str]] = []  # File path and its content

    def execute(self):
        """执行IBC目录结构创建"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始创建IBC目录结构...{Colors.ENDC}")

        # 给后续代码运行准备所需信息
        self._build_pre_execution_variables()

        # 创建src_staging目录用于存储_one_file_req.txt文件
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        try:
            os.makedirs(staging_dir_path, exist_ok=True)
            print(f"  {Colors.OKGREEN}src_staging目录创建成功: {staging_dir_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 创建src_staging目录失败: {e}{Colors.ENDC}")
            return

        # 按文件生成顺序遍历并生成后续文件
        for file_path in self.file_creation_order_list:
            self._create_single_one_file_req(file_path)









        # 为每个文件生成依赖关系，并获取新的依赖关系字典
        new_dependent_relation = self._generate_file_dependencies_2(staging_dir_path, file_creation_order_list, file_desc_dict, proj_root)
        
        cycle_detected = DirJsonFuncs.detect_circular_dependencies(new_dependent_relation)
        if cycle_detected:
            print(f"  {Colors.FAIL}错误: 检测到循环依赖: {cycle_detected}{Colors.ENDC}")
            return
        print(f"  {Colors.OKGREEN}循环依赖检测通过{Colors.ENDC}")

        # 生成dir_content.json文件，使用新生成的依赖关系
        self._generate_dir_content_json(proj_root, new_dependent_relation)
        
        print(f"{Colors.OKGREEN}IBC目录结构创建命令执行完毕!{Colors.ENDC}")

    def _build_pre_execution_variables(self) -> List[str]:
        """准备命令正式开始执行之前所需的变量内容"""
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 读取用户需求失败{Colors.ENDC}")
            return ""
        
        # 读取经过依赖项修复的目录结构
        final_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        try:
            with open(final_dir_file, 'r', encoding='utf-8') as f:
                final_dir_json_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取最终目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not final_dir_json_content:
            print(f"  {Colors.FAIL}错误: 最终目录结构内容为空{Colors.ENDC}")
            return

        # 检查是否包含必要的节点
        if "proj_root" not in final_dir_json_content or "dependent_relation" not in final_dir_json_content:
            print(f"  {Colors.FAIL}错误: 最终目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return
        
        # 从dependent_relation中获取文件创建顺序, 可以认为列表中靠近 index=0 的文件其层级低且被其它文件依赖
        dependent_relation = final_dir_json_content["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            return

        # 构建可用的第三方库可用清单以及模块依赖建议, 来源 refined_requirements.json
        allowed_libs_text = "（不允许使用任何第三方库）"
        module_suggestions_text = "（无可用模块依赖建议）"
        allowed_lib_keys = set()

        refined_requirements_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
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
        self.user_requirements = user_requirements
        self.final_dir_json_content = final_dir_json_content
        self.file_creation_order_list = file_creation_order_list
        self.implementation_plan_content = implementation_plan_content
        self.allowed_libs_text = allowed_libs_text
        self.module_suggestions_text = module_suggestions_text

        return

    def _create_single_one_file_req(file_path: str) -> bool:
        """为当前选中路径生成单文件需求描述并保存"""
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            
            # 构建用户提示词
            user_prompt_ofr = self._build_user_prompt_for_one_file_req(file_path)
            if not user_prompt_ofr:
                print(f"  {Colors.FAIL}错误: 无法构建用户提示词: {file_path}{Colors.ENDC}")
                return False

            # 获取模型输出
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_one_file_req,
                user_prompt=user_prompt_ofr
            ))
            
            if not success:
                print(f"  {Colors.FAIL}错误: 生成单文件需求描述失败: {file_path}{Colors.ENDC}")
                print(f"  {Colors.FAIL}重试当前文件的生成过程{Colors.ENDC}")
                continue
        
        # 循环已跳出，检查运行结果并进行相应操作
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，生成单文件需求描述失败: {file_path}{Colors.ENDC}")
            return False
        
        # 累计保存目前已经生成的文件需求描述
        self.accumulated_file_str_content.append((file_path, response_content))

        # 保存需求描述至具体文件
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
    
        parent_dir = os.path.dirname(req_file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        try:
            with open(req_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  {Colors.OKGREEN}文件需求描述已保存: {req_file_path}{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
            return False

    def _build_user_prompt_for_one_file_req(self, file_path: str) -> str:
        """
        构建单文件需求生成的用户提示词
        Args:
            file_path: 当前执行中的文件的路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 获取dir_json中的文件描述
        file_description = DirJsonFuncs.get_file_description(self.final_dir_json_content['proj_root'], file_path)
        if not file_description:
            print(f"  {Colors.FAIL}错误: 无法获取文件描述: {file_path}{Colors.ENDC}")
            return ""

        # 遍历读取已生成的累积描述，获取其中对外可见的描述
        accumulated_descriptions = []
        for _file_path, file_str_content in self.accumulated_file_str_content:
            extracted_desc = self._extract_section_content(file_str_content, 'description')
            extracted_func = self._extract_section_content(file_str_content, 'function')
            extracted_class = self._extract_section_content(file_str_content, 'class')

            cleaned_file_path = _file_path.replace("_one_file_req.txt", "")
            normed_file_path = os.path.normpath(cleaned_file_path)
            formatted = f"文件 {normed_file_path} 的接口描述:\n"
            if extracted_class:
                formatted += f"类信息:\n{extracted_class}\n\n"
            if extracted_func:
                formatted += f"函数信息:\n{extracted_func}\n\n"
            if extracted_desc:
                formatted += f"描述信息:\n{extracted_desc}"
            accumulated_descriptions.append(formatted)

        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 填充与文件描述相关的占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', self.user_requirements)
        user_prompt = user_prompt.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', self.implementation_plan_content)
        user_prompt = user_prompt.replace('FILE_DESCRIPTION_PLACEHOLDER', file_description)
        user_prompt = user_prompt.replace('EXISTING_FILE_DESCRIPTIONS_PLACEHOLDER', 
                                        '\n\n'.join(accumulated_descriptions) if accumulated_descriptions else '暂无已生成的文件需求描述')
        
        # 填充与第三方库相关的占位符
        user_prompt = user_prompt.replace('EXTERNAL_LIB_ALLOWLIST_PLACEHOLDER', self.allowed_libs_text)
        user_prompt = user_prompt.replace('MODULE_DEPENDENCY_SUGGESTIONS_PLACEHOLDER', self.module_suggestions_text)
        
        return user_prompt


    
    def _build_user_prompt_for_file_depend_analyzer(self, file_path: str) -> str:
        """
        构建文件依赖关系分析的用户提示词（role_name_2）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Args:
            file_path: 当前文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取当前文件的需求描述
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败: {e}{Colors.ENDC}")
            return ""
        
        # 提取 module 内容
        module_content = self._extract_import_content(file_requirement_content)
        if not module_content:
            print(f"  {Colors.WARNING}警告: 无法提取module内容: {file_path}{Colors.ENDC}")
        
        # 构建可用文件描述字典（从 staging 目录读取）
        available_file_desc_dict = {}
        try:
            for existing_file in os.listdir(staging_dir_path):
                if existing_file.endswith('_one_file_req.txt'):
                    existing_file_path = existing_file[:-17]  # 移除 '_one_file_req.txt'
                    if existing_file_path != file_path:  # 排除当前文件
                        req_path = os.path.join(staging_dir_path, existing_file)
                        with open(req_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        desc = self._extract_description_content(content)
                        if desc:
                            available_file_desc_dict[existing_file_path] = desc
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 构建可用文件描述字典失败: {e}{Colors.ENDC}")
        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_depend_analyzer_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""

        # 构造可用模块信息（仅包含当前可依赖的模块）
        available_modules_text = '\n\n'.join([
            f"模块路径: {path}\n模块描述: {desc}" 
            for path, desc in available_file_desc_dict.items() 
            if path != file_path
        ])

        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('CURRENT_FILE_REQUIREMENT_PLACEHOLDER', module_content)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('AVAILABLE_MODULES_PLACEHOLDER', available_modules_text if available_modules_text else '暂无其他模块')

        return user_prompt




    def _generate_single_file_requirement(self, file_path: str, proj_root_content: Dict) -> Optional[str]:
        """为单个文件生成需求描述
        
        Args:
            file_path: 文件路径
            proj_root_content: 项目根目录内容
            
        Returns:
            Optional[str]: 生成的需求描述，失败返回none
        """
        # 获取文件描述
        file_description = DirJsonFuncs.get_file_description(proj_root_content, file_path)
        if not file_description:
            print(f"  {Colors.FAIL}错误: 无法获取文件描述: {file_path}{Colors.ENDC}")
            return None
        
        # 生成新的文件需求描述
        print(f"  {Colors.OKBLUE}正在为文件生成需求描述: {file_path}{Colors.ENDC}")
        new_file_description = self._create_one_file_req_1(file_path)
        if not new_file_description:
            return None
        
        # 清理代码块标记
        return ICPChatHandler.clean_code_block_markers(new_file_description)




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



    def _analyze_single_file_dependency(self, file_path: str, staging_dir_path: str) -> List[str]:
        """分析单个文件的依赖关系
        
        Args:
            file_path: 文件路径
            staging_dir_path: staging 目录路径
            
        Returns:
            List[str]: 依赖文件列表
        """
        # 获取当前文件的需求描述
        req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
            return []

        # 从文件需求描述中提取module部分
        module_content = self._extract_import_content(file_requirement_content)
        if not module_content:
            print(f"  {Colors.WARNING}警告: 无法提取module内容: {file_path}{Colors.ENDC}")
            return []

        # 生成依赖关系
        dependencies = self._analyze_file_dependencies_2(file_path)
        
        # 从返回的依赖数据中提取依赖列表
        return dependencies.get("dependencies", [])

    def _generate_file_dependencies_2(
        self,
        ibc_root_path: str,
        file_creation_order_list: List[str],
        file_desc_dict: Dict[str, str],
        proj_root: Dict
    ) -> Dict[str, List[str]]:
        """为每个文件生成依赖关系"""
        # 初始化新的依赖关系字典
        new_dependent_relation = {}
        
        # 创建file_desc_dict的副本，用于动态更新
        available_file_desc_dict = file_desc_dict.copy()
        
        # 倒序处理文件（从抽象层级最高的文件开始）
        for file_path in reversed(file_creation_order_list):
            # 从可用文件描述字典中移除当前文件，控制ai的生成过程合理性，防止造成循环依赖
            if file_path in available_file_desc_dict:
                del available_file_desc_dict[file_path]
            
            # 分析单个文件的依赖
            dependency_list = self._analyze_single_file_dependency(file_path, ibc_root_path)
            new_dependent_relation[file_path] = dependency_list
        
        return new_dependent_relation

    def _extract_import_content(self, content: str) -> str:
        """从文件内容中提取import部分"""
        return self._extract_section_content(content, 'import')

    def _analyze_file_dependencies_2(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """分析文件依赖关系"""
        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_file_depend_analyzer(file_path)
        if not user_prompt:
            return {
                "file_path": file_path,
                "dependencies": []
            }

        # 调用AI分析依赖关系
        response_content, success = asyncio.run(self.chat_handler.get_role_response(
            role_name=self.role_one_file_req_depend,
            user_prompt=user_prompt
        ))
        
        if not success:
            return {
                "file_path": file_path,
                "dependencies": []
            }
        
        # 移除可能的代码块标记
        cleaned_content = response_content.strip()
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()
        
        # 解析AI返回的依赖关系
        try:
            # 尝试解析JSON格式的响应
            dependencies_data = json.loads(cleaned_content)
            return dependencies_data
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 解析依赖关系失败: {e}{Colors.ENDC}")
            print(f"  AI返回内容: {cleaned_content}")
            return {
                "file_path": file_path,
                "dependencies": []
            }

    def _generate_dir_content_json(self, proj_root: Dict, dependent_relation: Dict):
        """生成dir_content.json文件"""
        dir_content = {
            "proj_root": proj_root,
            "dependent_relation": dependent_relation
        }
        
        dir_content_file = os.path.join(self.proj_data_dir, "icp_dir_content_final.json")
        try:
            with open(dir_content_file, 'w', encoding='utf-8') as f:
                json.dump(dir_content, f, indent=2, ensure_ascii=False)
            print(f"  {Colors.OKGREEN}目录内容文件已保存: {dir_content_file}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存目录内容文件失败 {dir_content_file}: {e}{Colors.ENDC}")

    def is_cmd_valid(self):
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查最终目录结构文件是否存在
        final_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        if not os.path.exists(final_dir_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行循环依赖解决命令{Colors.ENDC}")
            return False
        
        # 检查文件级实现规划文件是否存在
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        if not os.path.exists(implementation_plan_file):
            print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
        
        # 检查用户原始需求是否存在
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.WARNING}警告: 用户原始需求不存在，请先加载用户需求{Colors.ENDC}")
            return False
        
        # 检查精炼需求文件是否存在（用于获取第三方库信息）
        refined_requirements_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
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
        if not self.chat_handler.has_role(self.role_one_file_req_depend):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_one_file_req_depend} 未加载{Colors.ENDC}")
            return False
        return True
    
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
        
        if 'dependency_refine_handler' in config:
            chat_api_config = config['dependency_refine_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少配置")
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
        sys_prompt_path_1 = os.path.join(prompt_dir, self.role_one_file_req + ".md")
        sys_prompt_path_2 = os.path.join(prompt_dir, self.role_one_file_req_depend + ".md")
        
        self.chat_handler.load_role_from_file(self.role_one_file_req, sys_prompt_path_1)
        self.chat_handler.load_role_from_file(self.role_one_file_req_depend, sys_prompt_path_2)



