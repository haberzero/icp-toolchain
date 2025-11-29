from enum import Enum
import enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


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


# TODO: 关于to_dict以及from_dict方法，以后可能需要重构。应该用一个专用的工厂类处理
@dataclass
class IbcBaseAstNode:
    """AST基础节点类"""
    uid: int = 0
    parent_uid: int = 0
    children_uids: List[int] = field(default_factory=list)
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
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'IbcBaseAstNode':
        """从字典创建节点"""
        return IbcBaseAstNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.DEFAULT,
            line_number=data.get("line_number", 0)
        )

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
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ModuleNode':
        """从字典创建节点"""
        return ModuleNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.MODULE,
            line_number=data.get("line_number", 0),
            identifier=data.get("identifier", ""),
            content=data.get("content", "")
        )

    def __repr__(self):
        return f"ModuleNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class ClassNode(IbcBaseAstNode):
    """Class节点类"""
    identifier: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    inh_params: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "external_desc": self.external_desc,
            "intent_comment": self.intent_comment,
            "params": self.inh_params
        })
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ClassNode':
        """从字典创建节点"""
        return ClassNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.CLASS,
            line_number=data.get("line_number", 0),
            identifier=data.get("identifier", ""),
            external_desc=data.get("external_desc", ""),
            intent_comment=data.get("intent_comment", ""),
            inh_params=data.get("params", {})
        )

    def __repr__(self):
        return f"ClassNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class FunctionNode(IbcBaseAstNode):
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
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FunctionNode':
        """从字典创建节点"""
        return FunctionNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.FUNCTION,
            line_number=data.get("line_number", 0),
            identifier=data.get("identifier", ""),
            external_desc=data.get("external_desc", ""),
            intent_comment=data.get("intent_comment", ""),
            params=data.get("params", {})
        )

    def __repr__(self):
        return f"FunctionNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class VariableNode(IbcBaseAstNode):
    """Variable节点类"""
    identifier: str = ""
    content: str = ""
    external_desc: str = ""
    intent_comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "identifier": self.identifier,
            "content": self.content,
            "external_desc": self.external_desc,
            "intent_comment": self.intent_comment
        })
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'VariableNode':
        """从字典创建节点"""
        return VariableNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.VARIABLE,
            line_number=data.get("line_number", 0),
            identifier=data.get("identifier", ""),
            content=data.get("content", ""),
            external_desc=data.get("external_desc", ""),
            intent_comment=data.get("intent_comment", "")
        )

    def __repr__(self):
        return f"VariableNode(uid={self.uid}, identifier={self.identifier})"


@dataclass
class BehaviorStepNode(IbcBaseAstNode):
    """BehaviorStep节点类"""
    content: str = ""
    symbol_refs: List[str] = field(default_factory=list)
    new_block_flag: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示"""
        result = super().to_dict()
        result.update({
            "content": self.content,
            "symbol_refs": self.symbol_refs,
            "new_block_flag": self.new_block_flag
        })
        return result
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'BehaviorStepNode':
        """从字典创建节点"""
        return BehaviorStepNode(
            uid=data.get("uid", 0),
            parent_uid=data.get("parent_uid", 0),
            children_uids=data.get("children_uids", []),
            node_type=AstNodeType(data["node_type"]) if data.get("node_type") else AstNodeType.BEHAVIOR_STEP,
            line_number=data.get("line_number", 0),
            content=data.get("content", ""),
            symbol_refs=data.get("symbol_refs", []),
            new_block_flag=data.get("new_block_flag", False)
        )

    def __repr__(self):
        return f"BehaviorStepNode(uid={self.uid})"


class VisibilityTypes(Enum):
    DEFAULT = "default" # 未被填充，性质等同于private
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    MODULE_LOCAL = "module_local"
    GLOBAL = "global"


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
    symbol_name: str = ""
    normalized_name: str = ""  # 规范化名称，由AI推断后填充
    visibility: VisibilityTypes = VisibilityTypes.DEFAULT  # 可见性，由AI推断后填充
    symbol_type: SymbolType = SymbolType.DEFAULT
    description: str = ""   # 对外功能描述
    
    def to_dict(self) -> Dict[str, Any]:
        """将符号节点转换为字典表示"""
        return {
            "uid": self.uid,
            "symbol_name": self.symbol_name,
            "normalized_name": self.normalized_name,
            "visibility": self.visibility.value,
            "description": self.description,
            "symbol_type": self.symbol_type.value
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SymbolNode':
        """从字典创建符号节点"""
        return SymbolNode(
            uid=data.get("uid", 0),
            symbol_name=data.get("symbol_name", ""),
            normalized_name=data.get("normalized_name", ""),
            visibility=data.get("visibility", VisibilityTypes.DEFAULT),
            description=data.get("description", ""),
            symbol_type=data.get("symbol_type", SymbolType.DEFAULT)
        )
    
    def __repr__(self):
        return f"SymbolNode(uid={self.uid}, name={self.symbol_name}, type={self.symbol_type})"
    
    def is_normalized(self) -> bool:
        """检查符号是否已经规范化（包含规范化名称和可见性）"""
        return bool(self.normalized_name and self.visibility is not VisibilityTypes.DEFAULT)
    
    def update_normalized_info_from_str(self, normalized_name: str, visibility: str) -> None:
        """直接从str更新规范化信息, 主要在ai进行文本填充后使用"""
        self.normalized_name = normalized_name
        self.visibility = VisibilityTypes(visibility)

    def update_normalized_info(self, normalized_name: str, visibility: VisibilityTypes) -> None:
        """更新规范化信息"""
        self.normalized_name = normalized_name
        self.visibility = visibility


@dataclass
class FileSymbolTable:
    """文件符号表类"""
    symbols: Dict[str, SymbolNode] = field(default_factory=dict)  # key为symbol_name
    
    def to_dict(self) -> Dict[str, Any]:
        """将文件符号表转换为字典表示"""
        symbols_dict = {}
        for name, symbol in self.symbols.items():
            symbols_dict[name] = symbol.to_dict()
        
        return symbols_dict
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FileSymbolTable':
        """从字典创建文件符号表"""
        symbols = {}
        
        for name, symbol_dict in data.items():
            symbol_node = SymbolNode.from_dict(symbol_dict)
            symbols[name] = symbol_node
        
        return FileSymbolTable(
            symbols=symbols
        )
    
    def __repr__(self):
        return f"FileSymbolTable(symbols_count={len(self.symbols)})"
    
    def add_symbol(self, symbol: SymbolNode) -> None:
        """添加符号"""
        self.symbols[symbol.symbol_name] = symbol
    
    def get_symbol(self, symbol_name: str) -> Optional[SymbolNode]:
        """获取符号"""
        return self.symbols.get(symbol_name)
    
    def remove_symbol(self, symbol_name: str) -> None:
        """移除符号"""
        if symbol_name in self.symbols:
            del self.symbols[symbol_name]
    
    def has_symbol(self, symbol_name: str) -> bool:
        """检查是否包含指定符号"""
        return symbol_name in self.symbols
    
    def get_all_symbols(self) -> Dict[str, SymbolNode]:
        """获取所有符号"""
        return self.symbols
    
    def get_unnormalized_symbols(self) -> Dict[str, SymbolNode]:
        """获取所有未规范化的符号"""
        unnormalized_symbols = {}
        
        for name, symbol in self.symbols.items():
            if not symbol.is_normalized():
                unnormalized_symbols[name] = symbol
        
        return unnormalized_symbols
