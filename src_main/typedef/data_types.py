from dataclasses import dataclass, field
from typing import List
from pydantic import SecretStr


class Colors:
    """颜色类"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

@dataclass
class CommandInfo:
    """命令信息数据类"""
    name: str                           # 命令全写
    aliases: List[str]                  # 命令缩写列表
    description: str                    # 命令描述
    help_text: str                      # 帮助文本

class CmdProcStatus:
    DEFAULT = "DEFAULT"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    CANCELED = "CANCELED"

@dataclass
class ChatApiConfig():
    base_url: str
    api_key: SecretStr
    model: str

@dataclass
class EmbeddingApiConfig():
    base_url: str
    api_key: SecretStr
    model: str