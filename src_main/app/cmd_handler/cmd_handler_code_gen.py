import os
import asyncio
import json
from typing import Dict, Any, List

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ibc_data_types import ClassMetadata, FunctionMetadata, VariableMetadata

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.ibc_data_store import get_instance as get_ibc_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler.icp_chat_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs
from libs.symbol_metadata_helper import SymbolMetadataHelper
from utils.issue_recorder import TextIssueRecorder
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_content


class CmdHandlerCodeGen(BaseCmdHandler):
    """目标代码生成命令处理器"""

    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="target_code_gen",
            aliases=["CG"],
            description="将规范化的IBC代码转换为目标编程语言代码",
            help_text="根据规范化的IBC代码生成完整的可执行目标语言代码",
        )
        
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_icp_config_file_path = os.path.join(self.work_dir_path, '.icp_proj_config', 'icp_config.json')

        # 获取coder_handler实例（单例）
        self.chat_handler = ICPChatHandler(handler_key='coder_handler')

        # 系统提示词加载
        app_data_store = get_app_data_store()
        self.role_code_gen = "9_target_code_gen"
        self.sys_prompt_code_gen = app_data_store.get_sys_prompt_by_name(self.role_code_gen)
        self.sys_prompt_retry_part = app_data_store.get_sys_prompt_by_name('retry_sys_prompt')
        
        # 用户提示词在命令运行过程中，经由模板以及过程变量进行构建
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分

        # issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容
    
    def execute(self):
        """执行目标代码生成"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始生成目标代码...{Colors.ENDC}")
        
        # 准备执行前所需的变量
        self._build_pre_execution_variables()
        
        # 按依赖顺序遍历并处理每个文件
        for file_path in self.file_creation_order_list:
            success = self._generate_single_target_code(file_path)
            if not success:
                print(f"{Colors.FAIL}文件 {file_path} 目标代码生成失败，退出运行{Colors.ENDC}")
                return
        
        # 所有文件处理完毕，统一更新目标代码文件的MD5值到统一的verify文件
        print(f"  {Colors.OKBLUE}开始更新目标代码文件校验码...{Colors.ENDC}")
        ibc_data_store = get_ibc_data_store()
        for file_path in self.file_creation_order_list:
            target_code_path = self._build_target_code_path(file_path)
            if os.path.exists(target_code_path):
                try:
                    with open(target_code_path, 'r', encoding='utf-8') as f:
                        target_code_content = f.read()
                    current_target_md5 = IbcFuncs.calculate_text_md5(target_code_content)
                    ibc_data_store.update_file_verify_data(self.work_data_dir_path, file_path, {
                        'target_code_verify_code': current_target_md5
                    })
                except Exception as e:
                    print(f"    {Colors.WARNING}警告: 更新目标代码校验码失败: {file_path}, {e}{Colors.ENDC}")
        print(f"  {Colors.OKGREEN}目标代码文件校验码更新完毕{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}目标代码生成完毕!{Colors.ENDC}")
    
    def _build_pre_execution_variables(self):
        """准备命令正式开始执行之前所需的变量内容"""
        # 读取依赖分析结果
        final_dir_content_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
        try:
            with open(final_dir_content_file, 'r', encoding='utf-8') as f:
                final_dir_structure_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取依赖分析结果失败: {e}{Colors.ENDC}")
            return
        
        if not final_dir_structure_str:
            print(f"  {Colors.FAIL}错误: 依赖分析结果内容为空{Colors.ENDC}")
            return
        
        final_dir_json_dict = json.loads(final_dir_structure_str)
        if "proj_root_dict" not in final_dir_json_dict or "dependent_relation" not in final_dir_json_dict:
            print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点(proj_root_dict或dependent_relation){Colors.ENDC}")
            return
        
        # 读取项目配置
        try:
            with open(self.work_icp_config_file_path, 'r', encoding='utf-8') as f:
                icp_config_json_dict = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取ICP配置文件失败: {e}{Colors.ENDC}")
            return

        # 获取目标语言和文件扩展名
        self.target_language = icp_config_json_dict.get('target_language', 'python')
        self.target_file_extension = icp_config_json_dict.get('target_file_extension', '.py')

        # 获取IBC文件夹路径
        if "path_mapping" in icp_config_json_dict:
            ibc_dir_name = icp_config_json_dict["path_mapping"].get("ibc_dir_name", "src_ibc")
            target_dir_name = icp_config_json_dict["path_mapping"].get("target_dir_name", "src_target")
        else:
            ibc_dir_name = "src_ibc"
            target_dir_name = "src_target"
        
        work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
        work_target_dir_path = os.path.join(self.work_dir_path, target_dir_name)
        
        if not os.path.exists(work_ibc_dir_path):
            print(f"  {Colors.FAIL}错误: src_ibc目录不存在，请先执行IBC生成命令{Colors.ENDC}")
            return
        
        # 创建目标代码目录
        os.makedirs(work_target_dir_path, exist_ok=True)
        
        # 获取文件创建顺序
        dependent_relation = final_dir_json_dict['dependent_relation']
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)

        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_str = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}{Colors.ENDC}")
            implementation_plan_str = ""

        # 读取提取的参数
        extracted_params_file = os.path.join(self.work_data_dir_path, 'extracted_params.json')
        extracted_params_str = ""
        try:
            with open(extracted_params_file, 'r', encoding='utf-8') as f:
                extracted_params_str = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取提取参数失败: {e}，将使用空参数{Colors.ENDC}")

        # 读取允许的第三方库清单
        allowed_libs_text = "（不允许使用任何第三方库）"
        refined_requirements_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(refined_requirements_file, 'r', encoding='utf-8') as rf:
                refined = json.load(rf)
                libs = refined.get('ExternalLibraryDependencies', {}) if isinstance(refined, dict) else {}
                if isinstance(libs, dict) and libs:
                    allowed_libs_text = "\n".join(f"- {name}: {desc}" for name, desc in libs.items())
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取第三方库清单失败: {e}{Colors.ENDC}")

        # 存储实例变量供后续使用
        self.proj_root_dict = final_dir_json_dict['proj_root_dict']
        self.proj_root_dict_json_str = json.dumps(self.proj_root_dict, indent=2, ensure_ascii=False)
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.work_ibc_dir_path = work_ibc_dir_path
        self.work_target_dir_path = work_target_dir_path
        self.implementation_plan_str = implementation_plan_str
        self.extracted_params_str = extracted_params_str
        self.allowed_libs_text = allowed_libs_text
        
        # 初始化更新状态.需要依赖self.file_creation_order_list等内容
        self.need_update_flag_dict = self._initialize_update_status()
    
    def _initialize_update_status(self) -> Dict[str, bool]:
        """初始化更新状态字典
        
        根据以下逻辑标记文件是否需要更新：
        1. 检查规范化符号元数据的MD5值变化
        2. 检查目标代码文件是否存在
        3. 检查依赖链中的变化（依赖传播）
        
        Returns:
            Dict[str, bool]: 文件路径到是否需要更新的映射
        """
        print(f"  {Colors.OKBLUE}开始检查文件更新状态...{Colors.ENDC}")
        need_update_flag_dict = {}

        file_list = self.file_creation_order_list
        ibc_data_store = get_ibc_data_store()
        
        # 第一阶段：检查规范化符号元数据的MD5和目标代码文件存在性
        for file_path in file_list:
            need_update = False
            
            # 从 verify_data 加载校验数据
            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
            
            # 检查规范化后的符号元数据是否变化
            symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, file_path)
            if os.path.exists(symbols_path):
                file_name = os.path.basename(file_path)
                symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
                
                if symbols_metadata:
                    current_normalized_md5 = IbcFuncs.calculate_symbols_metadata_md5(symbols_metadata)
                    saved_normalized_md5 = verify_data.get('symbol_normalize_verify_code', None)
                    
                    if saved_normalized_md5 is None:
                        print(f"    {Colors.OKBLUE}首次生成: {file_path}{Colors.ENDC}")
                        need_update = True
                    elif saved_normalized_md5 != current_normalized_md5:
                        print(f"    {Colors.OKBLUE}规范化符号已变化: {file_path}{Colors.ENDC}")
                        need_update = True
            else:
                print(f"    {Colors.WARNING}警告: 符号表文件不存在: {file_path}{Colors.ENDC}")
                need_update = True
            
            # 检查目标代码文件是否存在
            if not need_update:
                target_code_path = self._build_target_code_path(file_path)
                if not os.path.exists(target_code_path):
                    print(f"    {Colors.OKBLUE}目标代码文件不存在，需要生成: {file_path}{Colors.ENDC}")
                    need_update = True
            
            need_update_flag_dict[file_path] = need_update
        
        # 第二阶段：依赖链传播更新
        # 按依赖顺序遍历（file_list已经是拓扑排序后的顺序）
        for file_path in file_list:
            if need_update_flag_dict.get(file_path, False):
                # 如果当前文件已标记需要更新，则所有依赖它的文件也需要更新
                self._propagate_update_to_dependents(file_path, need_update_flag_dict)
            else:
                # 检查目标代码文件的MD5是否变化（用户可能手动修改了）
                target_code_path = self._build_target_code_path(file_path)
                if os.path.exists(target_code_path):
                    try:
                        with open(target_code_path, 'r', encoding='utf-8') as f:
                            target_code_content = f.read()
                        current_target_md5 = IbcFuncs.calculate_text_md5(target_code_content)
                        verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
                        saved_target_md5 = verify_data.get('target_code_verify_code', None)
                        
                        if saved_target_md5 is not None and saved_target_md5 != current_target_md5:
                            print(f"    {Colors.OKBLUE}目标代码被手动修改: {file_path}，依赖它的文件需要更新{Colors.ENDC}")
                            self._propagate_update_to_dependents(file_path, need_update_flag_dict)
                    except Exception as e:
                        print(f"    {Colors.WARNING}警告: 检查目标代码MD5失败: {file_path}, {e}{Colors.ENDC}")
        
        # 打印更新状态摘要
        update_count = sum(1 for v in need_update_flag_dict.values() if v)
        print(f"  {Colors.OKGREEN}更新状态检查完成: {update_count}/{len(file_list)} 个文件需要更新{Colors.ENDC}")
        
        return need_update_flag_dict
    
    def _propagate_update_to_dependents(self, file_path: str, need_update_flag_dict: Dict[str, bool]):
        """将更新标记传播到所有依赖当前文件的文件
        
        Args:
            file_path: 被依赖的文件路径
            need_update_flag_dict: 更新标记字典
        """
        # 遍历所有文件，找出依赖当前文件的文件
        for potential_dependent, dependencies in self.dependent_relation.items():
            if file_path in dependencies:
                if not need_update_flag_dict.get(potential_dependent, False):
                    print(f"    {Colors.OKBLUE}依赖传播: {potential_dependent} 需要更新（因为依赖 {file_path}）{Colors.ENDC}")
                    need_update_flag_dict[potential_dependent] = True
                    # 递归传播
                    self._propagate_update_to_dependents(potential_dependent, need_update_flag_dict)
    
    def _generate_single_target_code(self, icp_json_file_path: str) -> bool:
        """为单个文件生成目标代码（包含重试机制）
        
        Args:
            icp_json_file_path: 文件路径
            
        Returns:
            bool: 是否成功生成
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        # 检查是否需要更新
        if not self.need_update_flag_dict.get(icp_json_file_path, False):
            print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过生成: {icp_json_file_path}{Colors.ENDC}")
            return True
        
        print(f"    {Colors.OKBLUE}正在生成目标代码...{Colors.ENDC}")
        
        # 重置issue recorder和重试变量
        self.issue_recorder.clear()
        self.last_generated_content = None
        
        # 构建用户提示词基础部分
        self.user_prompt_base = self._build_user_prompt_for_code_gen(icp_json_file_path)
        if not self.user_prompt_base:
            print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
            return False
        
        # 带重试的目标代码生成逻辑
        max_attempts = 3
        is_valid = False
        generated_code = ""
        
        for attempt in range(max_attempts):
            print(f"    {Colors.OKBLUE}正在进行第 {attempt + 1}/{max_attempts} 次尝试...{Colors.ENDC}")
            
            # 根据是否是重试来组合提示词
            if attempt == 0:
                # 第一次尝试,使用基础提示词
                current_sys_prompt = self.sys_prompt_code_gen
                current_user_prompt = self.user_prompt_base
            else:
                # 重试时,添加重试部分
                current_sys_prompt = self.sys_prompt_code_gen + "\n\n" + self.sys_prompt_retry_part
                current_user_prompt = self.user_prompt_base + "\n\n" + self.user_prompt_retry_part
            
            # 调用AI进行代码生成
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_code_gen,
                sys_prompt=current_sys_prompt,
                user_prompt=current_user_prompt
            ))
            
            if not success or not response_content:
                print(f"    {Colors.WARNING}警告: AI响应失败或为空{Colors.ENDC}")
                continue
            
            # 清理代码块标记
            cleaned_code = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证生成的代码
            is_valid = self._validate_generated_code(cleaned_code, icp_json_file_path)
            
            if is_valid:
                generated_code = cleaned_code
                break
            
            # 如果验证失败，保存当前生成的内容并构建重试提示词
            self.last_generated_content = cleaned_code
            self.user_prompt_retry_part = self._build_user_prompt_retry_part()
        
        # 循环已跳出，检查运行结果
        if attempt == max_attempts - 1 and not is_valid:
            print(f"  {Colors.FAIL}已达到最大重试次数({max_attempts})，跳过该文件{Colors.ENDC}")
            return False
        
        # 验证成功，保存目标代码
        target_code_path = self._build_target_code_path(icp_json_file_path)
        try:
            # 创建目录
            parent_dir = os.path.dirname(target_code_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 保存代码
            with open(target_code_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            print(f"    {Colors.OKGREEN}目标代码已保存: {target_code_path}{Colors.ENDC}")
        except Exception as e:
            print(f"    {Colors.FAIL}错误: 保存目标代码失败: {e}{Colors.ENDC}")
            return False
        
        return True

    def _build_target_code_path(self, file_path: str) -> str:
        """构建目标代码文件路径
        
        Args:
            file_path: 相对文件路径（如 "src/ball/ball_entity"）
            
        Returns:
            str: 目标代码文件的完整路径
        """
        # 将路径分隔符统一为系统分隔符
        normalized_path = file_path.replace('/', os.sep)
        
        # 添加目标文件扩展名
        target_file_name = normalized_path + self.target_file_extension
        
        # 拼接完整路径
        return os.path.join(self.work_target_dir_path, target_file_name)

    def _build_user_prompt_for_code_gen(self, icp_json_file_path: str) -> str:
        """构建目标代码生成的用户提示词
        
        Args:
            icp_json_file_path: 当前文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        ibc_data_store = get_ibc_data_store()
        
        # 读取IBC代码
        ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, icp_json_file_path)
        try:
            with open(ibc_path, 'r', encoding='utf-8') as f:
                ibc_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC代码失败: {e}{Colors.ENDC}")
            return ""
        
        # 加载符号表和AST，用于符号替换
        file_name = os.path.basename(icp_json_file_path)
        symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
        
        # 检查符号表是否存在
        if not os.path.exists(symbols_path):
            print(f"  {Colors.WARNING}警告: 符号表文件不存在: {symbols_path}{Colors.ENDC}")
            print(f"  {Colors.WARNING}将使用未替换的IBC代码{Colors.ENDC}")
            normalized_ibc_content = ibc_content
        else:
            try:
                # 加载符号表
                symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
                
                # 重新解析IBC代码生成AST（用于符号替换）
                print(f"    {Colors.OKBLUE}正在解析IBC代码以生成AST...{Colors.ENDC}")
                ast_dict, _, _ = analyze_ibc_content(ibc_content)
                
                if not ast_dict:
                    print(f"  {Colors.WARNING}警告: AST生成失败，将使用未替换的IBC代码{Colors.ENDC}")
                    normalized_ibc_content = ibc_content
                else:
                    # 执行符号替换
                    print(f"    {Colors.OKBLUE}正在将IBC代码中的符号替换为规范化名称...{Colors.ENDC}")
                    normalized_ibc_content = IbcFuncs.replace_symbols_with_normalized_names(
                        ibc_content=ibc_content,
                        ast_dict=ast_dict,
                        symbols_metadata=symbols_metadata,
                        current_file_name=file_name
                    )
                    print(f"    {Colors.OKGREEN}符号替换完成{Colors.ENDC}")
                    
            except Exception as e:
                print(f"  {Colors.WARNING}警告: 符号替换失败: {e}{Colors.ENDC}")
                print(f"  {Colors.WARNING}将使用未替换的IBC代码{Colors.ENDC}")
                import traceback
                traceback.print_exc()
                normalized_ibc_content = ibc_content
        
        dependency_target_code = self._build_dependency_target_code(icp_json_file_path)
        
        # 读取提示词模板
        app_data_store = get_app_data_store()
        user_prompt_template_str = app_data_store.get_user_prompt_by_name('target_code_gen_user')
        if not user_prompt_template_str:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败{Colors.ENDC}")
            return ""
        
        # 填充占位符
        user_prompt_str = user_prompt_template_str.replace('TARGET_LANGUAGE_PLACEHOLDER', self.target_language)
        user_prompt_str = user_prompt_str.replace('CURRENT_FILE_PATH_PLACEHOLDER', icp_json_file_path)
        user_prompt_str = user_prompt_str.replace('EXTRACTED_PARAM_PLACEHOLDER', self.extracted_params_str if self.extracted_params_str else '无')
        user_prompt_str = user_prompt_str.replace('LIBRARY_PLACEHOLDER', self.allowed_libs_text)
        user_prompt_str = user_prompt_str.replace('PROJROOT_DIRCONTENT_PLACEHOLDER', self.proj_root_dict_json_str)
        user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', self.implementation_plan_str if self.implementation_plan_str else '无')
        user_prompt_str = user_prompt_str.replace('IBC_CONTENT_PLACEHOLDER', normalized_ibc_content)
        user_prompt_str = user_prompt_str.replace('DEPENDENCY_TARGET_CODE_PLACEHOLDER', dependency_target_code)
        
        return user_prompt_str

    def _build_dependency_target_code(self, icp_json_file_path: str) -> str:
        """构建依赖文件的目标代码内容
        
        读取当前文件依赖的其他文件已生成的目标代码，
        使大模型能够看到具体的实现细节，从而正确调用依赖符号。
        
        Args:
            icp_json_file_path: 文件路径
            
        Returns:
            str: 依赖文件的目标代码内容，按文件组织
        """
        # 获取当前文件的依赖列表
        dependencies = self.dependent_relation.get(icp_json_file_path, [])
        
        if not dependencies:
            return "无外部依赖，不需要参考其他文件的代码。"
        
        result_lines = []
        loaded_count = 0
        
        # 遍历每个依赖文件
        for dep_file_path in dependencies:
            target_code_path = self._build_target_code_path(dep_file_path)
            
            # 检查目标代码文件是否存在
            if not os.path.exists(target_code_path):
                result_lines.append(f"### {dep_file_path}")
                result_lines.append(f"目标代码文件尚未生成，请根据符号使用说明进行调用。")
                result_lines.append("")
                continue
            
            # 读取目标代码内容
            try:
                with open(target_code_path, 'r', encoding='utf-8') as f:
                    target_code_content = f.read()
                
                # 添加文件头和代码块
                result_lines.append(f"### {dep_file_path}")
                result_lines.append(f"文件路径：`{target_code_path}`")
                result_lines.append("")
                result_lines.append(f"```{self.target_language}")
                result_lines.append(target_code_content)
                result_lines.append("```")
                result_lines.append("")
                
                loaded_count += 1
                
            except Exception as e:
                result_lines.append(f"### {dep_file_path}")
                result_lines.append(f"读取目标代码失败: {e}")
                result_lines.append("")
                print(f"    {Colors.WARNING}警告: 读取依赖文件 {dep_file_path} 的目标代码失败: {e}{Colors.ENDC}")
        
        if loaded_count == 0:
            return "所有依赖文件的目标代码尚未生成，请根据符号使用说明进行调用。"
        
        return '\n'.join(result_lines)

    def _validate_generated_code(self, generated_code: str, file_path: str) -> bool:
        """验证生成的目标代码
        
        Args:
            generated_code: 生成的代码
            file_path: 文件路径
            
        Returns:
            bool: 是否有效
        """
        # 清空上一次验证的问题记录
        self.issue_recorder.clear()
        
        # 基础验证：代码不能为空
        if not generated_code or not generated_code.strip():
            error_msg = "生成的代码为空"
            print(f"    {Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 验证代码长度（防止生成过短的无效代码）
        if len(generated_code.strip()) < 10:
            error_msg = f"生成的代码过短（{len(generated_code.strip())} 字符），可能无效"
            print(f"    {Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 如果没有问题，认为验证通过
        if not self.issue_recorder.has_issues():
            print(f"    {Colors.OKGREEN}目标代码验证通过{Colors.ENDC}")
            return True
        
        # 如果有问题，输出问题数量
        issue_count = self.issue_recorder.get_issue_count()
        print(f"    {Colors.WARNING}警告: 目标代码生成发现 {issue_count} 个问题{Colors.ENDC}")
        return False

    def _build_user_prompt_retry_part(self) -> str:
        """构建用户提示词重试部分
        
        Returns:
            str: 重试部分的用户提示词，失败时返回空字符串
        """
        if not self.issue_recorder.has_issues() or not self.last_generated_content:
            return ""
        
        # 读取重试提示词模板
        app_data_store = get_app_data_store()
        retry_template = app_data_store.get_user_prompt_by_name('retry_prompt_template')
        if not retry_template:
            print(f"{Colors.FAIL}错误: 读取重试模板失败{Colors.ENDC}")
            return ""
        
        # 格式化上一次生成的内容（用代码块包裹）
        formatted_content = f"```{self.target_language}\n{self.last_generated_content}\n```"
        
        # 格式化问题列表
        issues_list = "\n".join([f"- {issue.issue_content}" for issue in self.issue_recorder.get_issues()])
        
        # 替换占位符
        retry_prompt = retry_template.replace('PREVIOUS_CONTENT_PLACEHOLDER', formatted_content)
        retry_prompt = retry_prompt.replace('ISSUES_LIST_PLACEHOLDER', issues_list)
        
        return retry_prompt

    def is_cmd_valid(self):
        """检查命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        try:
            # 检查依赖分析结果文件是否存在
            ibc_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
            if not os.path.exists(ibc_dir_file):
                print(f"  {Colors.WARNING}警告: 依赖分析结果文件不存在，请先执行依赖分析命令{Colors.ENDC}")
                return False
            
            # 读取目录结构并解析
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                dir_structure_str = f.read()
            dir_json_dict = json.loads(dir_structure_str)
            
            # 验证依赖分析结果完整性
            if "proj_root_dict" not in dir_json_dict or "dependent_relation" not in dir_json_dict:
                print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点(proj_root_dict或dependent_relation){Colors.ENDC}")
                return False
            
            # 读取项目配置获取IBC目录
            try:
                with open(self.work_icp_config_file_path, 'r', encoding='utf-8') as f:
                    icp_config_json_dict = json.load(f)
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取ICP配置文件失败: {e}{Colors.ENDC}")
                return False

            if "path_mapping" in icp_config_json_dict:
                ibc_dir_name = icp_config_json_dict["path_mapping"].get("ibc_dir_name", "src_ibc")
            else:
                ibc_dir_name = "src_ibc"
            
            work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
            
            # 检查src_ibc目录是否存在
            if not os.path.exists(work_ibc_dir_path):
                print(f"  {Colors.FAIL}错误: src_ibc目录不存在，请先执行IBC生成命令{Colors.ENDC}")
                return False
            
            # 检查符号规范化是否已完成（通过检查verify文件中的symbol_normalize_verify_code）
            dependent_relation = dir_json_dict['dependent_relation']
            file_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
            
            ibc_data_store = get_ibc_data_store()
            missing_normalize_files = []
            for file_path in file_list:
                verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
                if not verify_data.get('symbol_normalize_verify_code'):
                    missing_normalize_files.append(file_path)
            
            if missing_normalize_files:
                print(f"  {Colors.FAIL}错误: 以下文件尚未完成符号规范化，请先执行符号规范化命令:{Colors.ENDC}")
                for missing_file in missing_normalize_files[:5]:  # 只显示前5个
                    print(f"    - {missing_file}")
                if len(missing_normalize_files) > 5:
                    print(f"    ... 还有 {len(missing_normalize_files) - 5} 个文件")
                return False
            
            return True
                
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 依赖分析结果文件格式错误: {e}{Colors.ENDC}")
            return False
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 检查前置文件时发生异常: {e}{Colors.ENDC}")
            return False
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查系统提示词是否加载
        if not self.sys_prompt_code_gen:
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_code_gen} 未加载{Colors.ENDC}")
            return False
            
        return True
