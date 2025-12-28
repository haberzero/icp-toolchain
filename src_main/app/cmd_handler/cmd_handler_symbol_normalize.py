import os
import asyncio
import json
from typing import Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.ibc_data_store import get_instance as get_ibc_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs


class CmdHandlerSymbolNormalize(BaseCmdHandler):
    """符号规范化命令处理器
    
    设计结构：
    1. 变量预准备：_build_pre_execution_variables() - 集中加载所需数据
    2. 文件遍历：按依赖顺序遍历文件列表
    3. 单文件处理：_normalize_single_file_symbols() - 包含重试逻辑的主流程
    4. 符号提取：_extract_symbols_from_metadata() - 从符号元数据中提取待规范化符号
    5. 提示词构建：_build_user_prompt_for_symbol_normalizer() - 为规范化构建提示词
    6. 结果验证：_validate_normalized_result() - 验证AI返回的规范化结果
    7. 结果回写：_update_symbol_metadata() - 将规范化结果写回元数据
    """

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
        self.sys_prompt_symbol_normalizer = ""  # 系统提示词,在_init_ai_handlers中加载
        self.chat_handler = ICPChatHandler()
        
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
            # 检查IBC文件是否存在
            ibc_path = ibc_data_store.build_ibc_path(work_ibc_dir_path, file_path)
            if not os.path.exists(ibc_path):
                print(f"    {Colors.FAIL}读取文件 {file_path} 时出现错误{Colors.ENDC}")
                print(f"    {Colors.FAIL}错误: IBC文件不存在{Colors.ENDC}")
                return
            
            # 加载符号数据
            symbols_path = ibc_data_store.build_symbols_path(work_ibc_dir_path, file_path)
            file_name = os.path.basename(file_path)
            symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
            
            if not symbols_metadata:
                print(f"    {Colors.FAIL}读取文件 {file_path} 时出现错误{Colors.ENDC}")
                print(f"    {Colors.FAIL}错误: 相关符号表为空{Colors.ENDC}")
                return
            
            # 提取待规范化符号
            symbols_to_normalize = self._extract_symbols_from_metadata(symbols_metadata)
            if symbols_to_normalize:
                self.symbols_to_normalize_dict[file_path] = symbols_to_normalize

        # 存储实例变量供后续使用
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.work_ibc_dir_path = work_ibc_dir_path
        
        print(f"  {Colors.OKGREEN}已加载 {len(self.symbols_to_normalize_dict)} 个文件的待规范化符号{Colors.ENDC}")
    
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
        
        Args:
            icp_json_file_path: 文件路径
            
        Returns:
            bool: 是否成功规范化
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        # 检查是否有待规范化符号
        if icp_json_file_path not in self.symbols_to_normalize_dict:
            print(f"    {Colors.OKBLUE}没有需要规范化的符号{Colors.ENDC}")
            return True
        
        symbols_to_normalize = self.symbols_to_normalize_dict[icp_json_file_path]
        print(f"    {Colors.OKBLUE}正在进行符号规范化... (共 {len(symbols_to_normalize)} 个符号){Colors.ENDC}")
        
        # 带重试的符号规范化生成逻辑
        max_attempts = 3
        validated_result = None
        
        for attempt in range(max_attempts):
            if attempt > 0:
                print(f"    {Colors.OKBLUE}正在重试... (尝试 {attempt + 1}/{max_attempts}){Colors.ENDC}")
            
            # 构建用户提示词
            user_prompt = self._build_user_prompt_for_symbol_normalizer(icp_json_file_path)
            if not user_prompt:
                print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
                return False
            
            # 调用AI进行规范化
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_symbol_normalizer,
                sys_prompt=self.sys_prompt_symbol_normalizer,
                user_prompt=user_prompt
            ))
            
            if not success or not response_content:
                print(f"    {Colors.WARNING}警告: AI响应失败或为空{Colors.ENDC}")
                continue
            
            cleaned_response = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证规范化结果
            is_valid, validated_result = self._validate_response(
                cleaned_response, 
                symbols_to_normalize, 
                attempt, 
                max_attempts
            )
            
            if is_valid:
                # 验证成功，跳出重试循环
                break
        
        # 处理验证结果
        if validated_result and len(validated_result) > 0:
            return self._save_normalized_symbols(icp_json_file_path, validated_result)
        else:
            print(f"  {Colors.FAIL}已达到最大重试次数({max_attempts})，未能生成有效的规范化结果{Colors.ENDC}")
            return False

    def _validate_response(
        self, 
        cleaned_response: str, 
        symbols_to_normalize: Dict[str, Dict[str, Any]],
        attempt: int,
        max_attempts: int
    ) -> tuple[bool, Dict[str, str]]:
        """验证AI返回的符号规范化结果
        
        Args:
            cleaned_response: 清理后的AI响应内容
            symbols_to_normalize: 待规范化符号字典
            attempt: 当前尝试次数（从0开始）
            max_attempts: 最大尝试次数
            
        Returns:
            tuple[bool, Dict[str, str]]: (是否完全成功, 验证通过的结果字典)
            - 完全成功：所有符号都规范化成功
            - 部分成功（最后一次重试）：返回部分结果以便保存
            - 失败：返回空字典
        """
        # 验证JSON格式和标识符有效性
        validated_result = IbcFuncs.validate_normalized_result(cleaned_response, symbols_to_normalize)
        
        total_symbols = len(symbols_to_normalize)
        validated_count = len(validated_result)
        
        # 情况1：全部无效
        if validated_count == 0:
            print(f"    {Colors.WARNING}警告: AI返回的符号规范化结果为空或全部无效{Colors.ENDC}")
            return False, {}
        
        # 情况2：部分成功
        if validated_count < total_symbols:
            missing_symbols = set(symbols_to_normalize.keys()) - set(validated_result.keys())
            print(f"    {Colors.WARNING}警告: 仅规范化了 {validated_count}/{total_symbols} 个符号，{len(missing_symbols)} 个符号未成功{Colors.ENDC}")
            print(f"    {Colors.WARNING}未成功的符号:{Colors.ENDC}")
            for sym in list(missing_symbols)[:5]:  # 只显示前5个
                print(f"      - {sym}")
            if len(missing_symbols) > 5:
                print(f"      ... 还有 {len(missing_symbols) - 5} 个")
            
            # 如果还没到最后一次重试，继续重试
            if attempt < max_attempts - 1:
                print(f"    {Colors.WARNING}将在下次重试中尝试规范化所有符号{Colors.ENDC}")
                return False, {}
            else:
                # 最后一次重试仍然部分失败，保存部分结果
                print(f"    {Colors.WARNING}已达到最大重试次数{Colors.ENDC}")
                print(f"    {Colors.WARNING}注意: 仍有 {len(missing_symbols)} 个符号未能规范化，这些符号将在下次执行时继续尝试{Colors.ENDC}")
                return False, validated_result  # 返回部分结果用于保存
        
        # 情况3：全部成功
        return True, validated_result
    
    def _save_normalized_symbols(
        self, 
        icp_json_file_path: str, 
        validated_result: Dict[str, str]
    ) -> bool:
        """保存规范化符号到符号表
        
        Args:
            icp_json_file_path: 文件路径
            validated_result: 验证通过的规范化结果
            
        Returns:
            bool: 是否为完全成功（所有符号都规范化）
        """
        ibc_data_store = get_ibc_data_store()
        symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
        file_name = os.path.basename(icp_json_file_path)
        symbols_tree, symbols_metadata = ibc_data_store.load_symbols(symbols_path, file_name)
        
        # 更新符号元数据中的规范化名称
        updated_count = self._update_symbol_metadata(symbols_metadata, validated_result)
        
        # 保存更新后的符号数据
        ibc_data_store.save_symbols(symbols_path, file_name, symbols_tree, symbols_metadata)
        
        # 判断是否完全成功
        total_symbols = len(self.symbols_to_normalize_dict[icp_json_file_path])
        is_complete = (updated_count == total_symbols)
        
        if is_complete:
            print(f"    {Colors.OKGREEN}符号表已更新并保存: {symbols_path}{Colors.ENDC}")
            print(f"    {Colors.OKGREEN}成功规范化全部 {updated_count} 个符号{Colors.ENDC}")
        else:
            print(f"    {Colors.WARNING}符号表已更新并保存: {symbols_path}{Colors.ENDC}")
            print(f"    {Colors.WARNING}已保存部分成功的规范化结果 ({updated_count}/{total_symbols} 个符号){Colors.ENDC}")
        
        return is_complete

    def _build_user_prompt_for_symbol_normalizer(self, icp_json_file_path: str) -> str:
        """
        构建符号规范化的用户提示词（role_symbol_normalizer）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        包含所有前置条件检查，如果不满足条件则返回空字符串。
        
        Args:
            icp_json_file_path: 当前文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        ibc_data_store = get_ibc_data_store()
        
        # 读取IBC代码（IBC文件存在性已在预构建阶段检查过）
        ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, icp_json_file_path)
        try:
            with open(ibc_path, 'r', encoding='utf-8') as f:
                ibc_code = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC代码失败: {e}{Colors.ENDC}")
            return ""
        
        # 获取待规范化符号（在预构建阶段加载）
        symbols_to_normalize = self.symbols_to_normalize_dict[icp_json_file_path]
        
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
        unmatched_keys = []
        
        for symbol_key, normalized_name in normalized_symbols.items():
            # 按照完整路径精确匹配
            if symbol_key in symbols_metadata:
                symbols_metadata[symbol_key]["normalized_name"] = normalized_name
                symbols_metadata[symbol_key]["normalization_status"] = "completed"
                updated_count += 1
            else:
                # 不进行模糊匹配，AI 必须返回准确的 key
                unmatched_keys.append(symbol_key)
        
        # 输出统计信息
        if unmatched_keys:
            print(f"    {Colors.WARNING}警告: 以下 {len(unmatched_keys)} 个符号路径在元数据中未找到（AI返回的key格式可能有误）:{Colors.ENDC}")
            for key in unmatched_keys[:5]:  # 只显示前5个
                print(f"      - {key}")
            if len(unmatched_keys) > 5:
                print(f"      ... 还有 {len(unmatched_keys) - 5} 个")
        
        return updated_count

        
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
        
        # 加载符号规范化角色
        sys_prompt_path = os.path.join(app_prompt_dir_path, f"{self.role_symbol_normalizer}.md")
        try:
            with open(sys_prompt_path, 'r', encoding='utf-8') as f:
                self.sys_prompt_symbol_normalizer = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败 ({self.role_symbol_normalizer}): {e}")
