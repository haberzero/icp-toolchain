from typing import List, Optional
from openai import OpenAI

from typedef.ai_data_types import EmbeddingApiConfig, EmbeddingStatus


class EmbeddingInterface:
    """
    Embedding处理器，提供文本向量化功能
    使用标准 OpenAI API 格式进行调用，仅提供基础功能封装
    """
    
    def __init__(self, api_config: EmbeddingApiConfig):
        """
        初始化Embedding处理器
        
        Args:
            api_config: API配置信息
        """
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.client = None
        
        self._init_client()

    def _init_client(self):
        """初始化客户端，不含重试逻辑"""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            print(f"EmbeddingInterface 客户端初始化失败: {e}")
            self.client = None

    def embed_query(self, texts: str | List[str]) -> tuple[List[float] | List[List[float]], str]:
        try:
            # 支持单个文本或列表
            is_single = isinstance(texts, str)
            input_data = [texts] if is_single else [t for t in texts]
            
            response = self.client.embeddings.create(
                model=self.model,
                input=input_data
            )
            
            embeddings = [item.embedding for item in response.data]
            return (embeddings[0] if is_single else embeddings, EmbeddingStatus.SUCCESS)
            
        except Exception as e:
            print(f"Embedding请求失败: {e}")
            return ([], EmbeddingStatus.REQUEST_FAILED)
