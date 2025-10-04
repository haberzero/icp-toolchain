import sys, os
import asyncio
import json
from typing import List, Dict, Any
from pydantic import SecretStr

from typedef.data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from cfg.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.ai_handler.chat_handler import ChatHandler
from libs.dir_json_funcs import DirJsonFuncs


class CmdHandlerOneFileReqGen(BaseCmdHandler):
    """ICB目录结构下创建单文件需求描述并生成最新依赖关系"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="one_file_req_gen",
            aliases=["OFR"],
            description="在文件系统中创建src_staging目录结构以及one_file_req.txt文件",
            help_text="根据已有的dir_content.json文件的内容在src_staging目录结构下创建单文件的编程需求描述, 为ICB的生成做准备",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.icp_proj_data_dir
        self.ai_handler_1: ChatHandler
        self.ai_handler_2: ChatHandler
        self.role_name_1 = "7_one_file_req_gen"
        self.role_name_2 = "7_one_file_req_depend_analyzer"
        ai_handler_1, ai_handler_2 = self._init_ai_handlers()
        if ai_handler_1 is not None:
            self.ai_handler_1 = ai_handler_1
            self.ai_handler_1.init_chat_chain()
        if ai_handler_2 is not None:
            self.ai_handler_2 = ai_handler_2
            self.ai_handler_2.init_chat_chain()

    def execute(self):
        """执行ICB目录结构创建"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始创建ICB目录结构...{Colors.ENDC}")

        # 读取经过依赖项修复的目录结构
        final_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        try:
            with open(final_dir_file, 'r', encoding='utf-8') as f:
                final_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取最终目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not final_content:
            print(f"  {Colors.FAIL}错误: 最终目录结构内容为空{Colors.ENDC}")
            return

        # 检查是否包含必要的节点
        if "proj_root" not in final_content or "dependent_relation" not in final_content:
            print(f"  {Colors.FAIL}错误: 最终目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return

        # 从dependent_relation中获取文件创建顺序, 可以认为列表中靠近 index=0 的文件其层级低且被其它文件依赖
        proj_root = final_content["proj_root"]
        dependent_relation = final_content["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)

        # 创建src_staging目录用于存储_one_file_req.txt文件
        staging_dir_path = os.path.join(self.work_dir, 'src_staging')
        try:
            os.makedirs(staging_dir_path, exist_ok=True)
            print(f"  {Colors.OKGREEN}src_staging目录创建成功: {staging_dir_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 创建src_staging目录失败: {e}{Colors.ENDC}")
            return
        
        # 为每个单文件生成需求描述，保存到src_staging目录
        self._generate_file_requirements_1(staging_dir_path, proj_root, file_creation_order_list)
        
        # 构建文件描述字典供依赖分析使用
        file_desc_dict = self._build_file_desc_dict(staging_dir_path, file_creation_order_list)
        
        # 为每个文件生成依赖关系，并获取新的依赖关系字典
        new_dependent_relation = self._generate_file_dependencies_2(staging_dir_path, file_creation_order_list, file_desc_dict, proj_root)
        
        cycle_detected = DirJsonFuncs.detect_circular_dependencies(new_dependent_relation)
        if cycle_detected:
            print(f"  {Colors.FAIL}错误: 检测到循环依赖: {cycle_detected}{Colors.ENDC}")
            return {}

        # 生成dir_content.json文件，使用新生成的依赖关系
        self._generate_dir_content_json(proj_root, new_dependent_relation)
        
        print(f"{Colors.OKGREEN}ICB目录结构创建命令执行完毕!{Colors.ENDC}")

    def _generate_file_requirements_1(
            self, 
            staging_dir_path: str,  # 修改参数名称以反映实际用途
            proj_root_content: Dict, 
            file_creation_order_list: List[str]
        ) -> None:
        """为每个文件生成需求描述"""
        # 读取用户原始需求文本
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 检查用户原始需求是否存在
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return

        # 初始化累积描述字典，用于为后续文件生成提供上下文
        accumulated_descriptions_dict = {}
        
        # 按照依赖顺序为每个文件生成需求描述
        for file_path in file_creation_order_list:
            # 获取文件描述
            file_description = DirJsonFuncs.get_file_description(proj_root_content, file_path)
            if not file_description:
                print(f"  {Colors.FAIL}错误: 无法获取文件描述: {file_path}{Colors.ENDC}")
                continue
            
            # 为每个文件生成新的单文件编程需求描述
            print(f"  {Colors.OKBLUE}正在为文件生成需求描述: {file_path}{Colors.ENDC}")
            
            # 生成新的文件需求描述
            new_file_description = self._create_one_file_req_1(
                file_path, 
                file_description, 
                user_requirements,  # 使用用户原始需求
                list(accumulated_descriptions_dict.values())
            )

            # 移除可能的代码块标记
            lines = new_file_description.split('\n')
            if lines and lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            new_file_description = '\n'.join(lines).strip()
            
            # 保存新生成的描述到src_staging目录下的文件
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            
            # 确保文件的父目录存在
            parent_dir = os.path.dirname(req_file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            try:
                with open(req_file_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_description)
                print(f"  {Colors.OKGREEN}文件需求描述已保存: {req_file_path}{Colors.ENDC}")
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 保存文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
            
            # 将新生成的描述添加到累积描述中，供后续文件使用
            extracted_description = self._extract_description_content(new_file_description)
            extracted_func = self._extract_func_content(new_file_description)
            extracted_class = self._extract_class_content(new_file_description)
            
            # 组合所有提取的内容
            formatted_description = f"文件 {file_path} 的接口描述:\n"
            if extracted_class:
                formatted_description += f"类信息:\n{extracted_class}\n\n"
            if extracted_func:
                formatted_description += f"函数信息:\n{extracted_func}\n\n"
            if extracted_description:
                formatted_description += f"描述信息:\n{extracted_description}"
            
            if formatted_description:
                accumulated_descriptions_dict[file_path] = formatted_description

    def _extract_description_content(self, content: str) -> str:
        """从文件内容中提取description部分"""
        lines = content.split('\n')
        description_lines = []
        found_description = False
        
        for line in lines:
            # 查找description:开始的行
            if line.strip().startswith('description:'):
                found_description = True
                continue

            # 检查是否应该结束description部分的提取
            elif found_description: 
                stripped_line = line.strip()
                
                # 如果是空行，继续添加（保持格式）
                if not stripped_line:
                    description_lines.append(line)
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
                    # 添加description部分的内容行
                    description_lines.append(line)
        
        return '\n'.join(description_lines)

    def _extract_func_content(self, content: str) -> str:
        """从文件内容中提取func部分"""
        lines = content.split('\n')
        func_lines = []
        found_func = False
        
        for line in lines:
            # 查找func:开始的行
            if line.strip().startswith('func:'):
                found_func = True
                continue

            # 检查是否应该结束func部分的提取
            elif found_func: 
                stripped_line = line.strip()
                
                # 如果是空行，继续添加（保持格式）
                if not stripped_line:
                    func_lines.append(line)
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
                    # 添加func部分的内容行
                    func_lines.append(line)
        
        return '\n'.join(func_lines)

    def _extract_class_content(self, content: str) -> str:
        """从文件内容中提取class部分"""
        lines = content.split('\n')
        class_lines = []
        found_class = False
        
        for line in lines:
            # 查找class:开始的行
            if line.strip().startswith('class:'):
                found_class = True
                continue

            # 检查是否应该结束class部分的提取
            elif found_class: 
                stripped_line = line.strip()
                
                # 如果是空行，继续添加（保持格式）
                if not stripped_line:
                    class_lines.append(line)
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
                    # 添加class部分的内容行
                    class_lines.append(line)
        
        return '\n'.join(class_lines)

    def _create_one_file_req_1(
        self, 
        file_path: str, 
        file_description: str, 
        user_requirements: str,
        accumulated_descriptions: List[str]
    ) -> str:
        """创建新的文件需求描述"""
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_gen_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 填充占位符
        file_desc_json = json.dumps(
            {"path": file_path, "description": file_description}, 
            indent=2, 
            ensure_ascii=False)
        
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('USER_REQUIREMENTS_PLACEHOLDER', user_requirements)  # 使用新的占位符
        user_prompt = user_prompt.replace('FILE_DESCRIPTION_PLACEHOLDER', file_desc_json)
        user_prompt = user_prompt.replace('EXISTING_FILE_DESCRIPTIONS_PLACEHOLDER', 
                                        '\n\n'.join(accumulated_descriptions) if accumulated_descriptions else '暂无已生成的文件需求描述')

        # 调用AI生成需求描述
        response_content = asyncio.run(self._get_ai_response_1(self.ai_handler_1, user_prompt))
        return response_content

    def _generate_file_dependencies_2(
        self,
        icb_root_path: str,
        file_creation_order_list: List[str],
        file_desc_dict: Dict[str, str],
        proj_root: Dict
    ) -> Dict[str, List[str]]:
        """为每个文件生成依赖关系"""
        # 初始化新的依赖关系字典
        new_dependent_relation = {}
        
        # 创建file_desc_dict的副本，用于动态更新
        available_file_desc_dict = file_desc_dict.copy()
        
        # 倒序处理文件（从抽象层级最高的文件开始）
        for file_path in reversed(file_creation_order_list):
            # 从可用文件描述字典中移除当前文件，控制ai的生成过程合理性，防止造成循环依赖
            if file_path in available_file_desc_dict:
                del available_file_desc_dict[file_path]
            
            # 获取当前文件的需求描述
            req_file_path = os.path.join(icb_root_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_requirement_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                # 即使读取失败，也要在依赖关系中添加空列表
                new_dependent_relation[file_path] = []
                continue

            # 从文件需求描述中提取module部分
            module_content = self._extract_import_content(file_requirement_content)
            if not module_content:
                print(f"  {Colors.WARNING}警告: 无法提取module内容: {file_path}{Colors.ENDC}")
                # 即使无法提取module内容，也要在依赖关系中添加空列表
                new_dependent_relation[file_path] = []
                continue

            # 生成依赖关系
            dependencies = self._analyze_file_dependencies_2(
                file_path,
                module_content,
                available_file_desc_dict  # 使用动态更新的字典
            )
            
            # 从返回的依赖数据中提取依赖列表
            dependency_list = dependencies.get("dependencies", [])
            new_dependent_relation[file_path] = dependency_list
        
        return new_dependent_relation

    def _extract_import_content(self, content: str) -> str:
        """从文件内容中提取import部分"""
        lines = content.split('\n')
        import_lines = []
        found_import = False
        
        for line in lines:
            # 查找import:开始的行
            if line.strip().startswith('import:'):
                found_import = True
                continue

            # 检查是否应该结束import部分的提取
            elif found_import: 
                stripped_line = line.strip()
                
                # 如果是空行，继续添加（保持格式）
                if not stripped_line:
                    import_lines.append(line)
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
                    # 添加module部分的内容行
                    import_lines.append(line)
        
        return '\n'.join(import_lines)

    def _analyze_file_dependencies_2(
        self,
        file_path: str,
        module_content: str,
        available_file_desc_dict: Dict[str, str]
    ) -> Dict[str, Any]:
        """分析文件依赖关系"""
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        # 使用新的依赖分析提示词模板
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'one_file_req_depend_analyzer_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return {
                "file_path": file_path,
                "dependencies": []
            }

        # 构造可用模块信息（仅包含当前可依赖的模块）
        available_modules_text = '\n\n'.join([
            f"模块路径: {path}\n模块描述: {desc}" 
            for path, desc in available_file_desc_dict.items() 
            if path != file_path
        ])

        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('CURRENT_FILE_REQUIREMENT_PLACEHOLDER', module_content)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('AVAILABLE_MODULES_PLACEHOLDER', available_modules_text if available_modules_text else '暂无其他模块')

        # 调用AI分析依赖关系
        response_content = asyncio.run(self._get_ai_response_2(self.ai_handler_2, user_prompt))
        
        # 移除可能的代码块标记
        cleaned_content = response_content.strip()
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned_content = '\n'.join(lines).strip()
        
        # 解析AI返回的依赖关系
        try:
            # 尝试解析JSON格式的响应
            dependencies_data = json.loads(cleaned_content)
            return dependencies_data
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 解析依赖关系失败: {e}{Colors.ENDC}")
            print(f"  AI返回内容: {cleaned_content}")
            return {
                "file_path": file_path,
                "dependencies": []
            }

    def _generate_dir_content_json(self, proj_root: Dict, dependent_relation: Dict):
        """生成dir_content.json文件"""
        dir_content = {
            "proj_root": proj_root,
            "dependent_relation": dependent_relation
        }
        
        dir_content_file = os.path.join(self.proj_data_dir, "icp_dir_content_final.json")
        try:
            with open(dir_content_file, 'w', encoding='utf-8') as f:
                json.dump(dir_content, f, indent=2, ensure_ascii=False)
            print(f"  {Colors.OKGREEN}目录内容文件已保存: {dir_content_file}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存目录内容文件失败 {dir_content_file}: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证命令的前置条件"""
        # 检查最终目录结构文件是否存在
        final_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        if not os.path.exists(final_dir_file):
            print(f"  {Colors.WARNING}警告: 目录结构文件不存在，请先执行循环依赖解决命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查AI处理器是否初始化成功
        if not hasattr(self, 'ai_handler_1') or self.ai_handler_1 is None:
            print(f"  {Colors.FAIL}错误: {self.role_name_1} AI处理器1未正确初始化{Colors.ENDC}")
            return False
            
        # 检查AI处理器是否连接成功
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

    def _init_ai_handlers(self):
        """初始化AI处理器"""
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
        
        # 优先检查是否有dependency_refine_handler配置
        if 'dependency_refine_handler' in config:
            chat_api_config = config['dependency_refine_handler']
            handler_config = ChatApiConfig(
                base_url=chat_api_config.get('api-url', ''),
                api_key=SecretStr(chat_api_config.get('api-key', '')),
                model=chat_api_config.get('model', '')
            )
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
            handler_config = ChatApiConfig(
                base_url=chat_api_config.get('api-url', ''),
                api_key=SecretStr(chat_api_config.get('api-key', '')),
                model=chat_api_config.get('model', '')
            )
        else:
            print("错误: 配置文件缺少dependency_refine_handler或coder_handler配置")
            return None, None

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

    def _build_file_desc_dict(self, icb_root_path: str, file_creation_order_list: List[str]) -> Dict[str, str]:
        """构建文件描述字典"""
        file_desc_dict = {}
        
        # 遍历所有文件，提取其描述内容
        for file_path in file_creation_order_list:
            req_file_path = os.path.join(icb_root_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_requirement_content = f.read()
                    
                # 提取description部分
                extracted_description = self._extract_description_content(file_requirement_content)
                # 提取func部分
                extracted_func = self._extract_func_content(file_requirement_content)
                # 提取class部分
                extracted_class = self._extract_class_content(file_requirement_content)
                
                # 组合提取的内容
                combined_content = ""
                if extracted_class:
                    combined_content += f"类信息:\n{extracted_class}\n\n"
                if extracted_func:
                    combined_content += f"函数信息:\n{extracted_func}\n\n"
                if extracted_description:
                    combined_content += f"描述信息:\n{extracted_description}"
                
                if combined_content:
                    file_desc_dict[file_path] = combined_content.strip()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
                
        return file_desc_dict

    async def _get_ai_response_1(self, handler: ChatHandler, requirement_content: str) -> str:
        """异步获取AI响应（处理器1）"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name_1}正在生成目录结构...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name_1}运行完毕。")
        return response_content

    async def _get_ai_response_2(self, handler: ChatHandler, requirement_content: str) -> str:
        """异步获取AI响应（处理器2）"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name_2}正在分析依赖关系...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name_2}运行完毕。")
        return response_content