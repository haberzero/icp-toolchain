from enum import Enum
import enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, fields, asdict


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
    SELF_REF_IDENTIFIER = "SELF_REF_IDENTIFIER"  # self引用（self.xxx格式）
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
    symbol_refs: List[str] = field(default_factory=list)  # $开头的符号引用
    self_refs: List[str] = field(default_factory=list)  # self.xxx格式的引用
    new_block_flag: bool = False

    def __repr__(self):
        return f"BehaviorStepNode(uid={self.uid})"


# ====== 符号元数据 数据类型定义 ======

@dataclass
class SymbolMetadataBase:
    """符号元数据基类"""
    type: str  # 符号类型: folder/file/class/func/var
    description: str = ""  # 描述信息
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于JSON序列化"""
        result = asdict(self)
        # 移除空字符串和空字典
        return {k: v for k, v in result.items() if v not in ("", {}, False) or k in ("type", "__is_local__")}


@dataclass
class FolderMetadata(SymbolMetadataBase):
    """文件夹元数据"""
    type: str = "folder"


@dataclass
class FileMetadata(SymbolMetadataBase):
    """文件元数据"""
    type: str = "file"


@dataclass
class ClassMetadata(SymbolMetadataBase):
    """类符号元数据"""
    type: str = "class"
    visibility: str = "public"  # 可见性: public/protected/private
    normalized_name: str = ""  # 规范化后的名称
    __is_local__: bool = False  # 是否是本地符号（由VisibleSymbolBuilder添加）
    __local_file__: str = ""  # 本地符号所在文件（由VisibleSymbolBuilder添加）


@dataclass
class FunctionMetadata(SymbolMetadataBase):
    """函数符号元数据"""
    type: str = "func"
    visibility: str = "public"  # 可见性: public/protected/private
    parameters: Dict[str, str] = field(default_factory=dict)  # 参数列表 {参数名: 参数描述}
    normalized_name: str = ""  # 规范化后的名称
    __is_local__: bool = False  # 是否是本地符号
    __local_file__: str = ""  # 本地符号所在文件


@dataclass
class VariableMetadata(SymbolMetadataBase):
    """变量符号元数据"""
    type: str = "var"
    visibility: str = "public"  # 可见性: public/protected/private
    scope: str = "unknown"  # 作用域: global/field/local/unknown
    normalized_name: str = ""  # 规范化后的名称
    __is_local__: bool = False  # 是否是本地符号
    __local_file__: str = ""  # 本地符号所在文件


# 联合类型：所有符号元数据类型
SymbolMetadata = Union[FolderMetadata, FileMetadata, ClassMetadata, FunctionMetadata, VariableMetadata]


def create_symbol_metadata(data: Dict[str, Any]) -> SymbolMetadata:
    """从字典创建符号元数据对象
    
    Args:
        data: 符号元数据字典
        
    Returns:
        对应类型的符号元数据对象
        
    Raises:
        ValueError: 如果类型字段无效
    """
    symbol_type = data.get("type", "")
    
    if symbol_type == "folder":
        return FolderMetadata(**{k: v for k, v in data.items() if k in FolderMetadata.__dataclass_fields__})
    elif symbol_type == "file":
        return FileMetadata(**{k: v for k, v in data.items() if k in FileMetadata.__dataclass_fields__})
    elif symbol_type == "class":
        return ClassMetadata(**{k: v for k, v in data.items() if k in ClassMetadata.__dataclass_fields__})
    elif symbol_type == "func":
        return FunctionMetadata(**{k: v for k, v in data.items() if k in FunctionMetadata.__dataclass_fields__})
    elif symbol_type == "var":
        return VariableMetadata(**{k: v for k, v in data.items() if k in VariableMetadata.__dataclass_fields__})
    else:
        raise ValueError(f"未知的符号类型: {symbol_type}")
