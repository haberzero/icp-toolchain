from enum import Enum
from typing import List, Dict, Optional
from typedef.ibc_data_types import (
    IbcTokenType, Token, AstNode, AstNodeType, 
    ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode
)

from utils.ibc_analyzer.ibc_parser_uid_generator import IbcParserUidGenerator


class IbcParserStateError(Exception):
    """解析器状态机异常"""
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
            if token.type == IbcTokenType.NEWLINE:
                self.content = self.content.strip()
                # 行末不应以冒号结束
                if ":" == self.content[-1]:
                    raise IbcParserStateError(f"Line {token.line_num} ModuleDeclState: Cannot end with colon")
                self._create_module_node(ast_node_dict)
                self.pop_flag = True
            else:
                self.content += token.value
                self.sub_state = ModuleDeclSubState.EXPECTING_CONTENT

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
    EXPECTING_COMMA = "EXPECTING_COMMA"


class VarDeclState(BaseState):
    """变量声明状态类"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.VAR_DECL
        self.variables: Dict[str, str] = {}  # {name: description, ... }
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
                self.current_var_desc = ""
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Got an duplicate var definitions")
                self.current_var_name = ""
                self.current_var_desc = ""
                # 获取下一个变量名
                self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
            elif token.type == IbcTokenType.NEWLINE:
                # 没有描述的变量，行结束
                self.current_var_desc = ""
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Got an duplicate var definitions")
                self.current_var_name = ""
                self.current_var_desc = ""
                self._create_variable_nodes(ast_node_dict)
                self.pop_flag = True
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Expecting colon, comma or newline but got {token.type}")
         
        elif self.sub_state == VarDeclSubState.EXPECTING_VAR_DESC:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_var_desc = token.value.strip()
                self.sub_state = VarDeclSubState.EXPECTING_COMMA
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Expecting var description but got {token.type}")
        
        elif self.sub_state == VarDeclSubState.EXPECTING_COMMA:
            if token.type == IbcTokenType.COMMA:
                # 完成当前变量，开始下一个
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Got an duplicate var definitions")
                self.current_var_name = ""
                self.current_var_desc = ""
                self.sub_state = VarDeclSubState.EXPECTING_VAR_NAME
            elif token.type == IbcTokenType.NEWLINE:
                # 完成最后一个变量，行结束
                if self.current_var_name not in self.variables:
                    self.variables[self.current_var_name] = self.current_var_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Got an duplicate var definitions")
                self.current_var_name = ""
                self.current_var_desc = ""
                self._create_variable_nodes(ast_node_dict)
                self.pop_flag = True
            else:
                raise IbcParserStateError(f"Line {token.line_num} VarDeclState: Expecting comma or new line but got {token.type}")
    
    def _create_variable_nodes(self, ast_node_dict: Dict[int, AstNode]) -> None:
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
            ast_node_dict[uid] = var_node
            if self.parent_uid in ast_node_dict:
                ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag


# 对外描述解析的子状态枚举
class DescriptionSubState(Enum):
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_CONTENT = "EXPECTING_CONTENT"


# TODO: 未来也许应引入多行描述解析。当前逻辑只允许单行对外描述
    # 意味着现在的缩进解析需要改，缩进解析需要纳入状态机的体系中
class DescriptionState(BaseState):
    """描述状态类, 不产生节点, 产生解析内容"""
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.DESCRIPTION
        self.content = ""
        self.sub_state = DescriptionSubState.EXPECTING_COLON
        self.pop_flag = False

    def process_token(self, token: Token, ast_node_dict: Dict[int, AstNode]) -> None:
        self.current_token = token

        if self.sub_state == DescriptionSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = DescriptionSubState.EXPECTING_CONTENT
            else:
                raise IbcParserStateError(f"Line {token.line_num} DescriptionState: Expecting colon but got {token.type}")
        
        elif self.sub_state == DescriptionSubState.EXPECTING_CONTENT:
            if token.type == IbcTokenType.NEWLINE:
                # 行末不应以冒号结束
                self.content = self.content.strip()
                if ":" == self.content[-1]:
                    raise IbcParserStateError(f"Line {token.line_num} DescriptionState: Cannot end with colon")
                self.pop_flag = True
            else:
                self.content += token.value
                self.sub_state = DescriptionSubState.EXPECTING_CONTENT

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
    def __init__(self, parent_uid: int, uid_generator: IbcParserUidGenerator):
        super().__init__(parent_uid, uid_generator)
        self.state_type = ParserState.CLASS_DECL
        self.class_name = ""
        self.parent_class = ""
        self.inherit_desc = ""
        self.inh_params: Dict[str, str] = {}
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
                self.sub_state = ClassDeclSubState.EXPECTING_INH_CLASS
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting left parenthesis or colon but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_CLASS:
            if token.type == IbcTokenType.IDENTIFIER:
                self.parent_class = token.value
                self.sub_state = ClassDeclSubState.EXPECTING_INH_COLON
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting Parent Name or right parenthesis but got {token.type}")
            
        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_INH_DESC
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting COLON or right parenthesis but got {token.type}")

        elif self.sub_state == ClassDeclSubState.EXPECTING_INH_DESC:
            if token.type == IbcTokenType.IDENTIFIER:
                self.inherit_desc = token.value.strip()
                self.sub_state = ClassDeclSubState.EXPECTING_RPAREN
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting inherit description but got {token.type}")

        elif self.sub_state == ClassDeclSubState.EXPECTING_RPAREN:
            if token.type == IbcTokenType.RPAREN:
                self.sub_state = ClassDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting right parenthesis but got {token.type}")
                
        elif self.sub_state == ClassDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = ClassDeclSubState.EXPECTING_NEWLINE
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting colon but got {token.type}")
            
        elif self.sub_state == ClassDeclSubState.EXPECTING_NEWLINE:
            if token.type == IbcTokenType.NEWLINE:
            # 类声明结束，创建节点
                self._create_class_node(ast_node_dict)
                self.pop_flag = True
            else:
                raise IbcParserStateError(f"Line {token.line_num} ClassDeclState: Expecting new line but got {token.type}")

    def _create_class_node(self, ast_node_dict: Dict[int, AstNode]) -> None:
        """创建类节点"""
        uid = self.uid_generator.gen_uid()
        line_num = self.current_token.line_num if self.current_token else 0
        self.inh_params = {self.parent_class: self.inherit_desc}
        class_node = ClassNode(
            uid=uid,
            parent_uid=self.parent_uid,
            node_type=AstNodeType.CLASS,
            line_number=line_num,
            identifier=self.class_name,
            inh_params=self.inh_params
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

    EXPECTING_PARAM_NAME = "EXPECTING_PARAM_NAME"
    EXPECTING_PARAM_COLON = "EXPECTING_PARAM_COLON"
    EXPECTING_PARAM_DESC = "EXPECTING_PARAM_DESC"
    EXPECTING_PARAM_COMMA = "EXPECTING_PARAM_COMMA"

    EXPECTING_RPAREN = "EXPECTING_RPAREN"   # 此状态事实上不会被使用，在参数列表解析时，右括号会被覆盖
    EXPECTING_COLON = "EXPECTING_COLON"
    EXPECTING_NEWLIEN = "EXPECTING_NEWLIEN"


# TODO: 目前逻辑只支持同一行内的函数参数书写，后续应当支持多行参数书写
    # 意味着现在的缩进解析需要改，缩进解析需要纳入状态机的体系中
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
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting left parenthesis but got {token.type}")
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_NAME:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_param_name = token.value
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_COLON
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting param name or right parenthesis but got {token.type}")
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_DESC
            elif token.type == IbcTokenType.COMMA:
                # 没有参数描述，当前参数直接加入字典
                self.current_param_desc = ""
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Got an duplicate parameter definitions")
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            elif token.type == IbcTokenType.RPAREN:
                # 没有参数描述，当前参数直接加入字典，并且结束参数解析
                self.current_param_desc = ""
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Got an duplicate parameter definitions")
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting colon, comma or right parenthesis but got {token.type}")


        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_DESC:
            if token.type == IbcTokenType.IDENTIFIER:
                self.current_param_desc = token.value.strip()
                if self.current_param_name not in self.params:
                    self.params[self.current_param_name] = self.current_param_desc
                else:
                    raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Got an duplicate parameter definitions")
                self.current_param_name = ""
                self.current_param_desc = ""
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_COMMA
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting param description but got {token.type}")

        elif self.sub_state == FuncDeclSubState.EXPECTING_PARAM_COMMA:
            if token.type == IbcTokenType.COMMA:
                self.sub_state = FuncDeclSubState.EXPECTING_PARAM_NAME
            elif token.type == IbcTokenType.RPAREN:
                self.sub_state = FuncDeclSubState.EXPECTING_COLON
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting comma or right parenthesis but got {token.type}")

        elif self.sub_state == FuncDeclSubState.EXPECTING_COLON:
            if token.type == IbcTokenType.COLON:
                self.sub_state = FuncDeclSubState.EXPECTING_NEWLIEN
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting colon but got {token.type}")
        
        elif self.sub_state == FuncDeclSubState.EXPECTING_NEWLIEN:
            if token.type == IbcTokenType.NEWLINE:
                self._create_function_node(ast_node_dict)
                self.pop_flag = True
            else:
                raise IbcParserStateError(f"Line {token.line_num} FuncDeclState: Expecting new line but got {token.type}")
    
    def _create_function_node(self, ast_node_dict: Dict[int, AstNode]) -> None:
        """创建函数节点"""
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
            self.content += token.value
        elif token.type == IbcTokenType.NEWLINE:
            # 行为步骤结束，创建节点。行末冒号标志着开启新缩进代码块
            self.content = self.content.strip()
            if ":" == self.content[-1]:
                self.new_block_flag = True
            self._create_behavior_node(ast_node_dict)
            self.pop_flag = True
        else:
            self.content += token.value

    def _create_behavior_node(self, ast_node_dict: Dict[int, AstNode]) -> None:
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
        
        ast_node_dict[uid] = behavior_node
        if self.parent_uid in ast_node_dict:
            ast_node_dict[self.parent_uid].add_child(uid)

    def is_need_pop(self) -> bool:
        return self.pop_flag
