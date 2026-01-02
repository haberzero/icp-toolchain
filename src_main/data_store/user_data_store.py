import json
import os
import sys

from typedef.cmd_data_types import Colors

# 本文件涉及对用户工程中的持久性文件的存取
# 未完成，没考虑好怎么应对不同的用户初期需求输入，现在以根目录下的.md文件为主
# 之后ui界面出来或者工具链定义规范化之后再补全

class UserDataStore:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(UserDataStore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.user_prompt = ""

    def set_user_prompt(self, prompt):
        self.user_prompt = prompt

    def get_user_prompt(self):
        return self.user_prompt


_instance = UserDataStore()


def get_instance():
    return _instance
