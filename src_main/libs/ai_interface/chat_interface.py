from typing import Callable, Optional
from openai import AsyncOpenAI
import asyncio

from typedef.ai_data_types import ChatApiConfig, ChatResponseStatus

class ChatInterface:
    """Chat接口类，使用标准OpenAI API，仅提供基础功能封装"""
    
    def __init__(self, api_config: ChatApiConfig):
        """
        初始化Chat接口
        
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
            # 使用标准 OpenAI SDK 初始化客户端
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
        except Exception as e:
            print(f"ChatInterface 客户端初始化失败: {e}")
            self.client = None

    async def verify_connection(self) -> bool:
        """
        验证与模型的连接是否正常（通过发送简单的测试请求）
        使用简单对话请求验证，适用于所有兼容OpenAI的平台
        
        Returns:
            bool: 连接是否正常
        """
        if self.client is None:
            return False
        
        try:
            # 发送一个简单的测试请求来验证连接
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi"}
            ]
            
            # 使用非流式请求进行验证，减少响应处理复杂度
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=10  # 限制响应长度，减少token消耗
            )
            
            # 检查是否成功获得响应
            return response is not None and len(response.choices) > 0
        except Exception as e:
            print(f"模型连接验证失败: {e}")
            return False

    async def stream_response(
        self, 
        sys_prompt: str, 
        user_prompt: str, 
        callback: Callable[[str], None]
    ) -> str:
        """
        流式响应，不含重试机制
        
        Args:
            sys_prompt: 系统提示词
            user_prompt: 用户提示词
            callback: 回调函数，用于接收流式响应内容
            
        Returns:
            str: 响应状态码 (SUCCESS, CLIENT_NOT_INITIALIZED, STREAM_FAILED)
        """
        # 检查客户端是否已初始化
        if self.client is None:
            return ChatResponseStatus.CLIENT_NOT_INITIALIZED

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
            return ChatResponseStatus.SUCCESS
            
        except Exception as e:
            # 流式响应失败
            print(f"流式响应失败: {e}")
            return ChatResponseStatus.STREAM_FAILED