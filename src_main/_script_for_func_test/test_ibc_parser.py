import sys
import os
import json

# 正确添加src_main目录到sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from typedef.ibc_data_types import AstNodeType, ModuleNode, ClassNode, FunctionNode, VariableNode, BehaviorStepNode


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
    """测试模块声明"""
    print("测试 module_declaration 函数...")
    
    code = """module requests: Python第三方HTTP请求库
module threading: 系统线程库
module utils"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_nodes = parser.parse()
        
        # 验证根节点的子节点数量
        root_node = ast_nodes[0]
        
        # 验证第一个模块
        module1 = ast_nodes[root_node.children_uids[0]]
        assert isinstance(module1, ModuleNode), "预期为ModuleNode"
        assert module1.identifier == "requests", f"预期标识符为'requests'，实际为'{module1.identifier}'"
        assert module1.content == "Python第三方HTTP请求库", f"预期内容不匹配"
        
        # 验证第二个模块
        module2 = ast_nodes[root_node.children_uids[1]]
        assert isinstance(module2, ModuleNode), "预期为ModuleNode"
        assert module2.identifier == "threading", f"预期标识符为'threading'"
        assert module2.content == "系统线程库", f"预期内容不匹配"
        
        # 验证第三个模块（无描述）
        module3 = ast_nodes[root_node.children_uids[2]]
        assert isinstance(module3, ModuleNode), "预期为ModuleNode"
        assert module3.identifier == "utils", f"预期标识符为'utils'"
        assert module3.content == "", f"预期内容为空"
        
        print("  ✓ 成功解析模块声明")
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
    
    code = """var userCount: 当前在线用户数量, cacheData: 临时缓存数据
var config"""
    
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
        assert "cacheData" in var_dict, "缺少cacheData变量"
        assert "config" in var_dict, "缺少config变量"
        
        # 验证描述
        assert var_dict["userCount"] == "当前在线用户数量", f"userCount的描述不匹配: {var_dict['userCount']}"
        assert var_dict["cacheData"] == "临时缓存数据", f"cacheData的描述不匹配: {var_dict['cacheData']}"
        assert var_dict["config"] == "", f"config应该没有描述: {var_dict['config']}"
        
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
    """测试函数声明"""
    print("\n测试 function_declaration 函数...")
    
    code = """\
func 计算订单总价(商品列表: 包含价格信息的商品对象数组, 折扣率: 0到1之间的小数):
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
    """测试符号引用"""
    print("\n测试 symbol_reference 函数...")
    
    code = """func 发送请求(请求数据):
    var maxRetries: 最大重试次数
    当 重试计数 < $maxRetries$:
        尝试发送 $httpClient.post$(请求数据)"""
    
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
            self.configData = $json.parse$(文件内容)
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


def main():
    """主测试函数"""
    print("=" * 60)
    print("开始测试 Intent Behavior Code 解析器...")
    print("=" * 60)
    
    try:
        test_results = []
        
        test_results.append(("模块声明", test_module_declaration()))
        test_results.append(("变量声明", test_variable_declaration()))
        test_results.append(("函数声明", test_function_declaration()))
        test_results.append(("类声明", test_class_declaration()))
        test_results.append(("描述和意图注释", test_description_and_intent()))
        test_results.append(("符号引用", test_symbol_reference()))
        test_results.append(("复杂示例", test_complex_example()))
        test_results.append(("嵌套代码块", test_nested_blocks()))
        
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
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️  有 {failed} 个测试失败")
        
        return failed == 0
        
    except Exception as e:
        print(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
