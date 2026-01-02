import asyncio
import time
from typing import Dict, List, Optional, Tuple

from typedef.ai_data_types import EmbeddingApiConfig, EmbeddingStatus
from typedef.cmd_data_types import Colors

from .embedding_interface import EmbeddingInterface


class ICPEmbeddingInsts:
    """ICP嵌入处理器，提供文本向量化服务和重试机制
    
    使用单例模式，支持多个独立的handler实例（通过handler_key区分）：
    - embedding_handler: 用于文本嵌入场景
    - 可扩展支持更多类型的handler
    
    注意: 这是单例类，请使用 get_instance() 获取实例，不要直接实例化
    """
    
    # 类变量：存储不同handler_key对应的单例实例
    _instances: Dict[str, 'ICPEmbeddingInsts'] = {}
    
    def __init__(self, handler_key: str):
        """私有构造函数，请使用 get_instance() 获取实例
        
        Args:
            handler_key: handler类型标识
        """
        self._handler_key = handler_key
        self._embedding_interface: Optional[EmbeddingInterface] = None
        self._is_initialized: bool = False
        self._max_retry: int = 3
        self._retry_delay: float = 1.0
    
    @classmethod
    def get_instance(cls, handler_key: str = 'embedding_handler') -> 'ICPEmbeddingInsts':
        """获取指定handler_key的单例实例
        
        Args:
            handler_key: handler类型标识，默认为 'embedding_handler'
            
        Returns:
            ICPEmbeddingInsts: 对应handler_key的单例实例
        """
        if handler_key not in cls._instances:
            cls._instances[handler_key] = cls(handler_key)
        return cls._instances[handler_key]
    
    @classmethod
    def initialize_handler(
        cls,
        handler_key: str,
        api_config: EmbeddingApiConfig,
        max_retry: int = 3,
        retry_delay: float = 1.0
    ) -> bool:
        """初始化指定handler_key的EmbeddingInterface（类方法，用于全局初始化）
        
        Args:
            handler_key: handler类型标识
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            bool: 是否初始化成功
        """
        instance = cls.get_instance(handler_key)
        return instance.initialize(api_config, max_retry, retry_delay)
    
    def initialize(
        self, 
        api_config: EmbeddingApiConfig, 
        max_retry: int = 3, 
        retry_delay: float = 1.0,
        force_reinit: bool = False
    ) -> bool:
        """初始化当前实例的EmbeddingInterface（实例方法）
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            force_reinit: 是否强制重新初始化（即使已初始化）
            
        Returns:
            bool: 是否初始化成功
        """
        # 如果已经初始化且不强制重新初始化，直接返回成功
        if self._is_initialized and not force_reinit:
            print(f"EmbeddingInterface 已初始化 (handler: {self._handler_key})")
            return True
        
        # 如果强制重新初始化，先重置状态
        if force_reinit:
            self.reset()
        
        # 保存重试配置
        self._max_retry = max_retry
        self._retry_delay = retry_delay
        
        # 带重试的初始化
        for attempt in range(max_retry):
            try:
                self._embedding_interface = EmbeddingInterface(api_config)
                if self._embedding_interface.client is not None:
                    # 进行真实的连接验证
                    print(f"EmbeddingInterface 客户端创建成功，正在验证连接...")
                    is_connected = asyncio.run(
                        self._embedding_interface.verify_connection()
                    )
                    
                    if is_connected:
                        print(f"EmbeddingInterface 初始化成功 (handler: {self._handler_key}, 模型: {api_config.model})")
                        self._is_initialized = True
                        return True
                    else:
                        print(f"嵌入服务连接验证失败 (尝试 {attempt + 1}/{max_retry})")
                        self._embedding_interface = None
            except Exception as e:
                print(f"EmbeddingInterface 初始化失败 (尝试 {attempt + 1}/{max_retry}): {e}")
                self._embedding_interface = None
            
            if attempt < max_retry - 1:
                time.sleep(retry_delay)
        
        self._is_initialized = False
        print(f"EmbeddingInterface 初始化最终失败，已尝试 {max_retry} 次")
        return False
    
    def is_initialized(self) -> bool:
        """检查当前实例的EmbeddingInterface是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._is_initialized and self._embedding_interface is not None
    
    @classmethod
    def check_handler_initialized(cls, handler_key: str) -> bool:
        """检查指定handler是否已初始化（类方法）
        
        Args:
            handler_key: handler类型标识
            
        Returns:
            bool: 是否已初始化
        """
        if handler_key not in cls._instances:
            return False
        return cls._instances[handler_key].is_initialized()
    
    def reset(self) -> None:
        """重置EmbeddingInterface初始化状态，允许重新初始化
        
        在更改API配置后需要重新连接时使用
        """
        self._embedding_interface = None
        self._is_initialized = False
        print(f"已重置EmbeddingInterface初始化状态 (handler: {self._handler_key})")
    
    async def embed_documents(
        self, 
        texts: List[str],
        print_output: bool = False
    ) -> Tuple[str, List[List[float]]]:
        """
        批量嵌入文本（带内部重试机制）
        
        Args:
            texts: 文本列表
            print_output: 是否打印输出（默认False）
            
        Returns:
            tuple: (status, embeddings) - 状态码和嵌入向量列表
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.CLIENT_NOT_INITIALIZED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if print_output:
            print(f"    正在进行批量文本嵌入...")
        
        # 检查当前实例的EmbeddingInterface是否已初始化
        if not self.is_initialized():
            if print_output:
                print(f"\n{Colors.FAIL}错误: EmbeddingInterface未初始化 (handler: {self._handler_key}){Colors.ENDC}")
            return (EmbeddingStatus.CLIENT_NOT_INITIALIZED, [])
        
        # 带重试机制的调用
        for attempt in range(self._max_retry):
            status, embeddings = await self._embedding_interface.embed_query(texts)
            
            if status == EmbeddingStatus.SUCCESS:
                if print_output:
                    print(f"    批量嵌入完成，共处理 {len(texts)} 条文本")
                return (status, embeddings)
            
            # 客户端未初始化，不需要重试
            if status == EmbeddingStatus.CLIENT_NOT_INITIALIZED:
                if print_output:
                    print(f"\n{Colors.FAIL}错误: EmbeddingInterface客户端未初始化{Colors.ENDC}")
                return (status, [])
            
            # 请求失败，重试
            if attempt < self._max_retry - 1:
                if print_output:
                    print(f"\n{Colors.FAIL}嵌入请求失败，正在重试 ({attempt + 1}/{self._max_retry})...{Colors.ENDC}")
                time.sleep(self._retry_delay)
                continue
        
        # 重试失败
        if print_output:
            print(f"\n{Colors.FAIL}错误: 批量嵌入失败 (已重试 {self._max_retry} 次){Colors.ENDC}")
        return (EmbeddingStatus.REQUEST_FAILED, [])
    
    async def embed_query(
        self, 
        text: str,
        print_output: bool = False
    ) -> Tuple[str, List[float]]:
        """
        嵌入单个查询文本（带内部重试机制）
        
        Args:
            text: 查询文本
            print_output: 是否打印输出（默认False）
            
        Returns:
            tuple: (status, embedding) - 状态码和嵌入向量
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.CLIENT_NOT_INITIALIZED: 处理器未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        if print_output:
            print(f"    正在进行文本嵌入...")
        
        # 检查当前实例的EmbeddingInterface是否已初始化
        if not self.is_initialized():
            if print_output:
                print(f"\n{Colors.FAIL}错误: EmbeddingInterface未初始化 (handler: {self._handler_key}){Colors.ENDC}")
            return (EmbeddingStatus.CLIENT_NOT_INITIALIZED, [])
        
        # 带重试机制的调用
        for attempt in range(self._max_retry):
            status, embedding = await self._embedding_interface.embed_query(text)
            
            if status == EmbeddingStatus.SUCCESS:
                if print_output:
                    print(f"    文本嵌入完成")
                return (status, embedding)
            
            # 客户端未初始化，不需要重试
            if status == EmbeddingStatus.CLIENT_NOT_INITIALIZED:
                if print_output:
                    print(f"\n{Colors.FAIL}错误: EmbeddingInterface客户端未初始化{Colors.ENDC}")
                return (status, [])
            
            # 请求失败，重试
            if attempt < self._max_retry - 1:
                if print_output:
                    print(f"\n{Colors.FAIL}嵌入请求失败，正在重试 ({attempt + 1}/{self._max_retry})...{Colors.ENDC}")
                time.sleep(self._retry_delay)
                continue
        
        # 重试失败
        if print_output:
            print(f"\n{Colors.FAIL}错误: 文本嵌入失败 (已重试 {self._max_retry} 次){Colors.ENDC}")
        return (EmbeddingStatus.REQUEST_FAILED, [])
