import os
import asyncio
import json
import hashlib
import re
from typing import List, Dict, Any, Optional
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig, EmbeddingApiConfig
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ClassNode, FunctionNode, VariableNode, 
    VisibilityTypes, SymbolType, FileSymbolTable, SymbolNode
)

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager
from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from utils.icp_ai_handler.icp_embedding_handler import ICPEmbeddingHandler
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code, IbcAnalyzerError
from libs.dir_json_funcs import DirJsonFuncs
from libs.symbol_vector_db_manager import SymbolVectorDBManager


class CmdHandlerIbcGen(BaseCmdHandler):
    """将单文件需求描述转换为半自然语言行为描述代码"""
    
    MAX_RETRY_COUNT = 3
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="intent_behavior_code_gen",
            aliases=["IBC"],
            description="将单文件需求描述转换为半自然语言行为描述代码",
            help_text="根据单文件需求描述生成符合半自然语言行为描述语法的代码结构",
        )
        
        # 路径配置
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        
        # AI角色名称
        self.role_ibc_gen = "8_intent_behavior_code_gen"
        self.role_symbol_normalizer = "8_symbol_normalizer"
        
        # AI处理器
        self.chat_handler = ICPChatHandler()
        self.embedding_handler = ICPEmbeddingHandler()
        self.vector_db_manager = None
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def execute(self):
        """执行半自然语言行为描述代码生成"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始生成半自然语言行为描述代码...{Colors.ENDC}")
        
        # 初始化向量数据库
        if not self._init_vector_database():
            print(f"{Colors.WARNING}警告: 将继续执行但不进行符号向量化{Colors.ENDC}")
        
        # 加载项目数据
        project_data = self._load_project_data()
        if not project_data:
            return
        
        # 按依赖顺序处理每个文件
        self._process_all_files(project_data)
        
        print(f"{Colors.OKGREEN}半自然语言行为描述代码生成完毕!{Colors.ENDC}")

    def _init_vector_database(self) -> bool:
        """初始化符号向量数据库"""
        print(f"{Colors.OKBLUE}正在初始化符号向量数据库...{Colors.ENDC}")
        vector_db_path = os.path.join(self.proj_data_dir, 'symbol_vector_db')
        try:
            self.vector_db_manager = SymbolVectorDBManager(vector_db_path, self.embedding_handler)
            print(f"{Colors.OKGREEN}符号向量数据库管理器初始化完成{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}错误: 符号向量数据库管理器初始化失败: {e}{Colors.ENDC}")
            self.vector_db_manager = None
            return False
    
    def _load_project_data(self) -> Optional[Dict[str, Any]]:
        """加载项目数据，包括目录结构和用户需求"""
        # 读取IBC目录结构
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        try:
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                ibc_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC目录结构失败: {e}{Colors.ENDC}")
            return None
        
        if not ibc_content:
            print(f"  {Colors.FAIL}错误: IBC目录结构内容为空{Colors.ENDC}")
            return None
        
        if "proj_root" not in ibc_content or "dependent_relation" not in ibc_content:
            print(f"  {Colors.FAIL}错误: IBC目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return None
        
        # 读取用户需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return None
        
        # 检查目录
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        if not os.path.exists(staging_dir_path):
            print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令创建目录结构{Colors.ENDC}")
            return None
        
        # 返回项目数据
        return {
            'proj_root': ibc_content['proj_root'],
            'dependent_relation': ibc_content['dependent_relation'],
            'user_requirements': user_requirements,
            'staging_dir_path': staging_dir_path
        }
    
    def _process_all_files(self, project_data: Dict[str, Any]):
        """处理所有文件"""
        proj_root = project_data['proj_root']
        dependent_relation = project_data['dependent_relation']
        user_requirements = project_data['user_requirements']
        staging_dir_path = project_data['staging_dir_path']
        
        # 获取文件创建顺序
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 准备目录
        ibc_dir_name = self._get_ibc_directory_name()
        ibc_root_path = os.path.join(self.proj_work_dir, ibc_dir_name)
        os.makedirs(ibc_root_path, exist_ok=True)
        
        # 准备项目结构JSON
        project_structure_json = json.dumps(proj_root, indent=2, ensure_ascii=False)
        
        # 初始化更新状态
        update_status = self._initialize_update_status(
            file_creation_order_list,
            staging_dir_path,
            ibc_root_path
        )
        
        # 处理每个文件
        for file_path in file_creation_order_list:
            self._process_single_file(
                file_path=file_path,
                dependent_relation=dependent_relation,
                update_status=update_status,
                staging_dir_path=staging_dir_path,
                ibc_root_path=ibc_root_path
            )
    
    def _process_single_file(
        self,
        file_path: str,
        dependent_relation: Dict[str, List[str]],
        update_status: Dict[str, bool],
        staging_dir_path: str,
        ibc_root_path: str
    ):
        """处理单个文件"""
        print(f"  {Colors.OKBLUE}正在处理文件: {file_path}{Colors.ENDC}")
        
        # 检查是否需要更新
        if not self._should_update_file(file_path, dependent_relation, update_status):
            print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过生成: {file_path}{Colors.ENDC}")
            return
        
        # 生成并保存IBC代码（带重试）
        success = self._generate_and_save_ibc_with_retry(
            file_path=file_path,
            staging_dir_path=staging_dir_path,
            ibc_root_path=ibc_root_path
        )
        
        if success:
            print(f"  {Colors.OKGREEN}文件处理完成: {file_path}{Colors.ENDC}")
        else:
            print(f"  {Colors.WARNING}跳过文件: {file_path}{Colors.ENDC}")

    def _should_update_file(
        self,
        file_path: str,
        dependent_relation: Dict[str, List[str]],
        update_status: Dict[str, bool]
    ) -> bool:
        """检查文件是否需要更新"""
        # 检查依赖文件是否有更新
        current_file_dependencies = dependent_relation.get(file_path, [])
        if self._check_dependency_updated(current_file_dependencies, update_status):
            update_status[file_path] = True
            print(f"    {Colors.OKBLUE}检测到依赖文件已更新，当前文件需要重新生成{Colors.ENDC}")
        
        return update_status.get(file_path, True)
    
    def _read_file_requirements(self, file_path: str, staging_dir_path: str) -> Optional[str]:
        """读取文件需求描述"""
        req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
            return None
    
    def _generate_and_save_ibc_with_retry(
        self,
        file_path: str,
        staging_dir_path: str,
        ibc_root_path: str
    ) -> bool:
        """生成并保存IBC代码（带重试机制）"""
        for retry_count in range(self.MAX_RETRY_COUNT):
            if retry_count > 0:
                print(f"    {Colors.OKBLUE}正在重试生成IBC代码... (尝试 {retry_count + 1}/{self.MAX_RETRY_COUNT}){Colors.ENDC}")
            else:
                print(f"    正在生成IBC代码...")
            
            try:
                # 生成IBC代码
                ibc_code = self._generate_ibc_code(file_path)
                if not ibc_code:
                    print(f"    {Colors.WARNING}警告: AI响应为空{Colors.ENDC}")
                    continue
                
                # 保存IBC代码
                ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
                self._save_ibc_code(ibc_file_path, ibc_code)
                
                # 解析IBC代码
                print(f"    正在分析IBC代码生成AST...")
                ast_dict, symbol_table = analyze_ibc_code(ibc_code)
                
                # 保存AST
                ast_file_path = self._get_ast_file_path(ibc_file_path)
                self._save_ast(ast_dict, ast_file_path)
                
                # 符号规范化
                print(f"    正在进行符号规范化...")
                normalized_symbols_dict = self._normalize_symbols(file_path, symbol_table, ibc_code)
                
                # 更新符号表
                self._update_symbol_table(symbol_table, normalized_symbols_dict)
                
                # 保存符号表
                req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
                if self._save_symbol_table(symbol_table, req_file_path, ibc_root_path, file_path):
                    # 向量化符号
                    self._vectorize_symbols(file_path, symbol_table)
                    print(f"    {Colors.OKGREEN}IBC代码生成成功{Colors.ENDC}")
                    return True
                
            except IbcAnalyzerError as e:
                print(f"  {Colors.FAIL}错误: IBC代码分析失败 {file_path}: {e}{Colors.ENDC}")
            except RuntimeError as e:
                print(f"  {Colors.FAIL}错误: {e}{Colors.ENDC}")
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 处理失败 {file_path}: {e}{Colors.ENDC}")
            
            if retry_count < self.MAX_RETRY_COUNT - 1:
                print(f"  {Colors.WARNING}将重新生成IBC代码...{Colors.ENDC}")
            else:
                print(f"  {Colors.FAIL}已达到最大重试次数({self.MAX_RETRY_COUNT})，跳过该文件{Colors.ENDC}")
        
        return False
    
    def _save_ast(self, ast_dict: Dict[int, IbcBaseAstNode], ast_file_path: str):
        """保存AST到文件"""
        print(f"    正在保存AST到文件...")
        ibc_data_manager = get_ibc_data_manager()
        if ibc_data_manager.save_ast_to_file(ast_dict, ast_file_path):
            print(f"    {Colors.OKGREEN}AST已保存: {ast_file_path}{Colors.ENDC}")
        else:
            print(f"    {Colors.WARNING}警告: AST保存失败{Colors.ENDC}")
    
    def _update_symbol_table(self, symbol_table: FileSymbolTable, normalized_symbols_dict: Dict[str, Dict[str, str]]):
        """更新符号表中的规范化信息"""
        for symbol_name, norm_info in normalized_symbols_dict.items():
            symbol = symbol_table.get_symbol(symbol_name)
            if symbol:
                symbol.update_normalized_info(
                    norm_info['normalized_name'],
                    norm_info['visibility']
                )
    
    def _save_symbol_table(
        self,
        symbol_table: FileSymbolTable,
        req_file_path: str,
        ibc_root_path: str,
        file_path: str
    ) -> bool:
        """保存符号表"""
        print(f"    正在保存符号表...")
        
        # 保存MD5
        current_md5 = self._calculate_file_md5(req_file_path)
        symbol_table.file_md5 = current_md5
        
        # 保存符号表
        ibc_data_manager = get_ibc_data_manager()
        if ibc_data_manager.save_file_symbols(ibc_root_path, file_path, symbol_table):
            return True
        else:
            print(f"  {Colors.WARNING}警告: 符号表保存失败: {file_path}{Colors.ENDC}")
            return False
    
    def _vectorize_symbols(self, file_path: str, symbol_table: FileSymbolTable):
        """将符号添加到向量数据库"""
        if not self.vector_db_manager:
            print(f"    {Colors.WARNING}警告: 向量数据库管理器未初始化，跳过向量化{Colors.ENDC}")
            return
        
        print(f"    正在将符号添加到向量数据库...")
        try:
            self.vector_db_manager.add_file_symbols(file_path, symbol_table)
        except Exception as e:
            print(f"    {Colors.FAIL}错误: 向量化失败: {e}{Colors.ENDC}")
            import traceback
            print(f"    {Colors.FAIL}错误详情: {traceback.format_exc()}{Colors.ENDC}")
        """获取IBC目录名称，优先从配置文件读取behavioral_layer_dir，失败则使用默认值"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            
            # 尝试获取behavioral_layer_dir
            behavioral_layer_dir = icp_config["file_system_mapping"].get("behavioral_layer_dir")
            if behavioral_layer_dir:
                return behavioral_layer_dir
            else:
                return "src_ibc"
        except:
            return "src_ibc"

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

    def _generate_ibc_code(self, file_path: str) -> str:
        """
        生成IBC代码
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 生成的IBC代码
        """
        # 构建用户提示词
        user_prompt = self._build_user_prompt_for_ibc_generator(file_path)
        if not user_prompt:
            return ""

        # 调用AI生成半自然语言行为描述代码
        response_content, success = asyncio.run(self.chat_handler.get_role_response(
            role_name=self.role_ibc_gen,
            user_prompt=user_prompt
        ))
                        
        if not success:
            print(f"    {Colors.WARNING}警告: AI响应失败{Colors.ENDC}")
            return ""
        
        # 如果响应为空，说明AI调用失败
        if not response_content:
            print(f"    {Colors.WARNING}警告: AI响应为空{Colors.ENDC}")
            return ""
        
        # 清理代码块标记
        cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
        
        return cleaned_content

    def _save_ibc_code(self, ibc_file_path: str, content: str):
        """保存IBC代码到文件"""
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(ibc_file_path), exist_ok=True)
            with open(ibc_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    {Colors.OKGREEN}IBC代码已保存: {ibc_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存IBC代码失败 {ibc_file_path}: {e}{Colors.ENDC}")
    
    def _get_ast_file_path(self, ibc_file_path: str) -> str:
        """根据ibc文件路径生成AST文件路径
        
        Args:
            ibc_file_path: ibc文件的完整路径，例如: /path/to/file.ibc
            
        Returns:
            str: AST文件路径，例如: /path/to/file_ibc_ast.json
        """
        # 获取目录路径和文件名
        dir_path = os.path.dirname(ibc_file_path)
        file_name = os.path.basename(ibc_file_path)
        
        # 去掉.ibc后缀,得到原始文件名
        if file_name.endswith('.ibc'):
            base_name = file_name[:-4]  # 移除.ibc后缀
        else:
            base_name = file_name
        
        # 构建AST文件名: XxxFileNameXxx_ibc_ast.json
        ast_file_name = f"{base_name}_ibc_ast.json"
        
        # 返回完整路径
        return os.path.join(dir_path, ast_file_name)

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查IBC目录结构文件是否存在
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        if not os.path.exists(ibc_dir_file):
            print(f"  {Colors.WARNING}警告: IBC目录结构文件不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
            return False
        
        # 检查文件级实现规划文件是否存在
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        if not os.path.exists(implementation_plan_file):
            print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        if not ICPChatHandler.is_initialized():
            return False
        
        if not self.chat_handler.has_role(self.role_ibc_gen):
            return False
        
        if not ICPEmbeddingHandler.is_initialized():
            print(f"  {Colors.WARNING}警告: Embedding处理器未初始化{Colors.ENDC}")
            return False
        
        return True
    
    def _build_user_prompt_for_ibc_generator(self, file_path: str) -> str:
        """
        构建IBC代码生成的用户提示词（role_ibc_gen）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Args:
            file_path: 当前处理的文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户原始需求
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 读取用户需求失败{Colors.ENDC}")
            return ""
        
        # 读取项目结构
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        try:
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                ibc_content = json.load(f)
            project_structure_json = json.dumps(ibc_content['proj_root'], indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取项目结构失败: {e}{Colors.ENDC}")
            return ""
        
        # 读取文件需求描述
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_req_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败: {e}{Colors.ENDC}")
            return ""
        
        # 构建可用符号文本
        try:
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                ibc_content = json.load(f)
            dependent_relation = ibc_content.get('dependent_relation', {})
            dependencies = dependent_relation.get(file_path, [])
            ibc_dir_name = self._get_ibc_directory_name()
            ibc_root_path = os.path.join(self.proj_work_dir, ibc_dir_name)
            available_symbols_text = self._build_available_symbols_text(dependencies, ibc_root_path)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 构建可用符号失败: {e}，继续生成{Colors.ENDC}")
            available_symbols_text = '暂无可用的依赖符号'
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.proj_data_dir, 'icp_implementation_plan.txt')
        implementation_plan_content = ""
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_content = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e}，将仅使用文件需求描述{Colors.ENDC}")
        
        # 提取各个部分的内容
        class_content = self._extract_section_content(file_req_content, 'class')
        func_content = self._extract_section_content(file_req_content, 'func')
        var_content = self._extract_section_content(file_req_content, 'var')
        others_content = self._extract_section_content(file_req_content, 'others')
        behavior_content = self._extract_section_content(file_req_content, 'behavior')
        import_content = self._extract_section_content(file_req_content, 'import')
        
        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'intent_code_behavior_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan_content)
        user_prompt = user_prompt.replace('PROJECT_STRUCTURE_PLACEHOLDER', project_structure_json)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CLASS_CONTENT_PLACEHOLDER', class_content if class_content else '无')
        user_prompt = user_prompt.replace('FUNC_CONTENT_PLACEHOLDER', func_content if func_content else '无')
        user_prompt = user_prompt.replace('VAR_CONTENT_PLACEHOLDER', var_content if var_content else '无')
        user_prompt = user_prompt.replace('OTHERS_CONTENT_PLACEHOLDER', others_content if others_content else '无')
        user_prompt = user_prompt.replace('BEHAVIOR_CONTENT_PLACEHOLDER', behavior_content if behavior_content else '无')
        user_prompt = user_prompt.replace('IMPORT_CONTENT_PLACEHOLDER', import_content if import_content else '无')
        user_prompt = user_prompt.replace('AVAILABLE_SYMBOLS_PLACEHOLDER', available_symbols_text)
        
        return user_prompt

    def _build_user_prompt_for_symbol_normalizer(self, file_path: str, symbols: Dict[str, SymbolNode], ibc_code: str) -> str:
        """
        构建符号规范化的用户提示词（role_symbol_normalizer）
        
        从配置文件中直接读取所需信息，无需外部参数传递。
        
        Args:
            file_path: 当前文件路径
            symbols: 当前符号字典
            ibc_code: 当前IBC代码
        
        Returns:
            str: 完整的用户提示词，失败时抛出RuntimeError
        """
        # 读取提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'symbol_normalizer_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            raise RuntimeError(f"读取符号规范化提示词失败: {e}")
        
        # 获取目标语言
        target_language = self._get_target_language()
        
        # 格式化符号列表
        symbols_text = self._format_symbols_for_prompt(symbols)
        
        # 填充占位符
        user_prompt = user_prompt_template.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
        user_prompt = user_prompt.replace('FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CONTEXT_INFO_PLACEHOLDER', ibc_code)
        user_prompt = user_prompt.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
        
        return user_prompt
    
    
    # ========== 辅助方法 ==========
    
    def _initialize_update_status(
        self,
        file_creation_order_list: List[str],
        staging_dir_path: str,
        ibc_root_path: str,
    ) -> Dict[str, bool]:
        """
        初始化更新状态字典
        
        遍历所有文件，检查以下条件判断是否需要重新生成：
        1. 需求文件的MD5是否与已保存的符号表中的MD5匹配
        2. 目标IBC文件是否存在
        3. 符号表文件是否存在
        
        满足以下任一条件则需要更新：
        - 需求文件的MD5发生变化
        - 需求文件不存在
        - IBC文件不存在
        - 符号表文件不存在
        
        Args:
            file_creation_order_list: 文件创建顺序列表
            staging_dir_path: staging目录路径
            ibc_root_path: IBC根目录路径
            
        Returns:
            Dict[str, bool]: 更新状态字典，key为文件路径，value为是否需要更新
        """
        update_status = {}
        ibc_data_manager = get_ibc_data_manager()
        
        for file_path in file_creation_order_list:
            # 计算当前需求文件的MD5
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            current_md5 = self._calculate_file_md5(req_file_path)
            
            # 检查需求文件是否存在
            if not current_md5:
                update_status[file_path] = True
                continue
            
            # 检查IBC文件是否存在
            ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
            if not os.path.exists(ibc_file_path):
                update_status[file_path] = True
                continue
            
            # 检查符号表文件是否存在
            symbol_table_file = os.path.join(ibc_root_path, f"{file_path}_symbols.json")
            if not os.path.exists(symbol_table_file):
                update_status[file_path] = True
                continue
            
            # 加载已保存的符号表
            file_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, file_path)
            
            # 判断MD5是否匹配
            if file_symbol_table.file_md5 != current_md5:
                update_status[file_path] = True
            else:
                update_status[file_path] = False
        
        return update_status
    
    def _check_dependency_updated(
        self,
        dependencies: List[str],
        update_status: Dict[str, bool]
    ) -> bool:
        """
        检查当前文件的依赖文件是否有更新
        
        Args:
            dependencies: 依赖文件列表
            update_status: 更新状态字典
            
        Returns:
            bool: 如果任一依赖文件需要更新，返回True
        """
        for dep_file in dependencies:
            if update_status.get(dep_file, False):
                return True
        return False
    
    def _calculate_file_md5(self, file_path: str) -> str:
        """计算文件的MD5校验值"""
        if not os.path.exists(file_path):
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 计算文件MD5失败 {file_path}: {e}{Colors.ENDC}")
            return ""
    
    def _normalize_symbols(
        self, 
        file_path: str, 
        file_symbol_table: FileSymbolTable,
        ibc_code: str
    ) -> Dict[str, Dict[str, str]]:
        """对符号进行规范化处理"""
        symbols = file_symbol_table.get_all_symbols()
        if not symbols:
            print(f"    {Colors.WARNING}警告: 未从符号表中提取到符号: {file_path}{Colors.ENDC}")
            return {}
        
        # 检查AI处理器
        if not self.chat_handler.has_role(self.role_symbol_normalizer):
            raise RuntimeError("符号规范化AI处理器未初始化，请检查配置文件")
        
        # 构建提示词
        user_prompt = self._build_normalize_prompt(file_path, symbols, ibc_code)
        
        # 调用AI进行规范化（带重试）
        for attempt in range(self.MAX_RETRY_COUNT):
            try:
                print(f"    正在调用AI进行符号规范化（尝试 {attempt + 1}/{self.MAX_RETRY_COUNT}）...")
                response_content, success = asyncio.run(self.chat_handler.get_role_response(
                    role_name=self.role_symbol_normalizer,
                    user_prompt=user_prompt
                ))
                
                if not success:
                    print(f"    {Colors.WARNING}警告: AI响应失败{Colors.ENDC}")
                    continue
                
                normalized_symbols = self._parse_symbol_normalizer_response(response_content)
                if normalized_symbols:
                    return normalized_symbols
                
                print(f"    {Colors.WARNING}警告: AI返回的符号规范化结果为空{Colors.ENDC}")
            except Exception as e:
                print(f"    {Colors.FAIL}错误: AI调用失败: {e}{Colors.ENDC}")
            
            if attempt < self.MAX_RETRY_COUNT - 1:
                print(f"    {Colors.OKBLUE}准备重试...{Colors.ENDC}")
        
        raise RuntimeError(f"符号规范化失败：AI未能返回有效结果（已重试{self.MAX_RETRY_COUNT}次）")
    
    def _build_normalize_prompt(self, file_path: str, symbols: Dict[str, SymbolNode], ibc_code: str) -> str:
        """构建符号规范化提示词"""
        return self._build_user_prompt_for_symbol_normalizer(file_path, symbols, ibc_code)

    def _get_target_language(self) -> str:
        """获取目标编程语言"""
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config_json = json.load(f)
            return icp_config_json.get('target_language', 'python')
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取配置文件失败: {e}，使用默认语言python{Colors.ENDC}")
            return 'python'
    
    def _format_symbols_for_prompt(self, symbols: Dict[str, SymbolNode]) -> str:
        """格式化符号列表用于提示词"""
        lines = []
        for symbol_name, symbol in symbols.items():
            symbol_type = symbol.symbol_type.value if symbol.symbol_type else '未知'
            description = symbol.description if symbol.description else '无描述'
            lines.append(f"- {symbol_name} ({symbol_type}, 描述: {description})")
        return '\n'.join(lines)
    
    def _parse_symbol_normalizer_response(self, response: str) -> Dict[str, Dict[str, str]]:
        """解析符号规范化AI的响应"""
        try:
            # 清理代码块标记
            cleaned_response = ICPChatHandler.clean_code_block_markers(response)
            
            # 解析JSON
            result = json.loads(cleaned_response)
            
            # 有效的可见性值列表
            valid_visibilities = [v.value for v in VisibilityTypes]
            
            # 验证结果格式
            validated_result = {}
            for symbol_name, symbol_data in result.items():
                if 'normalized_name' in symbol_data and 'visibility' in symbol_data:
                    # 验证normalized_name符合标识符规范
                    if self._validate_identifier(symbol_data['normalized_name']):
                        # 验证visibility是预定义值
                        if symbol_data['visibility'] in valid_visibilities:
                            validated_result[symbol_name] = symbol_data
                        else:
                            print(f"    {Colors.WARNING}警告: 符号 {symbol_name} 的可见性值无效: {symbol_data['visibility']}，使用默认值{Colors.ENDC}")
                            # 仍然保留该符号，但使用默认可见性
                            symbol_data['visibility'] = 'file_local'
                            validated_result[symbol_name] = symbol_data
                    else:
                        print(f"    {Colors.WARNING}警告: 符号 {symbol_name} 的规范化名称无效: {symbol_data['normalized_name']}{Colors.ENDC}")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"    {Colors.FAIL}错误: 解析AI响应JSON失败: {e}{Colors.ENDC}")
            return {}
        except Exception as e:
            print(f"    {Colors.FAIL}错误: 处理AI响应失败: {e}{Colors.ENDC}")
            return {}
    
    def _validate_identifier(self, identifier: str) -> bool:
        """验证标识符是否符合规范"""
        if not identifier:
            return False
        # 标识符必须以字母或下划线开头，仅包含字母、数字、下划线
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    

    # ========== 符号信息构建 ==========
    
    def _build_available_symbols_text(
        self, 
        dependencies: List[str], 
        ibc_root_path: str
    ) -> str:
        """
        构建可用符号的文本描述
        
        根据符号的可见性过滤：
        - PUBLIC: 对所有文件可见
        - GLOBAL: 对所有文件可见
        - PROTECTED: 仅对子类/友元可见（需要AI自行判断）
        - MODULE_LOCAL: 仅在定义文件内可见，不对外暴露
        - PRIVATE: 私有，不对外暴露
        
        Args:
            dependencies: 依赖文件列表
            ibc_root_path: IBC根目录路径
            
        Returns:
            str: 可用符号的文本描述
        """
        if not dependencies:
            return '暂无可用的依赖符号'

        ibc_data_manager = get_ibc_data_manager()
        lines = ['可用的已生成符号：', '']
        
        # 定义可对外可见的符号类型（使用枚举）
        # MODULE_LOCAL 和 PRIVATE 不对外暴露
        externally_visible_types = [
            VisibilityTypes.PUBLIC,
            VisibilityTypes.GLOBAL,
            VisibilityTypes.PROTECTED
        ]
        
        for dep_file in dependencies:
            # 加载依赖文件的符号表
            dep_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, dep_file)
            
            if not dep_symbol_table.symbols:
                # TODO: 不应该直接continue 虽然理论上来说不应该进入这里
                continue
            
            lines.append(f"来自文件：{dep_file}")
            
            has_visible_symbols = False
            for symbol_name, symbol in dep_symbol_table.symbols.items():
                # 检查符号可见性
                # 1. 如果未规范化，也列出来（供生成时参考）
                # 2. 如果已规范化，仅列出对外可见的符号
                is_visible = False
                
                if not symbol.visibility:
                    # TODO: 这里逻辑有问题，不应该出现未规范化的内容，以后来修
                    # 未规范化的符号，也列出
                    is_visible = True
                elif symbol.visibility in externally_visible_types:
                    # 已规范化且可见性符合要求
                    is_visible = True
                
                if is_visible:
                    # 处理symbol_type，避免None情况
                    if symbol.symbol_type:
                        symbol_type_label = {
                            SymbolType.CLASS: '类',
                            SymbolType.FUNCTION: '函数',
                            SymbolType.VARIABLE: '变量',
                            SymbolType.MODULE: '模块'
                        }.get(symbol.symbol_type, symbol.symbol_type.value)
                    else:
                        symbol_type_label = '未知'
                    
                    description = symbol.description if symbol.description else '无描述'
                    lines.append(f"- {symbol_type_label} {symbol_name}")
                    lines.append(f"  描述：{description}")
                    
                    if symbol.normalized_name:
                        lines.append(f"  规范化名称：{symbol.normalized_name}")
                    
                    # 显示可见性信息
                    if symbol.visibility:
                        visibility_label = {
                            VisibilityTypes.PUBLIC: '公开（所有文件可用）',
                            VisibilityTypes.GLOBAL: '全局（所有文件可用）',
                            VisibilityTypes.PROTECTED: '受保护（仅子类/友元可用）'
                        }.get(symbol.visibility, symbol.visibility.value)
                        lines.append(f"  可见性：{visibility_label}")
                    
                    lines.append('')
                    has_visible_symbols = True
            
            # 如果该依赖文件没有可见符号，移除文件标题
            if not has_visible_symbols:
                lines.pop()  # 移除添加的第一行 "来自文件："
        
        # 添加可见性规则说明
        if len(lines) > 2:
            lines.append('')
            lines.append('**符号可见性规则说明：**')
            lines.append('- 公开(public)/全局(global): 可以直接使用')
            lines.append('- 受保护(protected): 仅当当前文件是符号所在类的子类或友元时才能使用，否则不能使用')
            lines.append('- 模块局部(module_local): 仅在符号定义文件内可用，不对外暴露')
            lines.append('- 私有(private): 不对外暴露，不能使用')
            lines.append('')
            lines.append('请你在生成代码时严格遵守以上可见性规则，不要使用不符合可见性要求的符号。')
        
        return '\n'.join(lines) if len(lines) > 2 else '暂无可用的依赖符号'
    
    # ========== 修改的方法：AI处理器初始化 ==========
    
    def _init_ai_handlers(self):
        """初始化AI处理器"""
        icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')
        if not os.path.exists(icp_api_config_file):
            print(f"错误: 配置文件 {icp_api_config_file} 不存在")
            return
        
        try:
            with open(icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        # 初始化Chat处理器
        chat_config = self._get_chat_config(config)
        if chat_config and not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(chat_config)
        
        # 加载角色
        self._load_chat_roles()
        
        # 初始化Embedding处理器
        embedding_config = self._get_embedding_config(config)
        if embedding_config and not ICPEmbeddingHandler.is_initialized():
            ICPEmbeddingHandler.initialize_embedding_handler(embedding_config)
    
    def _get_chat_config(self, config: Dict[str, Any]) -> Optional[ChatApiConfig]:
        """获取Chat API配置"""
        chat_api_config = None
        if 'intent_behavior_code_gen_handler' in config:
            chat_api_config = config['intent_behavior_code_gen_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少intent_behavior_code_gen_handler或coder_handler配置")
            return None
        
        return ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
    
    def _load_chat_roles(self):
        """加载Chat角色"""
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        
        # 加载IBC生成角色
        sys_prompt_path_1 = os.path.join(prompt_dir, f"{self.role_ibc_gen}.md")
        self.chat_handler.load_role_from_file(self.role_ibc_gen, sys_prompt_path_1)
        
        # 加载符号规范化角色
        sys_prompt_path_2 = os.path.join(prompt_dir, f"{self.role_symbol_normalizer}.md")
        self.chat_handler.load_role_from_file(self.role_symbol_normalizer, sys_prompt_path_2)
    
    def _get_embedding_config(self, config: Dict[str, Any]) -> Optional[EmbeddingApiConfig]:
        """获取Embedding API配置"""
        embedding_api_config = None
        if 'embedding_handler' in config:
            embedding_api_config = config['embedding_handler']
        else:
            print("警告: 配置文件缺少embedding_handler配置，使用coder_handler配置")
            if 'coder_handler' in config:
                embedding_api_config = config['coder_handler']
            else:
                return None
        
        return EmbeddingApiConfig(
            base_url=embedding_api_config.get('api-url', ''),
            api_key=SecretStr(embedding_api_config.get('api-key', '')),
            model=embedding_api_config.get('model', '')
        )
