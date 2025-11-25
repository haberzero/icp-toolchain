import sys, os
import asyncio
import json
from typing import List, Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs


class CmdHandlerOneFileDepend(BaseCmdHandler):
    """单文件依赖关系分析指令
    
    基于已生成的单文件需求描述，分析各文件间的依赖关系，生成最终的依赖关系表
    """
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="one_file_depend",
            aliases=["OFD"],
            description="分析单文件依赖关系并生成最终依赖表",
            help_text="基于单文件需求描述分析依赖关系，生成icp_dir_content_final.json",
        )
        
        # 初始化路径配置
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')
        self.staging_dir_path = os.path.join(self.proj_work_dir, 'src_staging')
        
        # 初始化AI处理器
        self.chat_handler = ICPChatHandler()
        self.role_name = "7_one_file_req_depend_analyzer"
        self._init_ai_handlers()

    def execute(self):
        """执行依赖关系分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始分析单文件依赖关系...{Colors.ENDC}")

        # 读取精炼后的目录结构（获取proj_root和文件创建顺序）
        refined_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        try:
            with open(refined_dir_file, 'r', encoding='utf-8') as f:
                refined_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取目录结构失败: {e}{Colors.ENDC}")
            return

        proj_root = refined_content.get("proj_root", {})
        dependent_relation = refined_content.get("dependent_relation", {})
        
        # 构建文件创建顺序（倒序处理，从高层到底层）
        file_creation_order = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 分析依赖关系
        new_dependent_relation = self._analyze_all_dependencies(file_creation_order)
        
        # 检测循环依赖
        circular_deps = DirJsonFuncs.detect_circular_dependencies(new_dependent_relation)
        if circular_deps:
            print(f"  {Colors.FAIL}错误: 检测到循环依赖: {circular_deps}{Colors.ENDC}")
            return
        
        print(f"  {Colors.OKGREEN}循环依赖检测通过{Colors.ENDC}")
        
        # 生成并保存最终的依赖关系文件
        self._save_final_dependency_file(proj_root, new_dependent_relation)
        
        print(f"{Colors.OKGREEN}依赖关系分析完成!{Colors.ENDC}")

    def _analyze_all_dependencies(self, file_creation_order: List[str]) -> Dict[str, List[str]]:
        """分析所有文件的依赖关系
        
        Args:
            file_creation_order: 文件创建顺序列表
        
        Returns:
            Dict[str, List[str]]: 新的依赖关系字典
        """
        new_dependent_relation = {}
        
        # 倒序处理文件（从高层到底层），确保不会产生循环依赖
        for file_path in reversed(file_creation_order):
            dependency_list = self._analyze_single_file_dependency(file_path)
            new_dependent_relation[file_path] = dependency_list
        
        return new_dependent_relation

    def _analyze_single_file_dependency(self, file_path: str) -> List[str]:
        """分析单个文件的依赖关系
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[str]: 依赖文件列表
        """
        print(f"  {Colors.OKBLUE}正在分析文件依赖关系: {file_path}{Colors.ENDC}")
        
        # 构建用户提示词
        user_prompt = self._build_user_prompt(file_path)
        if not user_prompt:
            return []

        # 调用AI分析依赖关系
        response_content, success = asyncio.run(self.chat_handler.get_role_response(
            role_name=self.role_name,
            user_prompt=user_prompt
        ))
        
        if not success:
            print(f"  {Colors.WARNING}警告: 依赖分析失败: {file_path}{Colors.ENDC}")
            return []
        
        # 清理代码块标记
        cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
        
        # 解析依赖关系
        try:
            dependencies_data = json.loads(cleaned_content)
            return dependencies_data.get("dependencies", [])
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 解析依赖关系失败: {e}{Colors.ENDC}")
            print(f"  AI返回内容: {cleaned_content}")
            return []

    def _build_user_prompt(self, file_path: str) -> str:
        """构建用户提示词
        
        Args:
            file_path: 当前文件路径
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取当前文件的需求描述
        req_file_path = os.path.join(self.staging_dir_path, f"{file_path}_one_file_req.txt")
        try:
            with open(req_file_path, 'r', encoding='utf-8') as f:
                file_requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取文件需求描述失败: {e}{Colors.ENDC}")
            return ""
        
        # 提取import部分
        import_content = self._extract_section_content(file_requirement_content, 'import:')
        if not import_content:
            print(f"  {Colors.WARNING}警告: 无法提取import内容: {file_path}{Colors.ENDC}")
        
        # 构建可用文件描述字典
        available_modules_text = self._build_available_modules_text(file_path)
        
        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_depend_analyzer_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""

        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('CURRENT_FILE_REQUIREMENT_PLACEHOLDER', import_content)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('AVAILABLE_MODULES_PLACEHOLDER', available_modules_text if available_modules_text else '暂无其他模块')

        return user_prompt

    def _build_available_modules_text(self, current_file_path: str) -> str:
        """构建可用模块信息文本
        
        Args:
            current_file_path: 当前文件路径
        
        Returns:
            str: 可用模块信息文本
        """
        available_modules = []
        
        try:
            for existing_file in os.listdir(self.staging_dir_path):
                if not existing_file.endswith('_one_file_req.txt'):
                    continue
                
                existing_file_path = existing_file[:-17]  # 移除 '_one_file_req.txt'
                if existing_file_path == current_file_path:  # 排除当前文件
                    continue
                
                req_path = os.path.join(self.staging_dir_path, existing_file)
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取description部分
                desc = self._extract_section_content(content, 'description:')
                if desc:
                    available_modules.append(f"模块路径: {existing_file_path}\n模块描述: {desc}")
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 构建可用模块信息失败: {e}{Colors.ENDC}")
        
        return '\n\n'.join(available_modules)

    def _extract_section_content(self, content: str, section_marker: str) -> str:
        """从文件内容中提取指定段落的内容
        
        Args:
            content: 文件内容
            section_marker: 段落标记 (例如 'import:', 'description:')
        
        Returns:
            str: 提取的段落内容
        """
        lines = content.split('\n')
        section_lines = []
        found_section = False
        
        for line in lines:
            if line.strip().startswith(section_marker):
                found_section = True
                continue
            
            if found_section:
                stripped_line = line.strip()
                
                # 空行继续添加
                if not stripped_line:
                    section_lines.append(line)
                    continue
                
                # 注释行跳过
                if stripped_line.startswith('#'):
                    continue
                
                # 检查是否是新段落（以字母开头且没有缩进）
                is_new_paragraph = (
                    stripped_line and 
                    stripped_line[0].isalpha() and 
                    not line.startswith((' ', '\t'))
                )
                
                if is_new_paragraph:
                    break
                else:
                    section_lines.append(line)
        
        return '\n'.join(section_lines)

    def _save_final_dependency_file(self, proj_root: Dict, dependent_relation: Dict):
        """生成并保存最终的依赖关系文件
        
        Args:
            proj_root: 项目根目录结构
            dependent_relation: 依赖关系字典
        """
        dir_content = {
            "proj_root": proj_root,
            "dependent_relation": dependent_relation
        }
        
        dir_content_file = os.path.join(self.proj_data_dir, "icp_dir_content_final.json")
        try:
            with open(dir_content_file, 'w', encoding='utf-8') as f:
                json.dump(dir_content, f, indent=2, ensure_ascii=False)
            print(f"  {Colors.OKGREEN}最终依赖关系文件已保存: {dir_content_file}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存依赖关系文件失败: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查精炼后的目录结构文件是否存在
        refined_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        if not os.path.exists(refined_dir_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行循环依赖解决命令{Colors.ENDC}")
            return False
        
        # 检查src_staging目录是否存在
        if not os.path.exists(self.staging_dir_path):
            print(f"  {Colors.WARNING}警告: src_staging目录不存在，请先执行单文件需求生成命令{Colors.ENDC}")
            return False
        
        # 检查是否有生成的需求描述文件
        req_files = [f for f in os.listdir(self.staging_dir_path) if f.endswith('_one_file_req.txt')]
        if not req_files:
            print(f"  {Colors.WARNING}警告: 未找到单文件需求描述，请先执行单文件需求生成命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
            return False
        
        return True

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
        
        # 优先使用dependency_refine_handler配置，否则使用coder_handler
        if 'dependency_refine_handler' in config:
            chat_api_config = config['dependency_refine_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=chat_api_config.get('api-key', ''),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载角色提示词
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        sys_prompt_path = os.path.join(prompt_dir, self.role_name + ".md")
        
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)
