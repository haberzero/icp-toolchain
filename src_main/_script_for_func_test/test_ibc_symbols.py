"""
IBC符号系统完整测试套件

测试范围：
1. 符号数据类型（SymbolNode）
2. 符号提取功能（从AST提取符号声明）
3. 函数参数存储
4. 符号表序列化/反序列化
5. 符号规范化流程
"""
import sys
import os
from typing import Dict

# 添加src_main目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_processor import IbcSymbolProcessor
from typedef.ibc_data_types import (
    SymbolNode, SymbolType, VisibilityTypes
)

# ==================== 数据类型基础测试 ======================================

def test_symbol_node_basics():
    """测试SymbolNode基本功能"""
    print("=" * 60)
    print("测试 SymbolNode 基本功能")
    print("=" * 60)
    
    try:
        # 创建函数符号（带参数）
        symbol = SymbolNode(
            uid=1,
            parent_symbol_name="",  # 根符号
            symbol_name="计算总价",
            normalized_name="",
            visibility=VisibilityTypes.DEFAULT,
            description="计算订单总价",
            symbol_type=SymbolType.FUNCTION,
            parameters={"商品列表": "商品数组", "折扣率": "0-1之间的小数"}
        )
        
        assert not symbol.is_normalized(), "新创建的符号应该未规范化"
        
        # 规范化
        symbol.update_normalized_info("CalculateTotal", VisibilityTypes.PUBLIC)
        assert symbol.is_normalized(), "更新后应该已规范化"
        assert symbol.normalized_name == "CalculateTotal"
        assert symbol.visibility == VisibilityTypes.PUBLIC
        
        # 序列化/反序列化
        symbol_dict = symbol.to_dict()
        symbol2 = SymbolNode.from_dict(symbol_dict)
        
        assert symbol2.uid == symbol.uid
        assert symbol2.symbol_name == symbol.symbol_name
        assert symbol2.normalized_name == symbol.normalized_name
        assert symbol2.symbol_type == symbol.symbol_type
        assert len(symbol2.parameters) == 2
        
        print("\n[通过] SymbolNode 基本功能测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 符号提取测试 ======================================

def test_basic_symbol_extraction():
    """测试基本符号提取"""
    print("=" * 60)
    print("测试基本符号提取")
    print("=" * 60)
    
    code = """module requests: Python HTTP库
var userCount: 在线用户数

func 计算总价(商品列表, 折扣率):
    返回 总价

class UserManager():
    var users: 用户字典
    
    func 添加用户(用户名, 密码):
        保存用户"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        all_symbols = symbol_table
        
        # 验证符号
        assert "userCount" in all_symbols
        assert "计算总价" in all_symbols
        assert "UserManager" in all_symbols
        assert "users" in all_symbols
        assert "添加用户" in all_symbols
        
        # 验证类型
        assert all_symbols["计算总价"].symbol_type == SymbolType.FUNCTION
        assert all_symbols["UserManager"].symbol_type == SymbolType.CLASS
        assert all_symbols["userCount"].symbol_type == SymbolType.VARIABLE
        
        # 验证未规范化
        for symbol in all_symbols.values():
            assert not symbol.is_normalized()
        
        print(f"\n提取符号数: {len(all_symbols)}")
        print("\n[通过] 基本符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_function_parameters_extraction():
    """测试函数参数提取"""
    print("=" * 60)
    print("测试函数参数提取")
    print("=" * 60)
    
    code = """func 计算总价(
    商品列表: 商品对象数组,
    折扣率: 0到1之间的小数,
    优惠券: 可选优惠券对象
):
    返回 总价

func 登录(
    用户名: 登录用户名,
    密码: 用户密码
):
    验证登录"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        func1 = symbol_table.get("计算总价")
        func2 = symbol_table.get("登录")
        
        # 验证参数
        assert len(func1.parameters) == 3
        assert "商品列表" in func1.parameters
        assert func1.parameters["折扣率"] == "0到1之间的小数"
        
        assert len(func2.parameters) == 2
        assert func2.parameters["用户名"] == "登录用户名"
        
        print(f"\n函数 '计算总价' 参数: {list(func1.parameters.keys())}")
        print(f"函数 '登录' 参数: {list(func2.parameters.keys())}")
        print("\n[通过] 函数参数提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_with_members_extraction():
    """测试类成员符号提取"""
    print("=" * 60)
    print("测试类成员符号提取")
    print("=" * 60)
    
    code = """description: 配置管理器
class ConfigManager():
    var configData: 配置数据
    var configPath: 配置路径
    
    description: 加载配置
    func 加载配置():
        读取配置文件"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        all_symbols = symbol_table
        
        # 验证类和成员
        assert "ConfigManager" in all_symbols
        assert all_symbols["ConfigManager"].description == "配置管理器"
        
        assert "configData" in all_symbols
        assert "configPath" in all_symbols
        assert "加载配置" in all_symbols
        assert all_symbols["加载配置"].description == "加载配置"
        
        print("\n[通过] 类成员符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 序列化测试 ====================

def test_symbol_table_serialization():
    """测试符号表序列化"""
    print("=" * 60)
    print("测试符号表序列化")
    print("=" * 60)
    
    code = """module json: JSON库

class DataProcessor(BaseProcessor: 基础处理器):
    var cache: 缓存数据
    
    func 处理数据(输入: 输入数据):
        验证 $输入$ 格式
        调用 $json.dumps$($输入$)"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        # 序列化
        table_dict = {}
        for symbol_name, symbol in symbol_table.items():
            table_dict[symbol_name] = symbol.to_dict()
        
        # 反序列化
        restored_table: Dict[str, SymbolNode] = {}
        for symbol_name, symbol_dict in table_dict.items():
            symbol_node = SymbolNode.from_dict(symbol_dict)
            restored_table[symbol_name] = symbol_node
        
        # 验证
        assert len(restored_table) == len(symbol_table)
        
        # 验证符号
        for symbol_name in symbol_table.keys():
            original = symbol_table.get(symbol_name)
            restored = restored_table.get(symbol_name)
            assert original.uid == restored.uid
            assert original.symbol_type == restored.symbol_type
        
        print(f"\n符号数: {len(table_dict)}")
        print("\n[通过] 符号表序列化测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 符号层次结构测试 ====================

def test_symbol_hierarchy():
    """测试符号层次结构（parent_symbol_name和children_symbol_names）"""
    print("=" * 60)
    print("测试符号层次结构")
    print("=" * 60)
    
    # 创建包含类和成员的IBC代码
    code = """class UserManager():
    var userList: 用户列表
    var sessionStore: 会话存储
    
    func 添加用户(用户名, 密码):
        保存用户信息
    
    func 删除用户(用户ID):
        删除用户信息

func 全局函数():
    执行操作"""
    
    try:
        # 解析代码
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 提取符号
        symbol_processor = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_processor.process_symbols()
        
        print(f"\n提取的符号数量: {len(symbol_table)}")
        
        # 查找类符号
        user_manager = symbol_table.get("UserManager")
        if not user_manager:
            print("\n✗ 未找到UserManager类")
            return False
        
        # 验证UserManager应该有4个子符号（2个变量 + 2个函数）
        print(f"\nUserManager的子符号数量: {len(user_manager.children_symbol_names)}")
        if len(user_manager.children_symbol_names) != 4:
            print(f"✗ UserManager应该有4个子符号，实际有{len(user_manager.children_symbol_names)}个")
            return False
        
        # 验证子符号的parent_symbol_name
        print("验证子符号的parent关系:")
        for child_symbol_name in user_manager.children_symbol_names:
            child_symbol = symbol_table.get(child_symbol_name)
            
            if not child_symbol:
                print(f"✗ 未找到符号{child_symbol_name}")
                return False
            
            if child_symbol.parent_symbol_name != "UserManager":
                print(f"✗ 子符号{child_symbol_name}的parent_symbol_name不正确")
                print(f"  期望: UserManager, 实际: {child_symbol.parent_symbol_name}")
                return False
        
        print(f"  ✓ 所有4个子符号的parent_symbol_name都正确")
        
        # 验证全局函数没有父符号（parent_symbol_name为空）
        global_func = symbol_table.get("全局函数")
        if not global_func:
            print("\n✗ 未找到全局函数")
            return False
        
        if global_func.parent_symbol_name != "":
            print(f"✗ 全局函数的parent_symbol_name应该为空，实际为{global_func.parent_symbol_name}")
            return False
        
        if len(global_func.children_symbol_names) != 0:
            print(f"✗ 全局函数不应该有子符号")
            return False
        
        print(f"  ✓ 全局函数parent_symbol_name为空，children_symbol_names为空")
        
        # 测试add_child和remove_child方法
        test_symbol = SymbolNode(
            uid=100,
            parent_symbol_name="",
            symbol_name="TestSymbol",
            symbol_type=SymbolType.CLASS
        )
        
        test_symbol.add_child("ChildSymbol1")
        test_symbol.add_child("ChildSymbol2")
        test_symbol.add_child("ChildSymbol1")  # 重复添加应该被忽略
        
        if len(test_symbol.children_symbol_names) != 2:
            print(f"\n✗ add_child测试失败")
            return False
        
        test_symbol.remove_child("ChildSymbol1")
        if len(test_symbol.children_symbol_names) != 1 or "ChildSymbol2" not in test_symbol.children_symbol_names:
            print(f"✗ remove_child测试失败")
            return False
        
        print(f"  ✓ add_child和remove_child方法正常工作")
        
        # 测试序列化和反序列化
        symbol_dict = user_manager.to_dict()
        
        if "parent_symbol_name" not in symbol_dict or "children_symbol_names" not in symbol_dict:
            print("\n✗ 序列化结果缺少parent_symbol_name或children_symbol_names")
            return False
        
        restored_symbol = SymbolNode.from_dict(symbol_dict)
        
        if restored_symbol.parent_symbol_name != user_manager.parent_symbol_name:
            print(f"✗ 反序列化后parent_symbol_name不匹配")
            return False
        
        if restored_symbol.children_symbol_names != user_manager.children_symbol_names:
            print(f"✗ 反序列化后children_symbol_names不匹配")
            return False
        
        print(f"  ✓ parent_symbol_name和children_symbol_names序列化/反序列化正常")
        
        print("\n[通过] 符号层次结构测试通过\n")
        return True
        
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 集成测试 ====================

def test_complete_workflow():
    """完整工作流程测试：提取、规范化、序列化"""
    print("=" * 60)
    print("完整工作流程测试")
    print("=" * 60)
    
    code = """module json: JSON处理库

description: 用户服务类
class UserService(BaseService: 基础服务类):
    var sessionStore: 会话存储
    
    description: 用户登录
    func 登录(
        用户名: 登录用户名,
        密码: 用户密码
    ):
        验证 $用户名$ 和 $密码$
        调用 $json.dumps$($用户数据$)
        创建会话
    
    func 登出(会话ID):
        清除会话"""
    
    try:
        # 步骤1: 解析并提取符号
        print("\n步骤1: 解析IBC代码并提取符号...")
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        all_symbols = symbol_table
        print(f"  提取符号数: {len(all_symbols)}")
        
        # 步骤2: 验证初始状态
        print("\n步骤2: 验证符号初始状态...")
        unnormalized = {name: symbol for name, symbol in symbol_table.items() 
                        if not symbol.is_normalized()}
        assert len(unnormalized) == len(all_symbols), "所有符号应该未规范化"
        print(f"  未规范化符号: {len(unnormalized)}/{len(all_symbols)}")
        
        # 步骤3: 模拟AI规范化
        print("\n步骤3: 模拟AI规范化符号...")
        normalization_map = {
            "UserService": ("UserService", "public"),
            "sessionStore": ("sessionStore", "private"),
            "登录": ("Login", "public"),
            "登出": ("Logout", "public")
        }
        
        for symbol_name, (normalized_name, visibility_str) in normalization_map.items():
            symbol = symbol_table.get(symbol_name)
            if symbol:
                visibility = VisibilityTypes.PUBLIC if visibility_str == "public" else VisibilityTypes.PRIVATE
                symbol.update_normalized_info(normalized_name, visibility)
                print(f"  - {symbol_name} -> {normalized_name} ({visibility_str})")
        
        # 步骤4: 验证规范化结果
        print("\n步骤4: 验证规范化结果...")
        unnormalized_after = {name: symbol for name, symbol in symbol_table.items() 
                              if not symbol.is_normalized()}
        print(f"  未规范化符号: {len(unnormalized_after)}/{len(all_symbols)}")
        assert len(unnormalized_after) == 0, "所有符号都应已规范化"
        
        # 步骤5: 序列化
        print("\n步骤5: 序列化符号表...")
        table_dict = {}
        for symbol_name, symbol in symbol_table.items():
            table_dict[symbol_name] = symbol.to_dict()
        print(f"  序列化完成，符号数: {len(table_dict)}")
        
        # 步骤6: 反序列化并验证
        print("\n步骤6: 反序列化并验证...")
        restored_table: Dict[str, SymbolNode] = {}
        for symbol_name, symbol_dict in table_dict.items():
            symbol_node = SymbolNode.from_dict(symbol_dict)
            restored_table[symbol_name] = symbol_node
        
        for symbol_name in all_symbols.keys():
            original = symbol_table.get(symbol_name)
            restored = restored_table.get(symbol_name)
            
            if original and restored:
                assert restored.is_normalized() or original.is_normalized() == False
                if original.is_normalized():
                    assert original.normalized_name == restored.normalized_name
                    assert original.visibility == restored.visibility
        
        print("  数据一致性验证通过")
        
        # 验证函数参数
        login_func = symbol_table.get("登录")
        assert len(login_func.parameters) == 2
        print(f"\n函数参数: {list(login_func.parameters.keys())}")
        
        print("\n[通过] 完整工作流程测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 主测试运行器 ====================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IBC符号系统完整测试套件")
    print("=" * 60)
    
    test_groups = [
        ("数据类型基础测试", [
            ("SymbolNode基本功能", test_symbol_node_basics),
        ]),
        ("符号提取测试", [
            ("基本符号提取", test_basic_symbol_extraction),
            ("函数参数提取", test_function_parameters_extraction),
            ("类成员符号提取", test_class_with_members_extraction),
        ]),
        ("序列化与集成测试", [
            ("符号表序列化", test_symbol_table_serialization),
            ("符号层次结构", test_symbol_hierarchy),
            ("完整工作流程", test_complete_workflow),
        ]),
    ]
    
    all_results = []
    
    for group_name, tests in test_groups:
        print(f"\n{'=' * 60}")
        print(f"测试组: {group_name}")
        print("=" * 60)
        
        for test_name, test_func in tests:
            result = test_func()
            all_results.append((test_name, result))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in all_results if result)
    failed = len(all_results) - passed
    
    for test_name, result in all_results:
        status = "[通过]" if result else "[失败]"
        print(f"{test_name:30} {status}")
    
    print("=" * 60)
    print(f"总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("所有测试通过!")
        print("=" * 60)
    else:
        print(f"警告: 有 {failed} 个测试失败")
        print("=" * 60)
