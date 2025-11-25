"""
AI 接口相关的数据类型定义
包括状态码、配置等
"""

from dataclasses import dataclass
from pydantic import SecretStr


# ====== Chat 相关类型定义 ======

class ChatResponseStatus:
    """Chat响应状态码"""
    SUCCESS = "SUCCESS"  # 响应成功
    CLIENT_NOT_INITIALIZED = "CLIENT_NOT_INITIALIZED"  # 客户端未初始化
    STREAM_FAILED = "STREAM_FAILED"  # 流式响应失败
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"  # 角色不存在


@dataclass
class ChatApiConfig:
    """Chat API 配置"""
    base_url: str
    api_key: SecretStr
    model: str


# ====== Embedding 相关类型定义 ======

class EmbeddingStatus:
    """嵌入操作状态码"""
    SUCCESS = "SUCCESS"  # 成功
    CLIENT_NOT_INITIALIZED = "CLIENT_NOT_INITIALIZED"  # 客户端未初始化
    REQUEST_FAILED = "REQUEST_FAILED"  # 请求失败


@dataclass
class EmbeddingApiConfig:
    """Embedding API 配置"""
    base_url: str
    api_key: SecretStr
    model: str
