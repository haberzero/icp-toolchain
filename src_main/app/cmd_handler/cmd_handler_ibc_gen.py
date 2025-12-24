import os
import asyncio
import json
import hashlib
import re
from typing import List, Dict, Any, Optional

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig
from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ClassNode, FunctionNode, VariableNode, 
    VisibilityTypes, SymbolType
)

from run_time_cfg.proj_run_time_cfg import get_instance as get_proj_run_time_cfg
from data_store.app_data_store import get_instance as get_app_data_store
from data_store.user_data_store import get_instance as get_user_data_store
from data_store.ibc_data_store import get_instance as get_ibc_data_store

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from utils.ibc_analyzer.ibc_visible_symbol_builder import VisibleSymbolBuilder
from libs.dir_json_funcs import DirJsonFuncs
from libs.ibc_funcs import IbcFuncs
from utils.issue_recorder import IbcIssueRecorder


class CmdHandlerIbcGen(BaseCmdHandler):
    """将单文件需求描述转换为半自然语言行为描述代码
    
    设计结构：
    1. 变量预准备：_build_pre_execution_variables() - 集中加载所需数据
    2. 文件遍历：按依赖顺序遍历文件列表
    3. 单文件处理：_create_single_ibc_file() - 包含重试逻辑的主流程
    4. 提示词构建：_build_user_prompt_for_xxx() - 为不同角色构建提示词
    5. 输出处理：验证、保存、解析、规范化、向量化
    """

    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="intent_behavior_code_gen",
            aliases=["IBC"],
            description="将单文件需求描述转换为半自然语言行为描述代码",
            help_text="根据单文件需求描述生成符合半自然语言行为描述语法的代码结构",
        )
        
        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')
        self.work_icp_config_file_path = os.path.join(self.work_config_dir_path, 'icp_config.json')

        self.role_ibc_gen = "7_intent_behavior_code_gen"
        self.sys_prompt_ibc_gen = ""  # 系统提示词,在_init_ai_handlers中加载
        self.chat_handler = ICPChatHandler()

        # 初始化issue recorder和上一次生成的内容
        self.ibc_issue_recorder = IbcIssueRecorder()
        self.last_generated_ibc_content = None  # 上一次生成的内容

        self._init_ai_handlers()
    
    def execute(self):
        """执行半自然语言行为描述代码生成"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始生成半自然语言行为描述代码...{Colors.ENDC}")
        
        # 准备执行前所需的变量
        self._build_pre_execution_variables()
        
        # 按依赖顺序遍历并处理每个文件
        for file_path in self.file_creation_order_list:
            success = self._create_single_ibc_file(file_path)
            if not success:
                print(f"{Colors.FAIL}文件 {file_path} 处理失败，退出运行{Colors.ENDC}")
                return
        
        # 所有文件处理完毕，统一更新ibc文件的MD5值到统一的verify文件
        print(f"  {Colors.OKBLUE}开始更新ibc文件校验码...{Colors.ENDC}")
        ibc_data_store = get_ibc_data_store()
        ibc_data_store.batch_update_ibc_verify_codes(
            self.work_data_dir_path,
            self.work_ibc_dir_path,
            self.file_creation_order_list
        )
        print(f"  {Colors.OKGREEN}ibc文件校验码更新完毕{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}半自然语言行为描述代码生成完毕!{Colors.ENDC}")
    
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
        
        # 读取用户需求
        user_data_store = get_user_data_store()
        user_requirements_str = user_data_store.get_user_prompt()
        if not user_requirements_str:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求{Colors.ENDC}")
            return
        
        # 检查目录
        work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
        if not os.path.exists(work_staging_dir_path):
            print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
            return
        
        # 读取项目配置
        try:
            with open(self.work_icp_config_file_path, 'r', encoding='utf-8') as f:
                icp_config_json_dict = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取ICP配置文件失败: {e}{Colors.ENDC}")
            return

        # 获取文件夹名称配置并创建对应文件夹
        if "file_system_mapping" in icp_config_json_dict:
            ibc_dir_name = icp_config_json_dict["file_system_mapping"].get("ibc_dir_name", "src_ibc")
        if ibc_dir_name is not None:
            work_ibc_dir_path = os.path.join(self.work_dir_path, ibc_dir_name)
        else:
            work_ibc_dir_path = os.path.join(self.work_dir_path, "src_ibc")
        os.makedirs(work_ibc_dir_path, exist_ok=True)
        
        # 获取文件创建顺序
        dependent_relation = final_dir_json_dict['dependent_relation']
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 存储实例变量供后续使用
        self.dir_json_dict = final_dir_json_dict
        self.proj_root_dict = final_dir_json_dict['proj_root_dict']
        self.proj_root_dict_json_str = json.dumps(self.proj_root_dict, indent=2, ensure_ascii=False)
        self.dependent_relation = dependent_relation
        self.file_creation_order_list = file_creation_order_list
        self.user_requirements_str = user_requirements_str
        self.work_staging_dir_path = work_staging_dir_path
        self.work_ibc_dir_path = work_ibc_dir_path
        
        # 初始化可见符号表构建器
        self.visible_symbol_builder = VisibleSymbolBuilder(
            proj_root_dict=self.proj_root_dict,
        )
        
        # 初始化更新状态.需要依赖self.file_creation_order_list等内容
        self.need_update_flag_dict = self._initialize_update_status()
    
    def _initialize_update_status(self) -> Dict[str, bool]:
        """初始化更新状态字典
        
        根据以下逻辑标记文件是否需要更新：
        1. 检查one_file_req的MD5值变化
        2. 检查ibc文件是否存在
        3. 检查依赖链中的变化（依赖传播）
        
        Returns:
            Dict[str, bool]: 文件路径到是否需要更新的映射
        """
        print(f"  {Colors.OKBLUE}开始检查文件更新状态...{Colors.ENDC}")
        need_update_flag_dict = {}

        file_list = self.file_creation_order_list
        
        # 第一阶段：检查one_file_req的MD5和ibc文件存在性
        for file_path in file_list:
            need_update = False
            
            req_file = os.path.join(self.work_staging_dir_path, f"{file_path}_one_file_req.txt")
            ibc_data_store = get_ibc_data_store()
            ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
            
            # 读取one_file_req的当前MD5
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    req_content = f.read()
                current_req_md5 = IbcFuncs.calculate_text_md5(req_content)
            except Exception as e:
                print(f"    {Colors.WARNING}警告: 读取one_file_req文件失败: {file_path}, {e}{Colors.ENDC}")
                need_update = True
                need_update_flag_dict[file_path] = need_update
                continue
            
            # 从统一的verify文件中加载该文件的校验数据
            ibc_data_store = get_ibc_data_store()
            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
            
            # 检查one_file_req的MD5是否变化
            saved_req_md5 = verify_data.get('one_file_req_verify_code', None)
            if saved_req_md5 is None:
                print(f"    {Colors.OKBLUE}首次生成: {file_path}{Colors.ENDC}")
                need_update = True
            elif saved_req_md5 != current_req_md5:
                print(f"    {Colors.OKBLUE}one_file_req已变化: {file_path}{Colors.ENDC}")
                need_update = True
            
            # 检查ibc文件是否存在
            if not need_update and not os.path.exists(ibc_path):
                print(f"    {Colors.OKBLUE}ibc文件不存在，需要生成: {file_path}{Colors.ENDC}")
                need_update = True
            
            need_update_flag_dict[file_path] = need_update
            
            # 更新one_file_req的MD5到统一的verify文件
            verify_data['one_file_req_verify_code'] = current_req_md5
            ibc_data_store.save_file_verify_data(self.work_data_dir_path, file_path, verify_data)
        
        # 第二阶段：依赖链传播更新
        # 按依赖顺序遍历（file_list已经是拓扑排序后的顺序）
        for file_path in file_list:
            if need_update_flag_dict.get(file_path, False):
                # 如果当前文件已标记需要更新，则所有依赖它的文件也需要更新
                self._propagate_update_to_dependents(file_path, need_update_flag_dict)
            else:
                # 检查ibc文件的MD5是否变化（用户可能手动修改了）
                ibc_data_store = get_ibc_data_store()
                ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, file_path)
                
                if os.path.exists(ibc_path):
                    try:
                        ibc_content = ibc_data_store.load_ibc_code(ibc_path)
                        if ibc_content:
                            current_ibc_md5 = IbcFuncs.calculate_text_md5(ibc_content)
                            
                            verify_data = ibc_data_store.load_file_verify_data(self.work_data_dir_path, file_path)
                            saved_ibc_md5 = verify_data.get('ibc_verify_code', None)
                        if saved_ibc_md5 is not None and saved_ibc_md5 != current_ibc_md5:
                            print(f"    {Colors.OKBLUE}ibc文件被手动修改: {file_path}，依赖它的文件需要更新{Colors.ENDC}")
                            self._propagate_update_to_dependents(file_path, need_update_flag_dict)
                    except Exception as e:
                        print(f"    {Colors.WARNING}警告: 检查ibc文件MD5失败: {file_path}, {e}{Colors.ENDC}")
        
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
    
    def _create_single_ibc_file(self, icp_json_file_path: str) -> bool:
        """为单个文件生成IBC代码（包含重试机制）
        
        Args:
            icp_json_file_path: 文件路径
        """
        print(f"  {Colors.OKBLUE}正在处理文件: {icp_json_file_path}{Colors.ENDC}")
        
        # 检查是否需要更新
        if not self.need_update_flag_dict.get(icp_json_file_path, False):
            print(f"    {Colors.WARNING}文件及其依赖均未变化，跳过生成: {icp_json_file_path}{Colors.ENDC}")
            return True

        # 带重试的生成逻辑（IBC 代码的生成过程不确定性更多，提供较多的重试次数）
        max_attempts = 5
        for attempt in range(max_attempts):
            print(f"    {Colors.OKBLUE}正在重试... (尝试 {attempt + 1}/{max_attempts}){Colors.ENDC}")

            # 构建用户提示词
            user_prompt = self._build_user_prompt_for_ibc_generator(icp_json_file_path)
            if not user_prompt:
                print(f"{Colors.FAIL}错误: 用户提示词构建失败，终止执行{Colors.ENDC}")
                return False
            
            # 将用户提示词保存到stage文件夹以便查看生成过程
            self._save_user_prompt_to_stage(icp_json_file_path, user_prompt, attempt + 1)
            
            # 调用AI生成IBC代码
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_ibc_gen,
                sys_prompt=self.sys_prompt_ibc_gen,
                user_prompt=user_prompt
            ))
            
            if not success or not response_content:
                print(f"    {Colors.WARNING}警告: AI响应失败或为空{Colors.ENDC}")
                continue
            
            # 清理代码块标记
            ibc_code = ICPChatHandler.clean_code_block_markers(response_content)

            # 解析IBC代码生成AST
            print(f"    {Colors.OKBLUE}正在分析IBC代码生成AST...{Colors.ENDC}")
            ast_dict, symbol_table = analyze_ibc_code(ibc_code, self.ibc_issue_recorder)
            
            # 检查是否得到有效的AST和符号表
            if not ast_dict or not symbol_table:
                print(f"    {Colors.WARNING}警告: IBC代码分析失败，未能生成有效的AST或符号表{Colors.ENDC}")
                continue

            # 保存IBC代码
            ibc_data_store = get_ibc_data_store()
            ibc_path = ibc_data_store.build_ibc_path(self.work_ibc_dir_path, icp_json_file_path)
            ibc_data_store.save_ibc_code(ibc_path, ibc_code)
            print(f"    {Colors.OKGREEN}IBC代码已保存: {ibc_path}{Colors.ENDC}")
            
            # # 保存AST（暂时不需要保存到文件）
            # ast_path = ibc_data_store.build_ast_path(self.work_ibc_dir_path, icp_json_file_path)
            # ibc_data_store.save_ast(ast_path, ast_dict)
            # print(f"    {Colors.OKGREEN}AST已保存: {ast_path}{Colors.ENDC}")
            
            # 保存符号表
            file_name = os.path.basename(icp_json_file_path)
            symbols_path = ibc_data_store.build_symbols_path(self.work_ibc_dir_path, icp_json_file_path)
            ibc_data_store.save_symbols(symbols_path, file_name, symbol_table)
            print(f"    {Colors.OKGREEN}符号表已保存: {symbols_path}{Colors.ENDC}")
            
            # IBC代码和符号表保存成功，返回成功
            return True
        
        # 达到最大重试次数
        print(f"  {Colors.FAIL}已达到最大重试次数({max_attempts})，跳过该文件{Colors.ENDC}")
        return False

    def _build_user_prompt_for_ibc_generator(self, icp_json_file_path: str) -> str:
        """
        构建IBC代码生成的用户提示词（role_ibc_gen）
        
        从项目数据目录中直接读取所需信息，无需外部参数传递。
        
        Args:
            icp_json_file_path: 当前处理的文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        
        # 使用可见符号表构建器构建当前文件的可见符号树
        ibc_data_store = get_ibc_data_store()

        # 先检查依赖符号表是否可用
        if not ibc_data_store.is_dependency_symbol_tables_valid(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=icp_json_file_path,
        ):
            # 依赖符号不可用时，认为用户提示词构建失败
            print(f"  {Colors.FAIL}警告: 依赖符号表构建失败，用户提示词构建失败: {icp_json_file_path}{Colors.ENDC}")
            return ""

        dependency_symbol_tables = ibc_data_store.load_dependency_symbol_tables(
            ibc_root=self.work_ibc_dir_path,
            dependent_relation=self.dependent_relation,
            current_file_path=icp_json_file_path,
        )

        symbols_tree, symbols_metadata = self.visible_symbol_builder.build_visible_symbol_tree(
            current_file_path=icp_json_file_path,
            dependency_symbol_tables=dependency_symbol_tables,
        )
        
        # 根据symbols_metadata构建可用依赖符号文本
        # symbols_metadata的键为点号分隔的路径（如 src.ball.ball_entity.BallEntity.get_position）
        # 这里只关心具体符号节点，忽略type为folder/file的元数据
        available_symbol_lines = []
        for symbol_path, meta in symbols_metadata.items():
            meta_type = meta.get("type")
            if meta_type in ("folder", "file"):
                continue

            desc = meta.get("description")
            if not desc:
                print(f"  {Colors.WARNING}警告: 依赖符号缺少对外功能描述: {symbol_path}{Colors.ENDC}")
                desc = "没有对外功能描述"

            available_symbol_lines.append(f"{symbol_path} ：{desc}")

        if available_symbol_lines:
            available_symbols_text = "可用的依赖符号（path.to.symbol ：对外功能描述）：\n\n" + "\n".join(available_symbol_lines)
        else:
            available_symbols_text = '暂无可用的依赖符号'
        
        
        # 读取文件级实现规划
        implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
        implementation_plan_str = ""
        try:
            with open(implementation_plan_file, 'r', encoding='utf-8') as f:
                implementation_plan_str = f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件级实现规划失败: {e} {Colors.ENDC}")
            return ""

        # 读取文件需求描述
        req_file_path = os.path.join(self.work_staging_dir_path, f"{icp_json_file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_req_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败: {e}{Colors.ENDC}")
            return ""

        class_content = self._extract_section_content(file_req_str, 'class')
        func_content = self._extract_section_content(file_req_str, 'func')
        var_content = self._extract_section_content(file_req_str, 'var')
        others_content = self._extract_section_content(file_req_str, 'others')
        behavior_content = self._extract_section_content(file_req_str, 'behavior')
        import_content = self._extract_section_content(file_req_str, 'import')
        
        # 读取用户提示词模板
        app_data_store = get_app_data_store()
        app_user_prompt_file_path = os.path.join(app_data_store.get_user_prompt_dir(), 'intent_code_behavior_gen_user.md')
        try:
            with open(app_user_prompt_file_path, 'r', encoding='utf-8') as f:
                user_prompt_template_str = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 填充占位符
        user_prompt_str = user_prompt_template_str
        user_prompt_str = user_prompt_str.replace('USER_REQUIREMENTS_PLACEHOLDER', self.user_requirements_str)
        user_prompt_str = user_prompt_str.replace('IMPLEMENTATION_PLAN_PLACEHOLDER', implementation_plan_str)
        user_prompt_str = user_prompt_str.replace('PROJECT_STRUCTURE_PLACEHOLDER', self.proj_root_dict_json_str)
        user_prompt_str = user_prompt_str.replace('CURRENT_FILE_PATH_PLACEHOLDER', icp_json_file_path)
        user_prompt_str = user_prompt_str.replace('CLASS_CONTENT_PLACEHOLDER', class_content if class_content else '无')
        user_prompt_str = user_prompt_str.replace('FUNC_CONTENT_PLACEHOLDER', func_content if func_content else '无')
        user_prompt_str = user_prompt_str.replace('VAR_CONTENT_PLACEHOLDER', var_content if var_content else '无')
        user_prompt_str = user_prompt_str.replace('OTHERS_CONTENT_PLACEHOLDER', others_content if others_content else '无')
        user_prompt_str = user_prompt_str.replace('BEHAVIOR_CONTENT_PLACEHOLDER', behavior_content if behavior_content else '无')
        user_prompt_str = user_prompt_str.replace('IMPORT_CONTENT_PLACEHOLDER', import_content if import_content else '无')
        user_prompt_str = user_prompt_str.replace('AVAILABLE_SYMBOLS_PLACEHOLDER', available_symbols_text)
        
        return user_prompt_str

    def _save_user_prompt_to_stage(self, icp_json_file_path: str, user_prompt: str, attempt: int) -> bool:
        """将用户提示词保存到stage文件夹以便查看
        
        Args:
            icp_json_file_path: 文件路径
            user_prompt: 用户提示词
            attempt: 当前尝试次数
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 构建保存路径，与one_file_req类似
            prompt_file_path = os.path.join(
                self.work_staging_dir_path, 
                f"{icp_json_file_path}_ibc_user_prompt_attempt{attempt}.txt"
            )
            
            # 创建目录
            parent_dir = os.path.dirname(prompt_file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # 保存提示词
            with open(prompt_file_path, 'w', encoding='utf-8') as f:
                f.write(user_prompt)
            
            print(f"    {Colors.OKGREEN}用户提示词已保存: {prompt_file_path}{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"    {Colors.WARNING}警告: 保存用户提示词失败 {prompt_file_path}: {e}{Colors.ENDC}")
            return False

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
            
            # 检查文件级实现规划文件是否存在
            implementation_plan_file = os.path.join(self.work_data_dir_path, 'icp_implementation_plan.txt')
            if not os.path.exists(implementation_plan_file):
                print(f"  {Colors.WARNING}警告: 文件级实现规划文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
                return False
            
            # 读取目录结构并解析
            with open(ibc_dir_file, 'r', encoding='utf-8') as f:
                dir_structure_str = f.read()
            dir_json_dict = json.loads(dir_structure_str)
            
            # 验证依赖分析结果完整性
            if "proj_root_dict" not in dir_json_dict or "dependent_relation" not in dir_json_dict:
                print(f"  {Colors.FAIL}错误: 依赖分析结果缺少必要的节点(proj_root_dict或dependent_relation){Colors.ENDC}")
                return False
            
            # 获取文件列表
            dependent_relation = dir_json_dict['dependent_relation']
            file_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
            
            # 检查src_staging目录是否存在
            work_staging_dir_path = os.path.join(self.work_dir_path, 'src_staging')
            if not os.path.exists(work_staging_dir_path):
                print(f"  {Colors.FAIL}错误: src_staging目录不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
                return False
            
            # 检查每个文件的one_file_req文件是否存在
            missing_files = []
            for file_path in file_list:
                req_file = os.path.join(work_staging_dir_path, f"{file_path}_one_file_req.txt")
                if not os.path.exists(req_file):
                    missing_files.append(f"{file_path}_one_file_req.txt")
            
            if missing_files:
                print(f"  {Colors.FAIL}错误: 以下one_file_req文件不存在，请先执行one_file_req_gen命令:{Colors.ENDC}")
                for missing_file in missing_files[:5]:  # 只显示前5个
                    print(f"    - {missing_file}")
                if len(missing_files) > 5:
                    print(f"    ... 还有 {len(missing_files) - 5} 个文件")
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
        
        if not self.sys_prompt_ibc_gen:
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
        
        # 加载IBC生成角色
        sys_prompt_path = os.path.join(app_prompt_dir_path, f"{self.role_ibc_gen}.md")
        try:
            with open(sys_prompt_path, 'r', encoding='utf-8') as f:
                self.sys_prompt_ibc_gen = f.read()
        except Exception as e:
            print(f"错误: 读取系统提示词文件失败 ({self.role_ibc_gen}): {e}")
