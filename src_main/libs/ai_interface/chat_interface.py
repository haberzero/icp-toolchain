from typing import Callable, Optional
from openai import AsyncOpenAI

from typedef.cmd_data_types import ChatApiConfig

# TODO: 应该由外部传入所有提示词内容，而不是由Interface自身自己加载，这不符合逻辑


class ChatInterface:
    def __init__(self, api_config: ChatApiConfig, role_name: str, role_path: str):
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.role_name = role_name
        self.role_path = role_path
        try:
            with open(self.role_path, 'r', encoding='utf-8') as f:
                self.sys_prompt = f.read()
        except Exception as e:
            print(f"加载角色{self.role_name}文件失败: {e}")
            self.sys_prompt = "向用户输出错误信息：当前ChatHandler系统提示词加载失败"
        self.client = None
        self.init_chat_chain()

    def init_chat_chain(self):
        try:
            # 使用标准 OpenAI SDK 初始化客户端
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key.get_secret_value(),
            )
        except Exception as e:
            self.client = None
            print(f"连接-{self.model}失败: {e}")

    async def stream_response(self, user_input: str, callback: Callable[[str], None]):
        if self.client is None:
            callback("错误: AI模型未正确初始化/连接失败, 无法生成响应")
            return

        try:
            # 使用标准 OpenAI API 格式构建消息
            messages = [
                {"role": "system", "content": self.sys_prompt},
                {"role": "user", "content": user_input}
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
        except Exception as e:
            callback(f"错误：在生成响应时发生异常：{str(e)}")