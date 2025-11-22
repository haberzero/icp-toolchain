"""
ICP AI Handler 包

提供对AI接口的高级封装，包括聊天和嵌入功能。
所有处理器使用单例模式共享底层AI客户端，避免资源浪费。
"""

from .icp_chat_handler import ICPChatHandler
from .icp_embedding_handler import ICPEmbeddingHandler

__all__ = ['ICPChatHandler', 'ICPEmbeddingHandler']
