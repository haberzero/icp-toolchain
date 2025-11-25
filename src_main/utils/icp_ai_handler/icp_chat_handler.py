"""
ICP Chat Handler - 管理聊天角色和AI接口的包装器

这个模块提供了一个高层次的接口来管理多个聊天角色，
所有角色共享一个ChatInterface实例以避免资源浪费。
包含重试机制逻辑。
"""

import os
import asyncio
import time
from typing import Dict, Callable, Optional
from pydantic import SecretStr

from typedef.ai_data_types import ChatApiConfig, ChatResponseStatus
from libs.ai_interface.chat_interface import ChatInterface


class ICPChatHandler:
    """ICP聊天处理器，管理多个角色的系统提示词，并提供重试机制"""
    
    # 类变量：共享的ChatInterface实例
    _shared_chat_interface: Optional[ChatInterface] = None
    _is_initialized: bool = False
    _max_retry: int = 3
    _retry_delay: float = 1.0
    
    def __init__(self):
        """初始化ICP聊天处理器"""
        # 实例变量：角色名称到系统提示词的映射
        self._role_prompts: Dict[str, str] = {}
    
    @classmethod
    def initialize_chat_interface(
        cls, 
        api_config: ChatApiConfig, 
        max_retry: int = 3, 
        retry_delay: float = 1.0
    ) -> bool:
        """
        初始化共享的ChatInterface实例（类方法），支持重试机制
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            bool: 是否初始化成功
        """
        if cls._shared_chat_interface is None:
            cls._max_retry = max_retry
            cls._retry_delay = retry_delay
            
            # 带重试的初始化
            for attempt in range(max_retry):
                try:
                    cls._shared_chat_interface = ChatInterface(api_config)
                    if cls._shared_chat_interface.client is not None:
                        print(f"ChatInterface 初始化成功 (模型: {api_config.model})")
                        cls._is_initialized = True
                        return True
                except Exception as e:
                    print(f"ChatInterface 初始化失败 (尝试 {attempt + 1}/{max_retry}): {e}")
                    if attempt < max_retry - 1:
                        time.sleep(retry_delay)
            
            cls._is_initialized = False
            print(f"ChatInterface 初始化最终失败，已尝试 {max_retry} 次")
            return False
        
        return cls._is_initialized
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查共享的ChatInterface是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return cls._is_initialized and cls._shared_chat_interface is not None
    
    def add_role_to_map(self, role_name: str, sys_prompt: str) -> None:
        """
        添加角色到映射表
        
        Args:
            role_name: 角色名称
            sys_prompt: 系统提示词内容
        """
        self._role_prompts[role_name] = sys_prompt
    
    def remove_role_from_map(self, role_name: str) -> bool:
        """
        从映射表中删除角色
        
        Args:
            role_name: 角色名称
            
        Returns:
            bool: 是否成功删除（角色存在则返回True）
        """
        if role_name in self._role_prompts:
            del self._role_prompts[role_name]
            return True
        return False
    
    def has_role(self, role_name: str) -> bool:
        """
        检查角色是否存在
        
        Args:
            role_name: 角色名称
            
        Returns:
            bool: 角色是否存在
        """
        return role_name in self._role_prompts
    
    def get_role_prompt(self, role_name: str) -> Optional[str]:
        """
        获取角色的系统提示词
        
        Args:
            role_name: 角色名称
            
        Returns:
            Optional[str]: 系统提示词，角色不存在时返回None
        """
        return self._role_prompts.get(role_name)
    
    async def get_role_response(
        self, 
        role_name: str, 
        user_prompt: str, 
        callback: Callable[[str], None]
    ) -> str:
        """
        获取指定角色的AI响应（包装ChatInterface的stream_response并添加重试机制）
        
        Args:
            role_name: 角色名称
            user_prompt: 用户提示词
            callback: 回调函数，用于接收流式响应内容
            
        Returns:
            str: 响应状态码
                - ChatResponseStatus.SUCCESS: 成功
                - ChatResponseStatus.CLIENT_NOT_INITIALIZED: 客户端未初始化
                - ChatResponseStatus.STREAM_FAILED: 流式响应失败（重试后）
                - ChatResponseStatus.ROLE_NOT_FOUND: 角色不存在
        """
        # 检查角色是否存在
        if role_name not in self._role_prompts:
            return ChatResponseStatus.ROLE_NOT_FOUND
        
        # 检查共享的ChatInterface是否已初始化
        if not self.is_initialized():
            return ChatResponseStatus.CLIENT_NOT_INITIALIZED
        
        # 获取角色的系统提示词
        sys_prompt = self._role_prompts[role_name]
        
        # 带重试机制的流式响应
        for attempt in range(self._max_retry):
            status = await self._shared_chat_interface.stream_response(
                sys_prompt=sys_prompt,
                user_prompt=user_prompt,
                callback=callback
            )
            
            # 成功则返回
            if status == ChatResponseStatus.SUCCESS:
                return ChatResponseStatus.SUCCESS
            
            # 客户端未初始化，不需要重试
            if status == ChatResponseStatus.CLIENT_NOT_INITIALIZED:
                return ChatResponseStatus.CLIENT_NOT_INITIALIZED
            
            # 流式响应失败，进行重试
            if attempt < self._max_retry - 1:
                print(f"流式响应失败，正在重试 ({attempt + 1}/{self._max_retry})...")
                return ChatResponseStatus.STREAM_RETRY

        # 重试失败
        print(f"流式响应失败 (已重试 {self._max_retry} 次)")
        return ChatResponseStatus.STREAM_FAILED
    
    def load_role_from_file(self, role_name: str, prompt_file_path: str) -> bool:
        """
        从文件加载角色的系统提示词
        
        Args:
            role_name: 角色名称
            prompt_file_path: 提示词文件路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                sys_prompt = f.read()
            self.add_role_to_map(role_name, sys_prompt)
            return True
        except Exception as e:
            print(f"加载角色 {role_name} 的提示词文件失败: {e}")
            return False
    
    def get_all_roles(self) -> list:
        """
        获取所有已注册的角色名称
        
        Returns:
            list: 角色名称列表
        """
        return list(self._role_prompts.keys())
    
    def clear_all_roles(self) -> None:
        """清空所有角色"""
        self._role_prompts.clear()
