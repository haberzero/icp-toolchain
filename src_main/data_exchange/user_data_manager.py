import sys, os
import json

from cfg.proj_cfg_manager import get_instance as get_proj_cfg_manager
from typedef.data_types import Colors

# 本文件涉及对用户工程中的持久性文件的存取

class UserDataManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(UserDataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.user_prompt = ""
            self.proj_cfg_manager = get_proj_cfg_manager()

    def set_user_prompt(self, prompt):
        self.user_prompt = prompt

    def get_user_prompt(self):
        return self.user_prompt


_instance = UserDataManager()


def get_instance():
    return _instance
