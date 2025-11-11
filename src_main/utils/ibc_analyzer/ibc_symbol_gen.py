"""
IBC符号提取和规范化模块

负责从AST中提取符号信息，并通过AI进行符号规范化处理
"""
import asyncio
import json
import re
from typing import Dict, Any, Optional
from typedef.ibc_data_types import (
    AstNode, ClassNode, FunctionNode, VariableNode, 
    VisibilityTypes
)
from typedef.cmd_data_types import Colors
from utils.ai_handler.chat_handler import ChatHandler
from data_exchange.app_data_manager import get_instance as get_app_data_manager


class IbcSymbolGenerator:
    """IBC符号生成器，负责从AST提取符号并进行规范化"""
    
    def __init__(self, ai_handler: Optional[ChatHandler] = None):
        """
        初始化符号生成器
        
        Args:
            ai_handler: 用于符号规范化的AI处理器（可选）
        """
        self.ai_handler = ai_handler
    
    def extract_and_normalize_symbols(
        self, 
        ast_dict: Dict[int, AstNode],
        file_path: str = ""
    ) -> Dict[str, Dict[str, Any]]:
        """
        从AST中提取符号并进行规范化
        
        Args:
            ast_dict: AST节点字典
            file_path: 文件路径（用于日志和AI提示）
            
        Returns:
            Dict[str, Dict[str, Any]]: 规范化后的符号表
                格式: {
                    "符号名称": {
                        "normalized_name": "规范化名称",
                        "visibility": "可见性",
                        "description": "描述",
                        "symbol_type": "类型"
                    }
                }
        """
        # 从AST中提取符号
        symbols_info = self._extract_symbols_from_ast(ast_dict)
        
        if not symbols_info:
            return {}
        
        # 检查AI处理器是否可用
        if self.ai_handler is None:
            # 使用默认规范化策略
            return self._default_symbol_normalization(symbols_info)
        
        # 调用AI进行符号规范化
        normalized_symbols = self._call_symbol_normalizer_ai(file_path, symbols_info)
        
        if not normalized_symbols:
            # AI失败，使用默认策略
            return self._default_symbol_normalization(symbols_info)
        
        # 合并符号信息和规范化结果
        result = {}
        for symbol_name, symbol_info in symbols_info.items():
            if symbol_name in normalized_symbols:
                result[symbol_name] = {
                    'normalized_name': normalized_symbols[symbol_name]['normalized_name'],
                    'visibility': normalized_symbols[symbol_name]['visibility'],
                    'description': symbol_info['description'],
                    'symbol_type': symbol_info['symbol_type']
                }
            else:
                # 使用默认策略处理缺失的符号
                default_result = self._default_symbol_normalization({symbol_name: symbol_info})
                if symbol_name in default_result:
                    result[symbol_name] = default_result[symbol_name]
        
        return result
    
    def _extract_symbols_from_ast(self, ast_dict: Dict[int, AstNode]) -> Dict[str, Dict[str, str]]:
        """
        从AST中提取符号信息
        
        Args:
            ast_dict: AST节点字典
            
        Returns:
            Dict[str, Dict[str, str]]: 符号信息字典
                格式: {
                    "符号名称": {
                        "symbol_type": "类型",
                        "description": "描述"
                    }
                }
        """
        symbols = {}
        
        for uid, node in ast_dict.items():
            if isinstance(node, ClassNode):
                symbols[node.identifier] = {
                    'symbol_type': 'class',
                    'description': node.external_desc
                }
            elif isinstance(node, FunctionNode):
                symbols[node.identifier] = {
                    'symbol_type': 'func',
                    'description': node.external_desc
                }
            elif isinstance(node, VariableNode):
                symbols[node.identifier] = {
                    'symbol_type': 'var',
                    'description': node.external_desc
                }
        
        return symbols
    
    def _call_symbol_normalizer_ai(
        self, 
        file_path: str, 
        symbols_info: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """
        调用AI进行符号规范化
        
        Args:
            file_path: 文件路径
            symbols_info: 符号信息字典
            
        Returns:
            Dict[str, Dict[str, str]]: AI返回的规范化结果
        """
        try:
            # 构建用户提示词
            app_data_manager = get_app_data_manager()
            user_prompt_file = os.path.join(
                app_data_manager.get_user_prompt_dir(), 
                'symbol_normalizer_user.md'
            )
            
            with open(user_prompt_file, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
            
            # 构建符号列表文本
            symbols_text = self._format_symbols_for_prompt(symbols_info)
            
            # 填充占位符
            user_prompt = user_prompt_template
            user_prompt = user_prompt.replace('FILE_PATH_PLACEHOLDER', file_path)
            user_prompt = user_prompt.replace('CONTEXT_INFO_PLACEHOLDER', f"文件路径: {file_path}")
            user_prompt = user_prompt.replace('AST_SYMBOLS_PLACEHOLDER', symbols_text)
            
            # 调用AI
            response_content = asyncio.run(self._get_ai_response(user_prompt))
            
            # 解析JSON响应
            return self._parse_symbol_normalizer_response(response_content)
            
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 调用符号规范化AI失败: {e}{Colors.ENDC}")
            return {}
    
    async def _get_ai_response(self, requirement_content: str) -> str:
        """异步获取AI响应"""
        if self.ai_handler is None:
            return ""
        
        response_content = ""
        
        def collect_response(content):
            nonlocal response_content
            response_content += content
            print(content, end="", flush=True)
        
        role_name = self.ai_handler.role_name if hasattr(self.ai_handler, 'role_name') else 'AI'
        print(f"{role_name}正在生成响应...")
        await self.ai_handler.stream_response(requirement_content, collect_response)
        print(f"\n{role_name}运行完毕。")
        return response_content
    
    def _format_symbols_for_prompt(self, symbols_info: Dict[str, Dict[str, str]]) -> str:
        """
        格式化符号列表用于提示词
        
        Args:
            symbols_info: 符号信息字典
            
        Returns:
            str: 格式化后的符号列表文本
        """
        lines = []
        for symbol_name, info in symbols_info.items():
            symbol_type = info['symbol_type']
            description = info['description'] if info['description'] else '无描述'
            lines.append(f"- {symbol_name} ({symbol_type}, 描述: {description})")
        return '\n'.join(lines)
    
    def _parse_symbol_normalizer_response(self, response: str) -> Dict[str, Dict[str, str]]:
        """
        解析符号规范化AI的响应
        
        Args:
            response: AI的响应内容
            
        Returns:
            Dict[str, Dict[str, str]]: 解析后的规范化结果
        """
        try:
            # 移除可能的代码块标记
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # 解析JSON
            result = json.loads(cleaned_response)
            
            # 验证结果格式
            validated_result = {}
            for symbol_name, symbol_data in result.items():
                if 'normalized_name' in symbol_data and 'visibility' in symbol_data:
                    # 验证normalized_name符合标识符规范
                    if self._validate_identifier(symbol_data['normalized_name']):
                        # 验证visibility是预定义值
                        if symbol_data['visibility'] in VisibilityTypes:
                            validated_result[symbol_name] = symbol_data
                        else:
                            print(f"  {Colors.WARNING}警告: 符号 {symbol_name} 的可见性值无效: {symbol_data['visibility']}{Colors.ENDC}")
                    else:
                        print(f"  {Colors.WARNING}警告: 符号 {symbol_name} 的规范化名称无效: {symbol_data['normalized_name']}{Colors.ENDC}")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"  {Colors.FAIL}错误: 解析AI响应JSON失败: {e}{Colors.ENDC}")
            return {}
        except Exception as e:
            print(f"  {Colors.FAIL}错误: 处理AI响应失败: {e}{Colors.ENDC}")
            return {}
    
    def _validate_identifier(self, identifier: str) -> bool:
        """
        验证标识符是否符合规范
        
        Args:
            identifier: 待验证的标识符
            
        Returns:
            bool: 是否符合规范
        """
        if not identifier:
            return False
        # 标识符必须以字母或下划线开头，仅包含字母、数字、下划线
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    
    def _default_symbol_normalization(
        self, 
        symbols_info: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        默认的符号规范化策略
        
        Args:
            symbols_info: 符号信息字典
            
        Returns:
            Dict[str, Dict[str, Any]]: 规范化后的符号表
        """
        result = {}
        for symbol_name, info in symbols_info.items():
            # 简单的默认策略：将中文转换为拼音或使用占位符
            normalized_name = self._simple_normalize(symbol_name, info['symbol_type'])
            
            # 根据类型推断默认可见性
            default_visibility = 'file_local'
            if info['symbol_type'] == 'class':
                default_visibility = 'public'
            
            result[symbol_name] = {
                'normalized_name': normalized_name,
                'visibility': default_visibility,
                'description': info['description'],
                'symbol_type': info['symbol_type']
            }
        
        return result
    
    def _simple_normalize(self, symbol_name: str, symbol_type: str) -> str:
        """
        简单的符号名称规范化
        
        Args:
            symbol_name: 原始符号名称
            symbol_type: 符号类型
            
        Returns:
            str: 规范化后的名称
        """
        # 移除空格和特殊字符，保留字母数字
        cleaned = ''.join(c for c in symbol_name if c.isalnum() or c == '_')
        
        if not cleaned:
            # 如果清理后为空，使用类型作为前缀
            cleaned = f"{symbol_type}_symbol"
        
        # 确保以字母开头
        if cleaned and not cleaned[0].isalpha():
            cleaned = f"{symbol_type}_{cleaned}"
        
        return cleaned if cleaned else 'unnamed_symbol'


# 添加缺失的import
import os
