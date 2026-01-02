from typing import List, Optional, Union

from openai import AsyncOpenAI
from typedef.ai_data_types import EmbeddingApiConfig, EmbeddingStatus


class EmbeddingInterface:
    """Embedding接口类，使用标准OpenAI API，仅提供基础功能封装"""
    
    def __init__(self, api_config: EmbeddingApiConfig):
        """
        初始化Embedding接口
        
        Args:
            api_config: API配置信息
        """
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化客户端连接，不含重试逻辑"""
        try:
            # 使用标准 OpenAI SDK 初始化异步客户端
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        except Exception as e:
            print(f"EmbeddingInterface 客户端初始化失败: {e}")
            self.client = None

    async def verify_connection(self) -> bool:
        """
        验证与模型的连接是否正常（通过发送简单的测试请求）
        
        Returns:
            bool: 连接是否正常
        """
        if self.client is None:
            return False
        
        try:
            # 发送一个简单的测试请求来验证连接
            response = await self.client.embeddings.create(
                model=self.model,
                input=["test connection"]
            )
            
            # 检查是否成功获得响应
            return response is not None and len(response.data) > 0
        except Exception as e:
            print(f"嵌入服务连接验证失败: {e}")
            return False

    async def embed_query(self, texts: Union[str, List[str]]) -> tuple[str, Union[List[float], List[List[float]]]]:
        """
        嵌入文本，不含重试机制
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            tuple: (status, embeddings) - 状态码和嵌入向量
                - EmbeddingStatus.SUCCESS: 成功
                - EmbeddingStatus.CLIENT_NOT_INITIALIZED: 客户端未初始化
                - EmbeddingStatus.REQUEST_FAILED: 请求失败
        """
        # 检查客户端是否已初始化
        if self.client is None:
            return (EmbeddingStatus.CLIENT_NOT_INITIALIZED, [])
        
        try:
            # 支持单个文本或列表
            is_single = isinstance(texts, str)
            input_data = [texts] if is_single else texts
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=input_data
            )
            
            embeddings = [item.embedding for item in response.data]
            result = embeddings[0] if is_single else embeddings
            
            return (EmbeddingStatus.SUCCESS, result)
            
        except Exception as e:
            print(f"Embedding请求失败: {e}")
            return (EmbeddingStatus.REQUEST_FAILED, [])
