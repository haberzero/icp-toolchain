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


DEBUG_FLAG = False


class CmdHandlerDependRefine(BaseCmdHandler):
    """解决循环依赖指令"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="dependency_refine",
            aliases=["DR"],
            description="解决项目中的循环依赖问题",
            help_text="根据检测到的循环依赖信息，重构依赖结构以解决循环依赖问题",
        )
        proj_cfg_manager = get_proj_cfg_manager()
        self.work_dir = proj_cfg_manager.get_work_dir()
        self.icp_proj_data_dir = os.path.join(self.work_dir, '.icp_proj_data')
        self.icp_api_config_file = os.path.join(self.icp_proj_data_dir, 'icp_api_config.json')
        
        self.proj_data_dir = self.icp_proj_data_dir
        self.ai_handler: ChatHandler
        self.role_name = "6_depend_refine"
        ai_handler = self._init_ai_handlers()
        if ai_handler is not None:
            self.ai_handler = ai_handler
            self.ai_handler.init_chat_chain()

    def execute(self):
        """执行循环依赖解决"""
        if not self.is_cmd_valid():
            return
        
        print(f"{Colors.OKBLUE}开始解决循环依赖问题...{Colors.ENDC}")
        
        # 读取依赖分析结果
        depend_analysis_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
        try:
            with open(depend_analysis_file, 'r', encoding='utf-8') as f:
                depend_content = f.read()
                new_json_content = json.loads(depend_content)
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取依赖分析结果失败: {e}{Colors.ENDC}")
            return
            
        if not depend_content:
            print(f"  {Colors.FAIL}错误: 依赖分析结果为空{Colors.ENDC}")
            return

        # 读取循环依赖信息
        circular_deps_file = os.path.join(self.proj_data_dir, 'circular_dependencies.txt')
        try:
            with open(circular_deps_file, 'r', encoding='utf-8') as f:
                circular_deps_content = f.read().strip()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取循环依赖信息失败: {e}{Colors.ENDC}")
            return
        
        if not circular_deps_content:
            print(f"  {Colors.OKBLUE}信息: 循环依赖信息为空，没有检测到循环依赖，无需执行{Colors.ENDC}")

        # 构建用户提示词
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'depend_refine_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return
            
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('CIRCULAR_DEPENDENCIES_PLACEHOLDER', circular_deps_content)
        user_prompt = user_prompt.replace('DEPENDENCY_STRUCTURE_PLACEHOLDER', depend_content)
        
        attempt = 0
        if not circular_deps_content:
            max_attempts = 0
        else:
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
            
            # 检查新JSON内容是否包含proj_root和dependent_relation节点
            if "proj_root" not in new_json_content or "dependent_relation" not in new_json_content:
                print(f"{Colors.WARNING}警告: 第 {attempt + 1} 次尝试生成的JSON结构不符合要求，正在重新生成...{Colors.ENDC}")
                continue
                
            # 验证循环依赖是否已被消除
            dependent_relation = new_json_content.get("dependent_relation", {})
            circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
            
            if not circular_dependencies:
                # 循环依赖已消除，跳出循环
                break
            else:
                # 仍然存在循环依赖，将这些循环依赖信息反馈给AI进行下一轮尝试
                print(f"{Colors.WARNING}警告: 第 {attempt + 1} 次尝试后仍检测到循环依赖:{Colors.ENDC}")
                for cycle in circular_dependencies:
                    print(f"  {Colors.WARNING}{cycle}{Colors.ENDC}")
                # 更新提示词，包含最新的循环依赖信息
                user_prompt = user_prompt_template
                user_prompt = user_prompt.replace('CIRCULAR_DEPENDENCIES_PLACEHOLDER', circular_deps_content)
                user_prompt = user_prompt.replace('DEPENDENCY_STRUCTURE_PLACEHOLDER', cleaned_content)
                # 在下一轮尝试中使用更新后的依赖结构
        
        # 循环已跳出，检查运行结果并进行相应操作
        if max_attempts == 0 or attempt < max_attempts - 1:
            print(f"{Colors.OKBLUE}循环依赖解决完成，正在保存结果...{Colors.ENDC}")
            # 确保dependent_relation中包含proj_root下的所有文件路径
            DirJsonFuncs.ensure_all_files_in_dependent_relation(new_json_content)
            output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(new_json_content, f, indent=2)
                print(f"循环依赖解决完成，结果已保存到: {output_file}")
                return
            except Exception as e:
                print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")
                return
        elif attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能成功消除循环依赖{Colors.ENDC}")
            return
        else:
            print(f"{Colors.OKBLUE}代码运行结果错误！此行输出理论上来说不应该出现，请开发人员检查逻辑！{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证解决循环依赖命令的前置条件"""
        # 检查依赖分析结果文件是否存在
        depend_analysis_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
        if not os.path.exists(depend_analysis_file):
            print(f"  {Colors.WARNING}警告: 依赖分析结果文件不存在，请先执行依赖分析命令{Colors.ENDC}")
            return False
            
        # 检查循环依赖文件是否存在
        circular_deps_file = os.path.join(self.proj_data_dir, 'circular_dependencies.txt')
        if not os.path.exists(circular_deps_file):
            print(f"  {Colors.WARNING}警告: 循环依赖文件不存在{Colors.ENDC}")
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
        """检查解决循环依赖命令的必要条件是否满足"""
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
            
        print(f"{self.role_name}正在解决循环依赖...")
        await handler.stream_response(requirement_content, collect_response)
        print(f"\n{self.role_name}运行完毕。")
        return response_content