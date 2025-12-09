"""
符号表持久化测试

测试符号表的保存和加载功能
"""
import sys
import os
from typing import Dict

# 添加src_main到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typedef.ibc_data_types import SymbolNode, SymbolType, VisibilityTypes
from data_store.ibc_data_store import get_instance as get_ibc_data_store


def test_symbol_table_basic_persistence():
    """测试符号表的基本持久化功能"""
    
    print("=" * 60)
    print("测试 1: 符号表基本持久化功能")
    print("=" * 60)
    
    # 1. 创建测试符号表
    print("\n1. 创建测试符号表...")
    symbol_table: Dict[str, SymbolNode] = {}
    
    # 添加类符号
    class_symbol = SymbolNode(
        uid=1,
        symbol_name="UserManager",
        normalized_name="UserManager",
        visibility=VisibilityTypes.PUBLIC,
        description="用户管理类",
        symbol_type=SymbolType.CLASS
    )
    symbol_table[class_symbol.symbol_name] = class_symbol
    
    # 添加函数符号
    func_symbol = SymbolNode(
        uid=2,
        symbol_name="登录",
        normalized_name="Login",
        visibility=VisibilityTypes.PUBLIC,
        description="用户登录功能",
        symbol_type=SymbolType.FUNCTION,
        parameters={"用户名": "登录用户名", "密码": "用户密码"}
    )
    symbol_table[func_symbol.symbol_name] = func_symbol
    
    # 添加变量符号
    var_symbol = SymbolNode(
        uid=3,
        symbol_name="用户列表",
        normalized_name="userList",
        visibility=VisibilityTypes.PRIVATE,
        description="存储所有用户的列表",
        symbol_type=SymbolType.VARIABLE
    )
    symbol_table[var_symbol.symbol_name] = var_symbol
    
    print(f"   创建了 {len(symbol_table)} 个符号")
    
    # 2. 保存符号表到文件
    print("\n2. 保存符号表到文件...")
    ibc_data_store = get_ibc_data_store()
    
    # 使用_dev_temp目录
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    os.makedirs(dev_temp_dir, exist_ok=True)
    
    # 创建测试的IBC根目录
    test_ibc_root = os.path.join(dev_temp_dir, "test_ibc_root")
    os.makedirs(test_ibc_root, exist_ok=True)
    
    test_file_path = "test_file.ibc"
    
    success = ibc_data_store.save_file_symbols(test_ibc_root, test_file_path, symbol_table)
    if not success:
        print(f"   ✗ 保存失败")
        return False
    print(f"   ✓ 保存成功")
    
    # 3. 从文件加载符号表
    print("\n3. 从文件加载符号表...")
    loaded_symbol_table = ibc_data_store.load_file_symbols(test_ibc_root, test_file_path)
    print(f"   加载了 {len(loaded_symbol_table)} 个符号")
    
    # 4. 验证加载的符号表
    print("\n4. 验证加载的符号表数据...")
    all_correct = True
    
    # 验证符号数量
    if len(loaded_symbol_table) != len(symbol_table):
        print(f"   ✗ 符号数量不匹配")
        all_correct = False
    else:
        print(f"   ✓ 符号数量匹配: {len(loaded_symbol_table)}")
    
    # 验证类符号
    loaded_class = loaded_symbol_table.get("UserManager")
    if not loaded_class or \
       loaded_class.symbol_name != class_symbol.symbol_name or \
       loaded_class.normalized_name != class_symbol.normalized_name or \
       loaded_class.visibility != class_symbol.visibility or \
       loaded_class.symbol_type != class_symbol.symbol_type:
        print(f"   ✗ 类符号验证失败")
        all_correct = False
    else:
        print(f"   ✓ 类符号数据正确")
    
    # 验证函数符号
    loaded_func = loaded_symbol_table.get("登录")
    if not loaded_func or \
       loaded_func.symbol_name != func_symbol.symbol_name or \
       loaded_func.normalized_name != func_symbol.normalized_name or \
       loaded_func.parameters != func_symbol.parameters:
        print(f"   ✗ 函数符号验证失败")
        all_correct = False
    else:
        print(f"   ✓ 函数符号数据正确")
    
    # 验证变量符号
    loaded_var = loaded_symbol_table.get("用户列表")
    if not loaded_var or \
       loaded_var.symbol_name != var_symbol.symbol_name or \
       loaded_var.visibility != var_symbol.visibility:
        print(f"   ✗ 变量符号验证失败")
        all_correct = False
    else:
        print(f"   ✓ 变量符号数据正确")
    
    return all_correct


def test_symbol_table_update():
    """测试符号表的更新功能"""
    
    print("\n" + "=" * 60)
    print("测试 2: 符号表更新功能")
    print("=" * 60)
    
    # 1. 创建初始符号表
    print("\n1. 创建初始符号表...")
    ibc_data_store = get_ibc_data_store()
    
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    test_ibc_root = os.path.join(dev_temp_dir, "test_ibc_root")
    test_file_path = "update_test.ibc"
    
    symbol_table: Dict[str, SymbolNode] = {}
    test_symbol = SymbolNode(
        uid=1,
        symbol_name="测试函数",
        normalized_name="",  # 未规范化
        visibility=VisibilityTypes.DEFAULT,
        description="测试函数描述",
        symbol_type=SymbolType.FUNCTION
    )
    symbol_table[test_symbol.symbol_name] = test_symbol
    
    # 保存初始符号表
    ibc_data_store.save_file_symbols(test_ibc_root, test_file_path, symbol_table)
    print(f"   ✓ 初始符号表已保存（未规范化）")
    
    # 2. 更新符号的规范化信息
    print("\n2. 更新符号规范化信息...")
    success = ibc_data_store.update_symbol_normalized_info(
        test_ibc_root,
        test_file_path,
        "测试函数",
        "TestFunction",
        VisibilityTypes.PUBLIC  # 使用枚举类型
    )
    
    if not success:
        print(f"   ✗ 更新失败")
        return False
    print(f"   ✓ 更新成功")
    
    # 3. 重新加载并验证
    print("\n3. 重新加载并验证...")
    loaded_symbol_table = ibc_data_store.load_file_symbols(test_ibc_root, test_file_path)
    loaded_symbol = loaded_symbol_table.get("测试函数")
    
    all_correct = True
    if not loaded_symbol:
        print(f"   ✗ 符号未找到")
        all_correct = False
    elif loaded_symbol.normalized_name != "TestFunction":
        print(f"   ✗ 规范化名称不正确: {loaded_symbol.normalized_name}")
        all_correct = False
    elif loaded_symbol.visibility != VisibilityTypes.PUBLIC:
        print(f"   ✗ 可见性不正确: {loaded_symbol.visibility}")
        all_correct = False
    else:
        print(f"   ✓ 符号已正确更新")
        print(f"     - 规范化名称: {loaded_symbol.normalized_name}")
        print(f"     - 可见性: {loaded_symbol.visibility.value}")
    
    return all_correct


def test_multiple_files_in_directory():
    """测试同一目录下多个文件的符号表"""
    
    print("\n" + "=" * 60)
    print("测试 3: 同一目录下多个文件的符号表")
    print("=" * 60)
    
    ibc_data_store = get_ibc_data_store()
    
    dev_temp_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "_dev_temp"
    )
    test_ibc_root = os.path.join(dev_temp_dir, "test_ibc_root")
    
    # 1. 保存第一个文件的符号表
    print("\n1. 保存第一个文件的符号表...")
    symbol_table1: Dict[str, SymbolNode] = {}
    symbol1 = SymbolNode(
        uid=1,
        symbol_name="File1Symbol",
        normalized_name="File1Symbol",
        visibility=VisibilityTypes.PUBLIC,
        description="文件1的符号",
        symbol_type=SymbolType.CLASS
    )
    symbol_table1[symbol1.symbol_name] = symbol1
    
    success1 = ibc_data_store.save_file_symbols(test_ibc_root, "file1.ibc", symbol_table1)
    print(f"   ✓ 文件1符号表已保存")
    
    # 2. 保存第二个文件的符号表
    print("\n2. 保存第二个文件的符号表...")
    symbol_table2: Dict[str, SymbolNode] = {}
    symbol2 = SymbolNode(
        uid=2,
        symbol_name="File2Symbol",
        normalized_name="File2Symbol",
        visibility=VisibilityTypes.PUBLIC,
        description="文件2的符号",
        symbol_type=SymbolType.FUNCTION
    )
    symbol_table2[symbol2.symbol_name] = symbol2
    
    success2 = ibc_data_store.save_file_symbols(test_ibc_root, "file2.ibc", symbol_table2)
    print(f"   ✓ 文件2符号表已保存")
    
    # 3. 验证两个文件的符号表都存在且互不干扰
    print("\n3. 验证两个文件的符号表...")
    loaded_table1 = ibc_data_store.load_file_symbols(test_ibc_root, "file1.ibc")
    loaded_table2 = ibc_data_store.load_file_symbols(test_ibc_root, "file2.ibc")
    
    all_correct = True
    
    if "File1Symbol" not in loaded_table1:
        print(f"   ✗ 文件1符号丢失")
        all_correct = False
    elif "File2Symbol" in loaded_table1:
        print(f"   ✗ 文件1包含了文件2的符号（符号泄漏）")
        all_correct = False
    else:
        print(f"   ✓ 文件1符号表正确")
    
    if "File2Symbol" not in loaded_table2:
        print(f"   ✗ 文件2符号丢失")
        all_correct = False
    elif "File1Symbol" in loaded_table2:
        print(f"   ✗ 文件2包含了文件1的符号（符号泄漏）")
        all_correct = False
    else:
        print(f"   ✓ 文件2符号表正确")
    
    return all_correct


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("符号表持久化测试套件")
    print("=" * 60)
    
    try:
        # 运行测试1：基本持久化功能
        result1 = test_symbol_table_basic_persistence()
        
        # 运行测试2：更新功能
        result2 = test_symbol_table_update()
        
        # 运行测试3：多文件功能
        result3 = test_multiple_files_in_directory()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        print(f"测试 1 - 符号表基本持久化功能: {'\u2713 通过' if result1 else '\u2717 失败'}")
        print(f"测试 2 - 符号表更新功能: {'\u2713 通过' if result2 else '\u2717 失败'}")
        print(f"测试 3 - 同一目录下多个文件的符号表: {'\u2713 通过' if result3 else '\u2717 失败'}")
        print("=" * 60)
        
        if result1 and result2 and result3:
            print("✓ 所有测试通过！")
        else:
            print("✗ 有测试失败，请检查输出")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
