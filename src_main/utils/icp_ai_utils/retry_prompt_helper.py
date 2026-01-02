import os
from typing import Tuple

from data_store.app_data_store import get_instance as get_app_data_store
from typedef.cmd_data_types import Colors


class RetryPromptHelper:
    """重试提示词构建辅助类

    设计目标：
    - 统一管理「问题诊断 + 修复建议」相关的提示词模板使用方式
    - 为各个 cmd_handler 提供简单、可复用的接口
    - 避免在每个 handler 中重复读模板、拼字符串

    注意：
    - 本工具类只负责拼装提示词字符串，不直接发起大模型调用
    - 具体的调用顺序（先诊断再修复）由各个 cmd_handler 控制
    """

    @staticmethod
    def build_retry_analysis_prompts(
        previous_sys_prompt: str,
        previous_user_prompt: str,
        previous_content: str,
        issues_text: str,
    ) -> Tuple[str, str]:
        """构建「问题诊断 + 修复建议」阶段的系统提示词和用户提示词

        Args:
            previous_sys_prompt: 上一次调用使用的系统提示词全文
            previous_user_prompt: 上一次调用使用的用户提示词全文
            previous_content: 上一次调用返回的原始输出内容
            issues_text: 由 issue_recorder 汇总的文字问题列表（已拼好字符串）

        Returns:
            (analysis_sys_prompt, analysis_user_prompt)
        """
        app_data_store = get_app_data_store()

        # 系统提示词：专门用于「诊断与修复建议」的角色说明
        prompt_dir = app_data_store.get_prompt_dir()
        analysis_sys_prompt_path = os.path.join(prompt_dir, "retry_analysis_sys_prompt.md")

        try:
            with open(analysis_sys_prompt_path, "r", encoding="utf-8") as f:
                analysis_sys_prompt = f.read()
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取重试分析系统提示词失败: {e}{Colors.ENDC}")
            # 退化为一个简单的系统提示词，保证流程不中断
            analysis_sys_prompt = (
                "你是一名问题诊断与修复建议专家，需要根据给定的提示词、输出结果和问题列表，"
                "分析问题根源并给出清晰的修复建议。"
            )

        # 用户提示词模板：包含上一次的提示词 / 输出 / 问题列表
        user_prompt_dir = app_data_store.get_user_prompt_dir()
        analysis_user_template_path = os.path.join(user_prompt_dir, "retry_analysis_prompt_template.md")

        try:
            with open(analysis_user_template_path, "r", encoding="utf-8") as f:
                analysis_user_template = f.read()
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取重试分析用户提示词模板失败: {e}{Colors.ENDC}")
            # 退化为一个简单的用户提示词
            analysis_user_template = (
                "下面是上一次调用时使用的系统提示词、用户提示词、输出结果和问题列表。\n\n"
                "【系统提示词】\n{PREV_SYS}\n\n"
                "【用户提示词】\n{PREV_USER}\n\n"
                "【输出结果】\n{PREV_CONTENT}\n\n"
                "【问题列表】\n{ISSUES}\n\n"
                "请你分析问题根源，并给出清晰的修复建议。只输出修复建议本身。"
            )

        # 将占位符替换为实际内容
        user_prompt = analysis_user_template
        user_prompt = user_prompt.replace("PREVIOUS_SYS_PROMPT_PLACEHOLDER", previous_sys_prompt or "(无)" )
        user_prompt = user_prompt.replace("PREVIOUS_USER_PROMPT_PLACEHOLDER", previous_user_prompt or "(无)")
        user_prompt = user_prompt.replace("PREVIOUS_CONTENT_PLACEHOLDER", previous_content or "(无输出)")
        user_prompt = user_prompt.replace("ISSUES_LIST_PLACEHOLDER", issues_text or "(未检测到问题描述)")

        return analysis_sys_prompt, user_prompt

    @staticmethod
    def build_fix_user_prompt_part(
        previous_content: str,
        issues_text: str,
        fix_suggestion: str,
        code_block_type: str = "",
    ) -> str:
        """构建「根据修复建议进行结果修复」阶段的用户提示词附加部分

        典型使用方式：
            final_user_prompt = user_prompt_base + "\n\n" + user_prompt_retry_part

        Args:
            previous_content: 上一次生成的原始内容
            issues_text: 问题列表的字符串表现形式
            fix_suggestion: 由模型给出的修复建议（自然语言）
            code_block_type: 可选的代码块类型（如"json"、"python"），为空则作为普通文本

        Returns:
            str: 可以直接拼接在基础用户提示词后的重试附加内容
        """
        app_data_store = get_app_data_store()
        user_prompt_dir = app_data_store.get_user_prompt_dir()
        retry_template_path = os.path.join(user_prompt_dir, "retry_prompt_template.md")

        try:
            with open(retry_template_path, "r", encoding="utf-8") as f:
                retry_template = f.read()
        except Exception as e:
            print(f"{Colors.WARNING}警告: 读取重试修复模板失败: {e}{Colors.ENDC}")
            # 退化为一个简单的说明文本
            header = "# 输出修复任务\n\n"
            body = "下面是上一次的输出以及自动校验发现的问题，请根据给出的修复建议对输出进行修改。\n\n"
            return (
                header
                + body
                + "【上一次输出】\n"
                + (previous_content or "(无)")
                + "\n\n【问题列表】\n"
                + (issues_text or "(未检测到问题描述)")
                + "\n\n【修复建议】\n"
                + (fix_suggestion or "(无修复建议)")
            )

        # 格式化上一次生成的内容
        if code_block_type:
            formatted_content = f"```{code_block_type}\n{previous_content}\n```"
        else:
            formatted_content = previous_content or ""

        # 替换占位符
        retry_prompt = retry_template.replace("PREVIOUS_CONTENT_PLACEHOLDER", formatted_content)
        retry_prompt = retry_prompt.replace("ISSUES_LIST_PLACEHOLDER", issues_text or "")

        # 在模板后面追加修复建议，避免修改现有占位符结构
        retry_prompt += "\n\n【修复建议】\n"
        retry_prompt += (fix_suggestion or "(无修复建议)")

        return retry_prompt
