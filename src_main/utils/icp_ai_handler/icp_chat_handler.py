"""
ICP Chat Handler - 管理AI接口的包装器

这个模块提供了一个高层次的接口来管理ChatInterface实例,
所有实例共享一个ChatInterface以避免资源浪费。包含重试机制逻辑。
"""

import asyncio
import time
from typing import Optional, Tuple

from typedef.ai_data_types import ChatApiConfig, ChatResponseStatus
from typedef.cmd_data_types import Colors
from libs.ai_interface.chat_interface import ChatInterface


class ICPChatHandler:
    """ICP聊天处理器,提供AI聊天接口和重试机制"""
    
    # 类变量：共享的ChatInterface实例
    _shared_chat_interface: Optional[ChatInterface] = None
    _is_initialized: bool = False
    _initialization_attempted: bool = False  # 标记是否已尝试过初始化
    _max_retry: int = 3
    _retry_delay: float = 1.0
    
    def __init__(self):
        """初始化ICP聊天处理器"""
        pass
    
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
        # 如果已经尝试过初始化，直接返回之前的结果
        if cls._initialization_attempted:
            return cls._is_initialized
        
        # 标记已尝试初始化
        cls._initialization_attempted = True
        
        if cls._shared_chat_interface is None:
            cls._max_retry = max_retry
            cls._retry_delay = retry_delay
            
            # 带重试的初始化
            for attempt in range(max_retry):
                try:
                    cls._shared_chat_interface = ChatInterface(api_config)
                    if cls._shared_chat_interface.client is not None:
                        # 进行真实的连接验证
                        print(f"ChatInterface 客户端创建成功，正在验证连接...")
                        is_connected = asyncio.run(
                            cls._shared_chat_interface.verify_connection()
                        )
                        
                        if is_connected:
                            print(f"ChatInterface 初始化成功 (模型: {api_config.model})")
                            cls._is_initialized = True
                            return True
                        else:
                            print(f"模型连接验证失败 (尝试 {attempt + 1}/{max_retry})")
                            cls._shared_chat_interface = None
                except Exception as e:
                    print(f"ChatInterface 初始化失败 (尝试 {attempt + 1}/{max_retry}): {e}")
                    cls._shared_chat_interface = None
                
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
    
    @classmethod
    def reset_initialization(cls) -> None:
        """
        重置初始化状态，允许重新初始化ChatInterface
        在更改API配置后需要重新连接时使用
        """
        cls._shared_chat_interface = None
        cls._is_initialized = False
        cls._initialization_attempted = False
        print("已重置ChatInterface初始化状态")
    
    @staticmethod
    def clean_code_block_markers(content: str) -> str:
        """
        清理响应内容中可能存在的代码块标记（```）
        
        Args:
            content: 原始响应内容
            
        Returns:
            str: 清理后的内容
        """
        cleaned_content = content.strip()
        
        # 移除可能的代码块标记
        lines = cleaned_content.split('\n')
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        
        return '\n'.join(lines).strip()
    
    async def get_role_response(
        self, 
        role_name: str,
        sys_prompt: str,
        user_prompt: str
    ) -> Tuple[str, bool]:
        """
        获取AI响应(包装ChatInterface的stream_response并添加重试机制)
        
        Args:
            role_name: 角色名称(用于日志输出)
            sys_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            Tuple[str, bool]: (响应内容, 是否成功)
        """
        print(f"    {role_name}正在生成响应...")
        
        # 检查共享的ChatInterface是否已初始化
        if not self.is_initialized():
            print(f"\n{Colors.FAIL}错误: ChatInterface未初始化{Colors.ENDC}")
            return ("", False)
        
        # 带重试机制的流式响应
        for attempt in range(self._max_retry):
            # 定义内部callback用于收集响应内容
            response_content = ""
            
            def collect_and_print(content: str) -> None:
                nonlocal response_content
                response_content += content
                print(content, end="", flush=True)
            
            status = await self._shared_chat_interface.stream_response(
                sys_prompt=sys_prompt,
                user_prompt=user_prompt,
                callback=collect_and_print
            )
            
            # 成功则返回收集到的内容
            if status == ChatResponseStatus.SUCCESS:
                print(f"\n    {role_name}运行完毕。")
                return (response_content, True)
            
            # 客户端未初始化，不需要重试
            if status == ChatResponseStatus.CLIENT_NOT_INITIALIZED:
                print(f"\n{Colors.FAIL}错误: ChatInterface未初始化{Colors.ENDC}")
                return ("", False)
            
            # 流式响应失败，清空当前收集到的内容并重试
            if attempt < self._max_retry - 1:
                print(f"\n{Colors.FAIL}流式响应失败，正在重试 ({attempt + 1}/{self._max_retry})...{Colors.ENDC}")
                # 清空当前收集到的内容，准备重试
                response_content = ""
                continue

        # 重试失败
        print(f"\n{Colors.FAIL}错误: 流式响应失败 (已重试 {self._max_retry} 次){Colors.ENDC}")
        return ("", False)
