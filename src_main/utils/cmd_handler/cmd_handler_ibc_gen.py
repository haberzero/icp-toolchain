import sys, os
import asyncio
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors
from typedef.ibc_data_types import (
    IbcParserBaseState, AstNodeType, ClassNode, FunctionNode, VariableNode, 
    VisibilityTypes, SymbolType, FileSymbolTable, SymbolNode
)

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager
from data_exchange.ibc_data_manager import get_instance as get_ibc_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from libs.ai_interface.chat_interface import ChatInterface
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code, IbcAnalyzerError
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator
from libs.dir_json_funcs import DirJsonFuncs


class CmdHandlerIbcGen(BaseCmdHandler):
    """将单文件需求描述转换为半自然语言行为描述代码"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="intent_behavior_code_gen",
            aliases=["IBC"],
            description="将单文件需求描述转换为半自然语言行为描述代码",
            help_text="根据单文件需求描述生成符合半自然语言行为描述语法的代码结构",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.proj_data_dir
        self.role_name_1 = "8_intent_behavior_code_gen"
        self.role_name_2 = "8_symbol_normalizer"
        
        # 初始化AI处理器
        ai_handler_1 = self._init_ai_handler_1()
        ai_handler_2 = self._init_ai_handler_2()
        if ai_handler_1 is not None:
            self.ai_handler_1 = ai_handler_1
            self.ai_handler_1.init_chat_chain()
        if ai_handler_2 is not None:
            self.ai_handler_2 = ai_handler_2
            self.ai_handler_2.init_chat_chain()

    def execute(self):
        """执行半自然语言行为描述代码生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成半自然语言行为描述代码...{Colors.ENDC}")

        # 读取IBC目录结构
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        try:
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                ibc_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取IBC目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not ibc_content:
            print(f"  {Colors.FAIL}错误: IBC目录结构内容为空{Colors.ENDC}")
            return

        # 检查是否包含必要的节点
        if "proj_root" not in ibc_content or "dependent_relation" not in ibc_content:
            print(f"  {Colors.FAIL}错误: IBC目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return

        # 从dependent_relation中获取文件创建顺序
        proj_root = ibc_content["proj_root"]
        dependent_relation = ibc_content["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 目录预处理
        staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        ibc_dir_name = self._get_ibc_directory_name()
        ibc_root_path = os.path.join(self.proj_work_dir, ibc_dir_name)
        
        # 检查src_staging目录是否存在
        if not os.path.exists(staging_dir_path):
            print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令创建目录结构{Colors.ENDC}")
            return
        
        # 确保IBC根目录存在
        os.makedirs(ibc_root_path, exist_ok=True)
        
        # 读取用户原始需求文本
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 检查用户原始需求是否存在
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return

        
        # 将proj_root_content转换为JSON格式的项目结构字符串
        project_structure_json = json.dumps(proj_root, indent=2, ensure_ascii=False)
        
        # 初始化更新状态跟踪字典：记录每个文件是否需要更新
        update_status = self._initialize_update_status(
            file_creation_order_list,
            staging_dir_path,
            ibc_root_path
        )
        
        # 按照依赖顺序为每个文件生成半自然语言行为描述代码
        for file_path in file_creation_order_list:
            print(f"  {Colors.OKBLUE}正在处理文件: {file_path}{Colors.ENDC}")
            
            # 获取当前文件的依赖文件列表
            current_file_dependencies = dependent_relation.get(file_path, [])
            
            # 检查依赖文件是否有更新，如果有则当前文件也需要更新
            if self._check_dependency_updated(current_file_dependencies, update_status):
                update_status[file_path] = True
                print(f"    {Colors.OKBLUE}检测到依赖文件已更新，当前文件需要重新生成{Colors.ENDC}")
            
            # 如果文件不需要更新，跳过该文件
            if not update_status.get(file_path, True):
                print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过生成: {file_path}{Colors.ENDC}")
                continue
            
            # 从src_staging目录读取文件需求描述
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_req_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 构建可用符号文本（从依赖的文件中提取）
            available_symbols_text = self._build_available_symbols_text(
                current_file_dependencies, 
                ibc_root_path
            )
            
            # 生成IBC代码
            print(f"    正在生成IBC代码...")
            ibc_code = self._generate_ibc_code(
                file_path,
                file_req_content,
                user_requirements,
                project_structure_json,
                available_symbols_text
            )
            
            if not ibc_code:
                print(f"  {Colors.WARNING}警告: 未能为文件生成IBC代码: {file_path}{Colors.ENDC}")
                continue
            
            # 保存IBC代码到文件
            ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
            self._save_ibc_code(ibc_file_path, ibc_code)
            
            # 解析IBC代码生成AST
            print(f"    正在分析IBC代码生成AST...")
            try:
                ast_dict, symbol_table = analyze_ibc_code(ibc_code)
            except IbcAnalyzerError as e:
                print(f"  {Colors.FAIL}错误: IBC代码分析失败 {file_path}: {e}{Colors.ENDC}")
                continue
            
            # 对符号进行规范化处理
            print(f"    正在进行符号规范化...")
            try:
                normalized_symbols_dict = self._normalize_symbols(
                    file_path,
                    symbol_table
                )
            except RuntimeError as e:
                print(f"  {Colors.FAIL}错误: 符号规范化失败 {file_path}: {e}{Colors.ENDC}")
                print(f"  {Colors.WARNING}请检查AI连接配置并重新运行命令{Colors.ENDC}")
                continue
            
            # 更新符号表中的规范化信息
            for symbol_name, norm_info in normalized_symbols_dict.items():
                symbol = symbol_table.get_symbol(symbol_name)
                if symbol:
                    symbol.update_normalized_info(
                        norm_info['normalized_name'],
                        norm_info['visibility']
                    )

            # 保存当前需求文件的MD5
            current_md5 = self._calculate_file_md5(req_file_path)
            symbol_table.file_md5 = current_md5
            
            # 保存符号表
            print(f"    正在保存符号表...")
            ibc_data_manager = get_ibc_data_manager()
            success = ibc_data_manager.save_file_symbols(
                ibc_root_path,
                file_path,
                symbol_table
            )
            
            if success:
                print(f"  {Colors.OKGREEN}文件处理完成: {file_path}{Colors.ENDC}")
            else:
                print(f"  {Colors.WARNING}警告: 符号表保存失败: {file_path}{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}半自然语言行为描述代码生成完毕!{Colors.ENDC}")


    def _get_ibc_directory_name(self) -> str:
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

    def _generate_ibc_code(
        self, 
        file_path: str, 
        file_req_content: str,
        user_requirements: str,
        project_structure_json: str,
        available_symbols_text: str
    ) -> str:
        """
        生成IBC代码
        
        Args:
            file_path: 文件路径
            file_req_content: 文件需求内容
            user_requirements: 用户原始需求
            project_structure_json: 项目结构JSON
            available_symbols_text: 可用符号文本
            
        Returns:
            str: 生成的IBC代码
        """
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
        
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'intent_code_behavior_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
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

        # 保存用户提示词到ibc_gen_temp目录
        self._save_user_prompt_to_temp(file_path, user_prompt, 'ibc_gen_prompt.txt')

        # 调用AI生成半自然语言行为描述代码
        response_content = asyncio.run(self._get_ai_response(self.ai_handler_1, user_prompt))
        
        # 移除可能的代码块标记
        lines = response_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()
        
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
        return hasattr(self, 'ai_handler_1') and self.ai_handler_1 is not None
    
    async def _get_ai_response(self, handler: ChatInterface, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        # 获取handler的role_name
        role_name = handler.role_name if hasattr(handler, 'role_name') else 'AI'
        print(f"    {role_name}正在生成响应...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n    {role_name}运行完毕。")
        return response_content
    
    # ========== 辅助方法 ==========
    
    def _initialize_update_status(
        self,
        file_creation_order_list: List[str],
        staging_dir_path: str,
        ibc_root_path: str,
    ) -> Dict[str, bool]:
        """
        初始化更新状态字典
        
        遍历所有文件，检查每个文件的MD5是否与已保存的符号表中的MD5匹配。
        如果不匹配，则标记为需要更新。
        
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
            # 加载已保存的符号表
            file_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, file_path)
            
            # 计算当前需求文件的MD5
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            current_md5 = self._calculate_file_md5(req_file_path)
            
            # 判断是否需要更新：MD5不匹配或文件不存在
            needs_update = (file_symbol_table.file_md5 != current_md5) or not current_md5
            update_status[file_path] = needs_update
        
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
        file_symbol_table: FileSymbolTable
    ) -> Dict[str, Dict[str, str]]:
        """
        对符号进行规范化处理
        
        Args:
            file_path: 文件路径
            file_symbol_table: 文件符号表
            
        Returns:
            Dict[str, Dict[str, str]]: 规范化后的符号信息字典
            
        Raises:
            RuntimeError: 当AI处理器未初始化或调用失败时抛出异常
        """
        symbols = file_symbol_table.get_all_symbols()
        
        if not symbols:
            print(f"    {Colors.WARNING}警告: 未从符号表中提取到符号: {file_path}{Colors.ENDC}")
            return {}
        
        # 检查AI处理器2是否初始化
        if not hasattr(self, 'ai_handler_2') or self.ai_handler_2 is None:
            error_msg = f"符号规范化AI处理器未初始化，请检查配置文件并重新初始化AI处理器"
            print(f"    {Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            raise RuntimeError(error_msg)
        
        # 构建符号列表文本
        symbols_text = self._format_symbols_for_prompt(symbols)
        
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'symbol_normalizer_user.md')
        
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            error_msg = f"读取符号规范化提示词失败: {e}"
            print(f"    {Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            raise RuntimeError(error_msg)

        # 获取目标编程语言
        icp_config_file = os.path.join(self.proj_config_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config_json = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return None
        target_language = icp_config_json.get('target_language', 'python')
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
        user_prompt = user_prompt.replace('FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CONTEXT_INFO_PLACEHOLDER', f"文件路径: {file_path}")
        user_prompt = user_prompt.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
        
        # 保存用户提示词到ibc_gen_temp目录
        self._save_user_prompt_to_temp(file_path, user_prompt, 'symbol_normalizer_prompt.txt')
        
        # 调用AI，支持重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"    正在调用AI进行符号规范化（尝试 {attempt + 1}/{max_retries}）...")
                response_content = asyncio.run(self._get_ai_response(self.ai_handler_2, user_prompt))
                
                # 解析JSON响应
                normalized_symbols = self._parse_symbol_normalizer_response(response_content)
                
                if normalized_symbols:
                    return normalized_symbols
                else:
                    print(f"    {Colors.WARNING}警告: AI返回的符号规范化结果为空{Colors.ENDC}")
                    if attempt < max_retries - 1:
                        print(f"    {Colors.OKBLUE}准备重试...{Colors.ENDC}")
                        continue
            except Exception as e:
                print(f"    {Colors.FAIL}错误: AI调用失败: {e}{Colors.ENDC}")
                if attempt < max_retries - 1:
                    print(f"    {Colors.OKBLUE}准备重试...{Colors.ENDC}")
                    continue
                else:
                    raise RuntimeError(f"符号规范化AI调用失败（已重试{max_retries}次）: {e}")
        
        # 所有重试都失败
        error_msg = f"符号规范化失败：AI未能返回有效结果（已重试{max_retries}次），请检查AI连接或提示词配置"
        print(f"    {Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
        raise RuntimeError(error_msg)
    
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
            # 移除可能的代码块标记
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
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
    
    def _save_user_prompt_to_temp(
        self,
        file_path: str,
        user_prompt: str,
        prompt_filename: str
    ) -> None:
        """
        保存用户提示词到ibc_gen_temp目录
        
        Args:
            file_path: 文件相对路径（如 "src/main.py"）
            user_prompt: 用户提示词内容
            prompt_filename: 提示词文件名（如 "ibc_gen_prompt.txt"）
        """
        try:
            # 构建 ibc_gen_temp 目录路径
            temp_dir = os.path.join(self.proj_work_dir, 'ibc_gen_temp')
            
            # 获取文件所在目录
            file_dir = os.path.dirname(file_path)
            if file_dir:
                prompt_dir = os.path.join(temp_dir, file_dir)
            else:
                prompt_dir = temp_dir
            
            # 确保目录存在
            os.makedirs(prompt_dir, exist_ok=True)
            
            # 构建完整的提示词文件路径
            prompt_file_path = os.path.join(prompt_dir, f"{os.path.basename(file_path)}_{prompt_filename}")
            
            # 写入文件
            with open(prompt_file_path, 'w', encoding='utf-8') as f:
                f.write(user_prompt)
            
            print(f"    {Colors.OKGREEN}用户提示词已保存: {prompt_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 保存用户提示词失败: {e}{Colors.ENDC}")
    
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
                continue
            
            lines.append(f"来自文件：{dep_file}")
            
            has_visible_symbols = False
            for symbol_name, symbol in dep_symbol_table.symbols.items():
                # 检查符号可见性
                # 1. 如果未规范化，也列出来（供生成时参考）
                # 2. 如果已规范化，仅列出对外可见的符号
                is_visible = False
                
                if not symbol.visibility:
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
    
    def _init_ai_handler_1(self) -> Optional[ChatInterface]:
        """初始化AI处理器1（IBC代码生成）"""
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在")
            return None
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return None
        
        if 'intent_behavior_code_gen_handler' in config:
            chat_api_config = config['intent_behavior_code_gen_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少intent_behavior_code_gen_handler或coder_handler配置")
            return None
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, f"{self.role_name_1}.md")
        
        return ChatInterface(handler_config, self.role_name_1, sys_prompt_path)
    
    def _init_ai_handler_2(self) -> Optional[ChatInterface]:
        """初始化AI处理器2（符号规范化）"""
        if not os.path.exists(self.icp_api_config_file):
            return None
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            return None
        
        # 优先查找symbol_normalizer_handler配置
        if 'symbol_normalizer_handler' in config:
            chat_api_config = config['symbol_normalizer_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            return None
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )
        
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, f"{self.role_name_2}.md")
        
        return ChatInterface(handler_config, self.role_name_2, sys_prompt_path)
