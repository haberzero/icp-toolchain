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


class CmdHandlerIcbGen(BaseCmdHandler):
    """将单文件需求描述转换为半自然语言行为描述代码"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="intent_code_behavior_gen",
            aliases=["ICB"],
            description="将单文件需求描述转换为半自然语言行为描述代码",
            help_text="根据单文件需求描述生成符合半自然语言行为描述语法的代码结构",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.icp_proj_data_dir
        self.ai_handler: ChatHandler
        self.role_name = "8_intent_code_behavior_gen"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行半自然语言行为描述代码生成"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始生成半自然语言行为描述代码...{Colors.ENDC}")

        # 读取ICB目录结构
        icb_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        try:
            with open(icb_dir_file, 'r', encoding='utf-8') as f:
                icb_content = json.load(f)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取ICB目录结构失败: {e}{Colors.ENDC}")
            return
        
        if not icb_content:
            print(f"  {Colors.FAIL}错误: ICB目录结构内容为空{Colors.ENDC}")
            return

        # 检查是否包含必要的节点
        if "proj_root" not in icb_content or "dependent_relation" not in icb_content:
            print(f"  {Colors.FAIL}错误: ICB目录结构缺少必要的节点(proj_root或dependent_relation){Colors.ENDC}")
            return

        # 从dependent_relation中获取文件创建顺序
        proj_root = icb_content["proj_root"]
        dependent_relation = icb_content["dependent_relation"]
        file_creation_order_list = DirJsonFuncs.build_file_creation_order(dependent_relation)
        
        # 获取ICB目录名称
        icb_dir_name = self._get_icb_directory_name()
        
        # 构建ICB目录路径
        icb_root_path = os.path.join(self.work_dir, icb_dir_name)
        
        # 构建_src_staging目录路径
        staging_dir_path = os.path.join(self.work_dir, '_src_staging')
        
        # 检查_src_staging目录是否存在
        if not os.path.exists(staging_dir_path):
            print(f"  {Colors.FAIL}错误: _src_staging目录不存在，请先执行one_file_req_gen命令创建目录结构{Colors.ENDC}")
            return
        
        # 为每个单文件生成半自然语言行为描述代码
        self._generate_intent_code_behavior(icb_root_path, staging_dir_path, proj_root, file_creation_order_list, dependent_relation)
        
        print(f"{Colors.OKGREEN}半自然语言行为描述代码生成命令执行完毕!{Colors.ENDC}")

    def _get_icb_directory_name(self) -> str:
        """获取ICB目录名称，优先从配置文件读取behavioral_layer_dir，失败则使用默认值"""
        icp_config_file = os.path.join(self.icp_proj_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            
            # 尝试获取behavioral_layer_dir
            behavioral_layer_dir = icp_config["file_system_mapping"].get("behavioral_layer_dir")
            if behavioral_layer_dir:
                return behavioral_layer_dir
            else:
                return "ICB"
        except FileNotFoundError:
            return "ICB"
        except json.JSONDecodeError as e:
            return "ICB"
        except Exception as e:
            return "ICB"

    def _generate_intent_code_behavior(
            self, 
            icb_root_path: str,
            staging_dir_path: str,  # 添加_src_staging目录路径参数
            proj_root_content: Dict, 
            file_creation_order_list: List[str],
            dependent_relation: Dict[str, List[str]]
        ) -> None:
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
        
        # 按照依赖顺序为每个文件生成半自然语言行为描述代码
        for file_path in file_creation_order_list:
            # 从_src_staging目录读取文件需求描述
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            try:
                with open(req_file_path, 'r', encoding='utf-8') as f:
                    file_req_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取文件需求描述失败 {req_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 为每个文件生成半自然语言行为描述代码
            print(f"  {Colors.OKBLUE}正在为文件生成半自然语言行为描述代码: {file_path}{Colors.ENDC}")
            
            # 获取依赖于当前文件的文件列表（即当前文件被哪些文件依赖）
            dependent_files = [f for f, deps in dependent_relation.items() if file_path in deps]
            
            # 构建可用文件描述字典（仅包含已处理过的文件）
            available_file_desc_dict = {k: v for k, v in accumulated_descriptions_dict.items() 
                                      if k in dependent_relation.get(file_path, [])}
            
            # 生成新的半自然语言行为描述代码
            intent_code_behavior = self._create_intent_code_behavior(
                file_path,
                file_req_content,
                user_requirements,
                list(available_file_desc_dict.values()),
                proj_root_content  # 传递proj_root_content用于生成项目结构
            )

            # 移除可能的代码块标记
            lines = intent_code_behavior.split('\n')  # 修复错误的变量名
            if lines and lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            cleaned_content = '\n'.join(lines).strip()
            
            if intent_code_behavior:
                # 保存半自然语言行为描述代码到ICB目录下的文件
                self._save_intent_code_behavior(icb_root_path, file_path, cleaned_content)
                
                # 将当前文件的描述添加到累积字典中，供后续文件参考
                accumulated_descriptions_dict[file_path] = f"文件 {file_path} 的接口描述:\n{file_req_content}"
            else:
                print(f"  {Colors.WARNING}警告: 未能为文件生成半自然语言行为描述代码: {file_path}{Colors.ENDC}")

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

    def _create_intent_code_behavior(
        self, 
        file_path: str, 
        file_req_content: str,
        user_requirements: str,
        available_descriptions: List[str],
        proj_root_content: Dict
    ) -> str:
        """创建新的半自然语言行为描述代码"""
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'intent_code_behavior_gen_user.md')
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

        # 调用AI生成半自然语言行为描述代码
        response_content = asyncio.run(self._get_ai_response(self.ai_handler, user_prompt))
        return response_content

    def _save_intent_code_behavior(self, icb_root_path: str, file_path: str, content: str):
        """保存半自然语言行为描述代码到文件"""
        behavior_file_path = os.path.join(icb_root_path, f"{file_path}.icb")
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
        # 检查ICB目录结构文件是否存在
        icb_dir_file = os.path.join(self.proj_data_dir, 'icp_dir_content_final.json')
        if not os.path.exists(icb_dir_file):
            print(f"  {Colors.WARNING}警告: ICB目录结构文件不存在，请先执行one_file_req_gen命令{Colors.ENDC}")
            return False
        
        return True
    
    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        return hasattr(self, 'ai_handler') and self.ai_handler is not None

    def _init_ai_handlers(self):
        """初始化AI处理器"""

        # 检查配置文件是否存在
        if not os.path.exists(self.icp_api_config_file):
            print(f"错误: 配置文件 {self.icp_api_config_file} 不存在，请创建该文件并填充必要内容")
            return None
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return None
        
        # 优先检查是否有intent_code_behavior_gen_handler配置
        if 'intent_code_behavior_gen_handler' in config:
            chat_api_config = config['intent_code_behavior_gen_handler']
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
            print("错误: 配置文件缺少intent_code_behavior_gen_handler或coder_handler配置")
            return None

        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        sys_prompt_path = os.path.join(prompt_dir, prompt_file_name)

        return ChatHandler(handler_config, self.role_name, sys_prompt_path)
    
    async def _get_ai_response(self, handler: ChatHandler, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name}正在生成半自然语言行为描述代码...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content