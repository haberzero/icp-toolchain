import sys, os
import asyncio
import json
from typing import List, Dict, Any

from pydantic import SecretStr

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, ChatApiConfig, Colors

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from utils.cmd_handler.base_cmd_handler import BaseCmdHandler
from libs.ai_interface.chat_interface import ChatInterface
from libs.dir_json_funcs import DirJsonFuncs


DEBUG_FLAG = False


class CmdHandlerDependAnalysis(BaseCmdHandler):
    """依赖分析指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="depend_analysis",
            aliases=["DA"],
            description="分析项目依赖关系",
            help_text="根据目录结构分析并生成项目依赖关系",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_data_dir, 'icp_api_config.json')

        self.ai_handler: ChatInterface
        self.role_name = "5_depend_analyzer"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行依赖分析"""
        if not self.is_cmd_valid():
            return
            
        print(f"{Colors.OKBLUE}开始进行依赖分析...{Colors.ENDC}")
        
        # 读取精炼需求
        refined_requirement_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        try:
            with open(refined_requirement_file, 'r', encoding='utf-8') as f:
                refined_requirement_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取精炼需求失败: {e}{Colors.ENDC}")
            return
            
        if not refined_requirement_content:
            print(f"  {Colors.FAIL}错误: 精炼需求内容为空{Colors.ENDC}")
            return
            
        # 读取带文件描述的目录结构
        dir_with_files_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_files.json')
        try:
            with open(dir_with_files_file, 'r', encoding='utf-8') as f:
                dir_with_files_content = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取带文件描述的目录结构失败: {e}{Colors.ENDC}")
            return
            
        if not dir_with_files_content:
            print(f"  {Colors.FAIL}错误: 带文件描述的目录结构内容为空{Colors.ENDC}")
            return

        # 读取原始目录结构用于后续比对
        try:
            old_json_content = json.loads(dir_with_files_content)
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 原始目录结构不是有效的JSON格式: {e}{Colors.ENDC}")
            return

        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'depend_analysis_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return
            
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('PROGRAMMING_REQUIREMENT_PLACEHOLDER', refined_requirement_content)
        user_prompt = user_prompt.replace('JSON_STRUCTURE_PLACEHOLDER', dir_with_files_content)
        
        max_attempts = 5
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            response_content = asyncio.run(self._get_ai_response(self.ai_handler, user_prompt))
            cleaned_content = response_content.strip()

            # 移除可能的代码块标记
            lines = cleaned_content.split('\n')
            if lines and lines[0].strip().startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            cleaned_content = '\n'.join(lines).strip()
            
            # 验证是否为有效的JSON
            try:
                new_json_content = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
                print(f"AI返回内容: {cleaned_content}")
                continue
            
            # 检查新JSON内容是否包含必需的根节点
            if "proj_root" not in new_json_content or "dependent_relation" not in new_json_content:
                print(f"{Colors.WARNING}警告: 生成的JSON缺少必需的根节点 proj_root 或 dependent_relation{Colors.ENDC}")
                continue
            
            # 检查proj_root结构是否与原始结构一致
            if not DirJsonFuncs.compare_structure(old_json_content["proj_root"], new_json_content["proj_root"]):
                print(f"{Colors.WARNING}警告: proj_root结构与原始结构不一致{Colors.ENDC}")
                continue
                
            # 检查dependent_relation中的依赖路径是否都存在于proj_root中
            if not DirJsonFuncs.validate_dependent_paths(new_json_content["dependent_relation"], new_json_content["proj_root"]):
                print(f"{Colors.WARNING}警告: 生成的 dependent_relation 出现了 proj_root 下不存在的路径{Colors.ENDC}")
                continue
            
            # 检查是否存在循环依赖
            circular_dependencies = DirJsonFuncs.detect_circular_dependencies(new_json_content["dependent_relation"])
            
            if circular_dependencies:
                # 存在循环依赖，将循环依赖信息保存到文件中
                circular_deps_file = os.path.join(self.proj_data_dir, 'circular_dependencies.txt')
                try:
                    with open(circular_deps_file, 'w', encoding='utf-8') as f:
                        for cycle in circular_dependencies:
                            f.write(f"{cycle}\n")
                    print(f"检测到循环依赖，已保存到: {circular_deps_file}")
                    
                    # 仍然保存依赖分析结果到icp_dir_content_with_depend.json
                    output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(cleaned_content)
                        print(f"依赖分析结果已保存到: {output_file}")
                        return  # 成功则退出循环
                    except Exception as e:
                        print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
                        return
                except Exception as e:
                    print(f"{Colors.FAIL}错误: 保存循环依赖信息失败: {e}{Colors.ENDC}")
                    return
            else:
                # 保存结果到icp_dir_content_with_depend.json
                output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
                circular_deps_file = os.path.join(self.proj_data_dir, 'circular_dependencies.txt')
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(cleaned_content)
                    print(f"依赖分析完成，结果已保存到: {output_file}")
                    with open(circular_deps_file, 'w', encoding='utf-8') as f:
                        f.write("")
                    print(f"未检测到循环依赖，循环依赖结果文本 {circular_deps_file} 已清空")
                    return  # 成功则退出循环
                except Exception as e:
                    print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
                    return
                
        print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的依赖关系{Colors.ENDC}")


    def _check_cmd_requirement(self) -> bool:
        """验证依赖分析命令的前置条件"""
        # 检查精炼需求文件是否存在
        refined_requirement_file = os.path.join(self.proj_data_dir, 'refined_requirements.json')
        if not os.path.exists(refined_requirement_file):
            print(f"  {Colors.WARNING}警告: 精炼需求文件不存在，请先执行需求分析命令{Colors.ENDC}")
            return False
            
        # 检查带文件描述的目录结构文件是否存在
        dir_with_files_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_files.json')
        if not os.path.exists(dir_with_files_file):
            print(f"  {Colors.WARNING}警告: 带文件描述的目录结构文件不存在，请先执行目录文件填充命令{Colors.ENDC}")
            return False
        
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查AI处理器是否初始化成功
        if not hasattr(self, 'ai_handler') or self.ai_handler is None:
            print(f"  {Colors.FAIL}错误: {self.role_name} AI处理器未正确初始化{Colors.ENDC}")
            return False
            
        # 检查AI处理器是否连接成功
        if not hasattr(self.ai_handler, 'llm') or self.ai_handler.llm is None:
            print(f"  {Colors.FAIL}错误: {self.role_name} AI模型连接失败{Colors.ENDC}")
            return False
            
        return True

    def is_cmd_valid(self):
        """检查依赖分析命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

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
        
        # 优先检查是否有depend_analysis_handler配置
        if 'depend_analysis_handler' in config:
            chat_api_config = config['depend_analysis_handler']
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
            print("错误: 配置文件缺少depend_analysis_handler或coder_handler配置")
            return None

        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        sys_prompt_path = os.path.join(prompt_dir, prompt_file_name)

        return ChatInterface(handler_config, self.role_name, sys_prompt_path)
    
    async def _get_ai_response(self, handler: ChatInterface, requirement_content: str) -> str:
        """异步获取AI响应"""
        response_content = ""
        def collect_response(content):
            nonlocal response_content
            response_content += content
            # 实时在CLI中显示AI回复
            print(content, end="", flush=True)
            
        print(f"{self.role_name}正在进行依赖分析...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content