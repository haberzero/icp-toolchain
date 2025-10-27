from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator


class IbcParserStateError(Exception):
    """词法分析器异常"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"ParserError: {self.message}"


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
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        self.state_type = ParserState.BASE_STATE
        self.parent_uid = parent_uid
        self.uid_generator = uid_generator
        self.current_token: Optional[Token] = None

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        pass

    def is_need_pop(self) -> bool:
        return False


class TopLevelState(BaseState):
    """顶层状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.TOP_LEVEL

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token


# 模块声明的子状态枚举
class ModuleDeclSubState(Enum):
    EXPECTING_MODULE_NAME = "EXPECTING_MODULE_NAME"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_CONTENT = "EXPECTING_CONTENT"


class ModuleDeclState(BaseState):
    """模块声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.MODULE_DECL
        self.module_name = ""
        self.content = ""
        self.sub_state = ModuleDeclSubState.EXPECTING_MODULE_NAME
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if self.sub_state == ModuleDeclSubState.EXPECTING_MODULE_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.module_name = token.value
                self.sub_state = ModuleDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ModuleDeclState: Expecting module name but got {token.type}")
                
        elif self.sub_state == ModuleDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ModuleDeclSubState.EXPECTING_CONTENT
            elif token.type == IbcTokenType.NEWLINE:
                # 没有描述内容直接结束
                self._create_module_node(ast_node_dict)
                self.pop_flag = True
            else:
                raise IbcParserStateError(f"Line {token.line_num} ModuleDeclState: Expecting colon but got {token.type}")
                
        elif self.sub_state == ModuleDeclSubState.EXPECTING_CONTENT:
            # 解析直到换行
            if token.type == IbcTokenType.IDENTIFIER:
                self.content = token.value
                
            elif token.type == IbcTokenType.NEWLINE:
                # 确保行末不以冒号结束
                if self.content[-1] == ":":
                    raise IbcParserStateError(f"Line {token.line_num} ModuleDeclState: Cannot end with colon")
                self._create_module_node(ast_node_dict)
                self.pop_flag = True

        self.last_token = token

    def _create_module_node(self, ast_node_dict: Dict[int, AstNode]) -> None:
        """创建模块节点"""
        if not self.current_token:
            raise IbcParserStateError("ModuleDeclState: current_token is None, check your code")
        
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num 
        module_node = ModuleNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.MODULE,
            line_number=line_num,
            identifier=self.module_name,
            content=self.content
        )
        
        ast_node_dict[uid] = module_node
        if self.parent_uid in ast_node_dict:
            ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


# 变量声明的子状态枚举
class VarDeclSubState(Enum):
    EXPECTING_VAR_NAME = "EXPECTING_VAR_NAME"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_VAR_DESC = "EXPECTING_VAR_DESC"
    VAR_COMPLETE = "VAR_COMPLETE"


class VarDeclState(BaseState):
    """变量声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.VAR_DECL
        self.variables: List[Tuple[str, str]] = []  # [(name, description), ...]
        self.current_var_name = ""
        self.current_var_desc = ""
        self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if self.sub_state == VarDeclSubState.EXPECTING_VAR_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_var_name = token.value
                self.sub_state = VarDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Expecting variable name but got {token.type}")
                
        elif self.sub_state == VarDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = VarDeclSubState.EXPECTING_VAR_DESC
            elif token.type == IbcTokenType.COMMA:
                # 没有描述的变量，直接完成当前变量
                self.variables.append((self.current_var_name, ""))
                self.current_var_name = ""
                self.current_var_desc = ""
                # 继续期待下一个变量名
                self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
            elif token.type == IbcTokenType.NEWLINE:
                # 没有描述的变量，行结束
                self.variables.append((self.current_var_name, ""))
                self._create_variable_nodes(ast_node_dict)
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Expecting colon, comma or newline but got {token.type}")
                
        elif self.sub_state == VarDeclSubState.EXPECTING_VAR_DESC:
            if token.type == IbcTokenType.IDENTIFIER:
                if self.current_var_desc:
                    self.current_var_desc += " " + token.value
                else:
                    self.current_var_desc = token.value
            elif token.type == IbcTokenType.COMMA:
                # 完成当前变量，开始下一个
                self.variables.append((self.current_var_name, self.current_var_desc))
                self.current_var_name = ""
                self.current_var_desc = ""
                self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
            elif token.type == IbcTokenType.NEWLINE:
                # 完成最后一个变量
                self.variables.append((self.current_var_name, self.current_var_desc))
                self._create_variable_nodes(ast_node_dict)
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Unexpected token in variable description parsing")
                
    def _create_variable_nodes(self, ast_node_dict: Dict[int, AstNode]) -> None:
        """为所有变量创建节点"""
        line_num = self.current_token.line_num if self.current_token else 0
        for var_name, var_desc in self.variables:
            uid = self.uid_generator.gen_uid()
            var_node = VariableNode(
                uid=uid,
                parent_uid=self.parent_uid,
                node_type=AstNodeType.VARIABLE,
                line_number=line_num,
                identifier=var_name,
                content=var_desc
            )
            ast_node_dict[uid] = var_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


class DescriptionState(BaseState):
    """描述状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.DESCRIPTION
        self.content = ""
        self.expecting_colon = True
        self.expecting_content = False
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if token.type == IbcTokenType.COLON and self.expecting_colon:
            self.expecting_colon = False
            self.expecting_content = True
        elif token.type == IbcTokenType.IDENTIFIER and self.expecting_content:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value
        elif token.type == IbcTokenType.NEWLINE:
            # 描述结束，暂存内容
            pass  # 内容将在关联节点创建时使用

    def is_need_pop(self) -> bool:
        return self.pop_flag

    def get_content(self) -> str:
        return self.content


class IntentCommentState(BaseState):
    """意图注释状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.INTENT_COMMENT
        self.content = ""
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if token.type == IbcTokenType.IDENTIFIER:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value

    def is_need_pop(self) -> bool:
        return self.pop_flag

    def get_content(self) -> str:
        return self.content


# 类声明的子状态枚举
class ClassDeclSubState(Enum):
    EXPECTING_CLASS_NAME = "EXPECTING_CLASS_NAME"
    EXPECTING_LPAREN = "EXPECTING_LPAREN"
    PARSING_PARENT_CLASS = "PARSING_PARENT_CLASS"
    EXPECTING_RPAREN = "EXPECTING_RPAREN"
    EXPECTING_COLON = "EXPECTING_COLON"
    COMPLETE = "COMPLETE"


class ClassDeclState(BaseState):
    """类声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.CLASS_DECL
        self.class_name = ""
        self.parent_class = ""
        self.inheritance_desc = ""
        self.params: Dict[str, str] = {}
        self.sub_state = ClassDeclSubState.EXPECTING_CLASS_NAME
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if self.sub_state == ClassDeclSubState.EXPECTING_CLASS_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.class_name = token.value
                self.sub_state = ClassDeclSubState.EXPECTING_LPAREN
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting class name but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_LPAREN:
            if token.type == IbcTokenType.LPAREN:
                self.sub_state = ClassDeclSubState.PARSING_PARENT_CLASS
            elif token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting left parenthesis or colon but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.PARSING_PARENT_CLASS:
            if token.type == IbcTokenType.IDENTIFIER:
                if not self.parent_class:
                    self.parent_class = token.value
                else:
                    if self.inheritance_desc:
                        self.inheritance_desc += " " + token.value
                    else:
                        self.inheritance_desc = token.value
            elif token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_RPAREN
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Unexpected token in parent class parsing")
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_RPAREN:
            if token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting right parenthesis but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.COMPLETE
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting colon but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.COMPLETE:
            if token.type == IbcTokenType.NEWLINE:
                # 类声明结束，创建节点
                uid = self.uid_generator.gen_uid()
                line_num = self.current_token.line_num if self.current_token else 0
                class_node = ClassNode(
                    uid=uid,
                    parent_uid=self.parent_uid,
                    node_type=AstNodeType.CLASS,
                    line_number=line_num,
                    identifier=self.class_name,
                    params=self.params
                )
                
                ast_node_dict[uid] = class_node
                if self.parent_uid in ast_node_dict:
                    ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


class ClassContentState(BaseState):
    """类内容状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.CLASS_CONTENT

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token


# 函数声明的子状态枚举
class FuncDeclSubState(Enum):
    EXPECTING_FUNC_NAME = "EXPECTING_FUNC_NAME"
    EXPECTING_LPAREN = "EXPECTING_LPAREN"
    PARSING_PARAMS = "PARSING_PARAMS"
    EXPECTING_RPAREN = "EXPECTING_RPAREN"
    EXPECTING_COLON = "EXPECTING_COLON"
    COMPLETE = "COMPLETE"


# 参数解析的子状态枚举
class ParamSubState(Enum):
    EXPECTING_PARAM_NAME = "EXPECTING_PARAM_NAME"
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_PARAM_DESC = "EXPECTING_PARAM_DESC"
    PARAM_COMPLETE = "PARAM_COMPLETE"


class FuncDeclState(BaseState):
    """函数声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.FUNC_DECL
        self.func_name = ""
        self.params: Dict[str, str] = {}
        self.current_param_name = ""
        self.current_param_desc = ""
        self.sub_state = FuncDeclSubState.EXPECTING_FUNC_NAME
        self.param_sub_state = ParamSubState.EXPECTING_PARAM_NAME
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if self.sub_state == FuncDeclSubState.EXPECTING_FUNC_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.func_name = token.value
                self.sub_state = FuncDeclSubState.EXPECTING_LPAREN
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting function name but got {token.type}")
                
        elif self.sub_state == FuncDeclSubState.EXPECTING_LPAREN:
            if token.type == IbcTokenType.LPAREN:
                self.sub_state = FuncDeclSubState.PARSING_PARAMS
                self.param_sub_state = ParamSubState.EXPECTING_PARAM_NAME
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting left parenthesis but got {token.type}")
                
        elif self.sub_state == FuncDeclSubState.PARSING_PARAMS:
            if token.type == IbcTokenType.IDENTIFIER:
                if self.param_sub_state == ParamSubState.EXPECTING_PARAM_NAME:
                    self.current_param_name = token.value
                    self.param_sub_state = ParamSubState.EXPECTING_COLON
                elif self.param_sub_state == ParamSubState.EXPECTING_PARAM_DESC:
                    self.current_param_desc = token.value
                    self.param_sub_state = ParamSubState.PARAM_COMPLETE
                    
            elif token.type == IbcTokenType.COLON:
                if self.param_sub_state == ParamSubState.EXPECTING_COLON:
                    self.param_sub_state = ParamSubState.EXPECTING_PARAM_DESC
                else:
                    raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Unexpected colon in parameter parsing")
                    
            elif token.type == IbcTokenType.COMMA:
                # 完成当前参数，开始下一个
                if self.current_param_name:
                    self.params[self.current_param_name] = self.current_param_desc
                self.current_param_name = ""
                self.current_param_desc = ""
                self.param_sub_state = ParamSubState.EXPECTING_PARAM_NAME
                
            elif token.type == IbcTokenType.RPAREN:
                # 完成最后一个参数
                if self.current_param_name:
                    self.params[self.current_param_name] = self.current_param_desc
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Unexpected token in parameter parsing")
                
        elif self.sub_state == FuncDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = FuncDeclSubState.COMPLETE
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting colon but got {token.type}")
                
        elif self.sub_state == FuncDeclSubState.COMPLETE:
            if token.type == IbcTokenType.NEWLINE:
                # 函数声明结束，创建节点
                uid = self.uid_generator.gen_uid()
                line_num = self.current_token.line_num if self.current_token else 0
                func_node = FunctionNode(
                    uid=uid,
                    parent_uid=self.parent_uid,
                    node_type=AstNodeType.FUNCTION,
                    line_number=line_num,
                    identifier=self.func_name,
                    params=self.params
                )
                
                ast_node_dict[uid] = func_node
                if self.parent_uid in ast_node_dict:
                    ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


class FuncContentState(BaseState):
    """函数内容状态类, 目前实际上不会被调用。token的处理逻辑主要集中在各自的状态机逻辑中 """
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.FUNC_CONTENT

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token


class BehaviorStepState(BaseState):
    """行为步骤状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.BEHAVIOR_STEP
        self.content = ""
        self.symbol_refs: List[str] = []
        self.new_block_flag = False
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token
        
        if token.type == IbcTokenType.REF_IDENTIFIER:
            self.symbol_refs.append(token.value)
        elif token.type == IbcTokenType.IDENTIFIER:
            if self.content:
                self.content += " " + token.value
            else:
                self.content = token.value
        elif token.type == IbcTokenType.COLON:
            self.content += ":"
        elif token.type == IbcTokenType.COMMA:
            self.content += ","
        elif token.type == IbcTokenType.LPAREN:
            self.content += "("
        elif token.type == IbcTokenType.RPAREN:
            self.content += ")"
        elif token.type == IbcTokenType.NEWLINE:
            # 行为步骤结束，创建节点
            # 如果出现行末冒号，则认为需要开启新代码块
            self.new_block_flag = (self.current_token is not None and 
                                    self.current_token.type == IbcTokenType.COLON)

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
            
            ast_node_dict[uid] = behavior_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag