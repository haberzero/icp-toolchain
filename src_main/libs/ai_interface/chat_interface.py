from typing import Callable, Optional
from openai import AsyncOpenAI
import asyncio

from typedef.cmd_data_types import ChatApiConfig

# 返回值状态码
class ResponseStatus:
    """响应状态码"""
    SUCCESS = "SUCCESS"  # 响应成功
    CLIENT_NOT_INITIALIZED = "CLIENT_NOT_INITIALIZED"  # 客户端未初始化
    STREAM_FAILED_AFTER_RETRY = "STREAM_FAILED_AFTER_RETRY"  # 流式响应重试后仍失败


class ChatInterface:
    """Chat接口类，使用标准OpenAI API"""
    
    def __init__(self, api_config: ChatApiConfig, max_retry: int = 3, retry_delay: float = 1.0):
        """
        初始化Chat接口
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
        """
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.max_retry = max_retry
        self.retry_delay = retry_delay
        self.client = None
        self.init_chat_chain()

    def init_chat_chain(self):
        """初始化客户端连接，支持重试机制"""
        for attempt in range(self.max_retry):
            try:
                # 使用标准 OpenAI SDK 初始化客户端
                self.client = AsyncOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key.get_secret_value(),
                )
                print(f"ChatInterface 客户端初始化成功 (模型: {self.model})")
                return
            except Exception as e:
                print(f"ChatInterface 初始化失败 (尝试 {attempt + 1}/{self.max_retry}): {e}")
                if attempt < self.max_retry - 1:
                    import time
                    time.sleep(self.retry_delay)
        
        self.client = None
        print(f"ChatInterface 初始化最终失败，已尝试 {self.max_retry} 次")

    async def stream_response(
        self, 
        sys_prompt: str, 
        user_prompt: str, 
        callback: Callable[[str], None]
    ) -> str:
        """
        流式响应，支持重试机制
        
        Args:
            sys_prompt: 系统提示词
            user_prompt: 用户提示词
            callback: 回调函数，用于接收流式响应内容
            
        Returns:
            str: 响应状态码 (SUCCESS, CLIENT_NOT_INITIALIZED, STREAM_FAILED_AFTER_RETRY)
        """
        # 检查客户端是否已初始化
        if self.client is None:
            return ResponseStatus.CLIENT_NOT_INITIALIZED

        # 重试机制
        for attempt in range(self.max_retry):
            try:
                # 使用标准 OpenAI API 格式构建消息
                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ]

                # 使用 OpenAI SDK 的流式响应
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True
                )

                async for chunk in stream:
                    # 提取流式响应的内容
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            # 确保传递给callback的是字符串类型
                            if isinstance(delta.content, str):
                                callback(delta.content)
                            else:
                                callback(str(delta.content))
                
                # 成功完成流式响应
                return ResponseStatus.SUCCESS
                
            except Exception as e:
                # 流式响应失败，进行重试
                if attempt < self.max_retry - 1:
                    # 还有重试机会，等待后重试（对外部不可见）
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    # 重试失败，返回错误状态
                    print(f"流式响应失败 (已重试 {self.max_retry} 次): {e}")
                    return ResponseStatus.STREAM_FAILED_AFTER_RETRY
        
        # 不应该到达这里
        return ResponseStatus.STREAM_FAILED_AFTER_RETRY