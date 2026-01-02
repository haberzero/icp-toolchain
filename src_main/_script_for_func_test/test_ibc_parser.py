import json
import os
import sys

# 正确添加src_main目录到sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typedef.ibc_data_types import (AstNodeType, BehaviorStepNode, ClassNode,
                                    FunctionNode, ModuleNode, VariableNode,
                                    VisibilityTypes)
from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser


def print_ast_tree(ast_nodes: dict, uid: int = 0, indent: int = 0) -> None:
    """递归打印AST树结构"""
    if uid not in ast_nodes:
        return
    
    node = ast_nodes[uid]
    prefix = "  " * indent
    
    if isinstance(node, ModuleNode):
        print(f"{prefix}Module: {node.identifier} (uid={node.uid})")
        if node.content:
            print(f"{prefix}  - 描述: {node.content}")
    elif isinstance(node, ClassNode):
        print(f"{prefix}Class: {node.identifier} (uid={node.uid})")
        if node.external_desc:
            print(f"{prefix}  - 对外描述: {node.external_desc}")
        if node.intent_comment:
            print(f"{prefix}  - 意图注释: {node.intent_comment}")
        if node.inh_params:
            for parent, desc in node.inh_params.items():
                if parent:
                    print(f"{prefix}  - 继承: {parent}" + (f" ({desc})" if desc else ""))
    elif isinstance(node, FunctionNode):
        print(f"{prefix}Func: {node.identifier} (uid={node.uid})")
        if node.external_desc:
            print(f"{prefix}  - 对外描述: {node.external_desc}")
        if node.intent_comment:
            print(f"{prefix}  - 意图注释: {node.intent_comment}")
        if node.params:
            print(f"{prefix}  - 参数:")
            for param_name, param_desc in node.params.items():
                print(f"{prefix}    * {param_name}" + (f": {param_desc}" if param_desc else ""))
    elif isinstance(node, VariableNode):
        print(f"{prefix}Var: {node.identifier} (uid={node.uid})")
        if node.content:
            print(f"{prefix}  - 描述: {node.content}")
        if node.type_ref:
            print(f"{prefix}  - 类型引用: {', '.join(node.type_ref)}")
    elif isinstance(node, BehaviorStepNode):
        print(f"{prefix}Behavior: {node.content[:50]}... (uid={node.uid})")
        if node.symbol_refs:
            print(f"{prefix}  - 符号引用: {', '.join(node.symbol_refs)}")
        if node.new_block_flag:
            print(f"{prefix}  - 新代码块标志: True")
    else:
        print(f"{prefix}Node (uid={node.uid}, type={node.node_type})")
    
    # 递归打印子节点
    for child_uid in node.children_uids:
        print_ast_tree(ast_nodes, child_uid, indent + 1)


def test_module_declaration():
    """测试模块声明，包括带路径分隔符的模块"""
    print("测试 module_declaration 函数...")
    
    code = """module utils.logger: 日志工具模块
module config.settings: 配置管理模块
module database.connection.pool: 数据库连接池
module threading: Python系统线程库
module requests"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 验证根节点的子节点数量
        root_node = ast_nodes[0]
        
        # 统计模块节点
        modules = []
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, ModuleNode):
                modules.append(node)
        
        assert len(modules) == 5, f"预期5个模块，实际{len(modules)}"
        
        # 验证第一个模块（带路径分隔符）
        assert modules[0].identifier == "utils.logger", f"预期标识符为'utils.logger'，实际为'{modules[0].identifier}'"
        assert modules[0].content == "日志工具模块", f"预期内容不匹配"
        
        # 验证第二个模块（带路径分隔符）
        assert modules[1].identifier == "config.settings", f"预期标识符为'config.settings'"
        assert modules[1].content == "配置管理模块", f"预期内容不匹配"
        
        # 验证第三个模块（多层级路径分隔符）
        assert modules[2].identifier == "database.connection.pool", f"预期标识符为'database.connection.pool'"
        assert modules[2].content == "数据库连接池", f"预期内容不匹配"
        
        # 验证第四个模块（不带路径分隔符）
        assert modules[3].identifier == "threading", f"预期标识符为'threading'"
        assert modules[3].content == "Python系统线程库", f"预期内容不匹配"
        
        # 验证第五个模块（无描述）
        assert modules[4].identifier == "requests", f"预期标识符为'requests'"
        assert modules[4].content == "", f"预期内容为空"
        
        print("  ✓ 成功解析模块声明（包括带路径分隔符的模块）")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variable_declaration():
    """测试变量声明"""
    print("\n测试 variable_declaration 函数...")
    
    code = """var userCount: 当前在线用户数量
var config, cache"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 验证变量节点
        var_dict = {}  # {name: description}
        for uid in root_node.children_uids:
            var_node = ast_nodes[uid]
            if isinstance(var_node, VariableNode):
                var_dict[var_node.identifier] = var_node.content
        
        assert "userCount" in var_dict, "缺少userCount变量"
        assert "config" in var_dict, "缺少config变量"
        assert "cache" in var_dict, "缺少cache变量"
        
        # 验证描述
        assert var_dict["userCount"] == "当前在线用户数量", f"userCount的描述不匹配: {var_dict['userCount']}"
        assert var_dict["config"] == "", f"config应该没有描述: {var_dict['config']}"
        assert var_dict["cache"] == "", f"cache应该没有描述: {var_dict['cache']}"
        
        print("  ✓ 成功解析变量声明")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_function_declaration():
    """测试函数声明（更新为符合新语法：多行参数）"""
    print("\n测试 function_declaration 函数...")
    
    code = """\
func 计算订单总价(
    商品列表: 包含价格信息的商品对象数组,
    折扣率: 0到1之间的小数
):
    初始化 总价 = 0
    遍历 商品列表 中的每个 商品:
        总价 = 总价 + 商品.价格"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        func_node = ast_nodes[root_node.children_uids[0]]
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        assert func_node.identifier == "计算订单总价", f"函数名不匹配"
        assert len(func_node.params) == 2, f"预期2个参数"
        assert "商品列表" in func_node.params, "缺少商品列表参数"
        assert "折扣率" in func_node.params, "缺少折扣率参数"
        
        # 验证函数体有行为步骤
        assert len(func_node.children_uids) > 0, "函数应该有子节点"
        
        print("  ✓ 成功解析函数声明")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_declaration():
    """测试类声明"""
    print("\n测试 class_declaration 函数...")
    
    code = """class UserManager(BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典
    
    func 添加用户(用户名, 密码):
        验证 用户名 和 密码 格式
        创建新用户对象"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        class_node = ast_nodes[root_node.children_uids[0]]
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.identifier == "UserManager", f"类名不匹配"
        assert "BaseManager" in class_node.inh_params, "缺少继承信息"
        
        # 验证类成员
        assert len(class_node.children_uids) >= 2, "类应该有成员变量和方法"
        
        print("  ✓ 成功解析类声明")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_description_and_intent():
    """测试description和意图注释"""
    print("\n测试 description_and_intent 函数...")
    
    code = """description: 处理用户登录请求，验证凭据并返回认证结果
@ 线程安全设计，所有公共方法都内置锁机制
class AuthService():
    @ 使用bcrypt进行密码哈希
    func 哈希密码(明文密码):
        实现密码哈希逻辑
        返回 哈希结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.external_desc == "处理用户登录请求，验证凭据并返回认证结果", "类的对外描述不匹配"
        assert class_node.intent_comment == "线程安全设计，所有公共方法都内置锁机制", "类的意图注释不匹配"
        
        # 验证函数的意图注释
        func_node = ast_nodes[class_node.children_uids[0]]
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        assert func_node.intent_comment == "使用bcrypt进行密码哈希", "函数的意图注释不匹配"
        
        print("  ✓ 成功解析description和意图注释")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbol_reference():
    """测试符号引用（新语法：单$起始）"""
    print("\n测试 symbol_reference 函数...")
    
    code = """func 发送请求(请求数据):
    var maxRetries: 最大重试次数
    当 重试计数 < $maxRetries:
        尝试发送 $httpClient.post(请求数据)"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 查找包含符号引用的行为步骤
        found_ref = False
        for uid in func_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, BehaviorStepNode) and node.symbol_refs:
                found_ref = True
                assert "maxRetries" in node.symbol_refs or "httpClient.post" in node.symbol_refs, \
                    f"符号引用不正确: {node.symbol_refs}"
        
        assert found_ref, "未找到符号引用"
        
        print("  ✓ 成功解析符号引用")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_example():
    """测试复杂示例"""
    print("\n测试 complex_example 函数...")
    
    code = """module json: 标准JSON解析库
module threading: 线程支持库

description: 线程安全的配置管理器，支持多数据源和热重载
@ 所有公共方法都保证线程安全，使用读写锁优化性能
class ConfigManager():
    var configData: 当前配置数据
    var configPath: 主配置文件路径
    var rwLock: 读写锁对象
    
    description: 初始化配置管理器
    func __init__(配置文件路径: 字符串路径，支持相对和绝对路径):
        self.configPath = 配置文件路径
        self.rwLock = 创建读写锁()
        self.加载配置()
    
    description: 从文件加载配置数据
    @ 使用JSON格式解析，自动处理编码问题
    func 加载配置():
        获取 self.rwLock 的写锁
        尝试:
            文件内容 = 读取文件(self.configPath)
            self.configData = $json.parse(文件内容)
        捕获 异常:
            记录错误信息
        最后:
            释放 self.rwLock 的写锁"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 验证有模块和类节点
        module_count = 0
        class_count = 0
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, ModuleNode):
                module_count += 1
            elif isinstance(node, ClassNode):
                class_count += 1
        
        assert module_count == 2, f"预期2个模块，实际{module_count}"
        assert class_count == 1, f"预期1个类，实际{class_count}"
        
        print("  ✓ 成功解析复杂示例")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_blocks():
    """测试嵌套代码块"""
    print("\n测试 nested_blocks 函数...")
    
    code = """func 处理数据(数据列表):
    遍历 数据列表:
        如果 数据有效:
            处理数据
            保存结果
        否则:
            记录错误"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有子节点
        assert len(func_node.children_uids) > 0, "函数应该有行为步骤"
        
        # 查找带new_block_flag的行为步骤
        found_nested = False
        for uid in func_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, BehaviorStepNode) and node.new_block_flag:
                found_nested = True
                # 验证这个步骤有子节点
                if len(node.children_uids) > 0:
                    print(f"    找到嵌套块: {node.content}")
        
        print("  ✓ 成功解析嵌套代码块")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiline_description():
    """测试多行description"""
    print("\n测试 multiline_description 函数...")
    
    code = """description:
    这是一个复杂的配置管理系统，具备的功能有
    从多个数据源读取配置信息，合并冲突设置，还提供热重载功能
class ConfigManager():
    var config

description: 单行描述测试
func 简单函数():
    执行操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 验证第一个类节点
        class_node = ast_nodes[root_node.children_uids[0]]
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        
        # 验证多行description被正确解析
        expected_desc = "这是一个复杂的配置管理系统，具备的功能有从多个数据源读取配置信息，合并冲突设置，还提供热重载功能"
        # 去除空格进行比较,因为多行可能有格式差异
        assert class_node.external_desc.replace("\n", "") == expected_desc, \
            f"多行description解析不正确: '{class_node.external_desc}'"
        
        # 验证第二个函数节点的单行description
        func_node = ast_nodes[root_node.children_uids[1]]
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        assert func_node.external_desc == "单行描述测试", \
            f"单行description解析不正确: '{func_node.external_desc}'"
        
        print("  ✓ 成功解析多行和单行description")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiline_func_declaration():
    """测试多行函数声明"""
    print("\n测试 multiline_func_declaration 函数...")
    
    code = """func 计算订单总价(
    商品列表: 包含价格信息的商品对象数组,
    折扣率: 0到1之间的小数表示折扣比例,
    优惠券: 可选的优惠券对象
):
    初始化 总价 = 0
    遍历 商品列表 中的每个 商品:
        总价 = 总价 + 商品.价格
    总价 = 总价 × 折扣率
    返回 总价

func 简单函数(参数1, 参数2):
    执行操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 验证第一个多行函数声明
        func_node1 = ast_nodes[root_node.children_uids[0]]
        assert isinstance(func_node1, FunctionNode), "预期为FunctionNode"
        assert func_node1.identifier == "计算订单总价", f"函数名不匹配: {func_node1.identifier}"
        
        # 验证参数数量
        assert len(func_node1.params) == 3, f"预期3个参数，实际{len(func_node1.params)}"
        
        # 验证参数名称和描述
        assert "商品列表" in func_node1.params, "缺少商品列表参数"
        assert "折扣率" in func_node1.params, "缺少折扣率参数"
        assert "优惠券" in func_node1.params, "缺少优惠券参数"
        
        assert func_node1.params["商品列表"] == "包含价格信息的商品对象数组", \
            f"商品列表参数描述不匹配: {func_node1.params['商品列表']}"
        assert func_node1.params["折扣率"] == "0到1之间的小数表示折扣比例", \
            f"折扣率参数描述不匹配: {func_node1.params['折扣率']}"
        assert func_node1.params["优惠券"] == "可选的优惠券对象", \
            f"优惠券参数描述不匹配: {func_node1.params['优惠券']}"
        
        # 验证函数有子节点(行为步骤)
        assert len(func_node1.children_uids) > 0, "函数应该有行为步骤"
        
        # 验证第二个单行函数声明
        func_node2 = ast_nodes[root_node.children_uids[1]]
        assert isinstance(func_node2, FunctionNode), "预期为FunctionNode"
        assert func_node2.identifier == "简单函数", f"函数名不匹配: {func_node2.identifier}"
        assert len(func_node2.params) == 2, f"预期2个参数，实际{len(func_node2.params)}"
        
        print("  ✓ 成功解析多行和单行函数声明")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiline_func_in_class():
    """测试类中的多行函数声明"""
    print("\n测试 multiline_func_in_class 函数...")
    
    code = """class ApiClient():
    var baseUrl: API基础地址
    
    description: 发送GET请求到指定接口
    @ 自动处理网络异常，最多重试3次
    func 获取数据(
        接口路径: 相对路径，不需要包含基础URL,
        查询参数: 字典形式的查询参数
    ):
        完整URL = self.baseUrl + 接口路径
        重试计数 = 0
        返回 响应数据"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.identifier == "ApiClient", f"类名不匹配: {class_node.identifier}"
        
        # 找到函数节点(跳过变量节点)
        func_node = None
        for uid in class_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, FunctionNode):
                func_node = node
                break
        
        assert func_node is not None, "未找到函数节点"
        assert func_node.identifier == "获取数据", f"函数名不匹配: {func_node.identifier}"
        
        # 验证description和intent注释
        assert func_node.external_desc == "发送GET请求到指定接口", \
            f"函数描述不匹配: {func_node.external_desc}"
        assert func_node.intent_comment == "自动处理网络异常，最多重试3次", \
            f"意图注释不匹配: {func_node.intent_comment}"
        
        # 验证多行参数
        assert len(func_node.params) == 2, f"预期2个参数，实际{len(func_node.params)}"
        assert "接口路径" in func_node.params, "缺少接口路径参数"
        assert "查询参数" in func_node.params, "缺少查询参数参数"
        
        # 验证函数有行为步骤
        assert len(func_node.children_uids) > 0, "函数应该有行为步骤"
        
        print("  ✓ 成功解析类中的多行函数声明")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_continuation_line_basic():
    """测试基本的延续行功能"""
    print("\n测试 continuation_line_basic 函数...")
    
    code = """func 处理数据(数据列表):
    初始化 总数 = 0,
        有效数 = 0,
        无效数 = 0
    遍历 数据列表 中的每个 元素"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        assert func_node.identifier == "处理数据", f"函数名不匹配: {func_node.identifier}"
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含延续行内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有三行的内容
        assert "初始化" in behavior1.content, f"缺少'初始化': {behavior1.content}"
        assert "总数" in behavior1.content, f"缺少'总数': {behavior1.content}"
        assert "有效数" in behavior1.content, f"缺少'有效数': {behavior1.content}"
        assert "无效数" in behavior1.content, f"缺少'无效数': {behavior1.content}"
        
        # 验证第二个行为步骤是普通行
        behavior2 = ast_nodes[func_node.children_uids[1]]
        assert isinstance(behavior2, BehaviorStepNode), "预期为BehaviorStepNode"
        assert "遍历" in behavior2.content, f"缺少'遍历': {behavior2.content}"
        
        print("  ✓ 成功解析基本延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_continuation_line_with_indent():
    """测试带缩进的延续行"""
    print("\n测试 continuation_line_with_indent 函数...")
    
    code = """func 构建查询语句():
    设置 SQL 语句 = SELECT 字段1,
            字段2,
            字段3,
            字段4 FROM 表名
    返回 SQL 语句"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含延续行内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有字段
        assert "SELECT" in behavior1.content, f"缺少'SELECT': {behavior1.content}"
        assert "字段1" in behavior1.content, f"缺少'字段1': {behavior1.content}"
        assert "字段2" in behavior1.content, f"缺少'字段2': {behavior1.content}"
        assert "字段3" in behavior1.content, f"缺少'字段3': {behavior1.content}"
        assert "字段4" in behavior1.content, f"缺少'字段4': {behavior1.content}"
        assert "FROM" in behavior1.content, f"缺少'FROM': {behavior1.content}"
        
        print("  ✓ 成功解析带缩进的延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_continuation_line_with_symbol_refs():
    """测试延续行中的符号引用（新语法：单$起始）"""
    print("\n测试 continuation_line_with_symbol_refs 函数...")
    
    code = """func 调用API():
    请求结果 = 调用 $httpClient.post 使用参数,
        url,
        data,
        headers
    处理 $请求结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含符号引用
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        assert "httpClient.post" in behavior1.symbol_refs, f"缺少符号引用'httpClient.post': {behavior1.symbol_refs}"
        
        # 验证内容包含参数
        assert "url" in behavior1.content, f"缺少'url': {behavior1.content}"
        assert "data" in behavior1.content, f"缺少'data': {behavior1.content}"
        assert "headers" in behavior1.content, f"缺少'headers': {behavior1.content}"
        
        # 验证第二个行为步骤
        behavior2 = ast_nodes[func_node.children_uids[1]]
        assert isinstance(behavior2, BehaviorStepNode), "预期为BehaviorStepNode"
        assert "请求结果" in behavior2.symbol_refs, f"缺少符号引用'请求结果': {behavior2.symbol_refs}"
        
        print("  ✓ 成功解析延续行中的符号引用")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_continuation_line_error_misalignment():
    """测试延续行错误：缩进不对齐"""
    print("\n测试 continuation_line_error_misalignment 函数...")
    
    code = """func 测试():
    执行操作1,
        执行操作2
        执行操作3"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 应该抛出异常
        print("  ❌ 测试失败: 应该抛出异常但没有")
        return False
    except Exception as e:
        # 验证是否包含正确的错误信息
        error_msg = str(e)
        if "align" in error_msg.lower() or "对齐" in error_msg:
            print(f"  ✓ 成功检测到延续行缩进不对齐错误: {e}")
            return True
        else:
            print(f"  ❌ 测试失败: 错误信息不正确: {e}")
            return False


def test_paren_continuation():
    """测试小括号延续行（新语法：单$起始）"""
    print("\n测试 paren_continuation 函数...")
    
    code = """func 调用API():
    请求结果 = $httpClient.post(
        url,
        data,
        headers
    )
    处理 $请求结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含括号内的内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        assert "httpClient.post" in behavior1.symbol_refs, f"缺少符号引用'httpClient.post': {behavior1.symbol_refs}"
        
        # 验证内容包含所有参数
        assert "url" in behavior1.content, f"缺少'url': {behavior1.content}"
        assert "data" in behavior1.content, f"缺少'data': {behavior1.content}"
        assert "headers" in behavior1.content, f"缺少'headers': {behavior1.content}"
        
        # 验证第二个行为步骤
        behavior2 = ast_nodes[func_node.children_uids[1]]
        assert isinstance(behavior2, BehaviorStepNode), "预期为BehaviorStepNode"
        assert "请求结果" in behavior2.symbol_refs, f"缺少符号引用'请求结果': {behavior2.symbol_refs}"
        
        print("  ✓ 成功解析小括号延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_brace_continuation():
    """测试花括号延续行"""
    print("\n测试 brace_continuation 函数...")
    
    code = """func 初始化配置():
    配置字典 = {
        key1: value1,
        key2: value2,
        key3: value3
    }
    返回 配置字典"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含花括号内的内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有键值对
        assert "key1" in behavior1.content, f"缺少'key1': {behavior1.content}"
        assert "key2" in behavior1.content, f"缺少'key2': {behavior1.content}"
        assert "key3" in behavior1.content, f"缺少'key3': {behavior1.content}"
        assert "value1" in behavior1.content, f"缺少'value1': {behavior1.content}"
        
        print("  ✓ 成功解析花括号延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bracket_continuation():
    """测试方括号延续行"""
    print("\n测试 bracket_continuation 函数...")
    
    code = """func 处理数组():
    数组列表 = [
        元素1,
        元素2,
        元素3
    ]
    遍历 数组列表"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含方括号内的内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有元素
        assert "元素1" in behavior1.content, f"缺少'元素1': {behavior1.content}"
        assert "元素2" in behavior1.content, f"缺少'元素2': {behavior1.content}"
        assert "元素3" in behavior1.content, f"缺少'元素3': {behavior1.content}"
        
        print("  ✓ 成功解析方括号延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_brackets():
    """测试嵌套括号"""
    print("\n测试 nested_brackets 函数...")
    
    code = """func 处理复杂数据():
    结果 = 调用函数(
        参数1,
        嵌套调用(
            内层参数1,
            内层参数2
        ),
        参数3
    )
    返回 结果"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含嵌套括号内的所有内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有参数
        assert "参数1" in behavior1.content, f"缺少'参数1': {behavior1.content}"
        assert "嵌套调用" in behavior1.content, f"缺少'嵌套调用': {behavior1.content}"
        assert "内层参数1" in behavior1.content, f"缺少'内层参数1': {behavior1.content}"
        assert "内层参数2" in behavior1.content, f"缺少'内层参数2': {behavior1.content}"
        assert "参数3" in behavior1.content, f"缺岑'参数3': {behavior1.content}"
        
        print("  ✓ 成功解析嵌套括号")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backslash_continuation():
    """测试反斜杠延续行"""
    print("\n测试 backslash_continuation 函数...")
    
    # 反斜杠延续行需要与起始行对齐，不能有额外缩进
    code = """\
func 长语句():
    这是一个非常非常长的语句 \\
    需要分成多行来书写 \\
    以便提高可读性
    执行操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含所有延续行的内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含所有部分
        assert "非常非常长" in behavior1.content, f"缺少'非常非常长': {behavior1.content}"
        assert "分成多行" in behavior1.content, f"缺少'分成多行': {behavior1.content}"
        assert "提高可读性" in behavior1.content, f"缺少'提高可读性': {behavior1.content}"
        
        print("  ✓ 成功解析反斜杠延续行")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_param_desc_with_commas():
    """测试参数描述中包含逗号（单个和多个）"""
    print("\n测试 param_desc_with_commas 函数...")
    
    # 场景1: 单个逗号和括号
    print("  1. 测试单个逗号和括号:")
    code1 = """func 计算实体边界坐标(
    坐标1: 初始值(0, 0),
    实体: 实体对象，具备半径值
):
    计算边界"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(func_node, FunctionNode), "预期为FunctionNode"
        assert len(func_node.params) == 2, f"预期2个参数，实际{len(func_node.params)}"
        assert "0, 0" in func_node.params["坐标1"], f"坐标1描述应包含括号和逗号: {func_node.params['坐标1']}"
        print("    ✓ 成功解析单个逗号和括号")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 多个逗号
    print("  2. 测试多个逗号:")
    code2 = """func 创建用户(
    用户信息: 包含姓名、年龄、地址、电话等信息的字典,
    权限级别: 管理员、普通用户、访客之一
):
    创建用户"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert "姓名、年龄、地址、电话" in func_node.params["用户信息"], \
            f"用户信息描述应包含多个项: {func_node.params['用户信息']}"
        print("    ✓ 成功解析多个逗号")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 参数描述逗号测试通过")
    return True


def test_param_desc_with_brackets():
    """测试参数描述中包含各种括号（嵌套和方括号）"""
    print("\n测试 param_desc_with_brackets 函数...")
    
    # 场景1: 嵌套括号
    print("  1. 测试嵌套括号:")
    code1 = """func 处理配置(
    配置项: 格式为dict(key: str, value: tuple(int, int)),
    选项: 可选参数
):
    处理逻辑"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert "dict(key: str, value: tuple(int, int))" in func_node.params["配置项"], \
            f"配置项描述应包含嵌套括号: {func_node.params['配置项']}"
        print("    ✓ 成功解析嵌套括号")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 方括号
    print("  2. 测试方括号:")
    code2 = """func 处理数据(
    数据: 格式为List[Dict[str, Any]]的数据结构,
    过滤器: 可选的过滤函数
):
    处理数据"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        assert "List[Dict[str, Any]]" in func_node.params["数据"], \
            f"数据描述应包含方括号: {func_node.params['数据']}"
        print("    ✓ 成功解析方括号")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 参数描述括号测试通过")
    return True


def test_param_type_ref_single():
    """测试参数类型引用：单个参数"""
    print("\n测试 param_type_ref_single 函数...")
    
    code = """module utils.logger: 日志工具模块

func 处理业务逻辑(
    数据, 
    日志器: 由外部传入实例，其类型为 $logger.Logger
    ):
    验证结果 = 验证数据(数据)"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 查找函数节点
        func_node = None
        for uid, node in ast_nodes.items():
            if isinstance(node, FunctionNode):
                func_node = node
                break
        
        assert func_node is not None, "未找到函数节点"
        assert func_node.identifier == "处理业务逻辑", f"函数名不匹配: {func_node.identifier}"
        
        # 验证参数
        assert "数据" in func_node.params
        assert "日志器" in func_node.params
        
        # 验证类型引用
        assert "日志器" in func_node.param_type_refs, "缺少日志器的类型引用"
        assert func_node.param_type_refs["日志器"] == "logger.Logger", \
            f"类型引用不匹配: {func_node.param_type_refs['日志器']}"
        assert "数据" not in func_node.param_type_refs, "数据参数不应有类型引用"
        
        print("  ✓ 成功解析单个参数类型引用")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_param_type_ref_multiple():
    """测试参数类型引用：多个参数"""
    print("\n测试 param_type_ref_multiple 函数...")
    
    code = """module config.types: 配置类型定义

func 初始化系统(
    配置: 系统配置对象 $config.types.SystemConfig,
    日志器: 日志实例 $logger.Logger,
    数据库连接):
    执行初始化操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 查找函数节点
        func_node = None
        for uid, node in ast_nodes.items():
            if isinstance(node, FunctionNode):
                func_node = node
                break
        
        assert func_node is not None, "未找到函数节点"
        
        # 验证参数数量
        assert len(func_node.params) == 3, f"预期3个参数，实际{len(func_node.params)}"
        
        # 验证类型引用
        assert "配置" in func_node.param_type_refs
        assert func_node.param_type_refs["配置"] == "config.types.SystemConfig"
        assert "日志器" in func_node.param_type_refs
        assert func_node.param_type_refs["日志器"] == "logger.Logger"
        assert "数据库连接" not in func_node.param_type_refs  # 没有类型引用
        
        print("  ✓ 成功解析多个参数类型引用")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_top_level_behaviors():
    """测试顶层行为描述（简单行为、代码块、与函数混合）"""
    print("\n测试 top_level_behaviors 函数...")
    
    # 场景1: 简单顶层行为
    print("  1. 测试简单顶层行为:")
    code1 = '''module logging: 日志库
module config: 配置模块

初始化日志系统()
加载配置文件($config.load)
记录信息 "系统已启动"'''
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        modules = []
        behaviors = []
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, ModuleNode):
                modules.append(node)
            elif isinstance(node, BehaviorStepNode) and node.content.strip():
                behaviors.append(node)
        
        assert len(modules) == 2, f"预期2个模块，实际{len(modules)}"
        assert len(behaviors) == 3, f"预期3个行为步骤，实际{len(behaviors)}"
        assert "初始化" in behaviors[0].content, f"缺少'初始化': {behaviors[0].content}"
        assert "config.load" in behaviors[1].symbol_refs, f"缺少符号引用: {behaviors[1].symbol_refs}"
        print("    ✓ 成功解析简单顶层行为")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 带代码块的顶层行为
    print("  2. 测试带代码块的顶层行为:")
    code2 = """module os: 系统操作库

检查文件路径 = "./config.json"

如果 $os.path.exists(检查文件路径):
    读取配置 = 打开文件(检查文件路径)
    解析配置内容
    记录 "配置已加载"

否则:
    记录 "配置文件不存在"

输出最终结果"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        assert len(root_node.children_uids) >= 4, f"预期至少4个子节点，实际{len(root_node.children_uids)}"
        
        condition_node = None
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, BehaviorStepNode) and "如果" in node.content and node.new_block_flag:
                condition_node = node
                break
        
        assert condition_node is not None, "找不到条件判断节点"
        assert condition_node.new_block_flag, "条件判断应该有new_block_flag"
        assert len(condition_node.children_uids) >= 3, f"条件块应该有至少3个行为步骤"
        print("    ✓ 成功解析带代码块的行为")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景3: 顶层行为与函数混合
    print("  3. 测试顶层行为与函数混合:")
    code3 = """module utils: 工具模块

初始化全局配置()

func 处理数据(数据):
    验证数据格式
    返回处理结果

调用处理函数 = $处理数据("test")
输出结果"""
    
    try:
        lexer = IbcLexer(code3)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        modules = []
        funcs = []
        behaviors = []
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, ModuleNode):
                modules.append(node)
            elif isinstance(node, FunctionNode):
                funcs.append(node)
            elif isinstance(node, BehaviorStepNode) and node.content.strip():
                behaviors.append(node)
        
        assert len(modules) == 1, f"预期1个模块，实际{len(modules)}"
        assert len(funcs) == 1, f"预期1个函数，实际{len(funcs)}"
        assert len(behaviors) == 3, f"预期3个顶层行为，实际{len(behaviors)}"
        assert funcs[0].identifier == "处理数据", f"函数名不匹配: {funcs[0].identifier}"
        has_func_ref = any("处理数据" in b.symbol_refs for b in behaviors)
        assert has_func_ref, f"缺少符号引用处理数据"
        print("    ✓ 成功解析顶层行为与函数混合")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 顶层行为测试通过")
    return True


def test_param_type_ref_multiple_error():
    """测试参数类型引用错误：一个参数多个引用"""
    print("\n测试 param_type_ref_multiple_error 函数...")
    
    code = """func 测试函数(
    参数: 这是 $type1.A 或者 $type2.B
    ):
    执行操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        print("  ❌ 测试失败: 应该抛出异常但没有")
        return False
    except Exception as e:
        if "can only contain one symbol reference" in str(e):
            print(f"  ✓ 正确捕获到异常")
            return True
        else:
            print(f"  ❌ 测试失败: 异常消息不正确: {e}")
            return False


def test_var_with_equal_sign():
    """测试变量定义使用 = 等号作为停止符"""
    print("\n测试 var_with_equal_sign 函数...")
    
    code = """var total = 0
var count = 10
var name: 用户姓名"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 验证变量节点
        var_dict = {}  # {name: description}
        for uid in root_node.children_uids:
            var_node = ast_nodes[uid]
            if isinstance(var_node, VariableNode):
                var_dict[var_node.identifier] = var_node.content
        
        assert "total" in var_dict, "缺少total变量"
        assert "count" in var_dict, "缺少count变量"
        assert "name" in var_dict, "缺少name变量"
        
        # 验证描述：= 号后的内容应该包含 = 号本身
        # 注意：由于 lexer 会保留空格，所以 = 后可能有多余空格
        assert var_dict["total"].startswith("=") and "0" in var_dict["total"], f"total的描述不匹配: {var_dict['total']}"
        assert var_dict["count"].startswith("=") and "10" in var_dict["count"], f"count的描述不匹配: {var_dict['count']}"
        assert var_dict["name"] == "用户姓名", f"name的描述不匹配: {var_dict['name']}"
        
        print("  ✓ 成功解析变量定义使用 = 等号")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_var_type_ref():
    """测试变量类型引用"""
    print("\n测试 var_type_ref 函数...")
    
    code = """module logger: 日志模块
module database: 数据库模块

var userCount: 当前在线用户数量
var logger: 日志实例，类型为 $logger.Logger
var dbConnection: 数据库连接对象 $database.Connection
var config"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        
        # 统计有效节点
        modules = []
        variables = []
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, ModuleNode):
                modules.append(node)
            elif isinstance(node, VariableNode):
                variables.append(node)
        
        assert len(modules) == 2, f"预期2个模块，实际{len(modules)}"
        assert len(variables) == 4, f"预期4个变量，实际{len(variables)}"
        
        # 查找带类型引用的变量
        logger_var = None
        db_var = None
        for var in variables:
            if var.identifier == "logger":
                logger_var = var
            elif var.identifier == "dbConnection":
                db_var = var
        
        assert logger_var is not None, "找不到logger变量"
        assert db_var is not None, "找不到dbConnection变量"
        
        # 验证类型引用（type_ref现在是列表）
        assert logger_var.type_ref == ["logger.Logger"], f"预期logger类型引用为['logger.Logger']，实际为'{logger_var.type_ref}'"
        assert db_var.type_ref == ["database.Connection"], f"预期dbConnection类型引用为['database.Connection']，实际为'{db_var.type_ref}'"
        
        # 验证描述中包含类型引用内容
        assert "logger.Logger" in logger_var.content, f"描述中应包含类型引用: {logger_var.content}"
        assert "database.Connection" in db_var.content, f"描述中应包含类型引用: {db_var.content}"
        
        print("  ✓ 成功解析变量类型引用")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_var_type_ref_error():
    """测试变量类型引用：一个变量允许多个引用"""
    print("\n测试 var_type_ref_error 函数...")
    
    code = """var data: 类型为 $type1.A 或者 $type2.B"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        data_var = None
        for uid in root_node.children_uids:
            node = ast_nodes[uid]
            if isinstance(node, VariableNode) and node.identifier == "data":
                data_var = node
                break
        
        assert data_var is not None, "找不到data变量"
        # 验证支持多个类型引用
        assert len(data_var.type_ref) == 2, f"预期2个类型引用，实际{len(data_var.type_ref)}"
        assert "type1.A" in data_var.type_ref, f"缺少type1.A引用: {data_var.type_ref}"
        assert "type2.B" in data_var.type_ref, f"缺少type2.B引用: {data_var.type_ref}"
        
        print(f"  ✓ 成功解析多个类型引用")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_inheritance_with_dollar():
    """测试类继承使用 $ 前缀的父类符号"""
    print("\n测试 class_inheritance_with_dollar 函数...")
    
    code = """class UserManager($base.BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.identifier == "UserManager", f"类名不匹配"
        assert "base.BaseManager" in class_node.inh_params, "缺少$前缀父类继承信息"
        assert class_node.inh_params["base.BaseManager"] == "使用公共基类管理生命周期", "继承描述不匹配"
        
        print("  ✓ 成功解析$前缀的类继承")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visibility_basic_and_default():
    """测试基本可见性（public/protected/private切换）和默认可见性"""
    print("\n测试 visibility_basic_and_default 函数...")
    
    # 场景1: 可见性切换
    print("  1. 测试可见性切换:")
    code1 = """class DataProcessor():
    private
    var _internal_buffer: 内部缓存区
    var _cache: 缓存数据
    
    func _validate_data(原始数据):
        验证数据格式
    
    protected
    func _process_internal(原始数据):
        预处理数据
    
    public
    func process_data(输入数据):
        处理输入数据
    
    func get_result():
        返回 结果
"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.visibility == VisibilityTypes.PUBLIC, f"顶层类应该是public，实际为{class_node.visibility}"
        
        members = {}
        for child_uid in class_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, (VariableNode, FunctionNode)):
                members[child_node.identifier] = child_node.visibility
        
        assert members.get('_internal_buffer') == VisibilityTypes.PRIVATE, "_internal_buffer应该是private"
        assert members.get('_validate_data') == VisibilityTypes.PRIVATE, "_validate_data应该是private"
        assert members.get('_process_internal') == VisibilityTypes.PROTECTED, "_process_internal应该是protected"
        assert members.get('process_data') == VisibilityTypes.PUBLIC, "process_data应该是public"
        print("    ✓ 成功验证可见性切换")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 默认可见性为public
    print("  2. 测试默认可见性:")
    code2 = """class TestClass():
    var member1: 成员1
    var member2: 成员2
    
    func method1():
        执行操作1
    
    func method2():
        执行操作2
"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        members = {}
        for child_uid in class_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, (VariableNode, FunctionNode)):
                members[child_node.identifier] = child_node.visibility
        
        for member_name, visibility in members.items():
            assert visibility == VisibilityTypes.PUBLIC, f"{member_name}应该是public，实际为{visibility}"
        print("    ✓ 成功验证默认可见性")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 可见性测试通过")
    return True


def test_visibility_nested():
    """测试嵌套结构的可见性（内部类和函数内定义）"""
    print("\n测试 visibility_nested 函数...")
    
    # 场景1: 内部类可见性
    print("  1. 测试内部类可见性:")
    code1 = """class OuterClass():
    var outer_member: 外部类成员
    
    private
    class InnerPrivateClass():
        var inner_member: 内部私有类成员
    
    protected
    class InnerProtectedClass():
        var inner_member: 内部保护类成员
    
    public
    class InnerPublicClass():
        var inner_member: 内部公开类成员
"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        outer_class = ast_nodes[root_node.children_uids[0]]
        
        assert outer_class.visibility == VisibilityTypes.PUBLIC, "顶层类应该是public"
        
        inner_classes = {}
        for child_uid in outer_class.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, ClassNode):
                inner_classes[child_node.identifier] = child_node.visibility
        
        assert inner_classes.get('InnerPrivateClass') == VisibilityTypes.PRIVATE, "InnerPrivateClass应该是private"
        assert inner_classes.get('InnerProtectedClass') == VisibilityTypes.PROTECTED, "InnerProtectedClass应该是protected"
        assert inner_classes.get('InnerPublicClass') == VisibilityTypes.PUBLIC, "InnerPublicClass应该是public"
        print("    ✓ 成功验证内部类可见性")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 函数内嵌套定义的类和函数
    print("  2. 测试函数内嵌套定义:")
    code2 = """class OuterClass():
    public
    func outer_method():
        class LocalClass():
            var local_member: 局部类成员
            
            func local_method():
                执行操作
        
        func local_function():
            返回结果
        
        使用局部类和函数
        返回 结果

func top_level_function():
    class TopFuncLocalClass():
        var member: 成员
    
    func top_func_local_function():
        执行操作
    
    返回 结果
"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        all_nodes = {}
        def collect_nodes(uid):
            node = ast_nodes[uid]
            if isinstance(node, (ClassNode, FunctionNode)):
                all_nodes[node.identifier] = node.visibility
            for child_uid in node.children_uids:
                collect_nodes(child_uid)
        
        collect_nodes(0)
        
        assert all_nodes.get('OuterClass') == VisibilityTypes.PUBLIC, "OuterClass应该是public"
        assert all_nodes.get('top_level_function') == VisibilityTypes.PUBLIC, "top_level_function应该是public"
        assert all_nodes.get('LocalClass') == VisibilityTypes.PRIVATE, "LocalClass应该是private"
        assert all_nodes.get('local_method') == VisibilityTypes.PRIVATE, "local_method应该是private"
        assert all_nodes.get('local_function') == VisibilityTypes.PRIVATE, "local_function应该是private"
        print("    ✓ 成功验证函数内嵌套定义都是private")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 嵌套可见性测试通过")
    return True


def test_var_simple_bracket_continuation():
    """测试变量声明中的简单括号延续行（方括号、小括号、花括号）"""
    print("\n测试 var_simple_bracket_continuation 函数...")
    
    # 场景1: 方括号延续行
    print("  1. 测试方括号延续行:")
    code1 = """func test():
    var 颜色列表 = ["#f8b862", "#f6ad49",
                       "#f39800", "#f08300"]
    var 球半径 = 15
    var 中心点坐标 = (0, 0)
"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        var_dict = {}
        for child_uid in func_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, VariableNode):
                var_dict[child_node.identifier] = child_node.content
        
        assert "颜色列表" in var_dict, "缺少颜色列表变量"
        assert "#f8b862" in var_dict["颜色列表"], f"颜色列表内容不完整: {var_dict['颜色列表']}"
        assert "#f39800" in var_dict["颜色列表"], f"颜色列表内容不完整: {var_dict['颜色列表']}"
        print("    ✓ 成功解析方括号延续行")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 小括号延续行
    print("  2. 测试小括号延续行:")
    code2 = """func test():
    var 距离 = sqrt(
        (球1.x - 球2.x) ** 2 +
        (球1.y - 球2.y) ** 2
    )
    var 半径总和 = 球1.半径 + 球2.半径
"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        var_dict = {}
        for child_uid in func_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, VariableNode):
                var_dict[child_node.identifier] = child_node.content
        
        assert "距离" in var_dict, "缺少距离变量"
        assert "球1.x" in var_dict["距离"], f"距离内容不完整: {var_dict['距离']}"
        assert "球2.y" in var_dict["距离"], f"距离内容不完整: {var_dict['距离']}"
        print("    ✓ 成功解析小括号延续行")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景3: 花括号延续行
    print("  3. 测试花括号延续行:")
    code3 = """func test():
    var 配置字典 = {
        "host": "localhost",
        "port": 8080,
        "debug": True
    }
    var 结果 = "完成"
"""
    
    try:
        lexer = IbcLexer(code3)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        var_dict = {}
        for child_uid in func_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, VariableNode):
                var_dict[child_node.identifier] = child_node.content
        
        assert "配置字典" in var_dict, "缺少配置字典变量"
        assert "host" in var_dict["配置字典"], f"配置字典内容不完整: {var_dict['配置字典']}"
        assert "8080" in var_dict["配置字典"], f"配置字典内容不完整: {var_dict['配置字典']}"
        print("    ✓ 成功解析花括号延续行")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 简单括号延续测试通过")
    return True


def test_var_complex_bracket_continuation():
    """测试变量声明中的复杂场景（真实案例和嵌套括号）"""
    print("\n测试 var_complex_bracket_continuation 函数...")
    
    # 场景1: 真实案例（类内的多行变量）
    print("  1. 测试真实案例（类内多行变量）:")
    code1 = """description: 物理引擎核心类
@ 负责协调所有球体的重力、摩擦和碰撞逻辑
class PhysicsEngine():
    private
    var ball_list: 球对象列表
    var gravity: 重力加速度常量

    public
    func __init__():
        self.ball_list = []
        self.gravity = 9.81

        var 颜色列表 = ["#f8b862", "#f6ad49", "#f39800",
                       "#f08300", "#ec6d51", "#ee7948"]
        
        var 球半径 = 15
        var 中心坐标 = (0, 0)
"""
    
    try:
        lexer = IbcLexer(code1)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        class_node = ast_nodes[root_node.children_uids[0]]
        
        assert isinstance(class_node, ClassNode), "预期为ClassNode"
        assert class_node.external_desc == "物理引擎核心类", "类描述不匹配"
        
        # 查找 __init__ 函数
        init_func = None
        for child_uid in class_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, FunctionNode) and child_node.identifier == "__init__":
                init_func = child_node
                break
        
        assert init_func is not None, "找不到__init__函数"
        
        # 收集函数内的变量
        var_dict = {}
        for child_uid in init_func.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, VariableNode):
                var_dict[child_node.identifier] = child_node.content
        
        assert "颜色列表" in var_dict, "缺少颜色列表变量"
        assert "#f8b862" in var_dict["颜色列表"], "颜色列表内容不完整"
        assert "#ee7948" in var_dict["颜色列表"], "颜色列表内容不完整"
        print("    ✓ 成功解析真实案例")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 场景2: 嵌套括号
    print("  2. 测试嵌套括号:")
    code2 = """func test():
    var 矩阵 = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]
    var 配置 = {
        "database": {
            "host": "localhost",
            "port": 3306
        }
    }
"""
    
    try:
        lexer = IbcLexer(code2)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        var_dict = {}
        for child_uid in func_node.children_uids:
            child_node = ast_nodes[child_uid]
            if isinstance(child_node, VariableNode):
                var_dict[child_node.identifier] = child_node.content
        
        assert "矩阵" in var_dict, "缺少矩阵变量"
        assert "配置" in var_dict, "缺少配置变量"
        assert "[1, 2, 3]" in var_dict["矩阵"] or "1, 2, 3" in var_dict["矩阵"], f"矩阵内容不完整: {var_dict['矩阵']}"
        assert "localhost" in var_dict["配置"], f"配置内容不完整: {var_dict['配置']}"
        assert "3306" in var_dict["配置"], f"配置内容不完整: {var_dict['配置']}"
        print("    ✓ 成功解析嵌套括号")
    except Exception as e:
        print(f"    ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("  ✓ 复杂括号延续测试通过")
    return True


def test_visibility_func_nested():
    """测试函数内嵌套定义的类和函数的可见性"""
    print("\n测试 visibility_func_nested 函数...")
    
    code = """class OuterClass():
    public
    func outer_method():
        class LocalClass():
            var local_member: 局部类成员
            
            func local_method():
                执行操作
        
        func local_function():
            返回结果
        
        使用局部类和函数
        返回 结果

func top_level_function():
    class TopFuncLocalClass():
        var member: 成员
    
    func top_func_local_function():
        执行操作
    
    返回 结果
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 收集所有节点
        all_nodes = {}
        def collect_nodes(uid):
            node = ast_nodes[uid]
            if isinstance(node, (ClassNode, FunctionNode)):
                all_nodes[node.identifier] = node.visibility
            for child_uid in node.children_uids:
                collect_nodes(child_uid)
        
        collect_nodes(0)
        
        # 验证顶层节点
        assert all_nodes.get('OuterClass') == VisibilityTypes.PUBLIC, "OuterClass应该是public"
        assert all_nodes.get('top_level_function') == VisibilityTypes.PUBLIC, "top_level_function应该是public"
        
        # 验证类内方法
        assert all_nodes.get('outer_method') == VisibilityTypes.PUBLIC, "outer_method应该是public"
        
        # 验证函数内定义的类和函数（必须是private）
        assert all_nodes.get('LocalClass') == VisibilityTypes.PRIVATE, "LocalClass应该是private"
        assert all_nodes.get('local_method') == VisibilityTypes.PRIVATE, "local_method应该是private"
        assert all_nodes.get('local_function') == VisibilityTypes.PRIVATE, "local_function应该是private"
        assert all_nodes.get('TopFuncLocalClass') == VisibilityTypes.PRIVATE, "TopFuncLocalClass应该是private"
        assert all_nodes.get('top_func_local_function') == VisibilityTypes.PRIVATE, "top_func_local_function应该是private"
        
        print("  ✓ 成功验证函数内嵌套定义的类和函数都是private")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_reference_parsing():
    """测试self引用解析"""
    print("\n测试 self_reference_parsing 函数...")
    
    code = """description: 测试类
class TestClass():
    var ball: 球体对象
    var internal_data: 内部数据
    
    func test_method():
        位置 = self.ball.get_position()
        数据 = self.internal_data
        结果 = self.process_data(数据)
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 找到BehaviorStepNode，验证self_refs列表
        behavior_nodes = []
        for uid, node in ast_nodes.items():
            if isinstance(node, BehaviorStepNode):
                behavior_nodes.append(node)
        
        # 应该有多个BehaviorStepNode
        assert len(behavior_nodes) > 0, "应该有BehaviorStepNode"
        
        # 收集所有self引用
        all_self_refs = []
        for node in behavior_nodes:
            all_self_refs.extend(node.self_refs)
        
        # 验证self引用是否正确收集
        expected_refs = ['ball.get_position', 'internal_data', 'process_data']
        for expected_ref in expected_refs:
            assert expected_ref in all_self_refs, f"未找到self引用: {expected_ref}"
        
        print(f"  ✓ 成功解析self引用: {', '.join(all_self_refs)}")
        print("\nAST树结构:")
        print_ast_tree(ast_nodes)
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mixed_continuation_and_comma():
    """测试混合场景：逗号延续和括号延续的组合"""
    print("\n测试 mixed_continuation_and_comma 函数...")
    
    code = """func 复杂配置():
    配置 = 创建配置对象(
        host = "localhost",
        port = 3306,
        options = {
            timeout: 30,
            retry: 3
        }
    ),
        备份配置 = 创建备份配置()
    返回 配置
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        root_node = ast_nodes[0]
        func_node = ast_nodes[root_node.children_uids[0]]
        
        # 验证函数有两个行为步骤（第一个是混合延续行，第二个是返回语句）
        assert len(func_node.children_uids) == 2, f"预期2个行为步骤，实际{len(func_node.children_uids)}"
        
        # 验证第一个行为步骤包含所有内容
        behavior1 = ast_nodes[func_node.children_uids[0]]
        assert isinstance(behavior1, BehaviorStepNode), "预期为BehaviorStepNode"
        
        # 验证内容包含括号内的所有属性
        assert "host" in behavior1.content, f"缺少'host': {behavior1.content}"
        assert "localhost" in behavior1.content, f"缺少'localhost': {behavior1.content}"
        assert "3306" in behavior1.content, f"缺少'3306': {behavior1.content}"
        assert "timeout" in behavior1.content, f"缺少'timeout': {behavior1.content}"
        assert "备份配置" in behavior1.content, f"缺少'备份配置': {behavior1.content}"
        
        print("  ✓ 成功解析逗号和括号的混合延续")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deep_nested_inheritance():
    """测试多层继承链的解析"""
    print("\n测试 deep_nested_inheritance 函数...")
    
    code = """description: 基础形状类
class Shape():
    var color: 颜色

description: 多边形类
class Polygon($Shape: 继承形状):
    var sides: 边数

description: 四边形类
class Quadrilateral($Polygon: 继承多边形):
    var angles: 角度列表

description: 矩形类
class Rectangle($Quadrilateral: 继承四边形):
    var width: 宽度
    var height: 高度
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 收集所有类节点
        class_nodes = {}
        for uid, node in ast_nodes.items():
            if isinstance(node, ClassNode):
                class_nodes[node.identifier] = node
        
        # 验证所有类都被解析
        assert "Shape" in class_nodes
        assert "Polygon" in class_nodes
        assert "Quadrilateral" in class_nodes
        assert "Rectangle" in class_nodes
        
        # 验证继承关系
        assert "Shape" in class_nodes["Polygon"].inh_params
        assert "Polygon" in class_nodes["Quadrilateral"].inh_params
        assert "Quadrilateral" in class_nodes["Rectangle"].inh_params
        
        # 验证继承描述
        assert class_nodes["Polygon"].inh_params["Shape"] == "继承形状"
        assert class_nodes["Quadrilateral"].inh_params["Polygon"] == "继承多边形"
        assert class_nodes["Rectangle"].inh_params["Quadrilateral"] == "继承四边形"
        
        print("  ✓ 成功解析多层继承链")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visibility_inheritance_interaction():
    """测试继承和可见性的交互"""
    print("\n测试 visibility_inheritance_interaction 函数...")
    
    code = """class BaseClass():
    public
    var public_member: 公开成员
    
    protected
    var protected_member: 受保护成员
    
    private
    var private_member: 私有成员

class DerivedClass($BaseClass: 继承基类):
    public
    var derived_public: 派生类公开成员
    
    protected
    var derived_protected: 派生类受保护成员
    
    func derived_method():
        访问 self.protected_member
        访问 self.public_member
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 收集类节点
        base_class = None
        derived_class = None
        for uid, node in ast_nodes.items():
            if isinstance(node, ClassNode):
                if node.identifier == "BaseClass":
                    base_class = node
                elif node.identifier == "DerivedClass":
                    derived_class = node
        
        assert base_class is not None
        assert derived_class is not None
        
        # 验证继承关系
        assert "BaseClass" in derived_class.inh_params
        
        # 验证基类成员的可见性
        base_members = {}
        for child_uid in base_class.children_uids:
            child = ast_nodes[child_uid]
            if isinstance(child, VariableNode):
                base_members[child.identifier] = child.visibility
        
        assert base_members["public_member"] == VisibilityTypes.PUBLIC
        assert base_members["protected_member"] == VisibilityTypes.PROTECTED
        assert base_members["private_member"] == VisibilityTypes.PRIVATE
        
        # 验证派生类成员的可见性
        derived_members = {}
        for child_uid in derived_class.children_uids:
            child = ast_nodes[child_uid]
            if isinstance(child, VariableNode):
                derived_members[child.identifier] = child.visibility
        
        assert derived_members["derived_public"] == VisibilityTypes.PUBLIC
        assert derived_members["derived_protected"] == VisibilityTypes.PROTECTED
        
        print("  ✓ 成功验证继承和可见性的交互")
        return True
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始测试 Intent Behavior Code 解析器...")
    print("=" * 60)
    
    try:
        test_results = []
        
        test_results.append(("模块声明", test_module_declaration()))
        test_results.append(("变量声明", test_variable_declaration()))
        test_results.append(("函数声明", test_function_declaration()))
        test_results.append(("类声明", test_class_declaration()))
        test_results.append(("类继承$前缀", test_class_inheritance_with_dollar()))
        test_results.append(("描述和意图注释", test_description_and_intent()))
        test_results.append(("符号引用", test_symbol_reference()))
        test_results.append(("复杂示例", test_complex_example()))
        test_results.append(("嵌套代码块", test_nested_blocks()))
        test_results.append(("多行description", test_multiline_description()))
        test_results.append(("多行函数声明", test_multiline_func_declaration()))
        test_results.append(("类中多行函数", test_multiline_func_in_class()))
        test_results.append(("基本延续行", test_continuation_line_basic()))
        test_results.append(("带缩进延续行", test_continuation_line_with_indent()))
        test_results.append(("延续行符号引用", test_continuation_line_with_symbol_refs()))
        test_results.append(("小括号延续行", test_paren_continuation()))
        test_results.append(("花括号延续行", test_brace_continuation()))
        test_results.append(("方括号延续行", test_bracket_continuation()))
        test_results.append(("嵌套括号", test_nested_brackets()))
        test_results.append(("反斜杠延续行", test_backslash_continuation()))
        
        # 参数描述测试（合并后）
        test_results.append(("参数描述逗号", test_param_desc_with_commas()))
        test_results.append(("参数描述括号", test_param_desc_with_brackets()))
        
        # 参数类型引用测试
        test_results.append(("单个参数类型引用", test_param_type_ref_single()))
        test_results.append(("多个参数类型引用", test_param_type_ref_multiple()))
        test_results.append(("参数多引用错误", test_param_type_ref_multiple_error()))
        
        # 顶层行为描述测试（合并后）
        test_results.append(("顶层行为描述", test_top_level_behaviors()))
        
        # 变量类型引用测试
        test_results.append(("变量类型引用", test_var_type_ref()))
        test_results.append(("变量多引用错误", test_var_type_ref_error()))
        test_results.append(("变量 = 等号语法", test_var_with_equal_sign()))
        
        # 变量括号延续行测试（合并后）
        test_results.append(("变量简单括号延续", test_var_simple_bracket_continuation()))
        test_results.append(("变量复杂括号延续", test_var_complex_bracket_continuation()))
        
        # 可见性测试（合并后）
        test_results.append(("基本可见性", test_visibility_basic_and_default()))
        test_results.append(("嵌套可见性", test_visibility_nested()))
        
        # self引用测试
        test_results.append(("self引用解析", test_self_reference_parsing()))
        
        # 边界场景测试
        test_results.append(("混合延续场景", test_mixed_continuation_and_comma()))
        test_results.append(("多层继承链", test_deep_nested_inheritance()))
        test_results.append(("继承可见性交互", test_visibility_inheritance_interaction()))
        
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:20} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print("=" * 60)
        print(f"总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("所有测试通过！✓")
            print("=" * 60)
        else:
            print(f"⚠️  有 {failed} 个测试失败")
            print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
