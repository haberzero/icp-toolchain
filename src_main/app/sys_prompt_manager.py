from typing import Dict, List


class SysPromptManager:
    """系统提示词管理器（单例）

    负责维护「角色名 -> 系统提示词内容」的映射。
    角色名与文件名在加载阶段解耦：
    - 加载时通过文件名读取内容
    - 注册到本管理器时仅保留角色名和内容
    文件名、路径在注册完成后不再重要。
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SysPromptManager, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._prompt_map: Dict[str, str] = {}

    def register_prompt(self, role_name: str, prompt_content: str) -> None:
        """按角色名注册系统提示词内容。

        Args:
            role_name: 逻辑上的角色名（与文件名解耦）。
            prompt_content: 提示词全文内容，为空时忽略。
        """
        if not role_name:
            return
        # 即便内容为空，也注册一个空字符串，方便 has_prompt 做统一判断
        self._prompt_map[role_name] = prompt_content or ""

    def get_prompt(self, role_name: str) -> str:
        """根据角色名获取系统提示词内容，未注册时返回空字符串。"""
        return self._prompt_map.get(role_name, "")

    def has_prompt(self, role_name: str) -> bool:
        """检查指定角色的系统提示词是否已注册且非空。"""
        value = self._prompt_map.get(role_name)
        return bool(value)

    def clear(self) -> None:
        """清空所有已注册的系统提示词。"""
        self._prompt_map.clear()

    def get_all_roles(self) -> List[str]:
        """获取所有已注册的角色名列表。"""
        return list(self._prompt_map.keys())


_instance = SysPromptManager()


def get_instance() -> SysPromptManager:
    return _instance
