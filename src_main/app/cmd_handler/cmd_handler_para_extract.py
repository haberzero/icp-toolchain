import asyncio
import json
import os
import sys
from typing import Tuple

from app.sys_prompt_manager import get_instance as get_sys_prompt_manager
from data_store.user_data_store import get_instance as get_user_data_store
from libs.text_funcs import ChatResponseCleaner
from run_time_cfg.proj_run_time_cfg import \
    get_instance as get_proj_run_time_cfg
from typedef.cmd_data_types import CmdProcStatus, Colors, CommandInfo
from utils.icp_ai_utils.icp_chat_inst import ICPChatInsts
from utils.issue_recorder import TextIssueRecorder

from .base_cmd_handler import BaseCmdHandler


class CmdHandlerParaExtract(BaseCmdHandler):
    """参数提取命令处理器"""
    
    def __init__(self):
        super().__init__()
        self.command_info = CommandInfo(
            name="para_extract",
            aliases=["PE"],
            description="从用户初始编程需求中提取参数",
            help_text="对用户需求进行解析，并且从中提取出关键的参数，供后续步骤使用",
        )
        # 关联系统提示词角色名
        self.role_name = "1_param_extractor"

        # 路径配置
        proj_run_time_cfg = get_proj_run_time_cfg()
        self.work_dir_path = proj_run_time_cfg.get_work_dir_path()
        self.work_data_dir_path = os.path.join(self.work_dir_path, 'icp_proj_data')
        self.work_config_dir_path = os.path.join(self.work_dir_path, '.icp_proj_config')
        self.work_api_config_file_path = os.path.join(self.work_config_dir_path, 'icp_api_config.json')

        # 获取coder_handler单例
        self.chat_handler = ICPChatInsts.get_instance(handler_key='coder_handler')

        # 提示词管理器
        self.sys_prompt_manager = get_sys_prompt_manager()

        # issue recorder
        self.issue_recorder = TextIssueRecorder()
        self.last_error_msg = ""  # 记录最近一次验证失败的原因

    def execute(self):
        """执行参数提取"""
        if not self.is_cmd_valid():
            return

        print(f"{Colors.OKBLUE}开始提取参数...{Colors.ENDC}")
        requirement_content = get_user_data_store().get_user_prompt()
        if not requirement_content:
            print(f"{Colors.FAIL}错误: 未找到用户需求内容{Colors.ENDC}")
            return

        max_attempts = 3
        cleaned_content = ""
        is_valid = False

        for attempt in range(max_attempts):
            print(f"{self.role_name}正在进行第 {attempt + 1}/{max_attempts} 次尝试...")

            base_sys_prompt = self.sys_prompt_manager.get_prompt(self.role_name)

            # 根据是否是重试来构造用户提示词
            current_user_prompt = requirement_content
            if attempt > 0 and self.last_error_msg:
                retry_hint = (
                    "上一次生成的参数模型存在以下问题，请在本次生成时进行修正：\n"
                    f"{self.last_error_msg}\n\n"
                    "请重新给出符合规范的参数模型JSON。"
                )
                current_user_prompt = requirement_content + "\n\n" + retry_hint

            response_content, success = asyncio.run(self.chat_handler.get_role_response(
                role_name=self.role_name,
                sys_prompt=base_sys_prompt,
                user_prompt=current_user_prompt
            ))

            if not success:
                print(f"{Colors.WARNING}警告: AI响应失败，将进行下一次尝试{Colors.ENDC}")
                continue

            if not response_content:
                print(f"{Colors.WARNING}警告: AI响应为空，将进行下一次尝试{Colors.ENDC}")
                continue

            # 清理代码块标记
            cleaned = ChatResponseCleaner.clean_code_block_markers(response_content)

            # 验证响应内容
            is_valid, error_msg = self._validate_response(cleaned)
            if is_valid:
                cleaned_content = cleaned
                break

            # 记录最近一次错误信息，用于下一次重试提示
            self.last_error_msg = error_msg or ""

        if not is_valid:
            print(f"{Colors.FAIL}错误: 达到最大尝试次数，未能生成符合要求的参数模型{Colors.ENDC}")
            return

        # 保存结果到extracted_params.json
        os.makedirs(self.work_data_dir_path, exist_ok=True)
        output_file = os.path.join(self.work_data_dir_path, 'extracted_params.json')
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"{Colors.OKGREEN}参数提取完成，结果已保存到: {output_file}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}错误: 保存文件失败: {e}{Colors.ENDC}")

    def _validate_response(self, cleaned_json_str: str) -> Tuple[bool, str]:
        """验证AI响应内容是否符合参数提取结果的基本结构要求

        Args:
            cleaned_json_str: 清理后的AI响应内容

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息；当有效时错误信息为空字符串)
        """
        # 尝试解析为JSON
        try:
            json_dict = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            error_msg = f"AI返回的内容不是有效的JSON格式: {e}"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            return False, error_msg

        if not isinstance(json_dict, dict):
            error_msg = "参数提取结果的顶层结构必须是对象（JSON Object）"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            return False, error_msg

        # 检查 important_param / suggested_param 至少存在一个
        important = json_dict.get("important_param")
        suggested = json_dict.get("suggested_param")

        if important is None and suggested is None:
            error_msg = "参数提取结果缺少 important_param 和 suggested_param 两个顶层字段中的至少一个"
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            return False, error_msg

        def _validate_param_section(section_name: str, section_value) -> Tuple[bool, str]:
            if section_value is None:
                return True, ""

            if not isinstance(section_value, dict):
                msg = f"字段 {section_name} 的值必须是对象（字典），当前类型: {type(section_value)}"
                return False, msg

            for param_name, param_info in section_value.items():
                if not isinstance(param_info, dict):
                    msg = f"{section_name}.{param_name} 的值必须是对象（字典）"
                    return False, msg

                required_fields = ["value", "type", "unit", "description", "constraints"]
                for field in required_fields:
                    if field not in param_info:
                        msg = f"{section_name}.{param_name} 缺少必需字段: {field}"
                        return False, msg

                # type / unit / description 必须为非空字符串
                if not isinstance(param_info["type"], str) or not param_info["type"].strip():
                    msg = f"{section_name}.{param_name}.type 必须是非空字符串"
                    return False, msg

                if not isinstance(param_info["unit"], str) or not param_info["unit"].strip():
                    msg = f"{section_name}.{param_name}.unit 必须是非空字符串"
                    return False, msg

                if not isinstance(param_info["description"], str) or not param_info["description"].strip():
                    msg = f"{section_name}.{param_name}.description 必须是非空字符串"
                    return False, msg

                # constraints 必须是列表
                if not isinstance(param_info["constraints"], list):
                    msg = f"{section_name}.{param_name}.constraints 必须是数组（列表）"
                    return False, msg

            return True, ""

        ok, msg = _validate_param_section("important_param", important)
        if not ok:
            error_msg = msg
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            return False, error_msg

        ok, msg = _validate_param_section("suggested_param", suggested)
        if not ok:
            error_msg = msg
            print(f"{Colors.FAIL}错误: {error_msg}{Colors.ENDC}")
            return False, error_msg

        print(f"{Colors.OKGREEN}参数提取结果验证通过{Colors.ENDC}")
        return True, ""




    def is_cmd_valid(self):
        """检查参数提取命令的必要条件是否满足"""
        return self._check_cmd_requirement() and self._check_ai_handler()

    def _check_cmd_requirement(self) -> bool:
        """验证参数提取命令的前置条件"""
        # 检查用户需求内容是否存在
        user_data_store = get_user_data_store()
        requirement_content = user_data_store.get_user_prompt()
        if not requirement_content:
            print(f"  {Colors.WARNING}警告: 未找到用户需求内容，请先提供需求内容{Colors.ENDC}")
            return False
            
        return True

    def _check_ai_handler(self) -> bool:
        """验证AI处理器是否初始化成功"""
        # 检查handler实例是否已初始化
        if not self.chat_handler.is_initialized():
            print(f"  {Colors.FAIL}错误: ChatInterface 未正确初始化{Colors.ENDC}")
            return False

        # 检查系统提示词是否加载
        if not self.sys_prompt_manager.has_prompt(self.role_name):
            print(f"  {Colors.FAIL}错误: 系统提示词 {self.role_name} 未加载{Colors.ENDC}")
            return False
            
        return True