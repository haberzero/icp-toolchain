import os
import json
import re
import hashlib
from typing import List, Dict, Optional, Union, Set, Any

from typedef.ibc_data_types import (
    IbcBaseAstNode, ClassNode, FunctionNode, VariableNode, 
    BehaviorStepNode, FileSymbolTable, SymbolType, VisibilityTypes
)

class IbcFuncs:
    """IBC代码处理相关的静态工具函数集合"""
    
    # ==================== MD5计算 ====================
    
    @staticmethod
    def calculate_text_md5(text: str) -> str:
        """计算文本字符串的MD5校验值"""
        try:
            text_hash = hashlib.md5()
            text_hash.update(text.encode('utf-8'))
            return text_hash.hexdigest()
        except UnicodeEncodeError as e:
            raise ValueError(f"文本编码错误,无法转换为UTF-8") from e
        except Exception as e:
            raise RuntimeError(f"计算文本MD5时发生未知错误") from e
    
    # ==================== 符号验证 ====================
    
    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """验证标识符是否符合编程规范
        
        标识符必须以字母或下划线开头,仅包含字母、数字、下划线
        """
        if not identifier:
            return False
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return re.match(pattern, identifier) is not None
    
    # ==================== 符号规范化响应解析 ====================
    
    @staticmethod
    def parse_symbol_normalizer_response(response: str) -> Dict[str, Dict[str, str]]:
        """解析符号规范化AI的响应
        
        Args:
            response: AI返回的JSON格式响应
            
        Returns:
            Dict[str, Dict[str, str]]: 符号规范化结果字典
                格式: {"原始符号名": {"normalized_name": "规范化名", "visibility": "可见性"}}
        """
        try:
            from app.ai_chat_handler import ICPChatHandler
            
            # 清理代码块标记
            cleaned_response = ICPChatHandler.clean_code_block_markers(response)
            
            # 解析JSON
            result = json.loads(cleaned_response)
            
            # 有效的可见性值列表
            valid_visibilities = [v.value for v in VisibilityTypes]
            
            # 验证结果格式
            validated_result = {}
            for symbol_name, symbol_data in result.items():
                if 'normalized_name' in symbol_data and 'visibility' in symbol_data:
                    # 验证normalized_name符合标识符规范
                    if IbcFuncs.validate_identifier(symbol_data['normalized_name']):
                        # 验证visibility是预定义值
                        if symbol_data['visibility'] in valid_visibilities:
                            validated_result[symbol_name] = symbol_data
                        else:
                            print(f"    警告: 符号 {symbol_name} 的可见性值无效: {symbol_data['visibility']},使用默认值")
                            # 仍然保留该符号,但使用默认可见性
                            symbol_data['visibility'] = 'module_local'
                            validated_result[symbol_name] = symbol_data
                    else:
                        print(f"    警告: 符号 {symbol_name} 的规范化名称无效: {symbol_data['normalized_name']}")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            print(f"    错误: 解析AI响应JSON失败: {e}")
            return {}
        except Exception as e:
            print(f"    错误: 处理AI响应失败: {e}")
            return {}
    
    # ==================== 符号映射构建 ====================
    
    @staticmethod
    def build_symbol_mapping(symbol_table: FileSymbolTable) -> Dict[str, str]:
        """构建符号名映射字典
        
        Args:
            symbol_table: 文件符号表
            
        Returns:
            Dict[str, str]: {原始名称 -> 规范化名称} 映射
        """
        mapping = {}
        for symbol_name, symbol in symbol_table.items():
            if symbol.normalized_name:
                mapping[symbol.symbol_name] = symbol.normalized_name
        return mapping
    
    # ==================== AST符号替换 ====================
    
    @staticmethod
    def replace_symbols_in_ast(
        ast_dict: Dict[int, IbcBaseAstNode],
        symbol_mapping: Dict[str, str],
        vector_db_manager=None
    ) -> None:
        """在AST中替换符号为规范化名称
        
        Args:
            ast_dict: AST节点字典
            symbol_mapping: 符号映射字典 {原始名称 -> 规范化名称}
            vector_db_manager: 符号向量数据库管理器(可选,用于$ref$引用查找)
        """
        for uid, node in ast_dict.items():
            if isinstance(node, ClassNode):
                IbcFuncs._replace_class_symbols(node, symbol_mapping)
            elif isinstance(node, FunctionNode):
                IbcFuncs._replace_function_symbols(node, symbol_mapping)
            elif isinstance(node, VariableNode):
                IbcFuncs._replace_variable_symbols(node, symbol_mapping)
            elif isinstance(node, BehaviorStepNode):
                IbcFuncs._replace_behavior_symbols(node, symbol_mapping, vector_db_manager)
    
    @staticmethod
    def _replace_class_symbols(node: ClassNode, symbol_mapping: Dict[str, str]) -> None:
        """替换类节点中的符号"""
        # 替换类名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
        
        # 替换继承参数中的符号
        if node.inh_params:
            new_params = {}
            for param_name, param_desc in node.inh_params.items():
                new_name = symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.inh_params = new_params
    
    @staticmethod
    def _replace_function_symbols(node: FunctionNode, symbol_mapping: Dict[str, str]) -> None:
        """替换函数节点中的符号"""
        # 替换函数名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
        
        # 替换参数中的符号
        if node.params:
            new_params = {}
            for param_name, param_desc in node.params.items():
                new_name = symbol_mapping.get(param_name, param_name)
                new_params[new_name] = param_desc
            node.params = new_params
    
    @staticmethod
    def _replace_variable_symbols(node: VariableNode, symbol_mapping: Dict[str, str]) -> None:
        """替换变量节点中的符号"""
        # 替换变量名
        if node.identifier in symbol_mapping:
            node.identifier = symbol_mapping[node.identifier]
    
    @staticmethod
    def _replace_behavior_symbols(
        node: BehaviorStepNode,
        symbol_mapping: Dict[str, str],
        vector_db_manager=None
    ) -> None:
        """替换行为步骤节点中的符号"""
        if not node.content:
            return
        
        # 替换行为描述中的符号引用
        content = node.content
        
        # 1. 替换本地符号(不在$...$中的符号)
        for original_name, normalized_name in symbol_mapping.items():
            # 使用单词边界确保完整匹配
            pattern = r'\b' + re.escape(original_name) + r'\b'
            content = re.sub(pattern, normalized_name, content)
        
        # 2. 处理$ref_symbols$引用
        if vector_db_manager:
            content = IbcFuncs._replace_ref_symbols(content, vector_db_manager)
        
        node.content = content
    
    @staticmethod
    def _replace_ref_symbols(content: str, vector_db_manager) -> str:
        """替换内容中的$ref_symbols引用
        
        Args:
            content: 原始内容
            vector_db_manager: 向量数据库管理器
            
        Returns:
            str: 替换后的内容
        """
        # 查找所有$...$模式
        pattern = r'\$([^$]+)\$'
        matches = re.finditer(pattern, content)
        
        replacements = []
        for match in matches:
            ref_text = match.group(1)
            
            # 使用向量搜索查找最匹配的符号
            normalized_name = vector_db_manager.search_symbol(ref_text)
        
            replacements.append((match.group(0), f"${normalized_name}$"))
        
        # 执行替换
        for old_text, new_text in replacements:
            content = content.replace(old_text, new_text)
        
        return content
    
    # ==================== 可用符号文本构建 ====================
    # 其实这个方法不应该是现在这个样子.准确来讲,整个ibc_funcs里面和符号处理有关的代码都应该在resolver被确认编写更新完毕之后再重构一遍
    
    @staticmethod
    def build_available_symbols_text(
        dependencies: List[str], 
        work_ibc_dir_path: str
    ) -> str:
        """构建可用符号的文本描述
        
        根据符号的可见性过滤:
        - PUBLIC: 对所有文件可见
        - GLOBAL: 对所有文件可见
        - PROTECTED: 仅对子类/友元可见(需要AI自行判断)
        - MODULE_LOCAL: 仅在定义文件内可见,不对外暴露
        - PRIVATE: 私有,不对外暴露
        
        Args:
            dependencies: 依赖文件列表
            work_ibc_dir_path: IBC根目录路径
            
        Returns:
            str: 可用符号的文本描述
        """
        if not dependencies:
            return '暂无可用的依赖符号'

        from data_store.ibc_data_store import get_instance as get_ibc_data_store
        
        ibc_data_store = get_ibc_data_store()
        lines = ['可用的已生成符号:', '']
        
        # 定义可对外可见的符号类型(使用枚举)
        # MODULE_LOCAL 和 PRIVATE 不对外暴露
        externally_visible_types = [
            VisibilityTypes.PUBLIC,
            VisibilityTypes.GLOBAL,
            VisibilityTypes.PROTECTED
        ]
        
        for dep_file in dependencies:
            # 加载依赖文件的符号表
            dep_symbol_table = ibc_data_store.load_file_symbols(work_ibc_dir_path, dep_file)
            
            if len(dep_symbol_table) == 0:
                continue
            
            lines.append(f"来自文件: {dep_file}")
            
            has_visible_symbols = False
            for symbol_name, symbol in dep_symbol_table.items():
                # 检查符号可见性
                # 1. 如果未规范化,也列出来(供生成时参考)
                # 2. 如果已规范化,仅列出对外可见的符号
                is_visible = False
                
                if not symbol.visibility or symbol.visibility == VisibilityTypes.DEFAULT:
                    # 未规范化的符号,也列出
                    is_visible = True
                elif symbol.visibility in externally_visible_types:
                    # 已规范化且可见性符合要求
                    is_visible = True
                
                if is_visible:
                    # 处理symbol_type,避免None情况
                    if symbol.symbol_type:
                        symbol_type_label = {
                            SymbolType.CLASS: '类',
                            SymbolType.FUNCTION: '函数',
                            SymbolType.VARIABLE: '变量',
                            SymbolType.MODULE: '模块'
                        }.get(symbol.symbol_type, symbol.symbol_type.value)
                    else:
                        symbol_type_label = '未知'
                    
                    description = symbol.description if symbol.description else '无描述'
                    lines.append(f"- {symbol_type_label} {symbol.symbol_name}")
                    lines.append(f"  描述: {description}")
                    
                    if symbol.normalized_name:
                        lines.append(f"  规范化名称: {symbol.normalized_name}")
                    
                    # 显示可见性信息
                    if symbol.visibility and symbol.visibility != VisibilityTypes.DEFAULT:
                        visibility_label = {
                            VisibilityTypes.PUBLIC: '公开(所有文件可用)',
                            VisibilityTypes.GLOBAL: '全局(所有文件可用)',
                            VisibilityTypes.PROTECTED: '受保护(仅子类/友元可用)'
                        }.get(symbol.visibility, symbol.visibility.value)
                        lines.append(f"  可见性: {visibility_label}")
                    
                    lines.append('')
                    has_visible_symbols = True
            
            # 如果该依赖文件没有可见符号,移除文件标题
            if not has_visible_symbols:
                lines.pop()  # 移除添加的第一行 "来自文件:"
        
        # 添加可见性规则说明
        if len(lines) > 2:
            lines.append('')
            lines.append('**符号可见性规则说明:**')
            lines.append('- 公开(public)/全局(global): 可以直接使用')
            lines.append('- 受保护(protected): 仅当当前文件是符号所在类的子类或友元时才能使用,否则不能使用')
            lines.append('- 模块局部(module_local): 仅在符号定义文件内可用,不对外暴露')
            lines.append('- 私有(private): 不对外暴露,不能使用')
            lines.append('')
            lines.append('请你在生成代码时严格遵守以上可见性规则,不要使用不符合可见性要求的符号。')
        
        return '\n'.join(lines) if len(lines) > 2 else '暂无可用的依赖符号'
