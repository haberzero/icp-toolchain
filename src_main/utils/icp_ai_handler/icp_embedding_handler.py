"""
ICP Embedding Handler - 管理嵌入向量服务的包装器

这个模块提供了一个高层次的接口来管理文本嵌入服务，
使用单例模式共享EmbeddingHandler实例以避免资源浪费。
"""

from typing import List, Optional, Tuple
from pydantic import SecretStr

from typedef.cmd_data_types import EmbeddingApiConfig
from libs.ai_interface.embedding_interface import EmbeddingHandler, EmbeddingStatus


class ICPEmbeddingHandler:
    """ICP嵌入处理器，提供文本向量化服务"""
    
    # 类变量：共享的EmbeddingHandler实例
    _shared_embedding_handler: Optional[EmbeddingHandler] = None
    _is_initialized: bool = False
    
    def __init__(self):
        """初始化ICP嵌入处理器"""
        pass
    
    @classmethod
    def initialize_embedding_handler(
        cls, 
        api_config: EmbeddingApiConfig, 
        max_retry: int = 3, 
        retry_delay: float = 1.0
    ) -> bool:
        """
        初始化共享的EmbeddingHandler实例（类方法）
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            bool: 是否初始化成功
        """
        if cls._shared_embedding_handler is None:
            cls._shared_embedding_handler = EmbeddingHandler(api_config, max_retry, retry_delay)
            cls._is_initialized = cls._shared_embedding_handler.is_initialized
        
        return cls._is_initialized
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查共享的EmbeddingHandler是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return cls._is_initialized and cls._shared_embedding_handler is not None
    
    @classmethod
    def get_shared_handler(cls) -> Optional[EmbeddingHandler]:
        """
        获取共享的EmbeddingHandler实例
        
        Returns:
            Optional[EmbeddingHandler]: 共享的EmbeddingHandler实例，未初始化时返回None
        """
        return cls._shared_embedding_handler
    
    def embed_documents(self, texts: List[str]) -> Tuple[List[List[float]], str]:
        """
        批量嵌入文本
        
        Args:
            texts: 文本列表
            
        Returns:
            tuple: (embeddings, status) - 嵌入向量列表和状态码
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.INIT_FAILED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if not self.is_initialized():
            return ([], EmbeddingStatus.INIT_FAILED)
        
        return self._shared_embedding_handler.embed_documents(texts)
    
    def embed_query(self, text: str) -> Tuple[List[float], str]:
        """
        嵌入单个查询文本
        
        Args:
            text: 查询文本
            
        Returns:
            tuple: (embedding, status) - 嵌入向量和状态码
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.INIT_FAILED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if not self.is_initialized():
            return ([], EmbeddingStatus.INIT_FAILED)
        
        return self._shared_embedding_handler.embed_query(text)
    
    def check_connection(self) -> bool:
        """
        检查嵌入服务连接状态
        
        Returns:
            bool: 连接是否正常
        """
        if not self.is_initialized():
            return False
        
        # 使用简单的测试文本检查连接
        _, status = self.embed_query("test connection")
        return status == EmbeddingStatus.SUCCESS
