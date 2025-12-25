import os
import asyncio
import json
from typing import Dict

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig
from typedef.ibc_data_types import SymbolNode

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.ibc_data_store import get_instance as get_ibc_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs


class CmdHandlerSymbolNormalize(BaseCmdHandler):
    """符号规范化命令处理器
    
    负责对已生成的IBC文件中的符号进行规范化处理:
    1. 读取IBC文件及其符号表
    2. 调用AI进行符号规范化（规范化名称）
    3. 更新符号表并保存
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

        self.role_symbol_normalizer = "7_symbol_normalizer"
        self.sys_prompt_symbol_normalizer = ""  # 系统提示词,在_init_ai_handlers中加载
        self.chat_handler = ICPChatHandler()
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
        
        # 存储实例变量供后续使用
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.work_ibc_dir_path = work_ibc_dir_path
    
    def _normalize_single_file_symbols(self, icp_json_file_path: str) -> bool:
        """为单个文件的符号进行规范化处理
        
        Args:
            icp_json_file_path: 文件路径
            
        Returns:
            bool: 是否成功规范化
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        ibc_data_store = get_ibc_data_store()
        
        # 加载IBC代码
        ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, icp_json_file_path)
        if not os.path.exists(ibc_path):
            print(f"    {Colors.WARNING}警告: IBC文件不存在，跳过: {ibc_path}{Colors.ENDC}")
            return True
        
        ibc_code = ibc_data_store.load_ibc_code(ibc_path)
        if not ibc_code:
            print(f"    {Colors.WARNING}警告: IBC代码为空，跳过{Colors.ENDC}")
            return True
        
        # 加载符号表
        symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
        file_name = os.path.basename(icp_json_file_path)
        symbol_table = ibc_data_store.load_symbols(symbols_path, file_name)
        
        if not symbol_table:
            print(f"    {Colors.WARNING}警告: 符号表为空，跳过{Colors.ENDC}")
            return True
        
        # 创建规范化符号（带重试）
        success, normalized_symbols_dict = self._create_normalized_symbols(
            icp_json_file_path, symbol_table, ibc_code
        )
        
        if not success or not normalized_symbols_dict:
            print(f"    {Colors.WARNING}警告: 符号规范化失败{Colors.ENDC}")
            return False
        
        # 更新符号表
        self._update_symbol_table(symbol_table, normalized_symbols_dict)
        
        # 保存更新后的符号表
        ibc_data_store.save_symbols(symbols_path, file_name, symbol_table)
        print(f"    {Colors.OKGREEN}符号表已更新并保存: {symbols_path}{Colors.ENDC}")
        
        return True
    
    def _create_normalized_symbols(
        self, 
        icp_json_file_path: str,
        symbol_table: Dict[str, SymbolNode],
        ibc_code: str
    ):
        """创建规范化符号（带重试机制）
        
        Args:
            icp_json_file_path: 文件路径
            symbol_table: 符号表字典
            ibc_code: IBC代码
            
        Returns:
            tuple: (成功标志, 规范化符号字典)
        """
        print(f"    正在进行符号规范化...")
        
        symbols = symbol_table
        if not symbols:
            print(f"    {Colors.WARNING}警告: 未从符号表中提取到符号{Colors.ENDC}")
            return False, {}
        
        # 检查AI处理器
        if not self.sys_prompt_symbol_normalizer:
            print(f"    {Colors.FAIL}错误: 符号规范化系统提示词未加载{Colors.ENDC}")
            return False, {}
        
        # 带重试的规范化调用
        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt > 0:
                print(f"    正在重试符号规范化... (尝试 {attempt + 1}/{max_attempts})")
            
            # 构建提示词
            user_prompt = self._build_user_prompt_for_symbol_normalizer(icp_json_file_path, symbols, ibc_code)
            
            # 调用AI进行规范化
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_symbol_normalizer,
                sys_prompt=self.sys_prompt_symbol_normalizer,
                user_prompt=user_prompt
            ))
            
            if not success:
                print(f"    {Colors.WARNING}警告: AI响应失败{Colors.ENDC}")
                continue
            
            # 解析响应
            cleaned_response = ICPChatHandler.clean_code_block_markers(response_content)

            # result = json.loads(cleaned_response)
            
            # # 验证结果格式
            # validated_result = {}
            # for symbol_name, normalized_name in result.items():
            #     # 验证normalized_name符合标识符规范
            #     if isinstance(normalized_name, str) and IbcFuncs.validate_identifier(normalized_name):
            #         validated_result[symbol_name] = normalized_name
            #     else:
            #         print(f"    警告: 符号 {symbol_name} 的规范化名称无效: {normalized_name}")
            

            if normalized_symbols:
                return True, normalized_symbols
            else:
                print(f"    {Colors.WARNING}警告: AI返回的符号规范化结果为空{Colors.ENDC}")
                continue
        
        # 达到最大重试次数
        print(f"    {Colors.FAIL}符号规范化失败：AI未能返回有效结果（已重试{max_attempts}次）{Colors.ENDC}")
        return False, {}

    def _build_user_prompt_for_symbol_normalizer(self, icp_json_file_path: str, symbols: Dict[str, SymbolNode], ibc_code: str) -> str:
        """
        构建符号规范化的用户提示词（role_symbol_normalizer）
        
        从配置文件中直接读取所需信息，无需外部参数传递。
        
        Args:
            icp_json_file_path: 当前文件路径
            symbols: 当前符号字典
            ibc_code: 当前IBC代码
        
        Returns:
            str: 完整的用户提示词，失败时抛出RuntimeError
        """
        # 读取提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'symbol_normalizer_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            raise RuntimeError(f"读取符号规范化提示词失败: {e}")
        
        # 获取目标语言
        target_language = self._get_target_language()
        
        # 格式化符号列表
        symbols_text = self._format_symbols_for_prompt(symbols)
        
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
    
    def _format_symbols_for_prompt(self, symbols: Dict[int, SymbolNode]) -> str:
        """格式化符号列表用于提示词"""
        lines = []
        for uid, symbol in symbols.items():
            symbol_type = symbol.symbol_type.value if symbol.symbol_type else '未知'
            description = symbol.description if symbol.description else '无描述'
            lines.append(f"- {symbol.symbol_name} ({symbol_type}, 描述: {description})")
        return '\n'.join(lines)
    
    def _update_symbol_table(self, symbol_table: Dict[str, SymbolNode], normalized_symbols: Dict[str, str]):
        """根据规范化结果更新符号表
        
        Args:
            symbol_table: 符号表字典
            normalized_symbols: 规范化符号字典 {"原始符号": "规范化符号"}
        """
        for symbol_name, normalized_name in normalized_symbols.items():
            if symbol_name in symbol_table:
                symbol = symbol_table.get(symbol_name)
                if symbol is None:
                    raise SymbolNotFoundError(symbol_name, "更新规范化信息")
                
                symbol.normalized_name = normalized_name

        
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
