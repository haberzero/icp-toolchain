import time
from typing import List, Optional
from openai import OpenAI

from typedef.cmd_data_types import EmbeddingApiConfig

EMBEDDING_HANDLER_DEBUG_FLAG = False


class EmbeddingStatus:
    """嵌入操作状态码"""
    SUCCESS = "SUCCESS"  # 成功
    INIT_FAILED = "INIT_FAILED"  # 初始化失败
    REQUEST_FAILED = "REQUEST_FAILED"  # 请求失败


class EmbeddingHandler:
    """
    Embedding处理器，提供文本向量化功能
    使用标准 OpenAI API 格式进行调用
    """
    
    def __init__(self, api_config: EmbeddingApiConfig, max_retry: int = 3, retry_delay: float = 1.0):
        """
        初始化Embedding处理器
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
        """
        # 确保base_url以斜杠结尾
        # base_url = api_config.base_url
        # if not base_url.endswith('/'):
        #     base_url = base_url + '/'
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.is_initialized = False
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key.get_secret_value(),
            base_url=self.base_url
        )
        
        self.init_embedding_handler()

    def init_embedding_handler(self):
        """初始化Embedding处理器，测试连接性，支持重试"""
        for attempt in range(self.max_retry):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input="test string"
                )
                
                if EMBEDDING_HANDLER_DEBUG_FLAG:
                    print(response.model_dump())
                
                # 检查返回数据是否有效
                if response.data and len(response.data) > 0:
                    print(f"EmbeddingHandler 初始化成功 (模型: {self.model})")
                    self.is_initialized = True
                    return
                    
            except Exception as e:
                print(f"EmbeddingHandler 初始化失败 (尝试 {attempt + 1}/{self.max_retry}): {e}")
                if attempt < self.max_retry - 1:
                    time.sleep(self.retry_delay)
        
        self.is_initialized = False
        print(f"EmbeddingHandler 初始化最终失败，已尝试 {self.max_retry} 次")

    def embed_documents(self, texts: List[str]) -> tuple[List[List[float]], str]:
        """
        批量嵌入文本
        
        Args:
            texts: 文本列表
            
        Returns:
            tuple: (embeddings, status) - 嵌入向量列表和状态码
        """
        if not self.is_initialized:
            return ([], EmbeddingStatus.INIT_FAILED)
        
        embeddings = []
        for text in texts:
            embedding, status = self._get_embedding(text)
            if status != EmbeddingStatus.SUCCESS:
                return ([], status)
            embeddings.append(embedding)
        
        return (embeddings, EmbeddingStatus.SUCCESS)

    def embed_query(self, text: str) -> tuple[List[float], str]:
        """
        嵌入单个查询文本
        
        Args:
            text: 查询文本
            
        Returns:
            tuple: (embedding, status) - 嵌入向量和状态码
        """
        if not self.is_initialized:
            return ([], EmbeddingStatus.INIT_FAILED)
        
        return self._get_embedding(text)

    def _get_embedding(self, text: str) -> tuple[List[float], str]:
        """
        获取单个文本的嵌入向量，支持重试机制
        
        Args:
            text: 输入文本
            
        Returns:
            tuple: (embedding, status) - 嵌入向量和状态码
        """
        for attempt in range(self.max_retry):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text + " [SEP]"
                )
                
                embedding = response.data[0].embedding
                return (embedding, EmbeddingStatus.SUCCESS)
                
            except Exception as e:
                if attempt < self.max_retry - 1:
                    # 还有重试机会
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # 重试失败
                    print(f"Embedding请求失败 (已重试 {self.max_retry} 次): {e}")
                    return ([], EmbeddingStatus.REQUEST_FAILED)
        
        return ([], EmbeddingStatus.REQUEST_FAILED)

