from enum import Enum
import enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, fields


# ====== Lexer 模块 数据类型定义 ======
class IbcTokenType(Enum):
    """Token类型枚举"""
    KEYWORDS = "KEYWORDS"  # 关键字
    IDENTIFIER = "IDENTIFIER"  # 一般文本
    LPAREN = "LPAREN"  # 左小括号 (
    RPAREN = "RPAREN"  # 右小括号 )
    LBRACE = "LBRACE"  # 左花括号 {
    RBRACE = "RBRACE"  # 右花括号 }
    LBRACKET = "LBRACKET"  # 左方括号 [
    RBRACKET = "RBRACKET"  # 右方括号 ]
    COMMA = "COMMA"  # 逗号 ,
    COLON = "COLON"  # 冒号 :
    EQUAL = "EQUAL"  # 等号 =
    BACKSLASH = "BACKSLASH"  # 反斜杠 \
    REF_IDENTIFIER = "REF_IDENTIFIER"  # 符号引用
    INDENT = "INDENT"  # 缩进
    DEDENT = "DEDENT"  # 退格
    NEWLINE = "NEWLINE"  # 换行符
    EOF = "EOF"  # 文件结束


class IbcKeywords(Enum):
    """关键字枚举"""
    MODULE = "module"
    FUNC = "func"
    CLASS = "class"
    VAR = "var"
    DESCRIPTION = "description"
    INTENT = "@"
    BEHAVIOR = "behavior"   # 特殊关键字，不由用户书写，而是由lexer自动添加至token list
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"


class Token:
    """Token类"""
    def __init__(self, type: IbcTokenType, value: str, line_num: int):
        self.type: IbcTokenType = type
        self.value: str = value
        self.line_num: int = line_num

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value}, {self.line_num})"


# ====== Parser 模块 数据类型定义 ======
class AstNodeType(Enum):
    """AST节点类型枚举"""
    DEFAULT = "DEFAULT"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    VARIABLE = "VARIABLE"
    BEHAVIOR_STEP = "BEHAVIOR_STEP"


class VisibilityTypes(Enum):
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"


# TODO: 关于to_dict以叏from_dict方法，以后可能需要重构。应该用一个专用的工厂类处理
@dataclass
class IbcBaseAstNode:
    """AST基础节点类"""
    uid: int = 0
    parent_uid: int = 0
    children_uids: List[int] = field(default_factory=list)
    node_type: AstNodeType = AstNodeType.DEFAULT
    line_number: int = 0
    visibility: VisibilityTypes = VisibilityTypes.PUBLIC  # 可见性标记，默认为public
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, Enum):
                result[f.name] = value.value
            else:
                result[f.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IbcBaseAstNode':
        """从字典创建节点"""
        init_kwargs = {}
        for f in fields(cls):
            if f.name not in data:
                continue
            value = data[f.name]
            if f.type is AstNodeType:
                value = AstNodeType(value) if value else AstNodeType.DEFAULT
            elif f.type is VisibilityTypes:
                value = VisibilityTypes(value) if value else VisibilityTypes.PUBLIC
            elif hasattr(f.type, '__origin__') and f.type.__origin__ is list:
                # 简单处理 List[T]
                value = list(value) if value else []
            init_kwargs[f.name] = value
        return cls(**init_kwargs)

    def __repr__(self):
        return f"AstNode(uid={self.uid}, type={self.node_type})"

    def add_child(self, child_uid: int) -> None:
        """添加子节点"""
        if child_uid not in self.children_uids:
            self.children_uids.append(child_uid)

    def remove_child(self, child_uid: int) -> None:
        """移除子节点"""
        if child_uid in self.children_uids:
            self.children_uids.remove(child_uid)


@dataclass
class ModuleNode(IbcBaseAstNode):
    """模块节点类"""
    identifier: str = ""
    content: str = ""

    def __repr__(self):
        return f"ModuleNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class ClassNode(IbcBaseAstNode):
    """类节点类"""
    identifier: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    inh_params: Dict[str, str] = field(default_factory=dict)

    def __repr__(self):
        return f"ClassNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class FunctionNode(IbcBaseAstNode):
    """函数节点类"""
    identifier: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    param_type_refs: Dict[str, str] = field(default_factory=dict)  # 参数类型引用 {参数名: 符号引用内容}，存储参数描述中的$引用

    def __repr__(self):
        return f"FunctionNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class VariableNode(IbcBaseAstNode):
    """变量节点类"""
    identifier: str = ""
    content: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    type_ref: List[str] = field(default_factory=list)  # 变量类型引用，存储变量描述中的$引用（允许多个）

    def __repr__(self):
        return f"VariableNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class BehaviorStepNode(IbcBaseAstNode):
    """行为步骤节点类"""
    content: str = ""
    symbol_refs: List[str] = field(default_factory=list)
    new_block_flag: bool = False

    def __repr__(self):
        return f"BehaviorStepNode(uid={self.uid})"


class SymbolType(Enum):
    """符号类型枚举"""
    DEFAULT = "default"
    CLASS = "class"
    FUNCTION = "func"
    VARIABLE = "var"


@dataclass
class SymbolNode:
    """符号表节点类"""
    uid: int = 0
    parent_symbol_name: str = ""  # 父符号名称，用于建立层次关系
    children_symbol_names: List[str] = field(default_factory=list)  # 子符号名称列表
    symbol_name: str = ""
    normalized_name: str = ""  # 规范化名称，由AI推断后填充
    visibility: VisibilityTypes = VisibilityTypes.PUBLIC  # 可见性，从 AST 节点直接填充，默认为public
    symbol_type: SymbolType = SymbolType.DEFAULT
    description: str = ""   # 对外功能描述
    parameters: Dict[str, str] = field(default_factory=dict)  # 函数参数 {参数名: 参数描述}，仅FUNCTION类型使用
    
    def to_dict(self) -> Dict[str, Any]:
        """将符号节点转换为字典表示"""
        return {
            "uid": self.uid,
            "parent_symbol_name": self.parent_symbol_name,
            "children_symbol_names": self.children_symbol_names,
            "symbol_name": self.symbol_name,
            "normalized_name": self.normalized_name,
            "visibility": self.visibility.value,
            "description": self.description,
            "symbol_type": self.symbol_type.value,
            "parameters": self.parameters
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SymbolNode':
        """从字典创建符号节点"""
        visibility_value = data.get("visibility", VisibilityTypes.PUBLIC)
        if isinstance(visibility_value, str):
            try:
                visibility_value = VisibilityTypes(visibility_value)
            except ValueError:
                visibility_value = VisibilityTypes.PUBLIC
        
        symbol_type_value = data.get("symbol_type", SymbolType.DEFAULT)
        if isinstance(symbol_type_value, str):
            try:
                symbol_type_value = SymbolType(symbol_type_value)
            except ValueError:
                symbol_type_value = SymbolType.DEFAULT
        
        return SymbolNode(
            uid=data.get("uid", 0),
            parent_symbol_name=data.get("parent_symbol_name", ""),
            children_symbol_names=data.get("children_symbol_names", []),
            symbol_name=data.get("symbol_name", ""),
            normalized_name=data.get("normalized_name", ""),
            visibility=visibility_value,
            description=data.get("description", ""),
            symbol_type=symbol_type_value,
            parameters=data.get("parameters", {})
        )
    
    def __repr__(self):
        return f"SymbolNode(uid={self.uid}, name={self.symbol_name}, type={self.symbol_type})"
    
    def is_normalized(self) -> bool:
        """检查符号是否已经规范化（包含规范化名称）"""
        return bool(self.normalized_name)
    
    def update_normalized_info(self, normalized_name: str, visibility: VisibilityTypes) -> None:
        """更新规范化信息"""
        self.normalized_name = normalized_name
        self.visibility = visibility
    
    def add_child(self, child_symbol_name: str) -> None:
        """添加子符号"""
        if child_symbol_name not in self.children_symbol_names:
            self.children_symbol_names.append(child_symbol_name)
    
    def remove_child(self, child_symbol_name: str) -> None:
        """移除子符号"""
        if child_symbol_name in self.children_symbol_names:
            self.children_symbol_names.remove(child_symbol_name)


# FileSymbolTable类已被移除，现在直接使用 Dict[str, SymbolNode] 类型
