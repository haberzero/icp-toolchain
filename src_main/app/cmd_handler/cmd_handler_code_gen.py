import sys, os
import asyncio
import json
from typing import List, Dict
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig, EmbeddingApiConfig
from typedef.ibc_data_types import IbcBaseAstNode

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager
from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from utils.icp_ai_handler.icp_embedding_handler import ICPEmbeddingHandler
from typedef.ai_data_types import ChatResponseStatus, EmbeddingStatus
from libs.dir_json_funcs import DirJsonFuncs
from utils.ibc_analyzer.ibc_code_reconstructor import IbcCodeReconstructor
from libs.symbol_vector_db_manager import SymbolVectorDBManager
from libs.symbol_replacer import SymbolReplacer


class CmdHandlerCodeGen(BaseCmdHandler):
    """将IBC代码转换为目标编程语言代码"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="code_gen",
            aliases=["CG"],
            description="将IBC代码转换为目标编程语言代码",
            help_text="读取IBC代码和AST，进行符号规范化替换，生成目标语言代码",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')
        
        self.role_name = "9_target_code_gen"
        
        # 使用ICPChatHandler和ICPEmbeddingHandler
        self.chat_handler = ICPChatHandler()
        self.embedding_handler = ICPEmbeddingHandler()
        
        # 符号向量数据库管理器（延迟初始化）
        self.vector_db_manager = None
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行目标代码生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成目标语言代码...{Colors.ENDC}")

        # 读取IBC目录结构
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        try:
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                ibc_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not ibc_content or "dependent_relation" not in ibc_content:
            print(f"  {Colors.FAIL}错误: IBC目录结构缺少必要的节点{Colors.ENDC}")
            return

        # 从dependent_relation中获取文件创建顺序
        dependent_relation = ibc_content["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 获取目录配置
        ibc_dir_name = self._get_ibc_directory_name()
        target_dir_name = self._get_target_directory_name()
        target_suffix = self._get_target_suffix()
        
        ibc_root_path = os.path.join(self.proj_work_dir, ibc_dir_name)
        target_root_path = os.path.join(self.proj_work_dir, target_dir_name)
        
        # 确保目标目录存在
        os.makedirs(target_root_path, exist_ok=True)
        
        # 初始化符号向量数据库
        vector_db_path = os.path.join(self.proj_data_dir, 'symbol_vector_db')
        self.vector_db_manager = SymbolVectorDBManager(vector_db_path, self.embedding_handler)
        
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        implementation_plan_content = ""
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_content = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}{Colors.ENDC}")
        
        # 读取目标编程语言
        target_language = self._get_target_language()
        
        # 按照依赖顺序处理每个文件
        for file_path in file_creation_order_list:
            print(f"\n  {Colors.OKBLUE}正在处理文件: {file_path}{Colors.ENDC}")
            
            # 1. 加载AST
            ast_file_path = self._get_ast_file_path(ibc_root_path, file_path)
            if not os.path.exists(ast_file_path):
                print(f"    {Colors.WARNING}警告: AST文件不存在，跳过: {ast_file_path}{Colors.ENDC}")
                continue
            
            print(f"    正在加载AST...")
            ibc_data_manager = get_ibc_data_manager()
            ast_dict = ibc_data_manager.load_ast_from_file(ast_file_path)
            
            if not ast_dict:
                print(f"    {Colors.FAIL}错误: AST加载失败{Colors.ENDC}")
                continue
            
            # 2. 加载符号表
            print(f"    正在加载符号表...")
            symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, file_path)
            
            if not symbol_table or not symbol_table.symbols:
                print(f"    {Colors.WARNING}警告: 符号表为空{Colors.ENDC}")
            
            # 3. 执行符号替换（在AST中）
            print(f"    正在执行符号规范化替换...")
            symbol_replacer = SymbolReplacer(ast_dict, symbol_table, self.vector_db_manager)
            symbol_replacer.replace_symbols_in_ast()
            
            # 4. 重建IBC代码
            print(f"    正在重建IBC代码...")
            code_reconstructor = IbcCodeReconstructor(ast_dict)
            normalized_ibc_code = code_reconstructor.reconstruct()
            
            # 保存规范化后的IBC代码（可选，用于调试）
            normalized_ibc_file = os.path.join(ibc_root_path, f"{file_path}_normalized.ibc")
            try:
                os.makedirs(os.path.dirname(normalized_ibc_file), exist_ok=True)
                with open(normalized_ibc_file, 'w', encoding='utf-8') as f:
                    f.write(normalized_ibc_code)
                print(f"    {Colors.OKGREEN}规范化IBC代码已保存: {normalized_ibc_file}{Colors.ENDC}")
            except Exception as e:
                print(f"    {Colors.WARNING}警告: 保存规范化IBC代码失败: {e}{Colors.ENDC}")
            
            # 5. 调用AI生成目标代码
            print(f"    正在生成目标语言代码...")
            target_code = self._generate_target_code(
                file_path,
                normalized_ibc_code,
                user_requirements,
                implementation_plan_content,
                target_language
            )
            
            if not target_code:
                print(f"    {Colors.FAIL}错误: 目标代码生成失败{Colors.ENDC}")
                continue
            
            # 6. 保存目标代码
            target_file_path = os.path.join(target_root_path, f"{file_path}{target_suffix}")
            try:
                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                with open(target_file_path, 'w', encoding='utf-8') as f:
                    f.write(target_code)
                print(f"  {Colors.OKGREEN}目标代码已生成: {target_file_path}{Colors.ENDC}")
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 保存目标代码失败: {e}{Colors.ENDC}")
                continue
        
        print(f"\n{Colors.OKGREEN}目标语言代码生成完毕!{Colors.ENDC}")

    def _generate_target_code(
        self,
        file_path: str,
        ibc_code: str,
        user_requirements: str,
        implementation_plan: str,
        target_language: str
    ) -> str:
        """
        生成目标语言代码
        
        Args:
            file_path: 文件路径
            ibc_code: 规范化后的IBC代码
            user_requirements: 用户原始需求
            implementation_plan: 文件级实现规划
            target_language: 目标编程语言
            
        Returns:
            str: 生成的目标代码
        """
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'target_code_gen_user.md')
        
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan)
        user_prompt = user_prompt.replace('IBC_CODE_PLACEHOLDER', ibc_code)
        
        # 调用AI生成目标代码
        response_content = asyncio.run(self._get_ai_response(self.role_name, user_prompt))
        
        if not response_content:
            print(f"    {Colors.WARNING}警告: AI响应为空{Colors.ENDC}")
            return ""
        
        # 移除可能的代码块标记
        lines = response_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()
        
        return cleaned_content

    def _get_ast_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """获取AST文件路径"""
        return os.path.join(ibc_root_path, f"{file_path}_ibc_ast.json")

    def _get_ibc_directory_name(self) -> str:
        """获取IBC目录名称"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            return icp_config["file_system_mapping"].get("behavioral_layer_dir", "src_ibc")
        except:
            return "src_ibc"

    def _get_target_directory_name(self) -> str:
        """获取目标代码目录名称"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            return icp_config["file_system_mapping"].get("target_layer_dir", "src_main")
        except:
            return "src_main"

    def _get_target_suffix(self) -> str:
        """获取目标代码文件后缀"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            return icp_config.get("target_suffix", ".py")
        except:
            return ".py"

    def _get_target_language(self) -> str:
        """获取目标编程语言"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            return icp_config.get("target_language", "Python")
        except:
            return "Python"

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查IBC目录结构文件是否存在
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        if not os.path.exists(ibc_dir_file):
            print(f"  {Colors.WARNING}警告: IBC目录结构文件不存在，请先执行ibc_gen命令{Colors.ENDC}")
            return False
        
        # 检查IBC目录是否存在
        ibc_dir_name = self._get_ibc_directory_name()
        ibc_root_path = os.path.join(self.proj_work_dir, ibc_dir_name)
        if not os.path.exists(ibc_root_path):
            print(f"  {Colors.WARNING}警告: IBC目录不存在，请先执行ibc_gen命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.WARNING}警告: Chat处理器未初始化{Colors.ENDC}")
            return False
        
        # 检查角色是否已加载
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.WARNING}警告: 角色 {self.role_name} 未加载{Colors.ENDC}")
            return False
        
        # 检查EmbeddingHandler是否初始化
        if not ICPEmbeddingHandler.is_initialized():
            print(f"  {Colors.WARNING}警告: Embedding处理器未初始化{Colors.ENDC}")
            return False
        
        return True
    
    async def _get_ai_response(self, role_name: str, user_prompt: str) -> str:
        """异步获取AI响应"""
        print(f"    {role_name}正在生成响应...")
        
        response_content, status = await self.chat_handler.get_role_response(
            role_name=role_name,
            user_prompt=user_prompt
        )
        
        if status == ChatResponseStatus.SUCCESS:
            print(f"\n    {role_name}运行完毕。")
            return response_content
        elif status == ChatResponseStatus.CLIENT_NOT_INITIALIZED:
            print(f"\n{Colors.FAIL}错误: ChatInterface未初始化{Colors.ENDC}")
            return ""
        elif status == ChatResponseStatus.STREAM_FAILED:
            print(f"\n{Colors.FAIL}错误: 流式响应失败{Colors.ENDC}")
            return ""
        else:
            print(f"\n{Colors.FAIL}错误: 未知状态 {status}{Colors.ENDC}")
            return ""
    
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
        
        # Chat处理器配置
        if 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少coder_handler配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载角色
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, f"{self.role_name}.md")
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)
        
        # Embedding处理器配置
        if 'embedding_handler' in config:
            embedding_api_config = config['embedding_handler']
        else:
            print("警告: 配置文件缺少embedding_handler配置，使用coder_handler配置")
            embedding_api_config = chat_api_config
        
        embedding_config = EmbeddingApiConfig(
            base_url=embedding_api_config.get('api-url', ''),
            api_key=SecretStr(embedding_api_config.get('api-key', '')),
            model=embedding_api_config.get('model', '')
        )
        
        # 初始化共享的EmbeddingHandler（只初始化一次）
        if not ICPEmbeddingHandler.is_initialized():
            ICPEmbeddingHandler.initialize_embedding_handler(embedding_config)
