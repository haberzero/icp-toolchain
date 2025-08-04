import sys
import os
import json
import asyncio
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass
from threading import Thread
from queue import Queue, Empty
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.messages import AIMessageChunk


# 状态枚举
class AppState(Enum):
    IDLE = "idle"              # 空闲状态
    PROCESSING = "processing"  # 处理中状态
    DONE = "done"              # 完成状态

# 配置数据类
@dataclass
class ModelConfig:
    base_url: str
    api_key: str
    model: str
    model_params: dict

# 信息交换层，用于在ui和逻辑层之间交换实时的信息，同时管理和ui相关的状态机
class UiCommInst:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UiCommInst, cls).__new__(cls)
        return cls._instance
    
    def inst_reset(self):
        self.current_state = AppState.IDLE
        self.user_input = ""

    
    def update_state(self):
        # 根据当前状态和上下文参数确定下一个状态,暂不完善
        if self.current_state == AppState.IDLE:
            if self.user_input:
                self.current_state = AppState.PROCESSING
            else:
                self.current_state = AppState.IDLE
                
        elif self.current_state == AppState.PROCESSING:
            pass
                
        elif self.current_state == AppState.DONE:
            self.current_state = AppState.IDLE

    def get_current_state(self):
        """获取当前状态"""
        return self.current_state


# 创建一个单例实例，供模块导入时使用
_instance = UiCommInst()

# 提供一个全局访问方法
def get_instance():
    return _instance

