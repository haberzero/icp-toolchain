import sys
import os
import json
import asyncio
from typing import Callable, Optional, Dict, List

from langchain_community.chat_models.tongyi import ChatTongyi

from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.messages import AIMessageChunk
from pydantic import SecretStr


# AI处理核心类
class AIProcessor:
    def __init__(self, api_config_path: str, prompt_config_path: str, prompt_name: str = "default"):
        self.api_config_path = api_config_path
        self.prompt_config_path = prompt_config_path
        self.prompt_name = prompt_name

        self.base_url = ""
        self.api_key = ""
        self.model = ""
        self.load_config()

        self.sys_prompt = ""
        self.load_prompt()

        self.init_chain()
        self.full_response = ""

    def load_config(self):
        with open(self.api_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.base_url = config[self.prompt_name].get('base_url', '')
            self.api_key = config[self.prompt_name].get('api_key', '')
            self.model = config[self.prompt_name].get('model', '')

    def load_prompt(self):
        _name = self.prompt_name
        if not os.path.exists(self.prompt_config_path):
            raise FileNotFoundError(f"提示词配置文件不存在：{self.prompt_config_path}")

        with open(self.prompt_config_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)

        prompt_path = json_content[_name]

        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.sys_prompt = f.read()
        else:
            print(f"警告：提示词文件不存在：{prompt_path}")
            self.sys_prompt = ""

    def init_chain(self):
        chat_llm = ChatTongyi(
            api_key=SecretStr(self.api_key),
            model=self.model,
            streaming=True,
        )

        system_prompt = self.sys_prompt if self.sys_prompt else "Tell user that something wrong."
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

        self.chain = prompt_template | chat_llm

        print(f"已配置模型: {self.prompt_name}")

    async def stream_response(self, user_input: str):
        if not self.chain:
            print("未配置模型")
            return

        async for chunk in self.chain.astream({"input": user_input}):
            if isinstance(chunk, AIMessageChunk):
                content = chunk.content
                if isinstance(content, str):
                    self._gather_full_response(content)
                else:
                    print(f"Unexpected content type: {type(content)}")

    def _gather_full_response(self, response_content: str):
        self.full_response += response_content
    
    def get_full_response(self):
        return self.full_response
    
    def clear_full_response(self):
        self.full_response = ""