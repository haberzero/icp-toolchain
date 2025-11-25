import sys, os
import asyncio
import json
from typing import Optional, Dict
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs


class CmdHandlerOneFileReqGen(BaseCmdHandler):
    """单文件需求描述生成指令
    
    按照依赖顺序为每个文件生成详细的需求描述，保存到src_staging目录
    """
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="one_file_req_gen",
            aliases=["OFR"],
            description="为每个文件生成详细的需求描述",
            help_text="按照依赖顺序为项目中的每个文件生成单文件需求描述",
        )
        
        # 初始化路径配置
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')
        self.staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        
        # 初始化AI处理器
        self.chat_handler = ICPChatHandler()
        self.role_name = "7_one_file_req_gen"
        self._init_ai_handlers()

    def execute(self):
        """执行单文件需求生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成单文件需求描述...{Colors.ENDC}")

        # 读取精炼后的目录结构
        refined_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        try:
            with open(refined_dir_file, 'r', encoding='utf-8') as f:
                refined_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录结构失败: {e}{Colors.ENDC}")
            return

        # 获取项目根节点和依赖关系
        proj_root = refined_content.get("proj_root", {})
        dependent_relation = refined_content.get("dependent_relation", {})
        
        # 构建文件创建顺序
        file_creation_order = DirJsonFuncs.build_file_creation_order(dependent_relation)

        # 创建src_staging目录
        try:
            os.makedirs(self.staging_dir_path, exist_ok=True)
            print(f"  {Colors.OKGREEN}src_staging目录创建成功: {self.staging_dir_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 创建src_staging目录失败: {e}{Colors.ENDC}")
            return
        
        # 为每个文件生成需求描述
        self._generate_all_file_requirements(proj_root, file_creation_order)
        
        print(f"{Colors.OKGREEN}单文件需求描述生成完成!{Colors.ENDC}")

    def _generate_all_file_requirements(self, proj_root: Dict, file_creation_order: list):
        """为所有文件生成需求描述"""
        for file_path in file_creation_order:
            # 生成单个文件的需求描述
            requirement_content = self._generate_single_file_requirement(file_path, proj_root)
            if not requirement_content:
                continue
            
            # 保存需求描述
            self._save_file_requirement(file_path, requirement_content)

    def _generate_single_file_requirement(self, file_path: str, proj_root: Dict) -> Optional[str]:
        """为单个文件生成需求描述
        
        Args:
            file_path: 文件路径
            proj_root: 项目根目录内容
            
        Returns:
            Optional[str]: 生成的需求描述，失败返回None
        """
        print(f"  {Colors.OKBLUE}正在为文件生成需求描述: {file_path}{Colors.ENDC}")
        
        # 构建用户提示词
        user_prompt = self._build_user_prompt(file_path, proj_root)
        if not user_prompt:
            return None
        
        # 调用AI生成需求描述
        response_content, success = asyncio.run(self.chat_handler.get_role_response(
            role_name=self.role_name,
            user_prompt=user_prompt
        ))
        
        if not success:
            print(f"  {Colors.WARNING}警告: 生成需求描述失败: {file_path}{Colors.ENDC}")
            return None
        
        # 清理代码块标记
        return ICPChatHandler.clean_code_block_markers(response_content)

    def _save_file_requirement(self, file_path: str, content: str) -> bool:
        """保存文件需求描述
        
        Args:
            file_path: 文件路径
            content: 需求描述内容
            
        Returns:
            bool: 是否成功
        """
        req_file_path = os.path.join(self.staging_dir_path, f"{file_path}_one_file_req.txt")
        
        # 确保文件的父目录存在
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

    def _build_user_prompt(self, file_path: str, proj_root: Dict) -> str:
        """构建用户提示词
        
        Args:
            file_path: 当前文件路径
            proj_root: 项目根目录内容
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 读取用户需求失败{Colors.ENDC}")
            return ""
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            return ""
        
        # 获取文件描述
        file_description = DirJsonFuncs.get_file_description(proj_root, file_path)
        if not file_description:
            print(f"  {Colors.FAIL}错误: 无法获取文件描述: {file_path}{Colors.ENDC}")
            return ""
        
        # 读取已生成的文件描述（累积信息）
        accumulated_descriptions = self._get_accumulated_descriptions()
        
        # 读取第三方库允许清单
        allowed_libs_text, module_suggestions_text = self._get_external_lib_info()
        
        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 构建文件描述JSON
        file_desc_json = json.dumps(
            {"path": file_path, "description": file_description}, 
            indent=2, 
            ensure_ascii=False
        )
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan)
        user_prompt = user_prompt.replace('FILE_DESCRIPTION_PLACEHOLDER', file_desc_json)
        user_prompt = user_prompt.replace('EXISTING_FILE_DESCRIPTIONS_PLACEHOLDER', 
                                        '\n\n'.join(accumulated_descriptions) if accumulated_descriptions else '暂无已生成的文件需求描述')
        user_prompt = user_prompt.replace('EXTERNAL_LIB_ALLOWLIST_PLACEHOLDER', allowed_libs_text)
        user_prompt = user_prompt.replace('MODULE_DEPENDENCY_SUGGESTIONS_PLACEHOLDER', module_suggestions_text)
        
        return user_prompt

    def _get_accumulated_descriptions(self) -> list:
        """获取已生成的累积文件描述"""
        accumulated_descriptions = []
        
        if not os.path.exists(self.staging_dir_path):
            return accumulated_descriptions
        
        try:
            for existing_file in os.listdir(self.staging_dir_path):
                if not existing_file.endswith('_one_file_req.txt'):
                    continue
                
                existing_path = os.path.join(self.staging_dir_path, existing_file)
                with open(existing_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取关键信息
                extracted_desc = self._extract_section_content(content, 'description:')
                extracted_func = self._extract_section_content(content, 'func:')
                extracted_class = self._extract_section_content(content, 'class:')
                
                # 格式化输出
                formatted = f"文件 {existing_file[:-17]} 的接口描述:\n"
                if extracted_class:
                    formatted += f"类信息:\n{extracted_class}\n\n"
                if extracted_func:
                    formatted += f"函数信息:\n{extracted_func}\n\n"
                if extracted_desc:
                    formatted += f"描述信息:\n{extracted_desc}"
                
                accumulated_descriptions.append(formatted)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取已生成文件失败: {e}{Colors.ENDC}")
        
        return accumulated_descriptions

    def _get_external_lib_info(self) -> tuple:
        """获取第三方库允许清单和模块依赖建议
        
        Returns:
            tuple: (允许库文本, 模块依赖建议文本)
        """
        allowed_libs_text = "（不允许使用任何第三方库）"
        module_suggestions_text = "（无可用模块依赖建议）"
        
        try:
            refined_requirements_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
            with open(refined_requirements_file, 'r', encoding='utf-8') as rf:
                refined_data = json.load(rf)
                
                # 提取第三方库依赖
                libs = refined_data.get('ExternalLibraryDependencies', {})
                if isinstance(libs, dict) and libs:
                    allowed_lines = [f"- {name}: {desc}" for name, desc in libs.items()]
                    allowed_libs_text = "\n".join(allowed_lines)
                    allowed_lib_keys = set(libs.keys())
                    
                    # 生成模块依赖建议
                    module_suggestions_lines = []
                    module_breakdown = refined_data.get('module_breakdown', {})
                    if isinstance(module_breakdown, dict):
                        for mod_name, mod_obj in module_breakdown.items():
                            if isinstance(mod_obj, dict):
                                deps = mod_obj.get('dependencies', [])
                                if isinstance(deps, list) and deps:
                                    filtered = [dep for dep in deps if dep in allowed_lib_keys]
                                    if filtered:
                                        module_suggestions_lines.append(f"- {mod_name}: {', '.join(filtered)}")
                    
                    if module_suggestions_lines:
                        module_suggestions_text = "\n".join(module_suggestions_lines)
        except Exception:
            pass
        
        return allowed_libs_text, module_suggestions_text

    def _extract_section_content(self, content: str, section_marker: str) -> str:
        """从文件内容中提取指定段落的内容
        
        Args:
            content: 文件内容
            section_marker: 段落标记 (例如 'description:', 'func:', 'class:')
        
        Returns:
            str: 提取的段落内容
        """
        lines = content.split('\n')
        section_lines = []
        found_section = False
        
        for line in lines:
            if line.strip().startswith(section_marker):
                found_section = True
                continue
            
            if found_section:
                stripped_line = line.strip()
                
                # 空行继续添加
                if not stripped_line:
                    section_lines.append(line)
                    continue
                
                # 注释行跳过
                if stripped_line.startswith('#'):
                    continue
                
                # 检查是否是新段落（以字母开头且没有缩进）
                is_new_paragraph = (
                    stripped_line and 
                    stripped_line[0].isalpha() and 
                    not line.startswith((' ', '\t'))
                )
                
                if is_new_paragraph:
                    break
                else:
                    section_lines.append(line)
        
        return '\n'.join(section_lines)

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查精炼后的目录结构文件是否存在
        refined_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        if not os.path.exists(refined_dir_file):
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
        
        # 检查精炼需求文件是否存在
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
        
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
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
        
        # 优先使用dependency_refine_handler配置，否则使用coder_handler
        if 'dependency_refine_handler' in config:
            chat_api_config = config['dependency_refine_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载角色提示词
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, self.role_name + ".md")
        
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)
