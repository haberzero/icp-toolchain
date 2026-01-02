from typing import Dict


class UserPromptManager:
    """用户提示词模板管理器（单例）

    负责维护「模板名/角色名 -> 用户提示词模板内容」的映射，
    并提供基于占位符的模板构建能力。
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(UserPromptManager, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._template_map: Dict[str, str] = {}

    def register_template(self, template_name: str, template_content: str) -> None:
        """按模板名注册用户提示词模板内容。"""
        if not template_name:
            return
        self._template_map[template_name] = template_content or ""

    def get_template(self, template_name: str) -> str:
        """根据模板名获取模板内容，未注册时返回空字符串。"""
        return self._template_map.get(template_name, "")

    def has_template(self, template_name: str) -> bool:
        """检查指定模板是否已注册且非空。"""
        value = self._template_map.get(template_name)
        return bool(value)

    def build_prompt_from_template(self, template_name: str, placeholder_mapping: Dict[str, str]) -> str:
        """基于模板和占位符映射构建最终的用户提示词。

        Args:
            template_name: 模板名（通常与文件名去掉后缀一致）。
            placeholder_mapping: 占位符到实际内容的映射，如
                {"PROGRAMMING_REQUIREMENT_PLACEHOLDER": "..."}

        Returns:
            str: 替换占位符后的完整提示词，若模板不存在则返回空字符串。
        """
        template = self.get_template(template_name)
        if not template:
            return ""

        result = template
        if placeholder_mapping:
            for placeholder, value in placeholder_mapping.items():
                # 占位符使用简单的 str.replace 进行替换
                result = result.replace(placeholder, value)
        return result

    def clear(self) -> None:
        """清空所有已注册的用户提示词模板。"""
        self._template_map.clear()


_instance = UserPromptManager()


def get_instance() -> UserPromptManager:
    return _instance
