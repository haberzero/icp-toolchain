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
    AstNode, AstNodeType, ClassNode, FunctionNode, VariableNode, 
    VisibilityTypes, FileSymbolTable, SymbolNode
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
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.icp_proj_data_dir
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
        staging_dir_path = os.path.join(self.work_dir, 'src_staging')
        ibc_dir_name = self._get_ibc_directory_name()
        ibc_root_path = os.path.join(self.work_dir, ibc_dir_name)
        
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
        
        # 初始化数据管理器
        ibc_data_manager = get_ibc_data_manager()
        
        # 将proj_root_content转换为JSON格式的项目结构字符串
        project_structure_json = json.dumps(proj_root, indent=2, ensure_ascii=False)
        
        # 按照依赖顺序为每个文件生成半自然语言行为描述代码
        for file_path in file_creation_order_list:
            print(f"  {Colors.OKBLUE}正在处理文件: {file_path}{Colors.ENDC}")
            
            # 检查是否已经有该文件的符号表，且MD5匹配
            file_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, file_path)
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            
            # 计算当前需求文件的MD5
            current_md5 = self._calculate_file_md5(req_file_path)
            
            # 如果符号表存在且MD5匹配，跳过该文件
            if file_symbol_table.file_md5 == current_md5 and current_md5:
                print(f"    {Colors.WARNING}文件未变化，跳过生成: {file_path}{Colors.ENDC}")
                continue
            
            # 从src_staging目录读取文件需求描述
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_req_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 获取当前文件的依赖文件列表
            current_file_dependencies = dependent_relation.get(file_path, [])
            
            # 构建可用符号文本（从依赖的文件中提取）
            available_symbols_text = self._build_available_symbols_text(
                file_path, 
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
            normalized_symbols_dict = self._normalize_symbols(
                file_path,
                symbol_table
            )
            
            # 更新符号表中的规范化信息
            for symbol_name, norm_info in normalized_symbols_dict.items():
                symbol = symbol_table.get_symbol(symbol_name)
                if symbol:
                    symbol.update_normalized_info(
                        norm_info['normalized_name'],
                        norm_info['visibility']
                    )
            
            # 设置文件MD5
            symbol_table.file_md5 = current_md5
            
            # 保存符号表
            print(f"    正在保存符号表...")
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

    def _generate_ibc_code(
        self, 
        file_path: str, 
        file_req_content: str,
        user_requirements: str,
        project_structure_json: str,
        available_symbols_text: str
    ) -> str:
        """生成IBC代码"""
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
        user_prompt = user_prompt.replace('PROJECT_STRUCTURE_PLACEHOLDER', project_structure_json)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CLASS_CONTENT_PLACEHOLDER', class_content if class_content else '无')
        user_prompt = user_prompt.replace('FUNC_CONTENT_PLACEHOLDER', func_content if func_content else '无')
        user_prompt = user_prompt.replace('VAR_CONTENT_PLACEHOLDER', var_content if var_content else '无')
        user_prompt = user_prompt.replace('OTHERS_CONTENT_PLACEHOLDER', others_content if others_content else '无')
        user_prompt = user_prompt.replace('BEHAVIOR_CONTENT_PLACEHOLDER', behavior_content if behavior_content else '无')
        user_prompt = user_prompt.replace('IMPORT_CONTENT_PLACEHOLDER', import_content if import_content else '无')
        user_prompt = user_prompt.replace('AVAILABLE_SYMBOLS_PLACEHOLDER', available_symbols_text)

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
        """对符号进行规范化处理"""
        symbols = file_symbol_table.get_all_symbols()
        
        if not symbols:
            print(f"    {Colors.WARNING}警告: 未从符号表中提取到符号: {file_path}{Colors.ENDC}")
            return {}
        
        # 检查AI处理器2是否初始化
        if not hasattr(self, 'ai_handler_2') or self.ai_handler_2 is None:
            print(f"    {Colors.WARNING}警告: 符号规范化AI处理器未初始化，使用默认命名策略{Colors.ENDC}")
            return self._default_symbol_normalization(symbols)
        
        # 构建符号列表文本
        symbols_text = self._format_symbols_for_prompt(symbols)
        
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'symbol_normalizer_user.md')
        
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"    {Colors.FAIL}错误: 读取符号规范化提示词失败: {e}{Colors.ENDC}")
            return self._default_symbol_normalization(symbols)
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('CONTEXT_INFO_PLACEHOLDER', f"文件路径: {file_path}")
        user_prompt = user_prompt.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
        
        # 调用AI
        response_content = asyncio.run(self._get_ai_response(self.ai_handler_2, user_prompt))
        
        # 解析JSON响应
        normalized_symbols = self._parse_symbol_normalizer_response(response_content)
        
        if not normalized_symbols:
            print(f"    {Colors.WARNING}警告: AI符号规范化失败，使用默认命名策略{Colors.ENDC}")
            return self._default_symbol_normalization(symbols)
        
        return normalized_symbols
    
    def _format_symbols_for_prompt(self, symbols: Dict[str, SymbolNode]) -> str:
        """格式化符号列表用于提示词"""
        lines = []
        for symbol_name, symbol in symbols.items():
            symbol_type = symbol.symbol_type.value
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
    
    def _default_symbol_normalization(self, symbols: Dict[str, SymbolNode]) -> Dict[str, Dict[str, str]]:
        """默认的符号规范化策略"""
        result = {}
        for symbol_name, symbol in symbols.items():
            # 简单的默认策略：将中文转换为拼音或使用占位符
            normalized_name = self._simple_normalize(symbol_name, symbol.symbol_type.value)
            
            # 根据类型推断默认可见性
            default_visibility = 'file_local'
            if symbol.symbol_type.value == 'class':
                default_visibility = 'public'
            
            result[symbol_name] = {
                'normalized_name': normalized_name,
                'visibility': default_visibility
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
    
    # ========== 符号信息构建 ==========
    
    def _build_available_symbols_text(
        self, 
        current_file: str, 
        dependencies: List[str], 
        ibc_root_path: str
    ) -> str:
        """构建可用符号的文本描述"""
        if not dependencies:
            return '暂无可用的依赖符号'
        
        ibc_data_manager = get_ibc_data_manager()
        lines = ['可用的依赖符号：', '']
        
        for dep_file in dependencies:
            # 加载依赖文件的符号表
            dep_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, dep_file)
            
            if not dep_symbol_table.symbols:
                continue
            
            lines.append(f"来自文件：{dep_file}")
            
            # 只列出对外可见的符号（如果未规范化，也列出来，因为生成时可能需要知道依赖的符号）
            visible_types = ['public', 'global', 'module_local', 'protected']
            
            has_visible_symbols = False
            for symbol_name, symbol in dep_symbol_table.symbols.items():
                # 未规范化或可见性为对外可见的符号
                if not symbol.visibility or symbol.visibility in visible_types:
                    symbol_type_label = {
                        'class': '类',
                        'func': '函数',
                        'var': '变量'
                    }.get(symbol.symbol_type.value, symbol.symbol_type.value)
                    
                    description = symbol.description if symbol.description else '无描述'
                    lines.append(f"- {symbol_type_label} {symbol_name}")
                    lines.append(f"  描述：{description}")
                    if symbol.normalized_name:
                        lines.append(f"  规范化名称：{symbol.normalized_name}")
                    lines.append('')
                    has_visible_symbols = True
            
            # 如果该依赖文件没有可见符号，移除文件标题
            if not has_visible_symbols:
                lines.pop()  # 移除 "来自文件：" 那一行
        
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
