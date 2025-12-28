import os
import asyncio
import json
from typing import Dict, Any, List

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.ibc_data_store import get_instance as get_ibc_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs
from utils.issue_recorder import TextIssueRecorder


class CmdHandlerSymbolNormalize(BaseCmdHandler):
    """符号规范化命令处理器"""

    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="symbol_normalize",
            aliases=["SN"],
            description="对IBC文件中的符号进行规范化处理",
            help_text="调用AI对符号进行规范化命名",
        )
        
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')
        self.work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')

        self.role_symbol_normalizer = "8_symbol_normalizer"
        self.sys_prompt_symbol_normalizer = ""  # 系统提示词基础部分,在_init_ai_handlers中加载
        self.sys_prompt_retry_part = ""  # 系统提示词重试部分,在_init_ai_handlers中加载
        self.chat_handler = ICPChatHandler()
        
        # 初始化issue recorder和上一次生成的内容
        self.issue_recorder = TextIssueRecorder()
        self.last_generated_content = None  # 上一次生成的内容
        
        self.user_prompt_base = ""  # 用户提示词基础部分
        self.user_prompt_retry_part = ""  # 用户提示词重试部分
        
        # 实例变量初始化（在_build_pre_execution_variables中赋值）
        self.dependent_relation = None
        self.file_creation_order_list = None
        self.work_ibc_dir_path = None
        self.symbols_to_normalize_dict = {}  # {file_path: symbols_to_normalize}
        
        self._init_ai_handlers()
    
    def execute(self):
        """执行符号规范化"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始符号规范化...{Colors.ENDC}")
        
        # 准备执行前所需的变量
        self._build_pre_execution_variables()
        
        # 按依赖顺序遍历并处理每个文件
        for file_path in self.file_creation_order_list:
            success = self._normalize_single_file_symbols(file_path)
            if not success:
                print(f"{Colors.FAIL}文件 {file_path} 符号规范化失败，退出运行{Colors.ENDC}")
                return
        
        print(f"{Colors.OKGREEN}符号规范化完毕!{Colors.ENDC}")
    
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

        # 获取IBC文件夹路径
        if "file_system_mapping" in icp_config_json_dict:
            ibc_dir_name = icp_config_json_dict["file_system_mapping"].get("ibc_dir_name", "src_ibc")
        else:
            ibc_dir_name = "src_ibc"
        
        work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
        
        if not os.path.exists(work_ibc_dir_path):
            print(f"  {Colors.FAIL}错误: src_ibc目录不存在，请先执行IBC生成命令{Colors.ENDC}")
            return
        
        # 获取文件创建顺序
        dependent_relation = final_dir_json_dict['dependent_relation']
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)

        # 预先加载所有文件的待规范化符号
        print(f"  {Colors.OKBLUE}正在加载待规范化符号...{Colors.ENDC}")
        self.symbols_to_normalize_dict = {}
        ibc_data_store = get_ibc_data_store()
        
        for file_path in file_creation_order_list:
            # 先从 verify_data 快速检查符号数量
            # 利用 IBC 生成阶段保存的 symbols_count 信息进行快速过滤
            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
            symbols_count_str = verify_data.get('symbols_count', None)
            
            # 如果符号数量为 0，直接跳过（无需规范化）
            if symbols_count_str is not None:
                try:
                    symbols_count = int(symbols_count_str)
                    if symbols_count == 0:
                        continue
                except ValueError:
                    pass  # 继续正常加载
            
            # 检查符号表文件是否存在
            symbols_path = ibc_data_store.build_symbols_path(work_ibc_dir_path, file_path)
            if not os.path.exists(symbols_path):
                print(f"  {Colors.FAIL}错误：文件 {file_path} 的符号表不存在{Colors.ENDC}")
                return
            
            # 加载符号数据
            file_name = os.path.basename(file_path)
            symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
            
            if not symbols_metadata:
                print(f"  {Colors.FAIL}错误：文件 {file_path} 的符号元数据为空{Colors.ENDC}")
                return
            
            # 提取待规范化符号（过滤已规范化和文件夹/文件节点）
            symbols_to_normalize = self._extract_symbols_from_metadata(symbols_metadata)
            if symbols_to_normalize:
                self.symbols_to_normalize_dict[file_path] = symbols_to_normalize

        # 存储实例变量供后续使用
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.work_ibc_dir_path = work_ibc_dir_path
        
        print(f"  {Colors.OKGREEN}已加载 {len(self.symbols_to_normalize_dict)} 个文件的待规范化符号{Colors.ENDC}")
        
        # 初始化更新状态.需要依赖self.file_creation_order_list等内容
        self.need_update_flag_dict = self._initialize_update_status()
    
    def _initialize_update_status(self) -> Dict[str, bool]:
        """初始化更新状态字典
        
        根据以下逻辑标记文件是否需要更新：
        1. 检查是否有待规范化的符号（最高优先级）
        2. 检查IBC文件的MD5值变化
        3. 检查符号元数据的MD5值变化
        4. 检查依赖链中的变化（依赖传播）
        
        Returns:
            Dict[str, bool]: 文件路径到是否需要更新的映射
        """
        print(f"  {Colors.OKBLUE}开始检查文件更新状态...{Colors.ENDC}")
        need_update_flag_dict = {}

        file_list = self.file_creation_order_list
        ibc_data_store = get_ibc_data_store()
        
        # 第一阶段：检查待规范化符号、IBC文件和符号元数据的MD5
        for file_path in file_list:
            need_update = False
            
            # 优先检查：是否有待规范化的符号
            if file_path in self.symbols_to_normalize_dict:
                print(f"    {Colors.OKBLUE}有待规范化符号: {file_path} (共 {len(self.symbols_to_normalize_dict[file_path])} 个){Colors.ENDC}")
                need_update = True
                need_update_flag_dict[file_path] = need_update
                continue
            
            # 从 verify_data 加载校验数据
            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
            
            # 检查符号数量，如果为 0 则无需规范化
            symbols_count_str = verify_data.get('symbols_count', None)
            if symbols_count_str is not None:
                try:
                    symbols_count = int(symbols_count_str)
                    if symbols_count == 0:
                        need_update_flag_dict[file_path] = False
                        continue
                except ValueError:
                    pass  # 继续正常检查
            
            # 检查IBC文件的MD5是否变化
            ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
            if os.path.exists(ibc_path):
                try:
                    current_ibc_md5 = IbcFuncs.calculate_text_md5(ibc_data_store.load_ibc_content(ibc_path) or "")
                    saved_ibc_md5 = verify_data.get('ibc_verify_code', None)
                    
                    if saved_ibc_md5 is not None and saved_ibc_md5 != current_ibc_md5:
                        print(f"    {Colors.OKBLUE}IBC文件已变化: {file_path}{Colors.ENDC}")
                        need_update = True
                except Exception as e:
                    print(f"    {Colors.WARNING}警告: 检查IBC文件MD5失败: {file_path}, {e}{Colors.ENDC}")
            
            # 检查符号元数据的MD5是否变化（如果IBC未变化）
            if not need_update:
                symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, file_path)
                if os.path.exists(symbols_path):
                    file_name = os.path.basename(file_path)
                    symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
                    
                    if symbols_metadata:
                        current_symbols_md5 = IbcFuncs.calculate_symbols_metadata_md5(symbols_metadata)
                        saved_symbols_md5 = verify_data.get('symbols_metadata_md5', None)
                        
                        if saved_symbols_md5 is not None and saved_symbols_md5 != current_symbols_md5:
                            print(f"    {Colors.OKBLUE}符号元数据已变化: {file_path}{Colors.ENDC}")
                            need_update = True
            
            need_update_flag_dict[file_path] = need_update
        
        # 第二阶段：依赖链传播更新
        # 按依赖顺序遍历（file_list已经是拓扑排序后的顺序）
        for file_path in file_list:
            if need_update_flag_dict.get(file_path, False):
                # 如果当前文件已标记需要更新，则所有依赖它的文件也需要更新
                self._propagate_update_to_dependents(file_path, need_update_flag_dict)
            else:
                # 检查规范化后符号元数据的MD5是否变化（用户可能手动修改了符号表）
                symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, file_path)
                file_name = os.path.basename(file_path)
                symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
                
                if symbols_metadata:
                    current_normalized_md5 = IbcFuncs.calculate_symbols_metadata_md5(symbols_metadata)
                    verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
                    saved_normalized_md5 = verify_data.get('symbol_normalize_verify_code', None)
                    
                    if saved_normalized_md5 is not None and saved_normalized_md5 != current_normalized_md5:
                        print(f"    {Colors.OKBLUE}规范化结果被手动修改: {file_path}，依赖它的文件需要更新{Colors.ENDC}")
                        self._propagate_update_to_dependents(file_path, need_update_flag_dict)
        
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
    
    def _extract_symbols_from_metadata(self, symbols_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """从符号元数据中提取待规范化的符号
        
        Args:
            symbols_metadata: 符号元数据字典
            
        Returns:
            待规范化符号字典 {symbol_path: metadata}
        """
        symbols_to_normalize = {}
        for symbol_path, meta in symbols_metadata.items():
            meta_type = meta.get("type", "unknown")
            # 过滤掉文件夹/文件节点
            if meta_type in ("folder", "file"):
                continue
            # 过滤已经规范化的符号
            if "normalized_name" in meta and meta["normalized_name"]:
                continue
            symbols_to_normalize[symbol_path] = meta
        return symbols_to_normalize
    
    def _normalize_single_file_symbols(self, icp_json_file_path: str) -> bool:
        """为单个文件的符号进行规范化处理（包含重试机制）
        
        如果该文件被标记为需要更新但不存在待规范化符号，则仅刷新规范化验证数据（不调用AI）。
        
        Args:
            icp_json_file_path: 文件路径
            
        Returns:
            bool: 是否成功规范化
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        # 检查是否需要更新
        if not self.need_update_flag_dict.get(icp_json_file_path, False):
            print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过规范化: {icp_json_file_path}{Colors.ENDC}")
            return True
        
        # 根据预处理阶段收集的结果获取待规范化符号列表
        symbols_to_normalize = self.symbols_to_normalize_dict.get(icp_json_file_path)

        # 虽然没有待规范化符号，但可能是依赖变化或符号元数据变化，需要更新验证数据
        if not symbols_to_normalize:
            print(f"    {Colors.OKBLUE}当前文件无待规范化符号，仅刷新规范化验证数据{Colors.ENDC}")
            ibc_data_store = get_ibc_data_store()
            symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
            file_name = os.path.basename(icp_json_file_path)
            symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
            if symbols_metadata:
                # 重新计算并保存 symbol_normalize_verify_code，避免下次重复被标记为需要更新
                self._save_normalize_verify_data(icp_json_file_path, symbols_metadata)
            return True
        
        print(f"    {Colors.OKBLUE}正在进行符号规范化... (共 {len(symbols_to_normalize)} 个符号){Colors.ENDC}")
        
        # 重置issue recorder和重试变量
        self.issue_recorder.clear()
        self.last_generated_content = None
        
        # 构建用户提示词基础部分
        self.user_prompt_base = self._build_user_prompt_for_symbol_normalizer(icp_json_file_path)
        if not self.user_prompt_base:
            print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
            return False
        
        # 带重试的符号规范化生成逻辑
        max_attempts = 3
        is_valid = False
        
        for attempt in range(max_attempts):
            print(f"    {Colors.OKBLUE}正在进行第 {attempt + 1}/{max_attempts} 次尝试...{Colors.ENDC}")
            
            # 根据是否是重试来组合提示词
            if attempt == 0:
                # 第一次尝试,使用基础提示词
                current_sys_prompt = self.sys_prompt_symbol_normalizer
                current_user_prompt = self.user_prompt_base
            else:
                # 重试时,添加重试部分
                current_sys_prompt = self.sys_prompt_symbol_normalizer + "\n\n" + self.sys_prompt_retry_part
                current_user_prompt = self.user_prompt_base + "\n\n" + self.user_prompt_retry_part
            
            # 调用AI进行规范化
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_symbol_normalizer,
                sys_prompt=current_sys_prompt,
                user_prompt=current_user_prompt
            ))
            
            if not success or not response_content:
                print(f"    {Colors.WARNING}警告: AI响应失败或为空{Colors.ENDC}")
                continue
            
            cleaned_response = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证规范化结果
            is_valid = self._validate_normalized_symbols(cleaned_response, symbols_to_normalize)
            
            if is_valid:
                # 验证通过，保存规范化结果
                self._save_normalized_symbols(icp_json_file_path, cleaned_response, symbols_to_normalize)
                break
            
            # 如果验证失败，保存当前生成的内容并构建重试提示词
            self.last_generated_content = cleaned_response
            self.user_prompt_retry_part = self._build_user_prompt_retry_part()
        
        # 循环已跳出，检查运行结果
        if attempt == max_attempts - 1 and not is_valid:
            print(f"  {Colors.FAIL}已达到最大重试次数({max_attempts})，跳过该文件{Colors.ENDC}")
            return False
        
        return True

    def _validate_normalized_symbols(
        self, 
        cleaned_response: str, 
        symbols_to_normalize: Dict[str, Dict[str, Any]]
    ) -> bool:
        """验证AI返回的符号规范化结果
        
        此方法只负责验证，不包含重试逻辑，也不进行任何数据更新或保存操作。
        验证失败时，会将未成功规范化的符号记录到issue_recorder中。
        
        Args:
            cleaned_response: 清理后的AI响应内容
            symbols_to_normalize: 待规范化符号字典
                
        Returns:
            bool: 是否验证完全成功（所有符号都规范化成功）
        """
        # 清空上一次验证的问题记录
        self.issue_recorder.clear()
        
        # 1. 解析JSON格式
        try:
            result = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            error_msg = f"JSON格式无效: {e}"
            print(f"    {Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        if not isinstance(result, dict):
            error_msg = "返回结果不是字典格式"
            print(f"    {Colors.WARNING}警告: {error_msg}{Colors.ENDC}")
            self.issue_recorder.record_issue(error_msg)
            return False
        
        # 2. 验证每个符号的规范化结果，收集未成功规范化的符号
        failed_symbols = []
        
        for symbol_path, meta in symbols_to_normalize.items():
            # 检查符号是否在返回结果中
            if symbol_path not in result:
                failed_symbols.append(f"{symbol_path} (未返回)")
                continue
            
            normalized_name = result[symbol_path]
            
            # 验证 normalized_name 符合标识符规范
            if not isinstance(normalized_name, str) or not normalized_name:
                failed_symbols.append(f"{symbol_path} (返回值为空)")
            elif not IbcFuncs.validate_identifier(normalized_name):
                failed_symbols.append(f"{symbol_path} (返回值'{normalized_name}'不符合标识符规范)")
        
        # 3. 检查验证结果
        total_symbols = len(symbols_to_normalize)

        if failed_symbols:
            print(f"    {Colors.WARNING}警告: {len(failed_symbols)}/{total_symbols} 个符号未成功规范化{Colors.ENDC}")
            # 将失败的符号记录到issue_recorder
            for failed_symbol in failed_symbols:
                self.issue_recorder.record_issue(failed_symbol)
            return False
        
        print(f"    {Colors.OKGREEN}符号规范化验证通过（{total_symbols}/{total_symbols}）{Colors.ENDC}")
        return True
        

    def _save_normalized_symbols(
        self, 
        icp_json_file_path: str,
        cleaned_response: str,
        symbols_to_normalize: Dict[str, Dict[str, Any]]
    ) -> None:
        """从AI返回结果中提取规范化数据，并保存到符号表
        
        Args:
            icp_json_file_path: 文件路径
            cleaned_response: 清理后的AI响应内容（已通过验证）
            symbols_to_normalize: 待规范化符号字典
        """
        result = json.loads(cleaned_response)
        
        # 提取已验证的规范化结果
        validated_result = {}
        for symbol_path in symbols_to_normalize.keys():
            if symbol_path in result:
                normalized_name = result[symbol_path]
                # 再次验证以确保安全
                if isinstance(normalized_name, str) and normalized_name and IbcFuncs.validate_identifier(normalized_name):
                    validated_result[symbol_path] = normalized_name
        
        # 加载符号表
        ibc_data_store = get_ibc_data_store()
        symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
        file_name = os.path.basename(icp_json_file_path)
        symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
        
        # 更新符号元数据中的规范化名称
        updated_count = self._update_symbol_metadata(symbols_metadata, validated_result)
        
        # 保存更新后的符号数据
        ibc_data_store.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        print(f"    {Colors.OKGREEN}符号表已保存: {symbols_path}{Colors.ENDC}")
        
        # 保存规范化验证数据
        self._save_normalize_verify_data(icp_json_file_path, symbols_metadata)
        
        print(f"    {Colors.OKGREEN}成功规范化 {updated_count} 个符号{Colors.ENDC}")

    def _build_user_prompt_for_symbol_normalizer(self, icp_json_file_path: str) -> str:
        """
        构建符号规范化的用户提示词（role_symbol_normalizer）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
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
                ibc_code = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC代码失败: {e}{Colors.ENDC}")
            return ""
        
        # 获取待规范化符号（必须存在，因为已在调用前检查过）
        symbols_to_normalize = self.symbols_to_normalize_dict.get(icp_json_file_path)
        if not symbols_to_normalize:
            print(f"  {Colors.FAIL}错误: 文件无待规范化符号，不应调用此方法{Colors.ENDC}")
            return ""
        
        # 读取提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'symbol_normalizer_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 获取目标语言
        target_language = self._get_target_language()
        
        # 格式化符号列表
        symbols_text = self._format_symbols_for_prompt(symbols_to_normalize)
        
        # 填充占位符
        user_prompt_str = user_prompt_template_str.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
        user_prompt_str = user_prompt_str.replace('FILE_PATH_PLACEHOLDER', icp_json_file_path)
        user_prompt_str = user_prompt_str.replace('CONTEXT_INFO_PLACEHOLDER', ibc_code)
        user_prompt_str = user_prompt_str.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
        
        return user_prompt_str

    def _get_target_language(self) -> str:
        """获取目标编程语言"""
        work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')
        try:
            with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
                icp_config_json_dict = json.load(f)
            return icp_config_json_dict.get('target_language', 'python')
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取配置文件失败: {e}，使用默认语言python{Colors.ENDC}")
            return 'python'
    
    def _format_symbols_for_prompt(self, symbols_to_normalize: Dict[str, Dict[str, Any]]) -> str:
        """格式化符号列表用于提示词
        
        Args:
            symbols_to_normalize: 待规范化符号字典
            
        Returns:
            格式化后的符号列表字符串
        """
        lines = []
        for symbol_path, meta in symbols_to_normalize.items():
            meta_type = meta.get("type", "unknown")
            description = meta.get("description") or "无描述"
            lines.append(f"- {symbol_path} ({meta_type}, 描述: {description})")
        return '\n'.join(lines)
    
    def _update_symbol_metadata(
        self, 
        symbols_metadata: Dict[str, Dict[str, Any]], 
        normalized_symbols: Dict[str, str]
    ) -> int:
        """根据规范化结果更新符号元数据
        
        Args:
            symbols_metadata: 符号元数据字典
            normalized_symbols: 规范化符号字典 {符号路径: 规范化名称}
            
        Returns:
            成功更新的符号数量
        """
        updated_count = 0
        
        for symbol_key, normalized_name in normalized_symbols.items():
            # 按照完整路径精确匹配
            if symbol_key in symbols_metadata:
                symbols_metadata[symbol_key]["normalized_name"] = normalized_name
                symbols_metadata[symbol_key]["normalization_status"] = "completed"
                updated_count += 1
        
        return updated_count

    def _save_normalize_verify_data(self, icp_json_file_path: str, symbols_metadata: Dict[str, Dict[str, Any]]) -> None:
        """保存符号规范化的验证数据到验证文件
        
        Args:
            icp_json_file_path: 文件路径
            symbols_metadata: 符号元数据字典
        """
        # 计算规范化后的符号元数据MD5
        normalized_md5 = IbcFuncs.calculate_symbols_metadata_md5(symbols_metadata)
        
        # 更新规范化相关的验证数据
        ibc_data_store = get_ibc_data_store()
        ibc_data_store.update_file_verify_data(self.work_data_dir_path, icp_json_file_path, {
            'symbol_normalize_verify_code': normalized_md5
        })
        
        print(f"    {Colors.OKGREEN}规范化验证数据已保存: MD5={normalized_md5[:8]}...{Colors.ENDC}")

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

        
    def is_cmd_valid(self):
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

            if "file_system_mapping" in icp_config_json_dict:
                ibc_dir_name = icp_config_json_dict["file_system_mapping"].get("ibc_dir_name", "src_ibc")
            else:
                ibc_dir_name = "src_ibc"
            
            work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
            
            # 检查src_ibc目录是否存在
            if not os.path.exists(work_ibc_dir_path):
                print(f"  {Colors.FAIL}错误: src_ibc目录不存在，请先执行IBC生成命令{Colors.ENDC}")
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
        if not ICPChatHandler.is_initialized():
            return False
        
        if not self.sys_prompt_symbol_normalizer:
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
        
        chat_api_config_dict = None
        if 'intent_behavior_code_gen_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['intent_behavior_code_gen_handler']
        elif 'coder_handler' in config_json_dict:
            chat_api_config_dict = config_json_dict['coder_handler']
        else:
            print("错误: 配置文件缺少intent_behavior_code_gen_handler或coder_handler配置")
            return

        chat_config = ChatApiConfig(
            base_url=chat_api_config_dict.get('api-url', ''),
            api_key=chat_api_config_dict.get('api-key', ''),
            model=chat_api_config_dict.get('model', '')
        )

        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(chat_config)
        
        # 加载系统提示词
        app_data_store = get_app_data_store()
        app_prompt_dir_path = app_data_store.get_prompt_dir()
        
        # 加载符号规范化角色的系统提示词基础部分
        sys_prompt_path = os.path.join(app_prompt_dir_path, f"{self.role_symbol_normalizer}.md")
        try:
            with open(sys_prompt_path, 'r', encoding='utf-8') as f:
                self.sys_prompt_symbol_normalizer = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败 ({self.role_symbol_normalizer}): {e}")
        
        # 加载系统提示词重试部分
        retry_sys_prompt_path = os.path.join(app_prompt_dir_path, 'retry_sys_prompt.md')
        try:
            with open(retry_sys_prompt_path, 'r', encoding='utf-8') as f:
                self.sys_prompt_retry_part = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词重试部分失败: {e}")
