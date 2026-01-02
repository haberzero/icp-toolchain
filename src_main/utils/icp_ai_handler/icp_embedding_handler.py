import time
from typing import List, Optional, Tuple

from libs.ai_interface.embedding_interface import EmbeddingInterface
from typedef.ai_data_types import EmbeddingApiConfig, EmbeddingStatus


class ICPEmbeddingHandler:
    """ICP嵌入处理器，提供文本向量化服务，并提供重试机制"""
    
    # 类变量：共享的 EmbeddingInterface 实例
    _shared_embedding_interface: Optional[EmbeddingInterface] = None
    _is_initialized: bool = False
    _initialization_attempted: bool = False  # 标记是否已尝试过初始化
    _max_retry: int = 3
    _retry_delay: float = 1.0
    
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
        初始化共享的 EmbeddingInterface，支持重试机制
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            bool: 是否初始化成功
        """
        # 如果已经尝试过初始化，直接返回之前的结果
        if cls._initialization_attempted:
            return cls._is_initialized
        
        # 标记已尝试初始化
        cls._initialization_attempted = True
        
        if cls._shared_embedding_interface is None:
            cls._max_retry = max_retry
            cls._retry_delay = retry_delay
            
            # 带重试的初始化
            for attempt in range(max_retry):
                try:
                    cls._shared_embedding_interface = EmbeddingInterface(api_config)
                    if cls._shared_embedding_interface.client is not None:
                        # 测试连接
                        _, status = cls._shared_embedding_interface.embed_query("test connection")
                        if status == EmbeddingStatus.SUCCESS:
                            print(f"EmbeddingInterface 初始化成功 (模型: {api_config.model})")
                            cls._is_initialized = True
                            return True
                except Exception as e:
                    print(f"EmbeddingInterface 初始化失败 (尝试 {attempt + 1}/{max_retry}): {e}")
                    if attempt < max_retry - 1:
                        time.sleep(retry_delay)
            
            cls._is_initialized = False
            print(f"EmbeddingInterface 初始化最终失败，已尝试 {max_retry} 次")
            return False
        
        return cls._is_initialized
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查共享的 EmbeddingInterface
        
        Returns:
            bool: 是否已初始化
        """
        return cls._is_initialized and cls._shared_embedding_interface is not None
    
    @classmethod
    def reset_initialization(cls) -> None:
        """
        重置初始化状态，允许重新初始化EmbeddingInterface
        在更改API配置后需要重新连接时使用
        """
        cls._shared_embedding_interface = None
        cls._is_initialized = False
        cls._initialization_attempted = False
        print("已重置EmbeddingInterface初始化状态")

    def embed_documents(self, texts: List[str]) -> Tuple[List[List[float]], str]:
        """
        批量嵌入文本（带内部重试机制）
        
        Args:
            texts: 文本列表
            
        Returns:
            tuple: (embeddings, status) - 嵌入向量列表和状态码
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.CLIENT_NOT_INITIALIZED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if not self.is_initialized():
            return ([], EmbeddingStatus.CLIENT_NOT_INITIALIZED)
        
        # 带重试的调用
        embeddings = []
        status = EmbeddingStatus.REQUEST_FAILED

        for attempt in range(self._max_retry):
            embeddings, status = self._shared_embedding_interface.embed_query(texts)
            
            if status == EmbeddingStatus.SUCCESS:
                return (embeddings, status)
            
            if attempt < self._max_retry - 1:
                time.sleep(self._retry_delay)
        
        # 所有重试都失败，返回最后一次的结果
        return (embeddings, status)
    
    def embed_query(self, text: str) -> Tuple[List[float], str]:
        """
        嵌入单个查询文本（带内部重试机制）
        
        Args:
            text: 查询文本
            
        Returns:
            tuple: (embedding, status) - 嵌入向量和状态码
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.CLIENT_NOT_INITIALIZED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if not self.is_initialized():
            return ([], EmbeddingStatus.CLIENT_NOT_INITIALIZED)
        
        # 带重试的调用
        embedding = []
        status = EmbeddingStatus.REQUEST_FAILED
        
        for attempt in range(self._max_retry):
            embedding, status = self._shared_embedding_interface.embed_query(text)
            
            if status == EmbeddingStatus.SUCCESS:
                return (embedding, status)
            
            if attempt < self._max_retry - 1:
                time.sleep(self._retry_delay)
        
        # 所有重试都失败，返回最后一次的结果
        return (embedding, status)
    
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
