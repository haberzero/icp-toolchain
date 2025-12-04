from enum import Enum
from typing import List, Dict, Optional
from typedef.ibc_data_types import (
    IbcTokenType, Token, IbcBaseAstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)
from typedef.exception_types import IbcParserError

from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator

class ParserState(Enum):
    """解析器状态枚举"""
    BASE_STATE = "BASE_STATE"  # 默认状态，不起作用，仅占位
    TOP_LEVEL = "TOP_LEVEL"  # 顶层状态
    MODULE_DECL = "MODULE_DECL"  # 模块声明解析
    VAR_DECL = "VAR_DECL"  # 变量声明解析
    DESCRIPTION = "DESCRIPTION"  # 对外描述解析
    INTENT_COMMENT = "INTENT_COMMENT"  # 意图注释解析
    CLASS_DECL = "CLASS_DECL"  # 类声明解析
    CLASS_CONTENT = "CLASS_CONTENT"  # 类内容解析
    FUNC_DECL = "FUNC_DECL"  # 函数声明解析
    FUNC_CONTENT = "FUNCTION_CONTENT"  # 函数内容解析
    BEHAVIOR_STEP = "BEHAVIOR_STEP"  # 行为步骤解析


class BaseState:
    """状态基类"""
    def __init__(
        self, 
        parent_uid: int, 
        uid_generator: IbcParserUidGenerator, 
        ast_node_dict: Dict[int, IbcBaseAstNode]
    ):
        self.state_type = ParserState.BASE_STATE
        self.parent_uid = parent_uid
        self.uid_generator = uid_generator
        self.ast_node_dict = ast_node_dict
        self.current_token: Optional[Token] = None
        self.pass_in_token_flag = False

    def process_token(self, token: Token) -> None:
        pass

    def is_need_pop(self) -> bool:
        return False

    def is_need_pass_in_token(self) -> bool:
        """对于那些需要多行内容逻辑解析的状态机, 它们需要接收缩进相关token而不让顶层处理"""
        return self.pass_in_token_flag


class TopLevelState(BaseState):
    """顶层状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.TOP_LEVEL

    def process_token(self, token: Token) -> None:
        self.current_token = token


# 模块声明的子状态枚举
class ModuleDeclSubState(Enum):
    EXPECTING_MODULE_NAME = "EXPECTING_MODULE_NAME"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_CONTENT = "EXPECTING_CONTENT"


class ModuleDeclState(BaseState):
    """模块声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.MODULE_DECL
        self.module_name = ""
        self.content = ""
        self.sub_state = ModuleDeclSubState.EXPECTING_MODULE_NAME
        self.pop_flag = False

    def process_token(self, token: Token) -> None:
        self.current_token = token
        
        if self.sub_state == ModuleDeclSubState.EXPECTING_MODULE_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.module_name = token.value.strip()
                self.sub_state = ModuleDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"ModuleDeclState: Expecting module name but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == ModuleDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ModuleDeclSubState.EXPECTING_CONTENT
            elif token.type == IbcTokenType.NEWLINE:
                # 没有描述内容直接结束
                self._create_module_node()
                self.pop_flag = True
            else:
                raise IbcParserError(
                    message=f"ModuleDeclState: Expecting colon but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == ModuleDeclSubState.EXPECTING_CONTENT:
            # 解析直到换行
            if token.type == IbcTokenType.NEWLINE:
                self.content = self.content.strip()
                # 行末不应以冒号结束
                if self.content and self.content[-1] == ":":
                    raise IbcParserError(
                        message=f"ModuleDeclState: Cannot end with colon",
                        line_num=token.line_num
                    )
                self._create_module_node()
                self.pop_flag = True
            else:
                self.content += token.value
                self.sub_state = ModuleDeclSubState.EXPECTING_CONTENT

    def _create_module_node(self) -> None:
        """创建模块节点"""
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num 
        self.content = self.content.strip()
        module_node = ModuleNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.MODULE,
            line_number=line_num,
            identifier=self.module_name,
            content=self.content
        )
        
        self.ast_node_dict[uid] = module_node
        if self.parent_uid in self.ast_node_dict:
            self.ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


# 变量声明的子状态枚举
class VarDeclSubState(Enum):
    EXPECTING_VAR_NAME = "EXPECTING_VAR_NAME"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_VAR_DESC = "EXPECTING_VAR_DESC"

class VarDeclState(BaseState):
    """变量声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.VAR_DECL
        # TODO: 暂时删除了单行内多变量声明的支持，但List仍暂时保留，未来可能仍想办法引入单行多变量声明
        self.variables: Dict[str, str] = {}  # {name: description}
        self.current_var_name = ""
        self.current_var_desc = ""
        self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
        self.pop_flag = False

    def process_token(self, token: Token) -> None:
        self.current_token = token
        
        if self.sub_state == VarDeclSubState.EXPECTING_VAR_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_var_name = token.value.strip()
                self.sub_state = VarDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"VarDeclState: Expecting variable name but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == VarDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = VarDeclSubState.EXPECTING_VAR_DESC
            elif token.type == IbcTokenType.NEWLINE:
                # 无描述内容直接结束
                self.current_var_desc = ""
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc
                else:
                    raise IbcParserError(
                        message=f"VarDeclState: Got an duplicate var definitions",
                        line_num=token.line_num
                    )
                self.current_var_name = ""
                self.current_var_desc = ""
                self._create_variable_nodes()
                self.pop_flag = True
            else:
                raise IbcParserError(
                    message=f"VarDeclState: Expecting colon or new line but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == VarDeclSubState.EXPECTING_VAR_DESC:
            if token.type == IbcTokenType.NEWLINE:
                # 结束当前变量，创建节点并弹出
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc.strip()
                else:
                    raise IbcParserError(
                        message=f"VarDeclState: Got an duplicate var definitions",
                        line_num=token.line_num
                    )
                self.current_var_name = ""
                self.current_var_desc = ""
                self._create_variable_nodes()
                self.pop_flag = True
            else:
                # 收集其他描述内容
                self.current_var_desc += token.value

    def _create_variable_nodes(self) -> None:
        """为所有变量创建节点"""
        line_num = self.current_token.line_num if self.current_token else 0
        for var_name, var_desc in self.variables.items():
            uid = self.uid_generator.gen_uid()
            var_node = VariableNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.VARIABLE,
                line_number=line_num,
                identifier=var_name,
                content=var_desc
            )
            self.ast_node_dict[uid] = var_node
            if self.parent_uid in self.ast_node_dict:
                self.ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag



# 对外描述解析的子状态枚举
class DescriptionSubState(Enum):
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_CONTENT = "EXPECTING_CONTENT"
    EXPECTING_ONELINE = "EXPECTING_ONELINE"
    EXPECTING_MULTILINE_INDENT = "EXPECTING_MULTILINE_INDENT"
    EXPECTING_MULTILINE_CONTENT = "EXPECTING_MULTILINE_CONTENT"


class DescriptionState(BaseState):
    """描述状态类, 不产生节点, 产生解析内容"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.DESCRIPTION
        self.content = ""
        self.sub_state = DescriptionSubState.EXPECTING_COLON
        self.pop_flag = False
        self.pass_in_token_flag = False
        self.multiline_indent_level: Optional[int] = None  # 记录多行内容的缩进级别

    def process_token(self, token: Token) -> None:
        self.current_token = token

        if self.sub_state == DescriptionSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = DescriptionSubState.EXPECTING_CONTENT
            else:
                raise IbcParserError(
                    message=f"DescriptionState: Expecting colon but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == DescriptionSubState.EXPECTING_CONTENT:
            if token.type == IbcTokenType.NEWLINE:
                # 冒号后直接换行,准备进入多行模式
                self.pass_in_token_flag = True
                self.sub_state = DescriptionSubState.EXPECTING_MULTILINE_INDENT
            elif token.type == IbcTokenType.IDENTIFIER:
                # 单行模式:冒号后有内容
                self.pass_in_token_flag = False
                self.content += token.value
                self.sub_state = DescriptionSubState.EXPECTING_ONELINE
            else:
                raise IbcParserError(
                    message=f"DescriptionState: Expecting newline or identifier but got {token.type}",
                    line_num=token.line_num
                )

        elif self.sub_state == DescriptionSubState.EXPECTING_ONELINE:
            if token.type == IbcTokenType.NEWLINE:
                # 行末不应以冒号结束
                self.content = self.content.strip()
                if self.content and self.content[-1] == ":":
                    raise IbcParserError(
                        message=f"DescriptionState: Cannot end with colon",
                        line_num=token.line_num
                    )
                self.pop_flag = True
            else:
                self.content += token.value
                # 保持在EXPECTING_ONELINE状态
        
        elif self.sub_state == DescriptionSubState.EXPECTING_MULTILINE_INDENT:
            if token.type == IbcTokenType.INDENT:
                self.sub_state = DescriptionSubState.EXPECTING_MULTILINE_CONTENT
            else:
                raise IbcParserError(
                    message=f"DescriptionState: Expecting indent in multiline mode but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == DescriptionSubState.EXPECTING_MULTILINE_CONTENT:
            if token.type == IbcTokenType.DEDENT:
                # 退缩进表示多行描述结束
                self.content = self.content.strip()
                if self.content and self.content[-1] == ":":
                    raise IbcParserError(
                        message=f"DescriptionState: Cannot end with colon",
                        line_num=token.line_num
                    )
                if self.content and self.content[-1] == "\n":
                    self.content = self.content[:-1]
                self.pass_in_token_flag = False
                self.pop_flag = True
            elif token.type == IbcTokenType.INDENT:
                # 不允许进一步缩进
                raise IbcParserError(
                    message=f"DescriptionState: Further indentation is not allowed in multiline description",
                    line_num=token.line_num
                )
            elif token.type == IbcTokenType.NEWLINE:
                # 换行,添加到内容中
                self.content += "\n"
                # 保持在EXPECTING_MULTILINE_CONTENT状态
            else:
                # 收集内容
                self.content += token.value
                # 保持在EXPECTING_MULTILINE_CONTENT状态

    def is_need_pop(self) -> bool:
        return self.pop_flag

    def get_content(self) -> str:
        return self.content


# 意图注释解析的子状态枚举
class IntentCommentSubState(Enum):
    EXPECTING_CONTENT = "EXPECTING_CONTENT"

class IntentCommentState(BaseState):
    """描述状态类, 不产生节点, 产生解析内容"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.INTENT_COMMENT
        self.content = ""
        self.sub_state = IntentCommentSubState.EXPECTING_CONTENT
        self.pop_flag = False

    def process_token(self, token: Token) -> None:
        self.current_token = token

        if self.sub_state == IntentCommentSubState.EXPECTING_CONTENT:
            if token.type == IbcTokenType.NEWLINE:
                # 行末不应以冒号结束
                self.content = self.content.strip()
                if self.content and self.content[-1] == ":":
                    raise IbcParserError(
                        message=f"IntentCommentState: Cannot end with colon",
                        line_num=token.line_num
                    )
                self.pop_flag = True
            else:
                self.content += token.value
                # 保持在EXPECTING_CONTENT状态

    def is_need_pop(self) -> bool:
        return self.pop_flag

    def get_content(self) -> str:
        return self.content


# 类声明的子状态枚举
class ClassDeclSubState(Enum):
    EXPECTING_CLASS_NAME = "EXPECTING_CLASS_NAME"
    EXPECTING_LPAREN = "EXPECTING_LPAREN"

    EXPECTING_INH_CLASS = "EXPECTING_INH_CLASS"
    EXPECTING_INH_COLON = "EXPECTING_INH_COLON"
    EXPECTING_INH_DESC = "EXPECTING_INH_DESC"

    EXPECTING_RPAREN = "EXPECTING_RPAREN"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_NEWLINE = "EXPECTING_NEWLINE"


# 备注：目前逻辑中不允许多继承
class ClassDeclState(BaseState):
    """类声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.CLASS_DECL
        self.class_name = ""
        self.parent_class = ""
        self.inherit_desc = ""
        self.inh_params: Dict[str, str] = {}
        self.sub_state = ClassDeclSubState.EXPECTING_CLASS_NAME
        self.pop_flag = False

    def process_token(self, token: Token) -> None:
        self.current_token = token
        
        if self.sub_state == ClassDeclSubState.EXPECTING_CLASS_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.class_name = token.value.strip()
                self.sub_state = ClassDeclSubState.EXPECTING_LPAREN
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting class name but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_LPAREN:
            if token.type == IbcTokenType.LPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_INH_CLASS
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting left parenthesis or colon but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_CLASS:
            if token.type == IbcTokenType.IDENTIFIER:
                self.parent_class = token.value.strip()
                self.sub_state = ClassDeclSubState.EXPECTING_INH_COLON
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting Parent Name or right parenthesis but got {token.type}",
                    line_num=token.line_num
                )
            
        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_INH_DESC
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting COLON or right parenthesis but got {token.type}",
                    line_num=token.line_num
                )

        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_DESC:
            if token.type == IbcTokenType.IDENTIFIER:
                self.inherit_desc = token.value.strip()
                self.sub_state = ClassDeclSubState.EXPECTING_RPAREN
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting inherit description but got {token.type}",
                    line_num=token.line_num
                )

        elif self.sub_state == ClassDeclSubState.EXPECTING_RPAREN:
            if token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting right parenthesis but got {token.type}",
                    line_num=token.line_num
                )
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_NEWLINE
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting colon but got {token.type}",
                    line_num=token.line_num
                )
            
        elif self.sub_state == ClassDeclSubState.EXPECTING_NEWLINE:
            if token.type == IbcTokenType.NEWLINE:
            # 类声明结束，创建节点
                self._create_class_node()
                self.pop_flag = True
            else:
                raise IbcParserError(
                    message=f"ClassDeclState: Expecting new line but got {token.type}",
                    line_num=token.line_num
                )

    def _create_class_node(self) -> None:
        """创建类节点"""
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num if self.current_token else 0
        if self.parent_class:
            self.inh_params = {self.parent_class: self.inherit_desc}
        class_node = ClassNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.CLASS,
            line_number=line_num,
            identifier=self.class_name,
            inh_params=self.inh_params
        )
        
        self.ast_node_dict[uid] = class_node
        if self.parent_uid in self.ast_node_dict:
            self.ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


class ClassContentState(BaseState):
    """类内容状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.CLASS_CONTENT

    def process_token(self, token: Token) -> None:
        self.current_token = token


# 函数声明的子状态枚举
class FuncDeclSubState(Enum):
    EXPECTING_FUNC_NAME = "EXPECTING_FUNC_NAME"
    EXPECTING_LPAREN = "EXPECTING_LPAREN"

    EXPECTING_PARAM_NAME = "EXPECTING_PARAM_NAME"
    EXPECTING_PARAM_COLON = "EXPECTING_PARAM_COLON"
    EXPECTING_PARAM_DESC = "EXPECTING_PARAM_DESC"
    EXPECTING_PARAM_DESC_COMMA_CHECK = "EXPECTING_PARAM_DESC_COMMA_CHECK"  # 参数描述中遇到逗号，等待下一个token判断

    EXPECTING_RPAREN = "EXPECTING_RPAREN"   # 参数描述结束后等待右括号
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_NEWLIEN = "EXPECTING_NEWLIEN"


class FuncDeclState(BaseState):
    """函数声明状态类。支持多行函数参数书写"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.FUNC_DECL
        self.func_name = ""
        self.params: Dict[str, str] = {}
        self.param_type_refs: Dict[str, str] = {}  # 存储参数描述中的符号引用
        self.current_param_name = ""
        self.current_param_desc = ""
        self.current_param_type_ref = ""  # 当前参数的类型引用
        self.sub_state = FuncDeclSubState.EXPECTING_FUNC_NAME
        self.pop_flag = False
        self.pass_in_token_flag = False
        self.pending_indent_level = 0
        self.paren_count = 0  # 用于跟踪参数描述中的括号

    def process_token(self, token: Token) -> None:
        self.current_token = token
        
        if self.sub_state == FuncDeclSubState.EXPECTING_FUNC_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.func_name = token.value.strip()
                self.sub_state = FuncDeclSubState.EXPECTING_LPAREN
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting function name but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_LPAREN:
            if token.type == IbcTokenType.LPAREN:
                # 左括号后需要启用token透传以支持多行参数
                self.pass_in_token_flag = True
                self.pending_indent_level = 0
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            elif token.type == IbcTokenType.COLON:
                self.sub_state = FuncDeclSubState.EXPECTING_NEWLIEN
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting left parenthesis but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_param_name = token.value.strip()
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_COLON
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            elif token.type == IbcTokenType.NEWLINE:
                # 直接忽略换行token
                pass
            elif token.type == IbcTokenType.INDENT:
                self.pending_indent_level += 1
            elif token.type == IbcTokenType.DEDENT:
                self.pending_indent_level -= 1
                if self.pending_indent_level < 0:
                    raise IbcParserError(
                        message=f"FuncDeclState: Unexpected dedent structure",
                        line_num=token.line_num
                    )
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting param name or right parenthesis but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_DESC
            elif token.type == IbcTokenType.COMMA:
                # 没有参数描述，当前参数直接加入字典
                self.current_param_desc = ""
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                else:
                    raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            elif token.type == IbcTokenType.RPAREN:
                # 没有参数描述，当前参数直接加入字典，并且结束参数解析
                self.current_param_desc = ""
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                else:
                    raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting colon, comma or right parenthesis but got {token.type}",
                    line_num=token.line_num
                )

        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_DESC:
            # 参数描述是贪婪式解析：冒号后所有内容都是描述，直到遇到换行
            if token.type == IbcTokenType.REF_IDENTIFIER:
                # 处理符号引用
                if self.current_param_type_ref:
                    # 已经有一个符号引用，报错
                    raise IbcParserError(
                        message=f"FuncDeclState: Parameter description can only contain one symbol reference, but got multiple",
                        line_num=token.line_num
                    )
                self.current_param_type_ref = token.value.strip()
                # 将引用内容也加入描述中
                self.current_param_desc += token.value
            elif token.type == IbcTokenType.NEWLINE:
                # 参数描述结束，检查行末是否有逗号
                desc_stripped = self.current_param_desc.strip()
                if desc_stripped and desc_stripped[-1] == ",":
                    # 行末有逗号，移除逗号，保存参数，准备解析下一个参数
                    self.current_param_desc = desc_stripped[:-1].strip()
                    if self.current_param_name not in self.params:
                        self.params[self.current_param_name] = self.current_param_desc
                        if self.current_param_type_ref:
                            self.param_type_refs[self.current_param_name] = self.current_param_type_ref
                    else:
                        raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                    self.current_param_name = ""
                    self.current_param_desc = ""
                    self.current_param_type_ref = ""
                    self.paren_count = 0
                    self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
                else:
                    # 行末没有逗号，保存参数，准备等待右括号
                    self.current_param_desc = desc_stripped
                    if self.current_param_name not in self.params:
                        self.params[self.current_param_name] = self.current_param_desc
                        if self.current_param_type_ref:
                            self.param_type_refs[self.current_param_name] = self.current_param_type_ref
                    else:
                        raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                    self.current_param_name = ""
                    self.current_param_desc = ""
                    self.current_param_type_ref = ""
                    self.paren_count = 0
                    self.sub_state = FuncDeclSubState.EXPECTING_RPAREN
            elif token.type == IbcTokenType.LPAREN:
                # 记录左括号
                self.paren_count += 1
                self.current_param_desc += token.value
            elif token.type == IbcTokenType.RPAREN:
                # 检查是否是参数描述内的右括号
                if self.paren_count > 0:
                    # 这是参数描述内的右括号，作为普通文本处理
                    self.paren_count -= 1
                    self.current_param_desc += token.value
                else:
                    # paren_count为0，这是函数参数列表的结束括号
                    # 保存当前参数，准备解析函数体的冒号
                    desc_stripped = self.current_param_desc.strip()
                    self.current_param_desc = desc_stripped
                    if self.current_param_name not in self.params:
                        self.params[self.current_param_name] = self.current_param_desc
                        if self.current_param_type_ref:
                            self.param_type_refs[self.current_param_name] = self.current_param_type_ref
                    else:
                        raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                    self.current_param_name = ""
                    self.current_param_desc = ""
                    self.current_param_type_ref = ""
                    self.paren_count = 0
                    self.sub_state = FuncDeclSubState.EXPECTING_COLON
            elif token.type == IbcTokenType.COMMA:
                # 遇到逗号，需要判断下一个token是否为换行
                self.current_param_desc += token.value
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_DESC_COMMA_CHECK
            else:
                # 所有其他token都作为描述内容收集
                self.current_param_desc += token.value

        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_DESC_COMMA_CHECK:
            # 在参数描述中遇到逗号后，检查下一个token
            if token.type == IbcTokenType.NEWLINE:
                # 逗号后是换行，说明逗号是参数分隔符，移除描述末尾的逗号
                desc_stripped = self.current_param_desc.strip()
                if desc_stripped and desc_stripped[-1] == ",":
                    self.current_param_desc = desc_stripped[:-1].strip()
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                    if self.current_param_type_ref:
                        self.param_type_refs[self.current_param_name] = self.current_param_type_ref
                else:
                    raise IbcParserError(
                    message=f"FuncDeclState: Got an duplicate parameter definitions",
                    line_num=token.line_num
                )
                self.current_param_name = ""
                self.current_param_desc = ""
                self.current_param_type_ref = ""
                self.paren_count = 0
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            else:
                # 逗号后不是换行，说明逗号是描述内容的一部分，继续收集内容
                self.current_param_desc += token.value
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_DESC

        elif self.sub_state == FuncDeclSubState.EXPECTING_RPAREN:
            # 参数描述结束后等待右括号
            if token.type == IbcTokenType.RPAREN:
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            elif token.type == IbcTokenType.NEWLINE:
                # 允许在右括号前换行
                pass
            elif token.type == IbcTokenType.INDENT:
                self.pending_indent_level += 1
            elif token.type == IbcTokenType.DEDENT:
                self.pending_indent_level -= 1
                if self.pending_indent_level < 0:
                    raise IbcParserError(
                    message=f"FuncDeclState: Unexpected dedent structure",
                    line_num=token.line_num
                )
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting right parenthesis but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.pass_in_token_flag = False
                self.sub_state = FuncDeclSubState.EXPECTING_NEWLIEN
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting colon but got {token.type}",
                    line_num=token.line_num
                )
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_NEWLIEN:
            if token.type == IbcTokenType.NEWLINE:
                self._create_function_node()
                self.pop_flag = True
            else:
                raise IbcParserError(
                    message=f"FuncDeclState: Expecting new line but got {token.type}",
                    line_num=token.line_num
                )
    
    def _create_function_node(self) -> None:
        """创建函数节点"""
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num if self.current_token else 0
        func_node = FunctionNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.FUNCTION,
            line_number=line_num,
            identifier=self.func_name,
            params=self.params,
            param_type_refs=self.param_type_refs
        )
        
        self.ast_node_dict[uid] = func_node
        if self.parent_uid in self.ast_node_dict:
            self.ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag
    
    def get_pending_indent_level(self) -> int:
        return self.pending_indent_level


class FuncContentState(BaseState):
    """函数内容状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.FUNC_CONTENT

    def process_token(self, token: Token) -> None:
        self.current_token = token


# 行为步骤的子状态枚举
class BehaviorStepSubState(Enum):
    EXPECTING_CONTENT = "EXPECTING_CONTENT"  # 等待内容
    EXPECTING_COMMA_CONTINUATION = "EXPECTING_COMMA_CONTINUATION"  # 逗号延续行模式（收集内容，允许缩进）
    EXPECTING_BACKSLASH_CONTINUATION = "EXPECTING_BACKSLASH_CONTINUATION"  # 反斜杠延续行模式（收集内容，跟踪缩进）
    EXPECTING_PAREN_CONTINUATION = "EXPECTING_PAREN_CONTINUATION"  # 小括号延续行模式
    EXPECTING_BRACE_CONTINUATION = "EXPECTING_BRACE_CONTINUATION"  # 花括号延续行模式
    EXPECTING_BRACKET_CONTINUATION = "EXPECTING_BRACKET_CONTINUATION"  # 方括号延续行模式


class BehaviorStepState(BaseState):
    """行为步骤状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator, ast_node_dict: Dict[int, IbcBaseAstNode]):
        super().__init__(parent_uid, uid_generator, ast_node_dict)
        self.state_type = ParserState.BEHAVIOR_STEP
        self.content = ""
        self.symbol_refs: List[str] = []
        self.new_block_flag = False
        self.pop_flag = False
        self.pass_in_token_flag = False
        self.sub_state = BehaviorStepSubState.EXPECTING_CONTENT
        self.local_indent_level = 0  # 局部缩进等级，从延续行起始开始计算
        self.backslash_continuation_started = False  # 标记是否已经开始反斜杠延续
        self.has_entered_continuation = False  # 标记是否进入过延续行模式
        
        # 括号封闭计数器
        self.paren_count = 0  # ()
        self.brace_count = 0  # {}
        self.bracket_count = 0  # []

    def process_token(self, token: Token) -> None:
        self.current_token = token
        
        # 处理符号引用（在所有子状态下都适用）
        if token.type == IbcTokenType.REF_IDENTIFIER:
            self.symbol_refs.append(token.value.strip())
            self.content += token.value
            return
        
        # 根据子状态处理token
        if self.sub_state == BehaviorStepSubState.EXPECTING_CONTENT:
            self._process_content_state(token)
        elif self.sub_state == BehaviorStepSubState.EXPECTING_COMMA_CONTINUATION:
            self._process_comma_continuation_state(token)
        elif self.sub_state == BehaviorStepSubState.EXPECTING_BACKSLASH_CONTINUATION:
            self._process_backslash_continuation_state(token)
        elif self.sub_state == BehaviorStepSubState.EXPECTING_PAREN_CONTINUATION:
            self._process_paren_continuation_state(token)
        elif self.sub_state == BehaviorStepSubState.EXPECTING_BRACE_CONTINUATION:
            self._process_brace_continuation_state(token)
        elif self.sub_state == BehaviorStepSubState.EXPECTING_BRACKET_CONTINUATION:
            self._process_bracket_continuation_state(token)
    
    def _process_content_state(self, token: Token) -> None:
        """处理普通内容状态"""
        # 处理左括号，进入对应的括号延续行模式
        if token.type == IbcTokenType.LPAREN:
            self.content += token.value
            self.paren_count = 1  # 初始化计数器
            self.sub_state = BehaviorStepSubState.EXPECTING_PAREN_CONTINUATION
            self.pass_in_token_flag = True
            self.has_entered_continuation = True
        elif token.type == IbcTokenType.LBRACE:
            self.content += token.value
            self.brace_count = 1  # 初始化计数器
            self.sub_state = BehaviorStepSubState.EXPECTING_BRACE_CONTINUATION
            self.pass_in_token_flag = True
            self.has_entered_continuation = True
        elif token.type == IbcTokenType.LBRACKET:
            self.content += token.value
            self.bracket_count = 1  # 初始化计数器
            self.sub_state = BehaviorStepSubState.EXPECTING_BRACKET_CONTINUATION
            self.pass_in_token_flag = True
            self.has_entered_continuation = True
        elif token.type == IbcTokenType.NEWLINE:
            content_stripped = self.content.strip()
            
            # 检查行末字符
            if content_stripped and content_stripped[-1] == ":":
                # 行末是冒号，开启新代码块
                self.new_block_flag = True
                self.content = content_stripped
                self._create_behavior_node()
                self.pop_flag = True
            elif content_stripped and content_stripped[-1] == ",":
                # 行末是逗号，进入逗号延续行模式
                self.sub_state = BehaviorStepSubState.EXPECTING_COMMA_CONTINUATION
                self.pass_in_token_flag = True
                self.local_indent_level = 0
                self.content += " "  # 添加空格以便后续内容连接
                self.has_entered_continuation = True
            elif content_stripped and content_stripped[-1] == "\\":
                # 行末是反斜杠，进入反斜杠延续行模式
                self.content = content_stripped[:-1]  # 移除反斜杠
                self.sub_state = BehaviorStepSubState.EXPECTING_BACKSLASH_CONTINUATION
                self.pass_in_token_flag = True
                self.backslash_continuation_started = True
                self.has_entered_continuation = True
            else:
                # 普通行结束
                self.content = content_stripped
                self._create_behavior_node()
                self.pop_flag = True
        else:
            # 收集其他内容
            self.content += token.value
    
    def _process_comma_continuation_state(self, token: Token) -> None:
        """处理逗号延续行状态"""
        if token.type == IbcTokenType.INDENT:
            # 延续行中的缩进
            self.local_indent_level += 1
        elif token.type == IbcTokenType.DEDENT:
            # 延续行中的退缩进
            self.local_indent_level -= 1
            if self.local_indent_level < 0:
                raise IbcParserError(
                    message=f"BehaviorStepState: Unexpected dedent structure",
                    line_num=token.line_num
                )
        elif token.type == IbcTokenType.NEWLINE:
            content_stripped = self.content.strip()
            
            # 检查行末字符
            if content_stripped and content_stripped[-1] == ":":
                # 逗号延续行也允许以冒号结尾，设置new_block_flag并直接弹出
                self.new_block_flag = True
                self.content = content_stripped
                self._create_behavior_node()
                self.pass_in_token_flag = False
                self.pop_flag = True
            elif content_stripped and content_stripped[-1] == ",":
                # 行末是逗号，保持延续行模式
                self.content += " "  # 添加空格以便后续内容连接
            else:
                # 行末不是逗号也不是冒号，直接弹出
                self.content = content_stripped
                self._create_behavior_node()
                self.pass_in_token_flag = False
                self.pop_flag = True
        else:
            # 收集内容
            self.content += token.value
    
    def _process_backslash_continuation_state(self, token: Token) -> None:
        """处理反斜杠延续行状态
        
        反斜杠延续行也跟踪缩进等级
        """
        if token.type == IbcTokenType.INDENT:
            # 跟踪局部缩进
            self.local_indent_level += 1
        elif token.type == IbcTokenType.DEDENT:
            # 跟踪局部退缩进
            self.local_indent_level -= 1
            if self.local_indent_level < 0:
                raise IbcParserError(
                    message=f"BehaviorStepState: Unexpected dedent structure",
                    line_num=token.line_num
                )
        elif token.type == IbcTokenType.NEWLINE:
            content_stripped = self.content.strip()
            
            # 延续行的行末不允许出现冒号
            if content_stripped and content_stripped[-1] == ":":
                raise IbcParserError(
                    message=f"BehaviorStepState: Backslash continuation line cannot end with colon",
                    line_num=token.line_num
                )
            
            # 检查行末是否以反斜杠结束
            if content_stripped and content_stripped[-1] == "\\":
                # 行末是反斜杠，继续延续行模式，移除反斜杠
                self.content = content_stripped[:-1] + " "  # 移除反斜杠并添加空格
            else:
                # 行末不是反斜杠，反斜杠延续行结束
                self.content = content_stripped
                self._create_behavior_node()
                self.pass_in_token_flag = False
                self.pop_flag = True
        else:
            # 收集内容
            self.content += token.value
    
    def _process_paren_continuation_state(self, token: Token) -> None:
        """处理小括号延续行状态"""
        if token.type == IbcTokenType.INDENT:
            # 跟踪局部缩进
            self.local_indent_level += 1
        elif token.type == IbcTokenType.DEDENT:
            # 跟踪局部退缩进
            self.local_indent_level -= 1
            if self.local_indent_level < 0:
                raise IbcParserError(
                    message=f"BehaviorStepState: Unexpected dedent structure",
                    line_num=token.line_num
                )
        elif token.type == IbcTokenType.LPAREN:
            self.paren_count += 1
            self.content += token.value
        elif token.type == IbcTokenType.RPAREN:
            self.paren_count -= 1
            self.content += token.value
            # 检查括号是否封闭
            if self.paren_count == 0:
                # 括号封闭，退出括号延续行模式
                self.sub_state = BehaviorStepSubState.EXPECTING_CONTENT
                self.pass_in_token_flag = False
        elif token.type == IbcTokenType.NEWLINE:
            # 新行，添加空格
            self.content += " "
        else:
            # 收集其他内容
            self.content += token.value
    
    def _process_brace_continuation_state(self, token: Token) -> None:
        """处理花括号延续行状态"""
        if token.type == IbcTokenType.INDENT:
            # 跟踪局部缩进
            self.local_indent_level += 1
        elif token.type == IbcTokenType.DEDENT:
            # 跟踪局部退缩进
            self.local_indent_level -= 1
            if self.local_indent_level < 0:
                raise IbcParserError(
                    message=f"BehaviorStepState: Unexpected dedent structure",
                    line_num=token.line_num
                )
        elif token.type == IbcTokenType.LBRACE:
            self.brace_count += 1
            self.content += token.value
        elif token.type == IbcTokenType.RBRACE:
            self.brace_count -= 1
            self.content += token.value
            # 检查括号是否封闭
            if self.brace_count == 0:
                # 括号封闭，退出括号延续行模式
                self.sub_state = BehaviorStepSubState.EXPECTING_CONTENT
                self.pass_in_token_flag = False
        elif token.type == IbcTokenType.NEWLINE:
            # 新行，添加空格
            self.content += " "
        else:
            # 收集其他内容
            self.content += token.value
    
    def _process_bracket_continuation_state(self, token: Token) -> None:
        """处理方括号延续行状态"""
        if token.type == IbcTokenType.INDENT:
            # 跟踪局部缩进
            self.local_indent_level += 1
        elif token.type == IbcTokenType.DEDENT:
            # 跟踪局部退缩进
            self.local_indent_level -= 1
            if self.local_indent_level < 0:
                raise IbcParserError(
                    message=f"BehaviorStepState: Unexpected dedent structure",
                    line_num=token.line_num
                )
        elif token.type == IbcTokenType.LBRACKET:
            self.bracket_count += 1
            self.content += token.value
        elif token.type == IbcTokenType.RBRACKET:
            self.bracket_count -= 1
            self.content += token.value
            # 检查括号是否封闭
            if self.bracket_count == 0:
                # 括号封闭，退出括号延续行模式
                self.sub_state = BehaviorStepSubState.EXPECTING_CONTENT
                self.pass_in_token_flag = False
        elif token.type == IbcTokenType.NEWLINE:
            # 新行，添加空格
            self.content += " "
        else:
            # 收集其他内容
            self.content += token.value
    
    def _create_behavior_node(self) -> None:
        """创建行为步骤节点"""
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num if self.current_token else 0
        behavior_node = BehaviorStepNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.BEHAVIOR_STEP,
            line_number=line_num,
            content=self.content,
            symbol_refs=self.symbol_refs,
            new_block_flag=self.new_block_flag
        )
        
        self.ast_node_dict[uid] = behavior_node
        if self.parent_uid in self.ast_node_dict:
            self.ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag
    
    def has_entered_continuation_mode(self) -> bool:
        """返回当前状态机是否进入过延续行模式"""
        return self.has_entered_continuation
    
    def get_local_indent_level(self) -> int:
        """返回局部缩进等级"""
        return self.local_indent_level
