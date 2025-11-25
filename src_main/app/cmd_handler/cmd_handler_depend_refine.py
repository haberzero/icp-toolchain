import sys, os
import asyncio
import json
from typing import List, Dict, Any

from typedef.cmd_data_types import CommandInfo, CmdProcStatus, Colors
from typedef.ai_data_types import ChatApiConfig

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from data_exchange.app_data_manager import get_instance as get_app_data_manager
from data_exchange.user_data_manager import get_instance as get_user_data_manager

from .base_cmd_handler import BaseCmdHandler
from utils.icp_ai_handler import ICPChatHandler
from libs.dir_json_funcs import DirJsonFuncs


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
        self.proj_work_dir = proj_cfg_manager.get_work_dir()
        self.proj_data_dir = os.path.join(self.proj_work_dir, 'icp_proj_data')
        self.proj_config_data_dir = os.path.join(self.proj_work_dir, '.icp_proj_config')
        self.icp_api_config_file = os.path.join(self.proj_config_data_dir, 'icp_api_config.json')

        # 使用新的 ICPChatHandler
        self.chat_handler = ICPChatHandler()
        self.role_name = "6_depend_refine"
        
        # 用于循环依赖信息传递的实例变量
        self.circular_deps_content = None  # 循环依赖信息字符串
        self.dependency_structure_content = None  # 依赖结构内容
        self.first_circle_flag = True  # 是否是第一次运行的标志
        
        # 初始化AI处理器
        self._init_ai_handlers()

    def _validate_response(self, cleaned_content: str) -> tuple[bool, Dict[str, Any]]:
        """
        验证AI响应内容是否符合要求
        
        Args:
            cleaned_content: 清理后的AI响应内容
            
        Returns:
            tuple[bool, Dict[str, Any]]: (是否有效, JSON内容字典)
        """
        # 验证是否为有效的JSON
        try:
            new_json_content = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"{Colors.FAIL}错误: AI返回的内容不是有效的JSON格式: {e}{Colors.ENDC}")
            print(f"AI返回内容: {cleaned_content}")
            return False, {}
        
        # 检查新JSON内容是否包含proj_root和dependent_relation节点
        if "proj_root" not in new_json_content or "dependent_relation" not in new_json_content:
            print(f"{Colors.WARNING}警告: 生成的JSON结构不符合要求，缺少必需的根节点{Colors.ENDC}")
            return False, {}
        
        # 确保dependent_relation中包含proj_root下的所有文件路径
        DirJsonFuncs.ensure_all_files_in_dependent_relation(new_json_content)
        
        # 检测循环依赖
        dependent_relation = new_json_content.get("dependent_relation", {})
        circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
        
        if circular_dependencies:
            # 仍然存在循环依赖，将这些循环依赖信息保存到实例变量中
            print(f"{Colors.WARNING}警告: 仍检测到循环依赖:{Colors.ENDC}")
            for cycle in circular_dependencies:
                print(f"  {Colors.WARNING}{cycle}{Colors.ENDC}")
            
            # 更新实例变量，用于下一轮提示词构建
            self.circular_deps_content = '\n'.join(circular_dependencies)
            self.dependency_structure_content = cleaned_content
            self.first_circle_flag = False
            
            return False, new_json_content
        
        # 所有检查都通过
        return True, new_json_content

    def _build_user_prompt_for_depend_refiner(self) -> str:
        """
        构建依赖修复的用户提示词
        
        从项目数据目录和实例变量中获取所需信息，无需外部参数传递。
        如果是第一次运行（first_circle_flag=True），从文件读取并检测循环依赖；
        如果不是第一次运行，则使用实例变量中保存的最新循环依赖信息。
        
        Returns:
            str: 完整的用户提示词，失败时返回空字符串
        """
        # 读取用户提示词模板
        app_data_manager = get_app_data_manager()
        user_prompt_file = os.path.join(app_data_manager.get_user_prompt_dir(), 'depend_refine_user.md')
        try:
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 读取用户提示词模板失败: {e}{Colors.ENDC}")
            return ""
        
        # 根据是否是第一次运行，选择不同的数据源
        if self.first_circle_flag:
            # 第一次运行，从文件读取依赖分析结果
            depend_analysis_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
            try:
                with open(depend_analysis_file, 'r', encoding='utf-8') as f:
                    depend_content = f.read()
            except Exception as e:
                print(f"  {Colors.FAIL}错误: 读取依赖分析结果失败: {e}{Colors.ENDC}")
                return ""
                
            if not depend_content:
                print(f"  {Colors.FAIL}错误: 依赖分析结果为空{Colors.ENDC}")
                return ""

            # 检测循环依赖
            dependent_relation = json.loads(depend_content)["dependent_relation"]
            circular_dependencies = DirJsonFuncs.detect_circular_dependencies(dependent_relation)
            
            if not circular_dependencies:
                print(f"{Colors.OKBLUE}信息: 未检测到循环依赖，无需执行修复{Colors.ENDC}")
                return ""
            
            # 输出检测到的循环依赖
            print(f"{Colors.WARNING}检测到以下循环依赖:{Colors.ENDC}")
            for cycle in circular_dependencies:
                print(f"  {Colors.WARNING}{cycle}{Colors.ENDC}")

            # 使用检测到的循环依赖信息
            circular_deps_content = '\n'.join(circular_dependencies)
        else:
            # 不是第一次运行，使用实例变量中的最新信息
            circular_deps_content = self.circular_deps_content
            depend_content = self.dependency_structure_content
        
        # 填充占位符
        user_prompt = user_prompt_template
        user_prompt = user_prompt.replace('CIRCULAR_DEPENDENCIES_PLACEHOLDER', circular_deps_content)
        user_prompt = user_prompt.replace('DEPENDENCY_STRUCTURE_PLACEHOLDER', depend_content)
        
        return user_prompt

    def execute(self):
        """执行循环依赖解决"""
        if not self.is_cmd_valid():
            return
        
        # 重置实例变量，确保每次execute都是干净的状态
        self.circular_deps_content = None
        self.dependency_structure_content = None
        self.first_circle_flag = True
        
        print(f"{Colors.OKBLUE}开始解决循环依赖问题...{Colors.ENDC}")
        
        max_attempts = 5
        new_json_content = {}
        
        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1} 次尝试...")
            
            # 构建用户提示词（会根据first_circle_flag自动选择数据源）
            user_prompt = self._build_user_prompt_for_depend_refiner()
            if not user_prompt:
                # 如果是第一次且没有循环依赖，直接返回
                if self.first_circle_flag:
                    return
                # 理论上不应出现的情况，抛出错误提示
                print(f"{Colors.FAIL}错误: 构建用户提示词失败，出现未知错误，请开发人员检查逻辑{Colors.ENDC}")
                return
            
            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                user_prompt=user_prompt
            ))
            
            # 如果响应失败，继续下一次尝试
            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue
                
            # 清理代码块标记
            cleaned_content = ICPChatHandler.clean_code_block_markers(response_content)
            
            # 验证响应内容（包含所有检查：JSON有效性、结构完整性、循环依赖检测）
            is_valid, new_json_content = self._validate_response(cleaned_content)
            if is_valid:
                # 所有检查都通过，跳出循环
                break
        
        # 清空实例变量，避免干扰下一次运行
        self.circular_deps_content = None
        self.dependency_structure_content = None
        self.first_circle_flag = True
        
        # 循环已跳出，检查运行结果并进行相应操作
        if attempt == max_attempts - 1:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能成功消除循环依赖{Colors.ENDC}")
            return

        print(f"{Colors.OKBLUE}循环依赖解决完成，正在保存结果...{Colors.ENDC}")
        output_file = os.path.join(self.proj_data_dir, 'icp_dir_content_refined.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(new_json_content, f, indent=2)
            print(f"{Colors.OKBLUE}循环依赖解决完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")

    def _check_cmd_requirement(self) -> bool:
        """验证解决循环依赖命令的前置条件"""
        # 检查依赖分析结果文件是否存在
        depend_analysis_file = os.path.join(self.proj_data_dir, 'icp_dir_content_with_depend.json')
        if not os.path.exists(depend_analysis_file):
            print(f"  {Colors.WARNING}警告: 依赖分析结果文件不存在，请先执行依赖分析命令{Colors.ENDC}")
            return False
        
        return True


    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查共享的ChatInterface是否初始化
        if not ICPChatHandler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False
        
        # 检查角色是否已加载
        if not self.chat_handler.has_role(self.role_name):
            print(f"  {Colors.FAIL}错误: 角色 {self.role_name} 未加载{Colors.ENDC}")
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
            return
        
        try:
            with open(self.icp_api_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"错误: 读取配置文件失败: {e}")
            return
        
        # 优先检查是否有dependency_refine_handler配置
        if 'dependency_refine_handler' in config:
            chat_api_config = config['dependency_refine_handler']
        elif 'coder_handler' in config:
            chat_api_config = config['coder_handler']
        else:
            print("错误: 配置文件缺少dependency_refine_handler或coder_handler配置")
            return
        
        handler_config = ChatApiConfig(
            base_url=chat_api_config.get('api-url', ''),
            api_key=chat_api_config.get('api-key', ''),
            model=chat_api_config.get('model', '')
        )
        
        # 初始化共享的ChatInterface（只初始化一次）
        if not ICPChatHandler.is_initialized():
            ICPChatHandler.initialize_chat_interface(handler_config)
        
        # 加载角色的系统提示词
        app_data_manager = get_app_data_manager()
        prompt_dir = app_data_manager.get_prompt_dir()
        prompt_file_name = self.role_name + ".md"
        sys_prompt_path = os.path.join(prompt_dir, prompt_file_name)
        
        # 从文件加载角色提示词
        self.chat_handler.load_role_from_file(self.role_name, sys_prompt_path)