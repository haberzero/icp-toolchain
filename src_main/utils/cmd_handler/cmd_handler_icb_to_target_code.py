import sys, os
import asyncio
import json
from typing import List, Dict, Any
from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from cfg.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from utils.ai_handler.chat_handler import ChatHandler
from libs.dir_json_funcs import DirJsonFuncs


class CmdHandlerIbcToTargetCode(BaseCmdHandler):
    """将IBC半自然语言行为描述代码转换为目标编程语言代码"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="ibc_to_target_code",
            aliases=["GG"],
            description="将IBC半自然语言行为描述代码转换为目标编程语言代码",
            help_text="根据IBC行为描述生成符合目标编程语言语法的可执行代码",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.icp_proj_data_dir
        self.ai_handler: ChatHandler
        self.role_name = "9_ibc_to_target_code"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行IBC到目标代码的转换"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始将IBC行为描述转换为目标编程语言代码...{Colors.ENDC}")

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
        
        # 获取目标代码目录名称
        target_dir_name = self._get_target_directory_name()
        
        # 获取IBC目录名称
        ibc_dir_name = self._get_ibc_directory_name()
        
        # 构建IBC目录路径
        ibc_root_path = os.path.join(self.work_dir, ibc_dir_name)
        
        # 检查IBC目录是否存在
        if not os.path.exists(ibc_root_path):
            print(f"  {Colors.FAIL}错误: IBC目录不存在，请先执行one_file_req_gen命令创建目录结构{Colors.ENDC}")
            return
        
        # 为每个IBC文件生成目标编程语言代码
        self._generate_target_code(ibc_root_path, proj_root, file_creation_order_list, dependent_relation)
        
        print(f"{Colors.OKGREEN}目标编程语言代码生成命令执行完毕!{Colors.ENDC}")

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
                return "IBC"
        except FileNotFoundError:
            return "IBC"
        except json.JSONDecodeError as e:
            return "IBC"
        except Exception as e:
            return "IBC"

    def _generate_target_code(
            self, 
            ibc_root_path: str, 
            proj_root_content: Dict, 
            file_creation_order_list: List[str],
            dependent_relation: Dict[str, List[str]]
        ) -> None:
        """为每个文件生成目标编程语言代码"""
        # 读取用户原始需求文本
        user_data_manager = get_user_data_manager()
        user_requirements = user_data_manager.get_user_prompt()
        
        # 检查用户原始需求是否存在
        if not user_requirements:
            print(f"  {Colors.FAIL}错误: 未找到用户原始需求，请确认需求已正确加载{Colors.ENDC}")
            return

        # 获取目标编程语言
        target_language = self._get_target_language()
        if not target_language:
            print(f"  {Colors.FAIL}错误: 无法获取目标编程语言{Colors.ENDC}")
            return

        # 初始化累积代码字典，用于为后续文件生成提供依赖内容
        accumulated_code_dict = {}
        
        # 按照依赖顺序为每个文件生成目标编程语言代码
        for file_path in file_creation_order_list:
            # 读取IBC文件内容
            ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
            try:
                with open(ibc_file_path, 'r', encoding='utf-8') as f:
                    ibc_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取IBC文件失败 {ibc_file_path}: {e}{Colors.ENDC}")
                continue
            
            # 为每个文件生成目标编程语言代码
            print(f"  {Colors.OKBLUE}正在为文件生成目标编程语言代码: {file_path}{Colors.ENDC}")
            
            # 获取依赖于当前文件的文件列表（即当前文件被哪些文件依赖）
            dependent_files = [f for f, deps in dependent_relation.items() if file_path in deps]
            
            # 构建可用文件代码字典（仅包含已处理过的文件）
            available_file_code_dict = {k: v for k, v in accumulated_code_dict.items() 
                                      if k in dependent_relation.get(file_path, [])}
            
            # 生成目标编程语言代码
            target_code = self._create_target_code(
                file_path,
                ibc_content,
                target_language,
                proj_root_content,  # 传递proj_root_content用于生成项目结构
                available_file_code_dict  # 传递依赖文件的内容
            )

            # 移除可能的代码块标记
            lines = target_code.split('\n')
            if lines and lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            target_code = '\n'.join(lines).strip()
            
            if target_code:
                # 保存目标编程语言代码到文件
                self._save_target_code(file_path, target_code, target_language)
                
                # 将当前文件的代码添加到累积字典中，供后续文件参考
                accumulated_code_dict[file_path] = target_code
            else:
                print(f"  {Colors.WARNING}警告: 未能为文件生成目标编程语言代码: {file_path}{Colors.ENDC}")

    def _get_target_language(self) -> str:
        """从icp_config.json获取目标编程语言"""
        icp_config_file = os.path.join(self.icp_proj_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            
            # 获取target_language
            target_language = icp_config.get("target_language")
            if target_language:
                return target_language
            else:
                print(f"  {Colors.WARNING}警告: icp_config.json中未配置target_language，使用默认值'Python'{Colors.ENDC}")
                return "Python"
        except FileNotFoundError:
            print(f"  {Colors.WARNING}警告: 未找到icp_config.json文件，使用默认值'Python'{Colors.ENDC}")
            return "Python"
        except json.JSONDecodeError as e:
            print(f"  {Colors.WARNING}警告: icp_config.json解析失败，使用默认值'Python'{Colors.ENDC}")
            return "Python"
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 获取目标编程语言时发生错误，使用默认值'Python': {e}{Colors.ENDC}")
            return "Python"

    def _get_target_directory_name(self) -> str:
        """获取目标代码目录名称，优先从配置文件读取target_layer_dir，失败则使用默认值"""
        icp_config_file = os.path.join(self.icp_proj_data_dir, 'icp_config.json')
        try:
            with open(icp_config_file, 'r', encoding='utf-8') as f:
                icp_config = json.load(f)
            
            # 尝试获取target_layer_dir
            target_layer_dir = icp_config["file_system_mapping"].get("target_layer_dir")
            if target_layer_dir:
                return target_layer_dir
            else:
                return "target_code"
        except FileNotFoundError:
            return "target_code"
        except json.JSONDecodeError as e:
            return "target_code"
        except Exception as e:
            return "target_code"

    def _create_target_code(
        self, 
        file_path: str, 
        ibc_content: str,
        target_language: str,
        proj_root_content: Dict,
        dependent_files_content: Dict[str, str]
    ) -> str:
        """创建目标编程语言代码"""
        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'ibc_to_target_code_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
            
        # 将proj_root_content转换为JSON格式的项目结构字符串
        project_structure_json = json.dumps(proj_root_content, indent=2, ensure_ascii=False)
        
        # 构建依赖文件内容字符串
        dependent_files_content_str = "\n\n".join([
            f"文件 {dep_file_path} 的内容:\n{dep_content}" 
            for dep_file_path, dep_content in dependent_files_content.items()
        ]) if dependent_files_content else "暂无依赖文件内容"
        
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('TARGET_LANGUAGE_PLACEHOLDER', target_language)
        user_prompt = user_prompt.replace('PROJECT_STRUCTURE_PLACEHOLDER', project_structure_json)
        user_prompt = user_prompt.replace('CURRENT_FILE_PATH_PLACEHOLDER', file_path)
        user_prompt = user_prompt.replace('IBC_CONTENT_PLACEHOLDER', ibc_content)
        user_prompt = user_prompt.replace('DEPENDENT_FILES_CONTENT_PLACEHOLDER', dependent_files_content_str)

        # 调用AI生成目标编程语言代码
        response_content = asyncio.run(self._get_ai_response(self.ai_handler, user_prompt))
        return response_content

    def _save_target_code(self, file_path: str, content: str, target_language: str):
        """保存目标编程语言代码到文件"""
        # 根据目标语言确定文件扩展名
        extension_map = {
            "Python": ".py",
            "Java": ".java",
            "JavaScript": ".js",
            "TypeScript": ".ts",
            "C++": ".cpp",
            "C": ".c",
            "Go": ".go",
            "Rust": ".rs"
        }
        
        extension = extension_map.get(target_language, ".txt")
        
        # 获取目标代码目录名称
        target_dir_name = self._get_target_directory_name()
        target_file_path = os.path.join(self.work_dir, target_dir_name, f"{file_path}{extension}")
        
        # 确保目标目录存在
        target_dir = os.path.dirname(target_file_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        try:
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  {Colors.OKGREEN}目标编程语言代码已保存: {target_file_path}{Colors.ENDC}")
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 保存目标编程语言代码失败 {target_file_path}: {e}{Colors.ENDC}")

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
        
        # 优先检查是否有coder_handler配置
        if 'coder_handler' in config:
            chat_api_config = config['coder_handler']
            handler_config = ChatApiConfig(
                base_url=chat_api_config.get('api-url', ''),
                api_key=SecretStr(chat_api_config.get('api-key', '')),
                model=chat_api_config.get('model', '')
            )
        else:
            print("错误: 配置文件缺少coder_handler配置")
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
            
        print(f"{self.role_name}正在生成目标编程语言代码...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content