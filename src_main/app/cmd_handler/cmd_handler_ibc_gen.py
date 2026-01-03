import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from data_store.sys_prompt_manager import get_instance as get_sys_prompt_manager
from data_store.user_prompt_manager import get_instance as get_user_prompt_manager
from data_store.ibc_data_store import get_instance as get_ibc_data_store
from data_store.user_data_store import get_instance as get_user_data_store
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs
from libs.text_funcs import ChatResponseCleaner
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from typedef.cmd_data_types import CmdProcStatus, Colors, CommandInfo
from typedef.ibc_data_types import (AstNodeType, ClassNode, FunctionNode,
                                    IbcBaseAstNode, VariableNode,
                                    VisibilityTypes)
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_content
from utils.ibc_analyzer.ibc_symbol_ref_resolver import SymbolRefResolver
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from utils.icp_ai_utils.icp_chat_inst import ICPChatInsts
from utils.issue_recorder import IbcIssueRecorder

from .base_cmd_handler import BaseCmdHandler


class CmdHandlerIbcGen(BaseCmdHandler):
    """半自然语言行为描述代码生成命令处理器"""

    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="intent_behavior_code_gen",
            aliases=["IBC"],
            description="将单文件需求描述转换为半自然语言行为描述代码",
            help_text="根据单文件需求描述生成符合半自然语言行为描述语法的代码结构",
        )
        
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')
        self.work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')

        # 获取coder_handler单例
        self.chat_handler = ICPChatInsts.get_instance(handler_key='coder_handler')

        # 提示词管理器
        self.sys_prompt_manager = get_sys_prompt_manager()
        self.user_prompt_manager = get_user_prompt_manager()
        self.role_name = "7_intent_behavior_code_gen"
        
        # 用户提示词在命令运行过程中，经由模板以及过程变量进行构建
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分

        # 初始化issue recorder和上一次生成的内容
        self.ibc_issue_recorder = IbcIssueRecorder()
        self.last_generated_ibc_content = None  # 上一次生成的IBC内容
        self.last_sys_prompt_used = ""  # 上一次调用时使用的系统提示词
        self.last_user_prompt_used = ""  # 上一次调用时使用的用户提示词

    
    def execute(self):
        """执行半自然语言行为描述代码生成"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始生成半自然语言行为描述代码...{Colors.ENDC}")
        
        # 准备执行前所需的变量
        self._build_pre_execution_variables()
        
        # 按依赖顺序遍历并处理每个文件
        for file_path in self.file_creation_order_list:
            success = self._create_single_ibc_file(file_path)
            if not success:
                print(f"{Colors.FAIL}文件 {file_path} 处理失败，退出运行{Colors.ENDC}")
                return
        
        # 所有文件处理完毕，统一更新ibc文件的MD5值到统一的verify文件
        print(f"  {Colors.OKBLUE}开始更新ibc文件校验码...{Colors.ENDC}")
        ibc_data_store = get_ibc_data_store()
        ibc_data_store.batch_update_ibc_verify_codes(
            self.work_data_dir_path,
            self.work_ibc_dir_path,
            self.file_creation_order_list
        )
        print(f"  {Colors.OKGREEN}ibc文件校验码更新完毕{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}半自然语言行为描述代码生成完毕!{Colors.ENDC}")
    
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
        
        # 读取用户需求
        user_data_store = get_user_data_store()
        user_requirements_str = user_data_store.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return
        
        # 读取外部库依赖信息（来自 refined_requirements.json）
        external_library_dependencies = {}
        refined_requirements_file = os.path.join(self.work_data_dir_path, 'refined_requirements.json')
        try:
            with open(refined_requirements_file, 'r', encoding='utf-8') as rf:
                refined = json.load(rf)
                external_library_dependencies = refined.get('ExternalLibraryDependencies', {}) if isinstance(refined, dict) else {}
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取外部库依赖信息失败: {e}，将使用空依赖{Colors.ENDC}")
        
        # 检查目录
        work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
        if not os.path.exists(work_staging_dir_path):
            print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
            return
        
        # 读取项目配置
        try:
            with open(self.work_icp_config_file_path, 'r', encoding='utf-8') as f:
                icp_config_json_dict = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取ICP配置文件失败: {e}{Colors.ENDC}")
            return

        # 获取文件夹名称配置并创建对应文件夹
        if "path_mapping" in icp_config_json_dict:
            ibc_dir_name = icp_config_json_dict["path_mapping"].get("ibc_dir_name", "src_ibc")
        if ibc_dir_name is not None:
            work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
        else:
            work_ibc_dir_path = os.path.join(self.work_dir_path, "src_ibc")
        os.makedirs(work_ibc_dir_path, exist_ok=True)
        
        # 获取文件创建顺序
        dependent_relation = final_dir_json_dict['dependent_relation']
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 存储实例变量供后续使用
        self.dir_json_dict = final_dir_json_dict
        self.proj_root_dict = final_dir_json_dict['proj_root_dict']
        self.proj_root_dict_json_str = json.dumps(self.proj_root_dict, indent=2, ensure_ascii=False)
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.user_requirements_str = user_requirements_str
        self.work_staging_dir_path = work_staging_dir_path
        self.work_ibc_dir_path = work_ibc_dir_path
        self.external_library_dependencies = external_library_dependencies
        
        # 初始化可见符号表构建器
        self.visible_symbol_builder = VisibleSymbolBuilder(
            proj_root_dict=self.proj_root_dict,
        )
        
        # 初始化更新状态.需要依赖self.file_creation_order_list等内容
        self.need_update_flag_dict = self._initialize_update_status()
    
    def _initialize_update_status(self) -> Dict[str, bool]:
        """初始化更新状态字典
        
        根据以下逻辑标记文件是否需要更新：
        1. 检查one_file_req的MD5值变化
        2. 检查ibc文件是否存在
        3. 检查依赖链中的变化（依赖传播）
        
        Returns:
            Dict[str, bool]: 文件路径到是否需要更新的映射
        """
        print(f"  {Colors.OKBLUE}开始检查文件更新状态...{Colors.ENDC}")
        need_update_flag_dict = {}

        file_list = self.file_creation_order_list
        
        # 第一阶段：检查one_file_req的MD5和ibc文件存在性
        for file_path in file_list:
            need_update = False
            
            req_file = os.path.join(self.work_staging_dir_path, f"{file_path}_one_file_req.txt")
            ibc_data_store = get_ibc_data_store()
            ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
            
            # 读取one_file_req的当前MD5
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    req_content = f.read()
                current_req_md5 = IbcFuncs.calculate_text_md5(req_content)
            except Exception as e:
                print(f"    {Colors.WARNING}警告: 读取one_file_req文件失败: {file_path}, {e}{Colors.ENDC}")
                need_update = True
                need_update_flag_dict[file_path] = need_update
                continue
            
            # 从统一的verify文件中加载该文件的校验数据
            ibc_data_store = get_ibc_data_store()
            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
            
            # 检查one_file_req的MD5是否变化
            saved_req_md5 = verify_data.get('one_file_req_verify_code', None)
            if saved_req_md5 is None:
                print(f"    {Colors.OKBLUE}首次生成: {file_path}{Colors.ENDC}")
                need_update = True
            elif saved_req_md5 != current_req_md5:
                print(f"    {Colors.OKBLUE}one_file_req已变化: {file_path}{Colors.ENDC}")
                need_update = True
            
            # 检查ibc文件是否存在
            if not need_update and not os.path.exists(ibc_path):
                print(f"    {Colors.OKBLUE}ibc文件不存在，需要生成: {file_path}{Colors.ENDC}")
                need_update = True
            
            need_update_flag_dict[file_path] = need_update
            
            # 注意: one_file_req的MD5更新移到了文件生成成功后(_create_single_ibc_file)
            # 只有生成成功并验证通过后才更新,避免失败文件被跳过的问题
        
        # 第二阶段：依赖链传播更新
        # 按依赖顺序遍历（file_list已经是拓扑排序后的顺序）
        for file_path in file_list:
            if need_update_flag_dict.get(file_path, False):
                # 如果当前文件已标记需要更新，则所有依赖它的文件也需要更新
                self._propagate_update_to_dependents(file_path, need_update_flag_dict)
            else:
                # 检查ibc文件的MD5是否变化（用户可能手动修改了）
                ibc_data_store = get_ibc_data_store()
                ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
                
                if os.path.exists(ibc_path):
                    try:
                        ibc_content = ibc_data_store.load_ibc_content(ibc_path)
                        if ibc_content:
                            current_ibc_md5 = IbcFuncs.calculate_text_md5(ibc_content)
                            
                            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
                            saved_ibc_md5 = verify_data.get('ibc_verify_code', None)
                        if saved_ibc_md5 is not None and saved_ibc_md5 != current_ibc_md5:
                            print(f"    {Colors.OKBLUE}ibc文件被手动修改: {file_path}，依赖它的文件需要更新{Colors.ENDC}")
                            self._propagate_update_to_dependents(file_path, need_update_flag_dict)
                    except Exception as e:
                        print(f"    {Colors.WARNING}警告: 检查ibc文件MD5失败: {file_path}, {e}{Colors.ENDC}")
        
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
    
    def _create_single_ibc_file(self, icp_json_file_path: str) -> bool:
        """为单个文件生成IBC代码（包含重试机制）
        
        Args:
            icp_json_file_path: 文件路径
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        # 检查是否需要更新
        if not self.need_update_flag_dict.get(icp_json_file_path, False):
            print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过生成: {icp_json_file_path}{Colors.ENDC}")
            return True

        # 重置实例变量
        self.ibc_issue_recorder.clear()
        self.last_generated_ibc_content = None
        self.last_sys_prompt_used = ""
        self.last_user_prompt_used = ""
        self.user_prompt_retry_part = ""
        
        # 构建用户提示词基础部分
        self.user_prompt_base = self._build_user_prompt_for_ibc_generator(icp_json_file_path)
        if not self.user_prompt_base:
            print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
            return False

        # 带重试的生成逻辑（IBC 代码的生成过程不确定性更多，提供较多的重试次数）
        max_attempts = 5
        is_valid = False
        ibc_content = ""
        ast_dict = {}
        symbols_tree = {}
        symbols_metadata = {}

        for attempt in range(max_attempts):
            print(f"    {Colors.OKBLUE}正在进行第 {attempt + 1}/{max_attempts} 次尝试...{Colors.ENDC}")

            base_sys_prompt = self.sys_prompt_manager.get_prompt(self.role_name)
            retry_sys_prompt = self.sys_prompt_manager.get_prompt('retry_sys_prompt')

            if attempt == 0:
                # 第一次尝试：直接使用基础提示词
                current_sys_prompt = base_sys_prompt
                current_user_prompt = self.user_prompt_base

                # 记录本次调用使用的提示词
                self.last_sys_prompt_used = current_sys_prompt
                self.last_user_prompt_used = current_user_prompt

                # 将用户提示词保存到stage文件夹以便查看生成过程
                self._save_user_prompt_to_stage(icp_json_file_path, current_user_prompt, attempt + 1)

                # 调用AI生成IBC代码
                response_content, success = asyncio.run(self.chat_handler.get_role_response(
                    role_name=self.role_name,
                    sys_prompt=current_sys_prompt,
                    user_prompt=current_user_prompt
                ))

                if not success or not response_content:
                    print(f"    {Colors.WARNING}警告: AI响应失败或为空{Colors.ENDC}")
                    continue

                # 清理代码块标记
                ibc_content = ChatResponseCleaner.clean_code_block_markers(response_content)

                # 解析IBC代码生成AST
                print(f"    {Colors.OKBLUE}正在分析IBC代码生成AST...{Colors.ENDC}")
                ast_dict, symbols_tree, symbols_metadata = analyze_ibc_content(ibc_content, self.ibc_issue_recorder)

                # 验证是否得到有效的AST和符号数据（包括符号引用验证）
                is_valid = self._validate_ibc_response(
                    ast_dict=ast_dict,
                    current_file_path=icp_json_file_path,
                    symbols_tree=symbols_tree,
                    symbols_metadata=symbols_metadata
                )
                if is_valid:
                    break

                # 如果验证失败，保存当前生成的内容，供后续诊断和修复使用
                self.last_generated_ibc_content = ibc_content

            else:
                # 重试阶段：先调用「诊断与修复建议」角色，再根据修复建议进行结果修复
                if not self.last_generated_ibc_content or not self.ibc_issue_recorder.has_issues():
                    print(f"    {Colors.WARNING}警告: 无可用的上一次输出或问题信息，无法执行重试修复{Colors.ENDC}")
                    continue

                # 构建问题列表文本（使用 IbcIssueRecorder 的格式）
                ibc_issues = self.ibc_issue_recorder.get_issues()
                issues_text = "\n".join(
                    [f"- 第{issue.line_num}行: {issue.message} (代码: {issue.line_content})" for issue in ibc_issues]
                )

                # 第一步：根据上一次提示词 / 输出 / 问题列表，生成修复建议
                analysis_sys_prompt = self.sys_prompt_manager.get_prompt("retry_analysis_sys_prompt")
                
                analysis_mapping = {
                    "PREVIOUS_SYS_PROMPT_PLACEHOLDER": self.last_sys_prompt_used or "(无)",
                    "PREVIOUS_USER_PROMPT_PLACEHOLDER": self.last_user_prompt_used or "(无)",
                    "PREVIOUS_CONTENT_PLACEHOLDER": self.last_generated_ibc_content or "(无输出)",
                    "ISSUES_LIST_PLACEHOLDER": issues_text or "(未检测到问题描述)"
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
                    print(f"    {Colors.WARNING}警告: 生成修复建议失败，将进行下一次尝试{Colors.ENDC}")
                    continue

                fix_suggestion = ChatResponseCleaner.clean_code_block_markers(fix_suggestion_raw)

                # 第二步：根据修复建议重新组织用户提示词，发起修复请求
                self.user_prompt_retry_part = self._build_user_prompt_retry_part(fix_suggestion)

                if retry_sys_prompt:
                    current_sys_prompt = base_sys_prompt + "\n\n" + retry_sys_prompt
                else:
                    current_sys_prompt = base_sys_prompt
                current_user_prompt = self.user_prompt_base + "\n\n" + self.user_prompt_retry_part

                # 将用户提示词保存到stage文件夹以便查看生成过程
                self._save_user_prompt_to_stage(icp_json_file_path, current_user_prompt, attempt + 1)

                # 调用AI生成修复后的IBC代码
                response_content, success = asyncio.run(self.chat_handler.get_role_response(
                    role_name=self.role_name,
                    sys_prompt=current_sys_prompt,
                    user_prompt=current_user_prompt
                ))

                if not success or not response_content:
                    print(f"    {Colors.WARNING}警告: 修复阶段AI响应失败或为空{Colors.ENDC}")
                    continue

                # 更新记录本次调用使用的提示词
                self.last_sys_prompt_used = current_sys_prompt
                self.last_user_prompt_used = current_user_prompt

                # 清理代码块标记
                ibc_content = ChatResponseCleaner.clean_code_block_markers(response_content)

                # 解析IBC代码生成AST
                print(f"    {Colors.OKBLUE}正在分析修复后的IBC代码生成AST...{Colors.ENDC}")
                ast_dict, symbols_tree, symbols_metadata = analyze_ibc_content(ibc_content, self.ibc_issue_recorder)

                # 再次验证修复后的响应内容
                is_valid = self._validate_ibc_response(
                    ast_dict=ast_dict,
                    current_file_path=icp_json_file_path,
                    symbols_tree=symbols_tree,
                    symbols_metadata=symbols_metadata
                )
                if is_valid:
                    break

                # 如果依然验证失败，保存当前生成的内容，供下一轮重试使用
                self.last_generated_ibc_content = ibc_content
        
        # 循环已跳出，检查运行结果并进行相应操作
        if attempt == max_attempts - 1 and not is_valid:
            print(f"  {Colors.FAIL}已达到最大重试次数({max_attempts})，跳过该文件{Colors.ENDC}")
            return False

        # 验证成功，保存IBC代码和符号表
        ibc_data_store = get_ibc_data_store()
        ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, icp_json_file_path)
        ibc_data_store.save_ibc_content(ibc_path, ibc_content)
        print(f"    {Colors.OKGREEN}IBC代码已保存: {ibc_path}{Colors.ENDC}")
        
        # 保存符号数据（符号树+元数据）
        file_name = os.path.basename(icp_json_file_path)
        symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
        ibc_data_store.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        print(f"    {Colors.OKGREEN}符号表已保存: {symbols_path}{Colors.ENDC}")
        
        # 保存符号元数据到验证文件（符号数量和MD5）
        symbols_count = IbcFuncs.count_symbols_in_metadata(symbols_metadata)
        symbols_metadata_md5 = IbcFuncs.calculate_symbols_metadata_md5(symbols_metadata)
        
        # 计算并保存IBC内容的MD5
        ibc_content_md5 = IbcFuncs.calculate_text_md5(ibc_content)
        
        # 读取one_file_req的MD5(用于在生成成功后更新)
        req_file = os.path.join(self.work_staging_dir_path, f"{icp_json_file_path}_one_file_req.txt")
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                req_content = f.read()
            current_req_md5 = IbcFuncs.calculate_text_md5(req_content)
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 读取one_file_req失败，无法更新MD5: {e}{Colors.ENDC}")
            current_req_md5 = None
        
        # 一次性更新所有验证数据
        update_data = {
            'symbols_count': str(symbols_count),
            'symbols_metadata_md5': symbols_metadata_md5,
            'ibc_verify_code': ibc_content_md5  # 保存IBC内容的MD5
        }
        
        # 只有成功读取到one_file_req的MD5时才更新(这是关键!)
        if current_req_md5 is not None:
            update_data['one_file_req_verify_code'] = current_req_md5
        
        ibc_data_store.update_file_verify_data(self.work_data_dir_path, icp_json_file_path, update_data)
        
        print(f"    {Colors.OKGREEN}验证数据已保存: 符号数={symbols_count}, MD5={symbols_metadata_md5[:8]}...{Colors.ENDC}")
        
        # IBC代码和符号表保存成功，返回成功
        return True

    def _build_user_prompt_for_ibc_generator(self, icp_json_file_path: str) -> str:
        """
        构建IBC代码生成的用户提示词（role_ibc_gen）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Args:
            icp_json_file_path: 当前处理的文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        
        # 使用可见符号表构建器构建当前文件的可见符号树
        ibc_data_store = get_ibc_data_store()

        # 先检查依赖符号表是否可用
        if not ibc_data_store.is_dependency_symbol_tables_valid(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=icp_json_file_path,
        ):
            # 依赖符号不可用时，认为用户提示词构建失败
            print(f"  {Colors.FAIL}警告: 依赖符号表构建失败，用户提示词构建失败: {icp_json_file_path}{Colors.ENDC}")
            return ""

        dependency_symbol_tables = ibc_data_store.load_dependency_symbol_tables(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=icp_json_file_path,
        )

        symbols_tree, symbols_metadata = self.visible_symbol_builder.build_visible_symbol_tree(
            current_file_path=icp_json_file_path,
            dependency_symbol_tables=dependency_symbol_tables,
        )
        
        # 构建模块依赖路径列表（点分隔格式）
        module_dependency_paths = []
        if icp_json_file_path in self.dependent_relation:
            dependencies = self.dependent_relation[icp_json_file_path]
            for dep_path in dependencies:
                # 将路径从 "src/ball/ball_entity" 转换为 "ball.ball_entity"
                module_path = dep_path.replace('/', '.')
                module_dependency_paths.append(module_path)
        
        # 构建模块依赖文本
        if module_dependency_paths:
            module_dependencies_text = "当前文件的模块依赖（需在IBC代码顶部引用的模块）：\n\n" + "\n".join(f"module {path}" for path in module_dependency_paths)
        else:
            module_dependencies_text = "当前文件无模块依赖"
        
        # 使用 IbcFuncs 构建可用依赖符号列表
        available_symbol_lines = IbcFuncs.build_available_symbol_list(
            symbols_metadata=symbols_metadata,
            proj_root_dict=self.proj_root_dict
        )

        if available_symbol_lines:
            available_symbols_text = "可用的依赖符号（filename.symbol ：对外功能描述）：\n\n" + "\n".join(available_symbol_lines)
        else:
            available_symbols_text = '暂无可用的依赖符号'
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        implementation_plan_str = ""
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_str = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e} {Colors.ENDC}")
            return ""

        # 读取文件需求描述
        req_file_path = os.path.join(self.work_staging_dir_path, f"{icp_json_file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_req_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败: {e}{Colors.ENDC}")
            return ""

        class_content = self._extract_section_content(file_req_str, 'class')
        func_content = self._extract_section_content(file_req_str, 'func')
        var_content = self._extract_section_content(file_req_str, 'var')
        others_content = self._extract_section_content(file_req_str, 'others')
        behavior_content = self._extract_section_content(file_req_str, 'behavior')
        extern_lib_content = self._extract_section_content(file_req_str, 'external_lib')
        
        # 读取提取的参数（前置检查已保证文件存在且格式正确）
        extracted_params_file = os.path.join(self.work_data_dir_path, 'extracted_params.json')
        try:
            with open(extracted_params_file, 'r', encoding='utf-8') as f:
                extracted_params_content = f.read()
            extracted_params_json = json.loads(extracted_params_content)
            extracted_params_text = self._format_extracted_params(extracted_params_json)
        except Exception as e:
            # 这里不应该发生，因为前置检查已经验证过
            print(f"  {Colors.FAIL}错误: 读取提取参数失败: {e}{Colors.ENDC}")
            return ""
        
        # 读取用户提示词模板
        user_prompt_template_str = self.user_prompt_manager.get_template('intent_code_behavior_gen_user')
        if not user_prompt_template_str:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败{Colors.ENDC}")
            return ""
        
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        # user_prompt_str = user_prompt_str.replace('USER_REQUIREMENTS_PLACEHOLDER', self.user_requirements_str)
        # user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan_str)
        # user_prompt_str = user_prompt_str.replace('PROJECT_STRUCTURE_PLACEHOLDER', self.proj_root_dict_json_str)
        # user_prompt_str = user_prompt_str.replace('CURRENT_FILE_PATH_PLACEHOLDER', icp_json_file_path)
        user_prompt_str = user_prompt_str.replace('EXTRACTED_PARAMS_PLACEHOLDER', extracted_params_text)
        user_prompt_str = user_prompt_str.replace('CLASS_CONTENT_PLACEHOLDER', class_content if class_content else '无')
        user_prompt_str = user_prompt_str.replace('FUNC_CONTENT_PLACEHOLDER', func_content if func_content else '无')
        user_prompt_str = user_prompt_str.replace('VAR_CONTENT_PLACEHOLDER', var_content if var_content else '无')
        user_prompt_str = user_prompt_str.replace('OTHERS_CONTENT_PLACEHOLDER', others_content if others_content else '无')
        user_prompt_str = user_prompt_str.replace('BEHAVIOR_CONTENT_PLACEHOLDER', behavior_content if behavior_content else '无')
        user_prompt_str = user_prompt_str.replace('EXTERN_LIB_CONTENT_PLACEHOLDER', extern_lib_content if extern_lib_content else '无')
        user_prompt_str = user_prompt_str.replace('MODULE_DEPENDENCIES_PLACEHOLDER', module_dependencies_text)
        user_prompt_str = user_prompt_str.replace('AVAILABLE_SYMBOLS_PLACEHOLDER', available_symbols_text)
        
        return user_prompt_str

    def _format_extracted_params(self, params_json: Dict[str, Any]) -> str:
        """格式化提取的参数为可读性好的文本
        
        Args:
            params_json: 提取的参数JSON对象
            
        Returns:
            str: 格式化后的参数文本
        """
        if not params_json:
            return "无可用参数"
        
        result_lines = []
        
        # 处理重要参数
        if 'important_param' in params_json and params_json['important_param']:
            result_lines.append("【重要参数】")
            result_lines.append("")
            for param_name, param_info in params_json['important_param'].items():
                result_lines.append(f"- {param_name}:")
                result_lines.append(f"  值: {param_info.get('value', 'N/A')}")
                result_lines.append(f"  类型: {param_info.get('type', 'N/A')}")
                result_lines.append(f"  单位: {param_info.get('unit', 'N/A')}")
                result_lines.append(f"  说明: {param_info.get('description', 'N/A')}")
                if 'constraints' in param_info and param_info['constraints']:
                    result_lines.append(f"  约束: {', '.join(param_info['constraints'])}")
                result_lines.append("")
        
        # 处理建议参数
        if 'suggested_param' in params_json and params_json['suggested_param']:
            result_lines.append("【建议参数】")
            result_lines.append("")
            for param_name, param_info in params_json['suggested_param'].items():
                result_lines.append(f"- {param_name}:")
                result_lines.append(f"  值: {param_info.get('value', 'N/A')}")
                result_lines.append(f"  类型: {param_info.get('type', 'N/A')}")
                result_lines.append(f"  单位: {param_info.get('unit', 'N/A')}")
                result_lines.append(f"  说明: {param_info.get('description', 'N/A')}")
                if 'constraints' in param_info and param_info['constraints']:
                    result_lines.append(f"  约束: {', '.join(param_info['constraints'])}")
                result_lines.append("")
        
        if not result_lines:
            return "无可用参数"
        
        return "\n".join(result_lines)

    def _save_user_prompt_to_stage(self, icp_json_file_path: str, user_prompt: str, attempt: int) -> bool:
        """将用户提示词保存到stage文件夹以便查看
        
        Args:
            icp_json_file_path: 文件路径
            user_prompt: 用户提示词
            attempt: 当前尝试次数
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 构建保存路径，与one_file_req类似
            prompt_file_path = os.path.join(
                self.work_staging_dir_path, 
                f"{icp_json_file_path}_ibc_user_prompt_attempt{attempt}.txt"
            )
            
            # 创建目录
            parent_dir = os.path.dirname(prompt_file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 保存提示词
            with open(prompt_file_path, 'w', encoding='utf-8') as f:
                f.write(user_prompt)
            
            print(f"    {Colors.OKGREEN}用户提示词已保存: {prompt_file_path}{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 保存用户提示词失败 {prompt_file_path}: {e}{Colors.ENDC}")
            return False

    def _extract_section_content(self, content: str, section_name: str) -> str:
        """从文件内容中提取指定部分的内容"""
        lines = content.split('\n')
        section_lines = []
        found_section = False
        
        for line in lines:
            # 查找section_name:开始的行
            if line.strip().startswith(f'{section_name}:'):
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

    def _validate_ibc_response(
        self, 
        ast_dict: Dict[str, Any],
        current_file_path: str,
        symbols_tree: Dict[str, Any] = None,
        symbols_metadata: Dict[str, Dict[str, Any]] = None
    ) -> bool:
        """验证IBC代码分析结果是否有效
        
        Args:
            ast_dict: AST字典
            current_file_path: 当前文件路径
            symbols_tree: 当前文件的符号树（用于符号引用验证）
            symbols_metadata: 当前文件的符号元数据（用于符号引用验证）
            
        Returns:
            bool: 是否有效
        """
        # 每次分析前清空issue recorder
        self.ibc_issue_recorder.clear()

        # 检查AST是否有效
        if not ast_dict:
            error_msg = "IBC代码分析失败，未能生成有效的AST"
            print(f"    {Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            # 如果分析失败没有记录issue，这里补充记录
            if not self.ibc_issue_recorder.has_issues():
                self.ibc_issue_recorder.record_issue(error_msg, 0, "")
            return False
        
        # 执行符号引用验证（包括类构造函数验证）
        print(f"    {Colors.OKBLUE}正在验证符号引用和类构造函数...{Colors.ENDC}")
        self._validate_symbol_references(
            ast_dict=ast_dict,
            current_file_path=current_file_path,
            local_symbols_tree=symbols_tree,
            local_symbols_metadata=symbols_metadata
        )
        
        # 如果没有问题，认为验证通过
        if not self.ibc_issue_recorder.has_issues():
            print(f"    {Colors.OKGREEN}IBC代码验证通过{Colors.ENDC}")
            return True
        
        # 如果有问题，输出问题数量以及具体的问题内容
        issue_count = self.ibc_issue_recorder.get_issue_count()
        print(f"    {Colors.WARNING}警告: IBC代码分析发现 {issue_count} 个问题{Colors.ENDC}")
        self.ibc_issue_recorder.print_issues()
        return False
    
    def _validate_symbol_references(
        self,
        ast_dict: Dict[int, IbcBaseAstNode],
        current_file_path: str,
        local_symbols_tree: Dict[str, Any] = None,
        local_symbols_metadata: Dict[str, Dict[str, Any]] = None
    ) -> None:
        """验证AST中的所有符号引用
        
        Args:
            ast_dict: AST字典
            current_file_path: 当前文件路径
            local_symbols_tree: 当前文件的符号树（用于验证对本地符号的引用）
            local_symbols_metadata: 当前文件的符号元数据
        """
        # 获取当前文件的可见符号树（用于符号引用验证）
        ibc_data_store = get_ibc_data_store()
        
        # 检查依赖符号表是否有效
        if not ibc_data_store.is_dependency_symbol_tables_valid(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=current_file_path,
        ):
            # 如果依赖符号表无效，跳过符号引用验证
            # 这种情况通常发生在文件没有依赖或依赖文件尚未生成符号表时
            return
        
        # 加载依赖符号表
        dependency_symbol_tables = ibc_data_store.load_dependency_symbol_tables(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=current_file_path,
        )
        
        # 构建可见符号树（包含依赖符号 + 本地符号）
        visible_symbols_tree, visible_symbols_metadata = self.visible_symbol_builder.build_visible_symbol_tree(
            current_file_path=current_file_path,
            dependency_symbol_tables=dependency_symbol_tables,
            include_local_symbols=True,
            local_symbols_tree=local_symbols_tree,
            local_symbols_metadata=local_symbols_metadata
        )
        
        # 创建符号引用解析器并执行验证
        ref_resolver = SymbolRefResolver(
            ast_dict=ast_dict,
            symbols_tree=visible_symbols_tree,
            symbols_metadata=visible_symbols_metadata,
            ibc_issue_recorder=self.ibc_issue_recorder,
            proj_root_dict=self.proj_root_dict,
            dependent_relation=self.dependent_relation,
            current_file_path=current_file_path,
            external_library_dependencies=self.external_library_dependencies
        )
        ref_resolver.resolve_all_references()
    
    def _build_user_prompt_retry_part(self, fix_suggestion: str) -> str:
        """构建用户提示词重试部分（基于修复建议的输出修复提示）
        
        Args:
            fix_suggestion: 上一步诊断阶段生成的修复建议
        
        Returns:
            str: 重试部分的用户提示词，失败时返回空字符串
        """
        if not self.ibc_issue_recorder.has_issues() or not self.last_generated_ibc_content:
            return ""
        
        # 使用 IbcIssueRecorder 的格式构建问题列表文本
        ibc_issues = self.ibc_issue_recorder.get_issues()
        issues_text = "\n".join(
            [f"- 第{issue.line_num}行: {issue.message} (代码: {issue.line_content})" for issue in ibc_issues]
        )
        
        # 替代 RetryPromptHelper.build_fix_user_prompt_part
        # 格式化上一次生成的内容
        formatted_content = f"```intent_behavior_code\n{self.last_generated_ibc_content}\n```"
        
        retry_mapping = {
            "PREVIOUS_CONTENT_PLACEHOLDER": formatted_content,
            "ISSUES_LIST_PLACEHOLDER": issues_text or ""
        }
        
        retry_prompt = self.user_prompt_manager.build_prompt_from_template("retry_prompt_template", retry_mapping)
        
        # 追加修复建议
        retry_prompt += "\n\n【修复建议】\n"
        retry_prompt += (fix_suggestion or "(无修复建议)")
        
        return retry_prompt

    def is_cmd_valid(self):
        """检查命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        try:
            # 检查提取参数文件是否存在
            extracted_params_file = os.path.join(self.work_data_dir_path, 'extracted_params.json')
            if not os.path.exists(extracted_params_file):
                print(f"  {Colors.WARNING}警告: 提取参数文件不存在，请先执行参数提取命令(para_extract){Colors.ENDC}")
                return False
            
            # 验证提取参数文件格式是否正确
            try:
                with open(extracted_params_file, 'r', encoding='utf-8') as f:
                    extracted_params_content = f.read()
                json.loads(extracted_params_content)  # 验证JSON格式
            except json.JSONDecodeError as e:
                print(f"  {Colors.FAIL}错误: 提取参数文件格式错误: {e}{Colors.ENDC}")
                return False
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取提取参数文件失败: {e}{Colors.ENDC}")
                return False
            
            # 检查依赖分析结果文件是否存在
            ibc_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
            if not os.path.exists(ibc_dir_file):
                print(f"  {Colors.WARNING}警告: 依赖分析结果文件不存在，请先执行依赖分析命令{Colors.ENDC}")
                return False
            
            # 检查文件级实现规划文件是否存在
            implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
            if not os.path.exists(implementation_plan_file):
                print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
                return False
            
            # 读取目录结构并解析
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                dir_structure_str = f.read()
            dir_json_dict = json.loads(dir_structure_str)
            
            # 验证依赖分析结果完整性
            if "proj_root_dict" not in dir_json_dict or "dependent_relation" not in dir_json_dict:
                print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点(proj_root_dict或dependent_relation){Colors.ENDC}")
                return False
            
            # 获取文件列表
            dependent_relation = dir_json_dict['dependent_relation']
            file_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
            
            # 检查src_staging目录是否存在
            work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
            if not os.path.exists(work_staging_dir_path):
                print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
                return False
            
            # 检查每个文件的one_file_req文件是否存在
            missing_files = []
            for file_path in file_list:
                req_file = os.path.join(work_staging_dir_path, f"{file_path}_one_file_req.txt")
                if not os.path.exists(req_file):
                    missing_files.append(f"{file_path}_one_file_req.txt")
            
            if missing_files:
                print(f"  {Colors.FAIL}错误: 以下one_file_req文件不存在，请先执行one_file_req_gen命令:{Colors.ENDC}")
                for missing_file in missing_files[:5]:  # 只显示前5个
                    print(f"    - {missing_file}")
                if len(missing_files) > 5:
                    print(f"    ... 还有 {len(missing_files) - 5} 个文件")
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
        
        # 检查用户提示词模板
        if not self.user_prompt_manager.has_template('intent_code_behavior_gen_user'):
            print(f"  {Colors.FAIL}错误: 用户提示词模板 intent_code_behavior_gen_user 未加载{Colors.ENDC}")
            return False
        
        if not self.user_prompt_manager.has_template('retry_prompt_template'):
            print(f"  {Colors.FAIL}错误: 用户提示词模板 retry_prompt_template 未加载{Colors.ENDC}")
            return False
            
        return True
