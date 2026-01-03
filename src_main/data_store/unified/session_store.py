from typing import Any, Dict


class SessionStore:
    """
    Manages transient session data.
    """
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def clear(self):
        self._data.clear()

    # Common session keys helpers
    
    @property
    def current_user_prompt(self) -> str:
        return self.get("user_prompt", "")
    
    @current_user_prompt.setter
    def current_user_prompt(self, value: str):
        self.set("user_prompt", value)

