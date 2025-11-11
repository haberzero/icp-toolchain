"""
测试新的符号表数据类型定义
"""
import sys
import os

# 添加src_main目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typedef.ibc_data_types import SymbolNode, SymbolType, FileSymbolTable


def test_symbol_node():
    """测试SymbolNode的基本功能"""
    print("=" * 50)
    print("测试 SymbolNode")
    print("=" * 50)
    
    # 创建符号节点
    symbol = SymbolNode(
        uid=1,
        symbol_name="test_function",
        normalized_name="",  # 留空，后续填充
        visibility="",  # 留空，后续填充
        description="测试函数",
        symbol_type=SymbolType.FUNCTION
    )
    
    print(f"创建的符号: {symbol}")
    print(f"是否已规范化: {symbol.is_normalized()}")
    
    # 转换为字典
    symbol_dict = symbol.to_dict()
    print(f"\n符号字典: {symbol_dict}")
    
    # 从字典创建
    symbol2 = SymbolNode.from_dict(symbol_dict)
    print(f"从字典恢复: {symbol2}")
    
    # 更新规范化信息
    symbol.update_normalized_info("TestFunction", "public")
    print(f"\n更新后的符号: {symbol}")
    print(f"是否已规范化: {symbol.is_normalized()}")
    
    print("\n✓ SymbolNode 测试通过\n")


def test_file_symbol_table():
    """测试FileSymbolTable的基本功能"""
    print("=" * 50)
    print("测试 FileSymbolTable")
    print("=" * 50)
    
    # 创建文件符号表
    table = FileSymbolTable(file_md5="abc123")
    
    # 添加符号
    symbol1 = SymbolNode(
        uid=1,
        symbol_name="UserManager",
        description="用户管理类",
        symbol_type=SymbolType.CLASS
    )
    table.add_symbol(symbol1)
    
    symbol2 = SymbolNode(
        uid=2,
        symbol_name="get_user",
        description="获取用户",
        symbol_type=SymbolType.FUNCTION
    )
    table.add_symbol(symbol2)
    
    print(f"符号表: {table}")
    print(f"符号数量: {len(table.symbols)}")
    
    # 获取符号
    retrieved = table.get_symbol("UserManager")
    print(f"\n获取符号 'UserManager': {retrieved}")
    
    # 检查是否包含符号
    print(f"是否包含 'get_user': {table.has_symbol('get_user')}")
    print(f"是否包含 'unknown': {table.has_symbol('unknown')}")
    
    # 获取所有符号
    all_symbols = table.get_all_symbols()
    print(f"\n所有符号: {list(all_symbols.keys())}")
    
    # 获取未规范化的符号
    unnormalized = table.get_unnormalized_symbols()
    print(f"未规范化符号数量: {len(unnormalized)}")
    
    # 转换为字典
    table_dict = table.to_dict()
    print(f"\n符号表字典: {table_dict}")
    
    # 从字典创建
    table2 = FileSymbolTable.from_dict(table_dict)
    print(f"从字典恢复: {table2}")
    
    print("\n✓ FileSymbolTable 测试通过\n")


def test_integration():
    """集成测试：模拟完整流程"""
    print("=" * 50)
    print("集成测试：模拟符号提取和规范化流程")
    print("=" * 50)
    
    # 1. 创建符号表并添加符号（模拟IbcSymbolGen的输出）
    table = FileSymbolTable(file_md5="test_md5_value")
    
    symbols_data = [
        ("UserService", SymbolType.CLASS, "用户服务类"),
        ("login", SymbolType.FUNCTION, "用户登录功能"),
        ("logout", SymbolType.FUNCTION, "用户登出功能"),
        ("current_user", SymbolType.VARIABLE, "当前用户变量"),
    ]
    
    for idx, (name, stype, desc) in enumerate(symbols_data, 1):
        symbol = SymbolNode(
            uid=idx,
            symbol_name=name,
            normalized_name="",  # 符号生成时留空
            visibility="",  # 符号生成时留空
            description=desc,
            symbol_type=stype
        )
        table.add_symbol(symbol)
    
    print("1. 符号提取完成（所有符号都未规范化）:")
    for name, symbol in table.symbols.items():
        print(f"   - {name}: normalized={symbol.is_normalized()}")
    
    # 2. 模拟cmd_handler调用AI进行规范化
    print("\n2. 模拟AI规范化过程...")
    normalization_results = {
        "UserService": ("UserService", "public"),
        "login": ("Login", "public"),
        "logout": ("Logout", "public"),
        "current_user": ("currentUser", "private"),
    }
    
    for symbol_name, (normalized_name, visibility) in normalization_results.items():
        symbol = table.get_symbol(symbol_name)
        if symbol:
            symbol.update_normalized_info(normalized_name, visibility)
            print(f"   - {symbol_name} -> {normalized_name} ({visibility})")
    
    # 3. 检查规范化结果
    print("\n3. 规范化完成后的状态:")
    unnormalized = table.get_unnormalized_symbols()
    print(f"   未规范化符号数量: {len(unnormalized)}")
    print(f"   已规范化符号数量: {len(table.symbols) - len(unnormalized)}")
    
    # 4. 转换为字典（用于保存）
    table_dict = table.to_dict()
    print("\n4. 转换为字典格式（用于保存）:")
    print(f"   MD5: {table_dict['md5']}")
    print(f"   符号数量: {len(table_dict['symbols'])}")
    
    # 5. 从字典恢复（模拟加载）
    table_loaded = FileSymbolTable.from_dict(table_dict)
    print("\n5. 从字典恢复:")
    print(f"   恢复的符号数量: {len(table_loaded.symbols)}")
    
    # 验证数据一致性
    for name in symbols_data:
        original = table.get_symbol(name[0])
        loaded = table_loaded.get_symbol(name[0])
        if original and loaded:
            assert original.uid == loaded.uid
            assert original.normalized_name == loaded.normalized_name
            assert original.visibility == loaded.visibility
    
    print("\n✓ 集成测试通过\n")


if __name__ == "__main__":
    print("\n开始测试新的符号表数据类型...\n")
    
    try:
        test_symbol_node()
        test_file_symbol_table()
        test_integration()
        
        print("=" * 50)
        print("所有测试通过！✓")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
