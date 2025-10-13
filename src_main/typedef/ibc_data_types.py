from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass, field


# ====== Lexer 模块 数据类型定义 ======
class IbcTokenType(Enum):
    """Token类型枚举"""
    KEYWORDS = "KEYWORDS"  # 保留关键字
    IDENTIFIER = "IDENTIFIER"  # 一般文本
    LPAREN = "LPAREN"  # 左括号
    RPAREN = "RPAREN"  # 右括号
    COMMA = "COMMA"  # 逗号
    COLON = "COLON"  # 冒号
    REF_IDENTIFIER = "REF_IDENTIFIER"  # 符号引用
    INTENT_COMMENT = "INTENT_COMMENT"  # 意图注释
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


class Token:
    """Token类"""
    def __init__(self, type_: IbcTokenType, value: str, line_num: int):
        self.type = type_
        self.value = value
        self.line_num = line_num

    def __repr__(self):
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


@dataclass
class AstNode:
    """AST基础节点类"""
    uid: str = ""
    parent_uid: str = ""
    children_uids: List[str] = field(default_factory=list)
    node_type: AstNodeType = AstNodeType.DEFAULT
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        return {
            "uid": self.uid,
            "parent_uid": self.parent_uid,
            "children_uids": self.children_uids,
            "node_type": self.node_type.value if self.node_type else None,
            "line_number": self.line_number
        }

    def __repr__(self):
        return f"AstNode(uid={self.uid}, type={self.node_type})"

    def add_child(self, child_uid: str) -> None:
        """添加子节点"""
        if child_uid not in self.children_uids:
            self.children_uids.append(child_uid)

    def remove_child(self, child_uid: str) -> None:
        """移除子节点"""
        if child_uid in self.children_uids:
            self.children_uids.remove(child_uid)


@dataclass
class ModuleNode(AstNode):
    """Module节点类"""
    identifier: str = ""
    content: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "content": self.content
        })
        return result

    def __repr__(self):
        return f"ModuleNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class ClassNode(AstNode):
    """Class节点类"""
    identifier: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "external_desc": self.external_desc,
            "intent_comment": self.intent_comment,
            "params": self.params
        })
        return result

    def __repr__(self):
        return f"ClassNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class FunctionNode(AstNode):
    """Function节点类"""
    identifier: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "external_desc": self.external_desc,
            "intent_comment": self.intent_comment,
            "params": self.params
        })
        return result

    def __repr__(self):
        return f"FunctionNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class VariableNode(AstNode):
    """Variable节点类"""
    identifier: str = ""
    content: str = ""
    external_desc: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "content": self.content,
            "external_desc": self.external_desc
        })
        return result

    def __repr__(self):
        return f"VariableNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class BehaviorStepNode(AstNode):
    """BehaviorStep节点类"""
    content: str = ""
    symbol_refs: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "content": self.content,
            "symbol_refs": self.symbol_refs
        })
        return result

    def __repr__(self):
        return f"BehaviorStepNode(uid={self.uid})"
