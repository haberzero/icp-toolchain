"""
ICP Chat Handler - 管理AI接口的包装器

这个模块提供了一个高层次的接口来管理ChatInterface实例,
使用单例模式管理不同配置的handler实例。包含重试机制逻辑。
"""

import asyncio
import time
from typing import Optional, Tuple, Dict

from typedef.ai_data_types import ChatApiConfig, ChatResponseStatus
from typedef.cmd_data_types import Colors
from libs.ai_interface.chat_interface import ChatInterface


class ICPChatHandler:
    """ICP聊天处理器,提供AI聊天接口和重试机制
    
    使用单例模式，支持两个独立的handler实例：
    - chat_handler: 用于对话场景
    - coder_handler: 用于代码生成场景
    """
    
    # 类变量：存储不同handler_key对应的单例实例
    _instances: Dict[str, 'ICPChatHandler'] = {}
    
    # 每个实例的状态变量
    _chat_interface: Optional[ChatInterface]
    _is_initialized: bool
    _initialization_attempted: bool
    _max_retry: int
    _retry_delay: float
    _handler_key: str
    
    def __new__(cls, handler_key: str = 'coder_handler'):
        """创建或获取指定handler_key的单例实例
        
        Args:
            handler_key: handler类型标识，支持 'chat_handler' 和 'coder_handler'
            
        Returns:
            ICPChatHandler: 对应handler_key的单例实例
        """
        if handler_key not in cls._instances:
            instance = super(ICPChatHandler, cls).__new__(cls)
            cls._instances[handler_key] = instance
        return cls._instances[handler_key]
    
    def __init__(self, handler_key: str = 'coder_handler'):
        """初始化ICP聊天处理器
        
        Args:
            handler_key: handler类型标识
        """
        # 避免重复初始化
        if hasattr(self, '_handler_key'):
            return
            
        self._handler_key = handler_key
        self._chat_interface = None
        self._is_initialized = False
        self._initialization_attempted = False
        self._max_retry = 3
        self._retry_delay = 1.0
    
    def initialize_chat_interface(
        self, 
        api_config: ChatApiConfig, 
        max_retry: int = 3, 
        retry_delay: float = 1.0
    ) -> bool:
        """
        初始化当前实例的ChatInterface，支持重试机制
        
        Args:
            api_config: API配置信息
            max_retry: 最大重试次数
            retry_delay: 重试延迟(秒)
            
        Returns:
            bool: 是否初始化成功
        """
        # 如果已经尝试过初始化，直接返回之前的结果
        if self._initialization_attempted:
            return self._is_initialized
        
        # 标记已尝试初始化
        self._initialization_attempted = True
        
        if self._chat_interface is None:
            self._max_retry = max_retry
            self._retry_delay = retry_delay
            
            # 带重试的初始化
            for attempt in range(max_retry):
                try:
                    self._chat_interface = ChatInterface(api_config)
                    if self._chat_interface.client is not None:
                        # 进行真实的连接验证
                        print(f"ChatInterface 客户端创建成功，正在验证连接...")
                        is_connected = asyncio.run(
                            self._chat_interface.verify_connection()
                        )
                        
                        if is_connected:
                            print(f"ChatInterface 初始化成功 (handler: {self._handler_key}, 模型: {api_config.model})")
                            self._is_initialized = True
                            return True
                        else:
                            print(f"模型连接验证失败 (尝试 {attempt + 1}/{max_retry})")
                            self._chat_interface = None
                except Exception as e:
                    print(f"ChatInterface 初始化失败 (尝试 {attempt + 1}/{max_retry}): {e}")
                    self._chat_interface = None
                
                if attempt < max_retry - 1:
                    time.sleep(retry_delay)
            
            self._is_initialized = False
            print(f"ChatInterface 初始化最终失败，已尝试 {max_retry} 次")
            return False
        
        return self._is_initialized
    
    def is_initialized(self) -> bool:
        """
        检查当前实例的ChatInterface是否已初始化
        
        Returns:
            bool: 是否已初始化
        """
        return self._is_initialized and self._chat_interface is not None
    
    def reset_initialization(self) -> None:
        """
        重置ChatInterface初始化状态，允许重新初始化ChatInterface
        在更改API配置后需要重新连接时使用
        """
        self._chat_interface = None
        self._is_initialized = False
        self._initialization_attempted = False
        print(f"已重置ChatInterface初始化状态 (handler: {self._handler_key})")
    
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
        
        # 检查当前实例的ChatInterface是否已初始化
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
            
            status = await self._chat_interface.stream_response(
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
