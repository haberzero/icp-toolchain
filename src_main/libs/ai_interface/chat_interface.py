from dataclasses import dataclass
from pydantic import SecretStr
from typing import Callable, Optional, Dict, List

from typedef.cmd_data_types import ChatApiConfig

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# TODO: 应该由外部传入所有提示词内容，而不是由Interface自身自己加载，这不符合逻辑


class ChatInterface:
    def __init__(self, api_config: ChatApiConfig, role_name: str, role_path: str):
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.role_name = role_name
        self.role_path = role_path
        try :
            with open(self.role_path, 'r', encoding='utf-8') as f:
                self.sys_prompt = f.read()
        except Exception as e:
            print(f"加载角色{self.role_name}文件失败: {e}")
            self.sys_prompt = "向用户输出错误信息：当前ChatHandler系统提示词加载失败"
        self.chain = None
        self.init_chat_chain()

    def init_chat_chain(self):
        try:
            self.llm = ChatOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
            )
        except Exception as e:
            self.llm = None
            print(f"连接-{self.model}失败: {e}")

    async def stream_response(self, user_input: str, callback: Callable[[str], None]):
        llm = self.llm
        if llm is None:
            callback("错误: AI模型未正确初始化/连接失败, 无法生成响应")
            return

        try:
            messages = [
                SystemMessage(content=self.sys_prompt),
                HumanMessage(content=user_input)
            ]

            async for chunk in llm.astream(messages):
                if isinstance(chunk, AIMessageChunk):
                    content = chunk.content
                    if content:
                        # 确保传递给callback的是字符串类型
                        if isinstance(content, str):
                            callback(content)
                        else:
                            callback(str(content))
        except Exception as e:
            callback(f"错误：在生成响应时发生异常：{str(e)}")