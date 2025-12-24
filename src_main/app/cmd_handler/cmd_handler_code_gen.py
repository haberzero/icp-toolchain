# import sys, os
# import asyncio
# import json
# from typing import List, Dict

# from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
# from typedef.ai_data_types import ChatApiConfig, EmbeddingApiConfig, EmbeddingStatus
# from typedef.ibc_data_types import IbcBaseAstNode

# from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
# from data_store.app_data_store import get_instance as get_app_data_store
# from data_store.user_data_store import get_instance as get_user_data_store
# from data_store.ibc_data_store import get_instance as get_ibc_data_store

# from .base_cmd_handler import BaseCmdHandler
# from utils.icp_ai_handler import ICPChatHandler
# from utils.icp_ai_handler.icp_embedding_handler import ICPEmbeddingHandler
# from libs.dir_json_funcs import DirJsonFuncs
# from utils.ibc_analyzer.ibc_code_reconstructor import IbcCodeReconstructor
# from libs.symbol_vector_db_manager import SymbolVectorDBManager
# from libs.symbol_replacer import SymbolReplacer


# class CmdHandlerCodeGen(BaseCmdHandler):
#     """将IBC代码转换为目标编程语言代码"""
    
#     def __init__(self):
#         super().__init__()
#         self.command_info = CommandInfo(
#             name="code_gen",
#             aliases=["CG"],
#             description="将IBC代码转换为目标编程语言代码",
#             help_text="读取IBC代码和AST，进行符号规范化替换，生成目标语言代码",
#         )
#         proj_run_time_cfg = get_proj_run_time_cfg()
#         self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
#         self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
#         self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
#         self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')
        
#         self.role_name = "8_target_code_gen"
#         self.sys_prompt = ""  # 系统提示词,在_init_ai_handlers中加载
        
#         # 使用ICPChatHandler和ICPEmbeddingHandler
#         self.chat_handler = ICPChatHandler()
#         self.embedding_handler = ICPEmbeddingHandler()
        
#         # 符号向量数据库管理器（延迟初始化）
#         self.vector_db_manager = None
        
#         # 初始化AI处理器
#         self._init_ai_handlers()

#     def execute(self):
#         """执行目标代码生成"""
#         if not self.is_cmd_valid():
#             return
            
#         print(f"{Colors.OKBLUE}开始生成目标语言代码...{Colors.ENDC}")

#         # 读取依赖分析结果
#         ibc_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
#         try:
#             with open(ibc_dir_file, 'r', encoding='utf-8') as f:
#                 ibc_content_json_dict = json.load(f)
#         except Exception as e:
#             print(f"  {Colors.FAIL}错误: 读取依赖分析结果失败: {e}{Colors.ENDC}")
#             return
        
#         if not ibc_content_json_dict or "dependent_relation" not in ibc_content_json_dict:
#             print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点{Colors.ENDC}")
#             return

#         # 从dependent_relation中获取文件创建顺序
#         dependent_relation = ibc_content_json_dict["dependent_relation"]
#         file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
#         # 获取目录配置
#         ibc_dir_name = self._get_ibc_directory_name()
#         target_dir_name = self._get_target_directory_name()
#         target_suffix = self._get_target_suffix()
        
#         work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
#         work_target_dir_path = os.path.join(self.work_dir_path, target_dir_name)
        
#         # 确保目标目录存在
#         os.makedirs(work_target_dir_path, exist_ok=True)
        
#         # 初始化符号向量数据库
#         vector_db_path = os.path.join(self.work_data_dir_path, 'symbol_vector_db')
#         self.vector_db_manager = SymbolVectorDBManager(vector_db_path, self.embedding_handler)
        
#         # 读取用户原始需求
#         user_data_store = get_user_data_store()
#         user_requirements_str = user_data_store.get_user_prompt()
        
#         # 读取文件级实现规划
#         implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
#         implementation_plan_str = ""
#         try:
#             with open(implementation_plan_file, 'r', encoding='utf-8') as f:
#                 implementation_plan_str = f.read()
#         except Exception as e:
#             print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}{Colors.ENDC}")
        
#         # 读取目标编程语言
#         target_language = self._get_target_language()
        
#         # 按照依赖顺序处理每个文件
#         for icp_json_file_path in file_creation_order_list:
#             print(f"\n  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
            
#             # 1. 加载AST
#             ast_file_path = self._get_ast_file_path(work_ibc_dir_path, icp_json_file_path)
#             if not os.path.exists(ast_file_path):
#                 print(f"    {Colors.WARNING}警告: AST文件不存在，跳过: {ast_file_path}{Colors.ENDC}")
#                 continue
            
#             print(f"    正在加载AST...")
#             ibc_data_store = get_ibc_data_store()
#             ast_dict = ibc_data_store.load_ast(ast_file_path)
            
#             if not ast_dict:
#                 print(f"    {Colors.FAIL}错误: AST加载失败{Colors.ENDC}")
#                 continue
            
#             # 2. 加载符号表
#             print(f"    正在加载符号表...")
#             symbols_path = ibc_data_store.build_symbols_path(work_ibc_dir_path, icp_json_file_path)
#             file_name = os.path.basename(icp_json_file_path)
#             symbol_table = ibc_data_store.load_symbols(symbols_path, file_name)
            
#             if not symbol_table or len(symbol_table) == 0:
#                 print(f"    {Colors.WARNING}警告: 符号表为空{Colors.ENDC}")
            
#             # 3. 执行符号替换（在AST中）
#             print(f"    正在执行符号规范化替换...")
#             symbol_replacer = SymbolReplacer(ast_dict, symbol_table, self.vector_db_manager)
#             symbol_replacer.replace_symbols_in_ast()
            
#             # 4. 重建IBC代码
#             print(f"    正在重建IBC代码...")
#             code_reconstructor = IbcCodeReconstructor(ast_dict)
#             normalized_ibc_code = code_reconstructor.reconstruct()
            
#             # 保存规范化后的IBC代码（可选，用于调试）
#             normalized_ibc_file = os.path.join(work_ibc_dir_path, f"{icp_json_file_path}_normalized.ibc")
#             try:
#                 os.makedirs(os.path.dirname(normalized_ibc_file), exist_ok=True)
#                 with open(normalized_ibc_file, 'w', encoding='utf-8') as f:
#                     f.write(normalized_ibc_code)
#                 print(f"    {Colors.OKGREEN}规范化IBC代码已保存: {normalized_ibc_file}{Colors.ENDC}")
#             except Exception as e:
#                 print(f"    {Colors.WARNING}警告: 保存规范化IBC代码失败: {e}{Colors.ENDC}")
            
#             # 5. 调用AI生成目标代码
#             print(f"    正在生成目标语言代码...")
#             target_code_str = self._generate_target_code(icp_json_file_path)
            
#             if not target_code_str:
#                 print(f"    {Colors.FAIL}错误: 目标代码生成失败{Colors.ENDC}")
#                 continue
            
#             # 6. 保存目标代码
#             target_file_path = os.path.join(work_target_dir_path, f"{icp_json_file_path}{target_suffix}")
#             try:
#                 os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
#                 with open(target_file_path, 'w', encoding='utf-8') as f:
#                     f.write(target_code_str)
#                 print(f"  {Colors.OKGREEN}目标代码已生成: {target_file_path}{Colors.ENDC}")
#             except Exception as e:
#                 print(f"  {Colors.FAIL}错误: 保存目标代码失败: {e}{Colors.ENDC}")
#                 continue
        
#         print(f"\n{Colors.OKGREEN}目标语言代码生成完毕!{Colors.ENDC}")

#     def _build_user_prompt_for_target_code_gen(self, icp_json_file_path: str) -> str:
#         """
#         构建目标代码生成的用户提示词
        
#         从项目数据目录中直接读取所需信息，无需外部参数传递。
        
#         Args:
#             icp_json_file_path: 当前处理的文件路径
        
#         Returns:
#             str: 完整的用户提示词，失败时返回空字符串
#         """
#         # 读取用户原始需求
#         user_data_store = get_user_data_store()
#         user_requirements_str = user_data_store.get_user_prompt()
#         if not user_requirements_str:
#             print(f"  {Colors.FAIL}错误: 读取用户需求失败{Colors.ENDC}")
#             return ""
        
#         # 读取文件级实现规划
#         implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
#         implementation_plan_str = ""
#         try:
#             with open(implementation_plan_file, 'r', encoding='utf-8') as f:
#                 implementation_plan_str = f.read()
#         except Exception as e:
#             print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}{Colors.ENDC}")
        
#         # 读取目标编程语言
#         target_language = self._get_target_language()
        
#         # 读取规范化后的IBC代码
#         ibc_dir_name = self._get_ibc_directory_name()
#         work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
#         normalized_ibc_file = os.path.join(work_ibc_dir_path, f"{icp_json_file_path}_normalized.ibc")
#         try:
#             with open(normalized_ibc_file, 'r', encoding='utf-8') as f:
#                 ibc_code_str = f.read()
#         except Exception as e:
#             print(f"  {Colors.FAIL}错误: 读取规范化IBC代码失败: {e}{Colors.ENDC}")
#             return ""
#         # 读取用户提示词模板
#         app_data_store = get_app_data_store()
#         app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'target_code_gen_user.md')
        
#         try:
#             with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
#                 user_prompt_template_str = f.read()
#         except Exception as e:
#             print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
#             return ""
        
#         # 填充模板
#         user_prompt_str = user_prompt_template_str
#         user_prompt_str = user_prompt_str.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
#         user_prompt_str = user_prompt_str.replace('CURRENT_FILE_PATH_PLACEHOLDER', icp_json_file_path)
#         user_prompt_str = user_prompt_str.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements_str)
#         user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan_str)
#         user_prompt_str = user_prompt_str.replace('IBC_CODE_PLACEHOLDER', ibc_code_str)
        
#         return user_prompt_str

#     def _generate_target_code(self, icp_json_file_path: str) -> str:
#         """
#         生成目标语言代码
        
#         Args:
#             icp_json_file_path: 文件路径
            
#         Returns:
#             str: 生成的目标代码
#         """
#         # 构建用户提示词
#         user_prompt_str = self._build_user_prompt_for_target_code_gen(icp_json_file_path)
#         if not user_prompt_str:
#             return ""
        
#         # 调用AI生成目标代码
#         response_str, success = asyncio.run(self.chat_handler.get_role_response(
#             role_name=self.role_name,
#             sys_prompt=self.sys_prompt,
#             user_prompt=user_prompt_str
#         ))
        
#         if not success:
#             print(f"    {Colors.WARNING}警告: AI响应失败{Colors.ENDC}")
#             return ""
        
#         if not response_str:
#             print(f"    {Colors.WARNING}警告: AI响应为空{Colors.ENDC}")
#             return ""
        
#         # 清理代码块标记
#         cleaned_code_str = ICPChatHandler.clean_code_block_markers(response_str)
        
#         return cleaned_code_str

#     def _get_ast_file_path(self, work_ibc_dir_path: str, icp_json_file_path: str) -> str:
#         """获取AST文件路径"""
#         return os.path.join(work_ibc_dir_path, f"{icp_json_file_path}_ibc_ast.json")

#     def _get_ibc_directory_name(self) -> str:
#         """获取IBC目录名称"""
#         work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')
#         try:
#             with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
#                 icp_config_json_dict = json.load(f)
#             return icp_config_json_dict["file_system_mapping"].get("behavioral_layer_dir", "src_ibc")
#         except:
#             return "src_ibc"

#     def _get_target_directory_name(self) -> str:
#         """获取目标代码目录名称"""
#         work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')
#         try:
#             with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
#                 icp_config_json_dict = json.load(f)
#             return icp_config_json_dict["file_system_mapping"].get("target_layer_dir", "src_main")
#         except:
#             return "src_main"

#     def _get_target_suffix(self) -> str:
#         """获取目标代码文件后缀"""
#         work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')
#         try:
#             with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
#                 icp_config_json_dict = json.load(f)
#             return icp_config_json_dict.get("target_suffix", ".py")
#         except:
#             return ".py"

#     def _get_target_language(self) -> str:
#         """获取目标编程语言"""
#         work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')
#         try:
#             with open(work_icp_config_file_path, 'r', encoding='utf-8') as f:
#                 icp_config_json_dict = json.load(f)
#             return icp_config_json_dict.get("target_language", "Python")
#         except:
#             return "Python"

#     def _check_cmd_requirement(self) -> bool:
#         """验证命令的前置条件"""
#         # 检查依赖分析结果文件是否存在
#         ibc_dir_file = os.path.join(self.work_data_dir_path, 'icp_dir_content_with_depend.json')
#         if not os.path.exists(ibc_dir_file):
#             print(f"  {Colors.WARNING}警告: 依赖分析结果文件不存在，请先执行依赖分析命令{Colors.ENDC}")
#             return False
        
#         # 检查IBC目录是否存在
#         ibc_dir_name = self._get_ibc_directory_name()
#         work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
#         if not os.path.exists(work_ibc_dir_path):
#             print(f"  {Colors.WARNING}警告: IBC目录不存在，请先执行ibc_gen命令{Colors.ENDC}")
#             return False
        
#         return True
    
#     def _check_ai_handler(self) -> bool:
#         """验证AI处理器是否初始化成功"""
#         # 检查ChatInterface是否初始化
#         if not ICPChatHandler.is_initialized():
#             print(f"  {Colors.WARNING}警告: Chat处理器未初始化{Colors.ENDC}")
#             return False
        
#         # 检查系统提示词是否加载
#         if not self.sys_prompt:
#             print(f"  {Colors.WARNING}警告: 系统提示词 {self.role_name} 未加载{Colors.ENDC}")
#             return False
        
#         # 检查EmbeddingHandler是否初始化
#         if not ICPEmbeddingHandler.is_initialized():
#             print(f"  {Colors.WARNING}警告: Embedding处理器未初始化{Colors.ENDC}")
#             return False
        
#         return True
    
#     def _init_ai_handlers(self):
#         """初始化AI处理器"""
#         if not os.path.exists(self.work_api_config_file_path):
#             print(f"错误: 配置文件 {self.work_api_config_file_path} 不存在")
#             return
        
#         try:
#             with open(self.work_api_config_file_path, 'r', encoding='utf-8') as f:
#                 config_json_dict = json.load(f)
#         except Exception as e:
#             print(f"错误: 读取配置文件失败: {e}")
#             return
        
#         # Chat处理器配置
#         if 'coder_handler' in config_json_dict:
#             chat_api_config_dict = config_json_dict['coder_handler']
#         else:
#             print("错误: 配置文件缺少coder_handler配置")
#             return
        
#         chat_handler_config = ChatApiConfig(
#             base_url=chat_api_config_dict.get('api-url', ''),
#             api_key=chat_api_config_dict.get('api-key', ''),
#             model=chat_api_config_dict.get('model', '')
#         )
        
#         # 初始化共享的ChatInterface（只初始化一次）
#         if not ICPChatHandler.is_initialized():
#             ICPChatHandler.initialize_chat_interface(chat_handler_config)
        
#         # 加载系统提示词
#         app_data_store = get_app_data_store()
#         app_prompt_dir_path = app_data_store.get_prompt_dir()
#         app_sys_prompt_file_path = os.path.join(app_prompt_dir_path, f"{self.role_name}.md")
        
#         try:
#             with open(app_sys_prompt_file_path, 'r', encoding='utf-8') as f:
#                 self.sys_prompt = f.read()
#         except Exception as e:
#             print(f"错误: 读取系统提示词文件失败: {e}")
        
#         # Embedding处理器配置
#         if 'embedding_handler' in config_json_dict:
#             embedding_api_config_dict = config_json_dict['embedding_handler']
#         else:
#             print("警告: 配置文件缺少embedding_handler配置，使用coder_handler配置")
#             embedding_api_config_dict = chat_api_config_dict
        
#         embedding_handler_config = EmbeddingApiConfig(
#             base_url=embedding_api_config_dict.get('api-url', ''),
#             api_key=embedding_api_config_dict.get('api-key', ''),
#             model=embedding_api_config_dict.get('model', '')
#         )
        
#         # 初始化共享的EmbeddingHandler（只初始化一次）
#         if not ICPEmbeddingHandler.is_initialized():
#             ICPEmbeddingHandler.initialize_embedding_handler(embedding_handler_config)
