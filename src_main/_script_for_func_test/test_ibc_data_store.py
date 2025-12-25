"""
IBC数据管理器测试

全面测试IbcDataStore类的所有功能方法，包括：
1. IBC代码文件管理
2. AST数据管理
3. 校验数据管理
4. 符号表数据管理
5. 真实IBC代码的AST持久化测试
"""
import sys
import os
from typing import Dict

# 添加src_main到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typedef.ibc_data_types import (
    IbcBaseAstNode, AstNodeType, ModuleNode, ClassNode, 
    FunctionNode, VariableNode, BehaviorStepNode,
    SymbolNode, SymbolType, VisibilityTypes
)
from data_store.ibc_data_store import get_instance as get_ibc_data_store
from utils.ibc_analyzer.ibc_analyzer import analyze_ibc_code
from libs.ibc_funcs import IbcFuncs


def setup_test_environment():
    """设置测试环境"""
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    test_ibc_root = os.path.join(dev_temp_dir, "test_ibc_data_store")
    
    # 清理并创建测试目录
    if os.path.exists(test_ibc_root):
        import shutil
        shutil.rmtree(test_ibc_root)
    os.makedirs(test_ibc_root, exist_ok=True)
    
    return test_ibc_root


def test_ibc_code_management():
    """测试IBC代码文件管理功能"""
    
    print("=" * 60)
    print("测试 1: IBC代码文件管理")
    print("=" * 60)
    
    test_ibc_root = setup_test_environment()
    ibc_data_store = get_ibc_data_store()
    
    # 测试用例1: 路径构建
    print("\n1.1 测试路径构建方法...")
    file_path = "user/manager"
    ibc_path = ibc_data_store.build_ibc_path(test_ibc_root, file_path)
    expected_path = os.path.join(test_ibc_root, "user", "manager.ibc")
    if ibc_path == expected_path:
        print(f"   ✓ 路径构建正确")
    else:
        print(f"   ✗ 路径构建错误")
        return False
    
    # 测试用例2: 保存IBC代码
    print("\n1.2 测试保存IBC代码...")
    test_code = """module UserManager: 用户管理模块

class User():
    var username: 用户名
    
    func login():
        验证用户身份
        返回登录结果
"""
    ibc_data_store.save_ibc_code(ibc_path, test_code)
    print(f"   ✓ IBC代码保存成功")
    
    # 测试用例3: 加载IBC代码
    print("\n1.3 测试加载IBC代码...")
    loaded_code = ibc_data_store.load_ibc_code(ibc_path)
    if loaded_code == test_code:
        print(f"   ✓ IBC代码加载正确，长度: {len(loaded_code)}")
    else:
        print(f"   ✗ IBC代码加载错误")
        return False
    
    # 测试用例4: 加载不存在的文件
    print("\n1.4 测试加载不存在的文件...")
    non_exist_path = ibc_data_store.build_ibc_path(test_ibc_root, "non/exist")
    loaded_code = ibc_data_store.load_ibc_code(non_exist_path)
    if loaded_code == "":
        print(f"   ✓ 不存在文件返回空字符串")
    else:
        print(f"   ✗ 不存在文件应返回空字符串")
        return False
    
    return True


def test_ast_management():
    """测试AST数据管理功能"""
    
    print("\n" + "=" * 60)
    print("测试 2: AST数据管理")
    print("=" * 60)
    
    test_ibc_root = setup_test_environment()
    ibc_data_store = get_ibc_data_store()
    
    # 测试用例1: 基本AST保存和加载
    print("\n2.1 测试基本AST保存和加载...")
    ast_dict = {}
    ast_dict[0] = IbcBaseAstNode(uid=0, node_type=AstNodeType.DEFAULT)
    
    module_node = ModuleNode(
        uid=1, parent_uid=0, node_type=AstNodeType.MODULE,
        identifier="TestModule", content="测试模块", line_number=1
    )
    ast_dict[1] = module_node
    ast_dict[0].add_child(1)
    
    class_node = ClassNode(
        uid=2, parent_uid=1, node_type=AstNodeType.CLASS,
        identifier="TestClass", external_desc="测试类", 
        inh_params={"BaseClass": "基础类"}, line_number=3
    )
    ast_dict[2] = class_node
    ast_dict[1].add_child(2)
    
    func_node = FunctionNode(
        uid=3, parent_uid=2, node_type=AstNodeType.FUNCTION,
        identifier="test_function", external_desc="测试函数",
        params={"x": "int参数", "y": "str参数"}, line_number=5
    )
    ast_dict[3] = func_node
    ast_dict[2].add_child(3)
    
    var_node = VariableNode(
        uid=4, parent_uid=3, node_type=AstNodeType.VARIABLE,
        identifier="test_var", content="测试变量", line_number=7
    )
    ast_dict[4] = var_node
    ast_dict[3].add_child(4)
    
    behavior_node = BehaviorStepNode(
        uid=5, parent_uid=3, node_type=AstNodeType.BEHAVIOR_STEP,
        content="执行操作", symbol_refs=["test_var"], line_number=9
    )
    ast_dict[5] = behavior_node
    ast_dict[3].add_child(5)
    
    print(f"   ✓ 创建了 {len(ast_dict)} 个AST节点")
    
    # 测试路径构建
    file_path = "test/module"
    ast_path = ibc_data_store.build_ast_path(test_ibc_root, file_path)
    
    # 保存AST
    ibc_data_store.save_ast(ast_path, ast_dict)
    print(f"   ✓ AST保存成功")
    
    # 加载AST
    loaded_ast = ibc_data_store.load_ast(ast_path)
    if len(loaded_ast) != len(ast_dict):
        print(f"   ✗ AST加载失败，节点数不匹配")
        return False
    print(f"   ✓ AST加载成功，节点数: {len(loaded_ast)}")
    
    # 验证节点类型和树结构
    if isinstance(loaded_ast[1], ModuleNode) and isinstance(loaded_ast[2], ClassNode) and \
       isinstance(loaded_ast[3], FunctionNode) and isinstance(loaded_ast[4], VariableNode) and \
       isinstance(loaded_ast[5], BehaviorStepNode):
        print(f"   ✓ AST节点类型正确")
    else:
        print(f"   ✗ AST节点类型错误")
        return False
    
    # 验证节点数据
    if loaded_ast[2].inh_params == class_node.inh_params and \
       loaded_ast[3].params == func_node.params and \
       loaded_ast[5].symbol_refs == behavior_node.symbol_refs:
        print(f"   ✓ AST节点数据正确")
    else:
        print(f"   ✗ AST节点数据错误")
        return False
    
    # 验证树结构
    if loaded_ast[0].children_uids == ast_dict[0].children_uids:
        print(f"   ✓ AST树结构正确")
    else:
        print(f"   ✗ AST树结构错误")
        return False
    
    # 测试用例2: 加载不存在的AST文件
    print("\n2.2 测试加载不存在的AST文件...")
    non_exist_path = ibc_data_store.build_ast_path(test_ibc_root, "non/exist")
    loaded_ast = ibc_data_store.load_ast(non_exist_path)
    if loaded_ast == {}:
        print(f"   ✓ 不存在文件返回空字典")
    else:
        print(f"   ✗ 不存在文件应返回空字典")
        return False
    
    return True


def test_ast_with_real_ibc_code():
    """测试真实IBC代码的AST持久化"""
    
    print("\n" + "=" * 60)
    print("测试 3: 真实IBC代码的AST持久化")
    print("=" * 60)
    
    test_ibc_root = setup_test_environment()
    ibc_data_store = get_ibc_data_store()
    
    # 示例IBC代码
    ibc_code = """
module UserManagement: 用户管理模块

class User():
    var username: 用户名
    var email: 电子邮件地址
    
    description: 用户登录功能
    @ 验证用户名和密码，返回登录结果
    func login(
        username: 用户名,
        password: 密码
    ):
        检查用户名是否存在 $username$
        验证密码是否正确 $password$
        如果验证成功:
            创建会话
            返回成功
        否则:
            返回失败
    """
    
    # 解析IBC代码生成AST
    print("\n3.1 解析IBC代码...")
    try:
        ast_dict, _ = analyze_ibc_code(ibc_code)
    except Exception as e:
        print(f"   ✗ 解析失败: {e}")
        return False
    
    if not ast_dict:
        print(f"   ✗ 解析失败，未生成有效AST")
        return False
    print(f"   ✓ 解析成功，生成 {len(ast_dict)} 个节点")
    
    # 保存AST到文件
    print("\n3.2 保存并加载AST...")
    ast_path = ibc_data_store.build_ast_path(test_ibc_root, "user/management")
    
    ibc_data_store.save_ast(ast_path, ast_dict)
    
    # 加载AST
    loaded_ast = ibc_data_store.load_ast(ast_path)
    if len(loaded_ast) != len(ast_dict):
        print(f"   ✗ AST加载失败")
        return False
    print(f"   ✓ AST保存和加载成功，节点数: {len(loaded_ast)}")
    
    # 验证关键节点
    print("\n3.3 验证关键节点...")
    module_count = sum(1 for node in loaded_ast.values() if isinstance(node, ModuleNode))
    class_count = sum(1 for node in loaded_ast.values() if isinstance(node, ClassNode))
    func_count = sum(1 for node in loaded_ast.values() if isinstance(node, FunctionNode))
    var_count = sum(1 for node in loaded_ast.values() if isinstance(node, VariableNode))
    
    if module_count == 1 and class_count == 1 and func_count == 1 and var_count == 2:
        print(f"   ✓ 节点类型正确 (Module: {module_count}, Class: {class_count}, Func: {func_count}, Var: {var_count})")
    else:
        print(f"   ✗ 节点类型数量不正确")
        return False
    
    # 验证节点标识符
    all_correct = True
    for uid, node in loaded_ast.items():
        if isinstance(node, ModuleNode) and node.identifier != "UserManagement":
            print(f"   ✗ Module节点标识符错误")
            all_correct = False
        elif isinstance(node, ClassNode) and node.identifier != "User":
            print(f"   ✗ Class节点标识符错误")
            all_correct = False
        elif isinstance(node, FunctionNode):
            if node.identifier != "login":
                print(f"   ✗ Function节点标识符错误")
                all_correct = False
            elif len(node.params) != 2:
                print(f"   ✗ Function节点参数数量错误")
                all_correct = False
    
    if all_correct:
        print(f"   ✓ 关键节点数据正确")
    
    return all_correct


def test_verify_data_management():
    """测试校验数据管理功能"""
    
    print("\n" + "=" * 60)
    print("测试 4: 校验数据管理")
    print("=" * 60)
    
    test_ibc_root = setup_test_environment()
    ibc_data_store = get_ibc_data_store()
    
    # 测试用例1: 基本保存和加载
    print("\n4.1 测试校验数据保存和加载...")
    file_path = "user/service"
    verify_path = ibc_data_store.build_verify_path(test_ibc_root, file_path)
    
    verify_data = {
        'ibc_verify_code': 'abc123def456',
        'one_file_req_verify_code': 'xyz789uvw012'
    }
    
    ibc_data_store.save_verify_data(verify_path, verify_data)
    
    loaded_data = ibc_data_store.load_verify_data(verify_path)
    if loaded_data == verify_data:
        print(f"   ✓ 校验数据保存和加载正确")
    else:
        print(f"   ✗ 校验数据加载错误")
        return False
    
    # 测试用例2: 更新校验码
    print("\n4.2 测试更新IBC校验码...")
    file_path = "test/verify"
    ibc_code = "module TestVerify: 测试校验码"
    ibc_path = ibc_data_store.build_ibc_path(test_ibc_root, file_path)
    ibc_data_store.save_ibc_code(ibc_path, ibc_code)
    
    ibc_data_store.update_verify_code(test_ibc_root, file_path)
    
    # 验证校验码
    verify_path = ibc_data_store.build_verify_path(test_ibc_root, file_path)
    verify_data = ibc_data_store.load_verify_data(verify_path)
    expected_md5 = IbcFuncs.calculate_text_md5(ibc_code)
    
    if verify_data.get('ibc_verify_code') == expected_md5:
        print(f"   ✓ 校验码更新成功且值正确")
    else:
        print(f"   ✗ 校验码值错误")
        return False
    
    # 测试用例3: 批量更新校验码
    print("\n4.3 测试批量更新校验码...")
    file_paths = ["batch/file1", "batch/file2", "batch/file3"]
    for fp in file_paths:
        ibc_path = ibc_data_store.build_ibc_path(test_ibc_root, fp)
        ibc_data_store.save_ibc_code(ibc_path, f"module {fp}: 测试")
    
    ibc_data_store.batch_update_verify_codes(test_ibc_root, file_paths)
    print(f"   ✓ 批量更新成功: {len(file_paths)} 个文件")
    
    # 测试用例4: 加载不存在的校验数据
    print("\n4.4 测试加载不存在的校验数据...")
    non_exist_path = ibc_data_store.build_verify_path(test_ibc_root, "non/exist")
    loaded_data = ibc_data_store.load_verify_data(non_exist_path)
    if loaded_data == {}:
        print(f"   ✓ 不存在文件返回空字典")
    else:
        print(f"   ✗ 不存在文件应返回空字典")
        return False
    
    return True


def test_symbol_management():
    """测试符号表数据管理功能"""
    
    print("\n" + "=" * 60)
    print("测试 5: 符号表数据管理")
    print("=" * 60)
    
    test_ibc_root = setup_test_environment()
    ibc_data_store = get_ibc_data_store()
    
    # 测试用例1: 基本保存和加载
    print("\n5.1 测试符号表保存和加载...")
    file_path = "user/manager"
    symbol_table: Dict[str, SymbolNode] = {}
    
    class_symbol = SymbolNode(
        uid=1, parent_symbol_name="",
        symbol_name="UserManager", normalized_name="UserManager",
        visibility=VisibilityTypes.PUBLIC,
        description="用户管理类", symbol_type=SymbolType.CLASS
    )
    symbol_table[class_symbol.symbol_name] = class_symbol
    
    func_symbol = SymbolNode(
        uid=2, parent_symbol_name="",
        symbol_name="登录", normalized_name="login",
        visibility=VisibilityTypes.PUBLIC,
        description="用户登录", symbol_type=SymbolType.FUNCTION,
        parameters={"用户名": "登录用户名", "密码": "用户密码"}
    )
    symbol_table[func_symbol.symbol_name] = func_symbol
    
    var_symbol = SymbolNode(
        uid=3, parent_symbol_name="",
        symbol_name="用户列表", normalized_name="userList",
        visibility=VisibilityTypes.PRIVATE,
        description="用户列表", symbol_type=SymbolType.VARIABLE
    )
    symbol_table[var_symbol.symbol_name] = var_symbol
    
    symbols_path = ibc_data_store.build_symbols_path(test_ibc_root, file_path)
    file_name = os.path.basename(file_path)
    ibc_data_store.save_symbols(symbols_path, file_name, symbol_table)
    
    loaded_symbols = ibc_data_store.load_symbols(symbols_path, file_name)
    if len(loaded_symbols) != len(symbol_table):
        print(f"   ✗ 符号表加载失败")
        return False
    print(f"   ✓ 符号表保存和加载成功，共 {len(loaded_symbols)} 个符号")
    
    # 验证符号数据
    loaded_class = loaded_symbols.get("UserManager")
    loaded_func = loaded_symbols.get("登录")
    loaded_var = loaded_symbols.get("用户列表")
    
    if loaded_class and loaded_class.symbol_type == SymbolType.CLASS and \
       loaded_func and loaded_func.normalized_name == "login" and \
       loaded_func.parameters == func_symbol.parameters and \
       loaded_var and loaded_var.visibility == VisibilityTypes.PRIVATE:
        print(f"   ✓ 符号数据正确")
    else:
        print(f"   ✗ 符号数据错误")
        return False
    
    # 测试用例2: 更新符号信息
    print("\n5.2 测试更新符号规范化信息...")
    ibc_data_store.update_symbol_info(
        symbols_path, file_name, "登录", "Login"
    )
    
    updated_symbols = ibc_data_store.load_symbols(symbols_path, file_name)
    updated_func = updated_symbols.get("登录")
    if updated_func.normalized_name == "Login":
        print(f"   ✓ 符号信息更新成功")
    else:
        print(f"   ✗ 符号信息更新错误")
        return False
    
    # 测试用例3: 同目录多文件符号表
    print("\n5.3 测试同目录多文件符号表...")
    file2_path = "user/service"
    symbol_table2: Dict[str, SymbolNode] = {}
    symbol2 = SymbolNode(
        uid=4, parent_symbol_name="",
        symbol_name="ServiceClass", normalized_name="ServiceClass",
        visibility=VisibilityTypes.PUBLIC,
        description="服务类", symbol_type=SymbolType.CLASS
    )
    symbol_table2[symbol2.symbol_name] = symbol2
    
    symbols_path2 = ibc_data_store.build_symbols_path(test_ibc_root, file2_path)
    file_name2 = os.path.basename(file2_path)
    ibc_data_store.save_symbols(symbols_path2, file_name2, symbol_table2)
    
    symbols1 = ibc_data_store.load_symbols(symbols_path, file_name)
    symbols2 = ibc_data_store.load_symbols(symbols_path2, file_name2)
    
    if "UserManager" in symbols1 and "ServiceClass" not in symbols1 and \
       "ServiceClass" in symbols2 and "UserManager" not in symbols2:
        print(f"   ✓ 多文件符号表互不干扰")
    else:
        print(f"   ✗ 多文件符号表错误")
        return False
    
    # 测试用例4: 加载不存在的符号表
    print("\n5.4 测试加载不存在的符号表...")
    non_exist_path = ibc_data_store.build_symbols_path(test_ibc_root, "non/exist")
    non_exist_symbols = ibc_data_store.load_symbols(non_exist_path, "exist")
    if non_exist_symbols == {}:
        print(f"   ✓ 不存在文件返回空字典")
    else:
        print(f"   ✗ 不存在文件应返回空字典")
        return False
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IBC数据管理器测试套件")
    print("=" * 60)
    
    try:
        # 运行所有测试
        result1 = test_ibc_code_management()
        result2 = test_ast_management()
        result3 = test_ast_with_real_ibc_code()
        result4 = test_verify_data_management()
        result5 = test_symbol_management()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"测试 1 - IBC代码文件管理: {'✓ 通过' if result1 else '✗ 失败'}")
        print(f"测试 2 - AST数据管理: {'✓ 通过' if result2 else '✗ 失败'}")
        print(f"测试 3 - 真实IBC代码AST: {'✓ 通过' if result3 else '✗ 失败'}")
        print(f"测试 4 - 校验数据管理: {'✓ 通过' if result4 else '✗ 失败'}")
        print(f"测试 5 - 符号表数据管理: {'✓ 通过' if result5 else '✗ 失败'}")
        print("=" * 60)
        
        if result1 and result2 and result3 and result4 and result5:
            print("✓ 所有测试通过！IbcDataStore功能完整且正确！")
        else:
            print("✗ 有测试失败，请检查输出")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
