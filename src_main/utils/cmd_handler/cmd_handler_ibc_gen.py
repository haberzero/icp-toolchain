import sys, os
import asyncio
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors
from typedef.ibc_data_types import AstNode, AstNodeType, ClassNode, FunctionNode, VariableNode, VisibilityTypes

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager
from data_exchange.ast_data_manager import get_instance as get_ast_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.ai_handler.chat_handler import ChatHandler
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code, IbcAnalyzerError
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
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')

        self.checksums_file = os.path.join(self.icp_proj_data_dir, 'file_checksums.json') # 临时，后续应该仔细修改处理
        self.ibc_build_dir = os.path.join(self.icp_proj_data_dir, 'ibc_build')
        
        self.proj_data_dir = self.icp_proj_data_dir
        self.ai_handler: ChatHandler
        self.role_name_1 = "8_intent_behavior_code_gen"
        self.role_name_2 = "8_symbol_normalizer"
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
        
        # 获取IBC目录名称
        ibc_dir_name = self._get_ibc_directory_name()
        
        # 构建IBC目录路径
        ibc_root_path = os.path.join(self.work_dir, ibc_dir_name)
        
        # 构建src_staging目录路径
        staging_dir_path = os.path.join(self.work_dir, 'src_staging')
        
        # 检查src_staging目录是否存在
        if not os.path.exists(staging_dir_path):
            print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令创建目录结构{Colors.ENDC}")
            return
        
        # 为每个单文件生成半自然语言行为描述代码
        """为每个文件生成半自然语言行为描述代码"""
        # 读取用户原始需求文本
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 检查用户原始需求是否存在
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return

        # 初始化累积描述字典，用于为后续文件生成提供上下文
        accumulated_descriptions_dict = {}
        
        # 初始化符号累积字典，用于为后续文件提供结构化的符号信息
        accumulated_symbols_dict = {}
        
        # 加载文件校验值记录
        checksums = self._load_file_checksums()
        
        # 加载已有的符号表
        symbols_table = self._load_symbols_table(ibc_root_path)
        
        # 按照依赖顺序为每个文件生成半自然语言行为描述代码
        for file_path in file_creation_order_list:
            # 从src_staging目录读取文件需求描述
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_req_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 为每个文件生成半自然语言行为描述代码
            print(f"  {Colors.OKBLUE}正在为文件生成半自然语言行为描述代码: {file_path}{Colors.ENDC}")
            
            # 当前文件所依赖的文件内容，用于提供上下文信息
            available_file_desc_dict = {}
            current_file_dependencies = dependent_relation.get(file_path, [])
            for file_key, file_description in accumulated_descriptions_dict.items():
                if file_key in current_file_dependencies:
                    available_file_desc_dict[file_key] = file_description
            
        #     # 为当前文件构建可用的依赖符号列表
        #     available_symbols_text = self._build_available_symbols_text(
        #         file_path, 
        #         current_file_dependencies, 
        #         accumulated_symbols_dict
        #     )
            
        #     # 生成新的半自然语言行为描述代码
        #     intent_behavior_code = self._ibc_generator_response(
        #         file_path,
        #         file_req_content,
        #         user_requirements,
        #         list(available_file_desc_dict.values()),
        #         proj_root_content,
        #         available_symbols_text
        #     )

        #     # 移除可能的代码块标记
        #     lines = intent_behavior_code.split('\n')
        #     if lines and lines[0].strip().startswith('```'):
        #         lines = lines[1:]
        #     if lines and lines[-1].strip().startswith('```'):
        #         lines = lines[:-1]
        #     cleaned_content = '\n'.join(lines).strip()
            
        #     if not cleaned_content:
        #         print(f"  {Colors.WARNING}警告: 未能为文件生成半自然语言行为描述代码: {file_path}{Colors.ENDC}")
        #         continue
            
        #     # 保存半自然语言行为描述代码到IBC目录下的文件
        #     self._save_intent_behavior_code(ibc_root_path, file_path, cleaned_content)
            
        #     # 计算文件校验值
        #     ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
        #     new_checksum = self._calculate_file_checksum(ibc_file_path)
            
        #     # 检查是否需要重新处理
        #     need_reprocess = True
        #     if file_path in checksums:
        #         old_checksum = checksums[file_path].get('checksum', '')
        #         if old_checksum == new_checksum:
        #             need_reprocess = False
        #             print(f"  {Colors.WARNING}文件校验值一致，跳过符号规范化处理: {file_path}{Colors.ENDC}")
            
        #     # 构建 AST
        #     ast_dict = self._build_and_save_ast(ibc_file_path, file_path)
        #     if ast_dict is None:
        #         # AST构建失败，跳过符号规范化，但继续处理下一个文件
        #         accumulated_descriptions_dict[file_path] = f"文件 {file_path} 的接口描述:\n{file_req_content}"
        #         continue
            
        #     # 符号规范化处理
        #     file_symbols = {}
        #     if need_reprocess:
        #         file_symbols = self._process_symbol_normalization(
        #             file_path, 
        #             ast_dict
        #         )
                
        #         # 更新符号表
        #         if file_symbols:
        #             symbols_table[file_path] = file_symbols
        #             self._save_symbols_table(ibc_root_path, symbols_table)
                
        #         # 更新文件校验值
        #         checksums[file_path] = {
        #             'checksum': new_checksum,
        #             'last_modified': datetime.now().isoformat()
        #         }
        #         self._save_file_checksums(checksums)
        #     else:
        #         # 使用已有的符号表
        #         file_symbols = symbols_table.get(file_path, {})
            
        #     # 将当前文件的描述添加到累积字典中，供后续文件参考
        #     accumulated_descriptions_dict[file_path] = f"文件 {file_path} 的接口描述:\n{file_req_content}"
            
        #     # 将符号信息添加到累积符号字典
        #     if file_symbols:
        #         accumulated_symbols_dict[file_path] = {
        #             'symbols': self._extract_visible_symbols(file_symbols)
        #         }
        
        # print(f"{Colors.OKGREEN}半自然语言行为描述代码生成命令执行完毕!{Colors.ENDC}")

    def _get_ibc_directory_name(self) -> str:
        """获取IBC目录名称，优先从配置文件读取behavioral_layer_dir，失败则使用默认值"""
        icp_config_file = os.path.join(self.icp_proj_data_dir, 'icp_config.json')
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

    def _ibc_generator_response(
        self, 
        file_path: str, 
        file_req_content: str,
        user_requirements: str,
        available_descriptions: List[str],
        proj_root_content: Dict,
        available_symbols_text: str
    ) -> str:
        """创建新的半自然语言行为描述代码"""
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'intent_behavior_code_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 提取各个部分的内容
        class_content = self._extract_section_content(file_req_content, 'class')
        func_content = self._extract_section_content(file_req_content, 'func')
        var_content = self._extract_section_content(file_req_content, 'var')
        others_content = self._extract_section_content(file_req_content, 'others')
        behavior_content = self._extract_section_content(file_req_content, 'behavior')
        import_content = self._extract_section_content(file_req_content, 'import')
        
        # 将proj_root_content转换为JSON格式的项目结构字符串
        project_structure_json = json.dumps(proj_root_content, indent=2, ensure_ascii=False)
        
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements)
        user_prompt = user_prompt.replace('PROJECT_STRUCTURE_PLACEHOLDER', project_structure_json)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CLASS_CONTENT_PLACEHOLDER', class_content if class_content else '无')
        user_prompt = user_prompt.replace('FUNC_CONTENT_PLACEHOLDER', func_content if func_content else '无')
        user_prompt = user_prompt.replace('VAR_CONTENT_PLACEHOLDER', var_content if var_content else '无')
        user_prompt = user_prompt.replace('OTHERS_CONTENT_PLACEHOLDER', others_content if others_content else '无')
        user_prompt = user_prompt.replace('BEHAVIOR_CONTENT_PLACEHOLDER', behavior_content if behavior_content else '无')
        user_prompt = user_prompt.replace('IMPORT_CONTENT_PLACEHOLDER', import_content if import_content else '无')
        user_prompt = user_prompt.replace('EXISTING_FILE_DESCRIPTIONS_PLACEHOLDER', 
                                        '\n\n'.join(available_descriptions) if available_descriptions else '暂无已生成的文件需求描述')
        user_prompt = user_prompt.replace('AVAILABLE_SYMBOLS_PLACEHOLDER', available_symbols_text)

        # 调用AI生成半自然语言行为描述代码
        response_content = asyncio.run(self._get_ai_response(self.ai_handler_1, user_prompt))
        return response_content

    def _save_intent_behavior_code(self, ibc_root_path: str, file_path: str, content: str):
        """保存半自然语言行为描述代码到文件"""
        behavior_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(behavior_file_path), exist_ok=True)
            with open(behavior_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  {Colors.OKGREEN}半自然语言行为描述代码已保存: {behavior_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存半自然语言行为描述代码失败 {behavior_file_path}: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查IBC目录结构文件是否存在
        ibc_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        if not os.path.exists(ibc_dir_file):
            print(f"  {Colors.WARNING}警告: IBC目录结构文件不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        return hasattr(self, 'ai_handler_1') and self.ai_handler_1 is not None
    
    async def _get_ai_response(self, handler: ChatHandler, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        # 获取handler的role_name
        role_name = handler.role_name if hasattr(handler, 'role_name') else 'AI'
        print(f"{role_name}正在生成响应...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{role_name}运行完毕。")
        return response_content
    
    # ========== 新增方法：文件校验值管理 ==========
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """计算文件的SHA256校验值"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 计算文件校验值失败 {file_path}: {e}{Colors.ENDC}")
            return ""
    
    def _load_file_checksums(self) -> Dict[str, Dict[str, str]]:
        """加载文件校验值记录"""
        if not os.path.exists(self.checksums_file):
            return {}
        
        try:
            with open(self.checksums_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取校验值文件失败: {e}{Colors.ENDC}")
            return {}
    
    def _save_file_checksums(self, checksums: Dict[str, Dict[str, str]]) -> None:
        """保存文件校验值记录"""
        try:
            os.makedirs(os.path.dirname(self.checksums_file), exist_ok=True)
            with open(self.checksums_file, 'w', encoding='utf-8') as f:
                json.dump(checksums, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 保存校验值文件失败: {e}{Colors.ENDC}")
    
    # ========== 新增方法：AST构建与存储 ==========
    
    def _build_and_save_ast(self, ibc_file_path: str, file_path: str) -> Optional[Dict[int, AstNode]]:
        """构建并保存AST"""
        try:
            # 读取IBC文件内容
            with open(ibc_file_path, 'r', encoding='utf-8') as f:
                ibc_content = f.read()
            
            # 调用ibc_analyzer进行语法分析
            print(f"  {Colors.OKBLUE}正在构建AST: {file_path}{Colors.ENDC}")
            ast_dict = analyze_ibc_code(ibc_content)
            
            # 保存AST到文件
            ast_file_path = os.path.join(self.ibc_build_dir, f"{file_path}.ibc_ast.json")
            os.makedirs(os.path.dirname(ast_file_path), exist_ok=True)
            
            ast_data_manager = get_ast_data_manager()
            if ast_data_manager.save_ast_to_file(ast_dict, ast_file_path):
                print(f"  {Colors.OKGREEN}AST已保存: {ast_file_path}{Colors.ENDC}")
            else:
                print(f"  {Colors.WARNING}警告: AST保存失败{Colors.ENDC}")
            
            return ast_dict
            
        except IbcAnalyzerError as e:
            print(f"  {Colors.FAIL}错误: IBC语法分析失败 {file_path}: {e}{Colors.ENDC}")
            return None
        except Exception as e:
            print(f"  {Colors.FAIL}错误: AST构建失败 {file_path}: {e}{Colors.ENDC}")
            return None
    
    # ========== 新增方法：符号规范化处理 ==========
    
    def _process_symbol_normalization(self, file_path: str, ast_dict: Dict[int, AstNode]) -> Dict[str, Dict[str, Any]]:
        """处理符号规范化"""
        # 从AST中提取符号
        symbols_info = self._extract_symbols_from_ast(ast_dict)
        
        if not symbols_info:
            print(f"  {Colors.WARNING}警告: 未从AST中提取到符号: {file_path}{Colors.ENDC}")
            return {}
        
        # 检查AI处理器2是否初始化
        if self.ai_handler_2 is None:
            print(f"  {Colors.WARNING}警告: 符号规范化AI处理器未初始化，使用默认命名策略{Colors.ENDC}")
            return self._default_symbol_normalization(symbols_info)
        
        # 调用AI进行符号规范化
        print(f"  {Colors.OKBLUE}正在进行符号规范化: {file_path}{Colors.ENDC}")
        normalized_symbols = self._call_symbol_normalizer_ai(file_path, symbols_info)
        
        if not normalized_symbols:
            print(f"  {Colors.WARNING}警告: AI符号规范化失败，使用默认命名策略{Colors.ENDC}")
            return self._default_symbol_normalization(symbols_info)
        
        # 合并符号信息和规范化结果
        result = {}
        for symbol_name, symbol_info in symbols_info.items():
            if symbol_name in normalized_symbols:
                result[symbol_name] = {
                    'normalized_name': normalized_symbols[symbol_name]['normalized_name'],
                    'visibility': normalized_symbols[symbol_name]['visibility'],
                    'description': symbol_info['description'],
                    'symbol_type': symbol_info['symbol_type']
                }
            else:
                # 使用默认策略处理缺失的符号
                default_result = self._default_symbol_normalization({symbol_name: symbol_info})
                if symbol_name in default_result:
                    result[symbol_name] = default_result[symbol_name]
        
        print(f"  {Colors.OKGREEN}符号规范化完成，共处理 {len(result)} 个符号{Colors.ENDC}")
        return result
    
    def _extract_symbols_from_ast(self, ast_dict: Dict[int, AstNode]) -> Dict[str, Dict[str, str]]:
        """从AST中提取符号信息"""
        symbols = {}
        
        for uid, node in ast_dict.items():
            if isinstance(node, ClassNode):
                symbols[node.identifier] = {
                    'symbol_type': 'class',
                    'description': node.external_desc
                }
            elif isinstance(node, FunctionNode):
                symbols[node.identifier] = {
                    'symbol_type': 'func',
                    'description': node.external_desc
                }
            elif isinstance(node, VariableNode):
                symbols[node.identifier] = {
                    'symbol_type': 'var',
                    'description': node.external_desc
                }
        
        return symbols
    
    def _call_symbol_normalizer_ai(self, file_path: str, symbols_info: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """调用AI进行符号规范化"""
        try:
            # 构建用户提示词
            app_data_manager = get_app_data_manager()
            user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'symbol_normalizer_user.md')
            
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
            
            # 构建符号列表文本
            symbols_text = self._format_symbols_for_prompt(symbols_info)
            
            # 填充占位符
            user_prompt = user_prompt_template
            user_prompt = user_prompt.replace('FILE_PATH_PLACEHOLDER', file_path)
            user_prompt = user_prompt.replace('CONTEXT_INFO_PLACEHOLDER', f"文件路径: {file_path}")
            user_prompt = user_prompt.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
            
            # 调用AI
            response_content = asyncio.run(self._get_ai_response(self.ai_handler_2, user_prompt))
            
            # 解析JSON响应
            return self._parse_symbol_normalizer_response(response_content)
            
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 调用符号规范化AI失败: {e}{Colors.ENDC}")
            return {}
    
    def _format_symbols_for_prompt(self, symbols_info: Dict[str, Dict[str, str]]) -> str:
        """格式化符号列表用于提示词"""
        lines = []
        for symbol_name, info in symbols_info.items():
            symbol_type = info['symbol_type']
            description = info['description'] if info['description'] else '无描述'
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
            
            # 验证结果格式
            validated_result = {}
            for symbol_name, symbol_data in result.items():
                if 'normalized_name' in symbol_data and 'visibility' in symbol_data:
                    # 验证normalized_name符合标识符规范
                    if self._validate_identifier(symbol_data['normalized_name']):
                        # 验证visibility是预定义值
                        if symbol_data['visibility'] in VisibilityTypes:
                            validated_result[symbol_name] = symbol_data
                        else:
                            print(f"  {Colors.WARNING}警告: 符号 {symbol_name} 的可见性值无效: {symbol_data['visibility']}{Colors.ENDC}")
                    else:
                        print(f"  {Colors.WARNING}警告: 符号 {symbol_name} 的规范化名称无效: {symbol_data['normalized_name']}{Colors.ENDC}")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 解析AI响应JSON失败: {e}{Colors.ENDC}")
            return {}
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 处理AI响应失败: {e}{Colors.ENDC}")
            return {}
    
    def _validate_identifier(self, identifier: str) -> bool:
        """验证标识符是否符合规范"""
        if not identifier:
            return False
        # 标识符必须以字母或下划线开头，仅包含字母、数字、下划线
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    
    def _default_symbol_normalization(self, symbols_info: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """默认的符号规范化策略"""
        result = {}
        for symbol_name, info in symbols_info.items():
            # 简单的默认策略：将中文转换为拼音或使用占位符
            # 这里使用简单的策略，实际可以集成拼音库
            normalized_name = self._simple_normalize(symbol_name, info['symbol_type'])
            
            # 根据类型推断默认可见性
            default_visibility = 'file_local'
            if info['symbol_type'] == 'class':
                default_visibility = 'public'
            
            result[symbol_name] = {
                'normalized_name': normalized_name,
                'visibility': default_visibility,
                'description': info['description'],
                'symbol_type': info['symbol_type']
            }
        
        return result
    
    def _simple_normalize(self, symbol_name: str, symbol_type: str) -> str:
        """简单的符号名称规范化"""
        # 移除空格和特殊字符，保留字母数字
        cleaned = ''.join(c for c in symbol_name if c.isalnum() or c == '_')
        
        if not cleaned:
            # 如果清理后为空，使用类型作为前缀
            cleaned = f"{symbol_type}_symbol"
        
        # 确保以字母开头
        if cleaned and not cleaned[0].isalpha():
            cleaned = f"{symbol_type}_{cleaned}"
        
        return cleaned if cleaned else 'unnamed_symbol'
    
    # ========== 新增方法：符号表管理 ==========
    
    def _load_symbols_table(self, ibc_root_path: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """加载符号表"""
        symbols_file = os.path.join(ibc_root_path, 'symbols.json')
        if not os.path.exists(symbols_file):
            return {}
        
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取符号表失败: {e}{Colors.ENDC}")
            return {}
    
    def _save_symbols_table(self, ibc_root_path: str, symbols_table: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """保存符号表"""
        symbols_file = os.path.join(ibc_root_path, 'symbols.json')
        try:
            os.makedirs(os.path.dirname(symbols_file), exist_ok=True)
            with open(symbols_file, 'w', encoding='utf-8') as f:
                json.dump(symbols_table, f, ensure_ascii=False, indent=2)
            print(f"  {Colors.OKGREEN}符号表已更新: {symbols_file}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存符号表失败: {e}{Colors.ENDC}")
    
    # ========== 新增方法：符号上下文构建 ==========
    
    def _extract_visible_symbols(self, file_symbols: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取对外可见的符号"""
        visible_symbols = []
        visible_types = ['public', 'global', 'module_local', 'protected']
        
        for symbol_name, symbol_data in file_symbols.items():
            if symbol_data.get('visibility') in visible_types:
                visible_symbols.append({
                    'original_name': symbol_name,
                    'normalized_name': symbol_data.get('normalized_name', ''),
                    'description': symbol_data.get('description', ''),
                    'visibility': symbol_data.get('visibility', ''),
                    'symbol_type': symbol_data.get('symbol_type', '')
                })
        
        return visible_symbols
    
    def _build_available_symbols_text(self, current_file: str, dependencies: List[str], accumulated_symbols: Dict[str, Dict]) -> str:
        """构建可用符号的文本描述"""
        if not dependencies:
            return '暂无可用的依赖符号'
        
        lines = ['可用的依赖符号：', '']
        
        for dep_file in dependencies:
            if dep_file not in accumulated_symbols:
                continue
            
            symbols = accumulated_symbols[dep_file].get('symbols', [])
            if not symbols:
                continue
            
            lines.append(f"来自文件：{dep_file}")
            
            for symbol in symbols:
                symbol_type = symbol.get('symbol_type', '')
                original_name = symbol.get('original_name', '')
                normalized_name = symbol.get('normalized_name', '')
                description = symbol.get('description', '无描述')
                
                type_label = {'class': '类', 'func': '函数', 'var': '变量'}.get(symbol_type, symbol_type)
                lines.append(f"- {type_label} {original_name} ({normalized_name})")
                lines.append(f"  描述：{description}")
                lines.append('')
        
        return '\n'.join(lines) if len(lines) > 2 else '暂无可用的依赖符号'
    
    # ========== 修改的方法：AI处理器初始化 ==========
    
    def _init_ai_handler_1(self) -> Optional[ChatHandler]:
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
        
        return ChatHandler(handler_config, self.role_name_1, sys_prompt_path)
    
    def _init_ai_handler_2(self) -> Optional[ChatHandler]:
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
        
        return ChatHandler(handler_config, self.role_name_2, sys_prompt_path)
