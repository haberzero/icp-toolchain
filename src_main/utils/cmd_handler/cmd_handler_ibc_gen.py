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
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.proj_data_dir, 'icp_api_config.json')
        self.ibc_build_dir = os.path.join(self.proj_work_dir, 'ibc_build')

        self.ai_handler_1: ChatHandler
        self.ai_handler_2: ChatHandler
        self.role_name_1 = "8_intent_behavior_code_gen"
        self.role_name_2 = "8_symbol_normalizer"
        
        # 用于存储当前会话中的AST字典，key为文件路径，value为AST字典
        self.ast_memory: Dict[str, Dict[int, AstNode]] = {}
        
        # 初始化两个AI handler
        ai_handler_1, ai_handler_2 = self._init_ai_handlers()
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
        
        # 读取用户原始需求文本
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 检查用户原始需求是否存在
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return
        
        # 按照依赖顺序为每个文件生成半自然语言行为描述代码
        for file_path in file_creation_order_list:
            print(f"  {Colors.OKBLUE}正在处理文件: {file_path}{Colors.ENDC}")
            
            # 检查MD5，如果文件已经生成且MD5匹配，则跳过
            # TODO：这里存在缺陷，应该是如果某个文件出现了更新，则整个后续链条中的ibc文件都应该被进一步检查是否有必要更新，否则极容易生成出错
            # 而且还应该有一个机制，利用好已经被生成过的ibc文件。所以可能甚至需要引入新的ai_handler
            # 大概想通了，后续增加一个指令，这个指令是ibc_update，事实上是“基于ibc更新ibc”？和直接的完整生成流程其实存在差别
            # 而且这种问题在传统代码中不存在,因为这个中间过程步骤是由开发者自己掌控的,过程中很少出现ai的直接介入
            if self._should_skip_file_generation(file_path, ibc_root_path):
                print(f"  {Colors.OKGREEN}文件已存在且未更改，跳过生成: {file_path}{Colors.ENDC}")
                # 从ibc_build加载AST到内存
                self._load_ast_to_memory(file_path, ibc_root_path)
                continue
            
            # 从src_staging目录读取文件需求描述
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_req_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 获取当前文件的依赖列表
            current_file_dependencies = dependent_relation.get(file_path, [])
            
            # 构建可用符号文本
            available_symbols_text = self._build_available_symbols_text(file_path, current_file_dependencies, ibc_root_path)
            
            # 生成IBC代码，最多重试3次
            ibc_code = self._generate_ibc_with_retry(
                file_path, 
                file_req_content, 
                user_requirements, 
                proj_root, 
                available_symbols_text,
                ibc_root_path,
                max_retries=3
            )
            
            if not ibc_code:
                print(f"  {Colors.FAIL}错误: 文件IBC代码生成失败: {file_path}{Colors.ENDC}")
                continue
            
            # 保存IBC代码
            self._save_intent_behavior_code(ibc_root_path, file_path, ibc_code)
            
            # 计算并存储MD5
            ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
            file_md5 = self._calculate_file_md5(ibc_file_path)
            
            # 获取当前AST（在generate_ibc_with_retry中已经解析并存储到内存）
            ast_dict = self.ast_memory.get(file_path, {})
            if not ast_dict:
                print(f"  {Colors.WARNING}警告: 未找到文件的AST: {file_path}{Colors.ENDC}")
                continue
            
            # 符号规范化处理
            normalized_symbols = self._process_symbol_normalization(file_path, ast_dict)
            
            # 更新符号表：存储md5和符号信息到对应文件夹的symbols.json
            file_symbol_data = {
                'md5': file_md5,
                'symbols': normalized_symbols  # normalized_symbols已经是Dict[str, Dict[str, Any]]类型
            }
            self._save_file_symbols(ibc_root_path, file_path, file_symbol_data)
            
            print(f"  {Colors.OKGREEN}文件IBC代码生成完成: {file_path}{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}IBC代码生成命令执行完毕！{Colors.ENDC}")


    def _get_ibc_directory_name(self) -> str:
        """获取IBC目录名称，优先从配置文件读取behavioral_layer_dir，失败则使用默认值"""
        icp_config_file = os.path.join(self.proj_data_dir, 'icp_config.json')
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
        # 检查AI处理器1是否初始化成功
        if not hasattr(self, 'ai_handler_1') or self.ai_handler_1 is None:
            print(f"  {Colors.FAIL}错误: {self.role_name_1} AI处理器1未正确初始化{Colors.ENDC}")
            return False
            
        # 检查AI处理器1是否连接成功
        if not hasattr(self.ai_handler_1, 'llm') or self.ai_handler_1.llm is None:
            print(f"  {Colors.FAIL}错误: {self.role_name_1} AI模型1连接失败{Colors.ENDC}")
            return False
            
        # 检查AI处理器2是否初始化成功
        if not hasattr(self, 'ai_handler_2') or self.ai_handler_2 is None:
            print(f"  {Colors.FAIL}错误: {self.role_name_2} AI处理器2未正确初始化{Colors.ENDC}")
            return False
            
        # 检查AI处理器2是否连接成功
        if not hasattr(self.ai_handler_2, 'llm') or self.ai_handler_2.llm is None:
            print(f"  {Colors.FAIL}错误: {self.role_name_2} AI模型2连接失败{Colors.ENDC}")
            return False
            
        return True
    
    def is_cmd_valid(self):
        return self._check_cmd_requirement() and self._check_ai_handler()
    
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
    
    # ========== 新增方法：MD5计算 ==========
    
    def _calculate_file_md5(self, file_path: str) -> str:
        """计算文件的MD5值"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 计算文件MD5失败 {file_path}: {e}{Colors.ENDC}")
            return ""
    
    # ========== 新增方法：文件生成跳过检查 ==========
    
    def _should_skip_file_generation(self, file_path: str, ibc_root_path: str) -> bool:
        """检查是否应跳过文件生成（基于MD5比较）"""
        # 检查IBC文件是否存在
        ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
        if not os.path.exists(ibc_file_path):
            return False
        
        # 加载该文件的符号表数据
        file_symbols_data = self._load_file_symbols(ibc_root_path, file_path)
        if not file_symbols_data:
            return False
        
        # 获取符号表中存储的MD5
        stored_md5 = file_symbols_data.get('md5', '')
        if not stored_md5:
            return False
        
        # 计算当前IBC文件的MD5
        current_md5 = self._calculate_file_md5(ibc_file_path)
        
        # 比较MD5是否相同
        return current_md5 == stored_md5
    
    # ========== 新增方法：AST内存管理 ==========
    
    def _load_ast_to_memory(self, file_path: str, ibc_root_path: str) -> bool:
        """从ibc_build加载AST到内存"""
        ast_file_path = os.path.join(self.ibc_build_dir, f"{file_path}.ibc_ast.json")
        if not os.path.exists(ast_file_path):
            print(f"  {Colors.WARNING}警告: AST文件不存在: {ast_file_path}{Colors.ENDC}")
            return False
        
        try:
            ast_data_manager = get_ast_data_manager()
            ast_dict = ast_data_manager.load_ast_from_file(ast_file_path)
            if ast_dict:
                self.ast_memory[file_path] = ast_dict
                print(f"  {Colors.OKGREEN}AST已加载到内存: {file_path}{Colors.ENDC}")
                return True
            else:
                print(f"  {Colors.WARNING}警告: AST加载失败: {file_path}{Colors.ENDC}")
                return False
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 加载AST失败 {ast_file_path}: {e}{Colors.ENDC}")
            return False
    
    # ========== 新增方法：IBC生成重试逻辑 ==========
    
    def _generate_ibc_with_retry(
        self, 
        file_path: str,
        file_req_content: str,
        user_requirements: str,
        proj_root_content: Dict,
        available_symbols_text: str,
        ibc_root_path: str,
        max_retries: int = 3
    ) -> str:
        """生成IBC代码，带重试机制"""
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"  {Colors.WARNING}重试生成IBC代码，第{attempt + 1}次尝试...{Colors.ENDC}")
            
            # 生成IBC代码
            ibc_code = self._ibc_generator_response(
                file_path,
                file_req_content,
                user_requirements,
                [],  # available_descriptions，这里不再需要
                proj_root_content,
                available_symbols_text
            )
            
            if not ibc_code:
                print(f"  {Colors.WARNING}警告: AI未返回有效内容{Colors.ENDC}")
                continue
            
            # 移除代码块标记
            cleaned_code = self._clean_code_blocks(ibc_code)
            if not cleaned_code:
                print(f"  {Colors.WARNING}警告: 清理后的代码为空{Colors.ENDC}")
                continue
            
            # 尝试进行语法分析
            try:
                ast_dict = analyze_ibc_code(cleaned_code)
                # 分析成功，将AST存储到内存和文件
                self.ast_memory[file_path] = ast_dict
                
                # 保存AST到文件
                ast_file_path = os.path.join(self.ibc_build_dir, f"{file_path}.ibc_ast.json")
                os.makedirs(os.path.dirname(ast_file_path), exist_ok=True)
                ast_data_manager = get_ast_data_manager()
                if ast_data_manager.save_ast_to_file(ast_dict, ast_file_path):
                    print(f"  {Colors.OKGREEN}AST分析成功并已保存: {file_path}{Colors.ENDC}")
                
                return cleaned_code
                
            except IbcAnalyzerError as e:
                print(f"  {Colors.FAIL}错误: IBC语法分析失败: {e}{Colors.ENDC}")
                if attempt == max_retries - 1:
                    print(f"  {Colors.FAIL}已达到最大重试次数，放弃生成: {file_path}{Colors.ENDC}")
                    return ""
        
        return ""
    
    def _clean_code_blocks(self, code: str) -> str:
        """移除代码块标记"""
        lines = code.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        return '\n'.join(lines).strip()
    
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
    
    # ========== 新增方法：符号表管理（分布式存储） ==========
    
    def _get_symbols_file_path(self, ibc_root_path: str, file_path: str) -> str:
        """获取文件对应的symbols.json路径"""
        # 获取文件所在目录
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_root_path, file_dir)
        else:
            symbols_dir = ibc_root_path
        
        return os.path.join(symbols_dir, 'symbols.json')
    
    def _load_dir_symbols_table(self, symbols_file: str) -> Dict[str, Any]:
        """加载目录级别的符号表"""
        if not os.path.exists(symbols_file):
            return {}
        
        try:
            with open(symbols_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取符号表失败 {symbols_file}: {e}{Colors.ENDC}")
            return {}
    
    def _load_file_symbols(self, ibc_root_path: str, file_path: str) -> Dict[str, Any]:
        """加载指定文件的符号数据"""
        symbols_file = self._get_symbols_file_path(ibc_root_path, file_path)
        dir_symbols_table = self._load_dir_symbols_table(symbols_file)
        
        # 从目录符号表中获取当前文件的数据
        file_name = os.path.basename(file_path)
        return dir_symbols_table.get(file_name, {})
    
    def _save_file_symbols(self, ibc_root_path: str, file_path: str, file_symbol_data: Dict[str, Any]) -> None:
        """保存文件的符号数据到对应目录的symbols.json"""
        symbols_file = self._get_symbols_file_path(ibc_root_path, file_path)
        
        # 加载目录级别的符号表
        dir_symbols_table = self._load_dir_symbols_table(symbols_file)
        
        # 更新当前文件的数据
        file_name = os.path.basename(file_path)
        dir_symbols_table[file_name] = file_symbol_data
        
        # 保存更新后的符号表
        try:
            os.makedirs(os.path.dirname(symbols_file), exist_ok=True)
            with open(symbols_file, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols_table, f, ensure_ascii=False, indent=2)
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
    
    def _build_available_symbols_text(self, current_file: str, dependencies: List[str], ibc_root_path: str) -> str:
        """构建可用符号的文本描述"""
        if not dependencies:
            return '暂无可用的依赖符号'
        
        lines = ['可用的依赖符号：', '']
        
        for dep_file in dependencies:
            # 从对应目录的symbols.json加载符号数据
            file_symbols_data = self._load_file_symbols(ibc_root_path, dep_file)
            if not file_symbols_data:
                continue
            
            symbols = file_symbols_data.get('symbols', {})
            if not symbols:
                continue
            
            lines.append(f"来自文件：{dep_file}")
            
            # symbols是一个Dict[str, Dict[str, Any]]，需要遍历
            for original_name, symbol_data in symbols.items():
                if not isinstance(symbol_data, dict):
                    continue
                    
                symbol_type = symbol_data.get('symbol_type', '')
                description = symbol_data.get('description', '无描述')
                visibility = symbol_data.get('visibility', '')
                
                # 只包含对外可见的符号
                visible_types = ['public', 'global', 'module_local', 'protected']
                if visibility not in visible_types:
                    continue
                
                type_label = {'class': '类', 'func': '函数', 'var': '变量'}.get(symbol_type, symbol_type)
                lines.append(f"- {type_label} {original_name}")
                lines.append(f"  描述：{description}")
                lines.append('')
        
        return '\n'.join(lines) if len(lines) > 2 else '暂无可用的依赖符号'
    
    # ========== 修改的方法：AI处理器初始化 ==========
    
    def _init_ai_handlers(self):
        """初始化两个AI处理器"""
        # 检查配置文件是否存在
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在，请创建该文件并填充必要内容")
            return None, None
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return None, None
        
        # 优先检查是否有intent_behavior_code_gen_handler配置
        if 'intent_behavior_code_gen_handler' in config:
            chat_api_config = config['intent_behavior_code_gen_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少intent_behavior_code_gen_handler或coder_handler配置")
            return None, None
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=SecretStr(chat_api_config.get('api-key', '')),
            model=chat_api_config.get('model', '')
        )

        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name_1 = self.role_name_1 + ".md"
        prompt_file_name_2 = self.role_name_2 + ".md"
        sys_prompt_path_1 = os.path.join(prompt_dir, prompt_file_name_1)
        sys_prompt_path_2 = os.path.join(prompt_dir, prompt_file_name_2)

        # 创建两个AI处理器实例
        ai_handler_1 = ChatHandler(handler_config, self.role_name_1, sys_prompt_path_1)
        ai_handler_2 = ChatHandler(handler_config, self.role_name_2, sys_prompt_path_2)

        return ai_handler_1, ai_handler_2
