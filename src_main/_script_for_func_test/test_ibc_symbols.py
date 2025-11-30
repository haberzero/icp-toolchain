"""
IBC符号系统完整测试套件

测试范围：
1. 符号数据类型（SymbolNode, SymbolReference, FileSymbolTable）
2. 符号提取功能（从AST提取符号声明）
3. 符号引用提取（行为引用、模块调用、类继承）
4. 函数参数存储
5. 符号表序列化/反序列化
6. 符号规范化流程
"""
import sys
import os

# 添加src_main目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_processor import IbcSymbolProcessor
from typedef.ibc_data_types import (
    SymbolNode, SymbolType, FileSymbolTable, SymbolReference, 
    ReferenceType, VisibilityTypes
)


# ==================== 数据类型基础测试 ====================

def test_symbol_node_basics():
    """测试SymbolNode基本功能"""
    print("=" * 60)
    print("测试 SymbolNode 基本功能")
    print("=" * 60)
    
    try:
        # 创建函数符号（带参数）
        symbol = SymbolNode(
            uid=1,
            symbol_name="计算总价",
            normalized_name="",
            visibility=VisibilityTypes.DEFAULT,
            description="计算订单总价",
            symbol_type=SymbolType.FUNCTION,
            parameters={"商品列表": "商品数组", "折扣率": "0-1之间的小数"}
        )
        
        assert not symbol.is_normalized(), "新创建的符号应该未规范化"
        
        # 规范化
        symbol.update_normalized_info_from_str("CalculateTotal", "public")
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


def test_symbol_reference_basics():
    """测试SymbolReference基本功能"""
    print("=" * 60)
    print("测试 SymbolReference 基本功能")
    print("=" * 60)
    
    try:
        # 创建引用
        ref = SymbolReference(
            ref_symbol_name="json.dumps",
            ref_type=ReferenceType.BEHAVIOR_REF,
            source_uid=10,
            line_number=5,
            context="调用 json.dumps(data)"
        )
        
        # 序列化/反序列化
        ref_dict = ref.to_dict()
        ref2 = SymbolReference.from_dict(ref_dict)
        
        assert ref2.ref_symbol_name == ref.ref_symbol_name
        assert ref2.ref_type == ref.ref_type
        assert ref2.source_uid == ref.source_uid
        
        print("\n[通过] SymbolReference 基本功能测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_symbol_table_basics():
    """测试FileSymbolTable基本功能"""
    print("=" * 60)
    print("测试 FileSymbolTable 基本功能")
    print("=" * 60)
    
    try:
        table = FileSymbolTable()
        
        # 添加符号
        symbol1 = SymbolNode(
            uid=1, symbol_name="UserManager",
            symbol_type=SymbolType.CLASS, description="用户管理类"
        )
        table.add_symbol(symbol1)
        
        # 添加引用
        ref1 = SymbolReference(
            ref_symbol_name="BaseManager",
            ref_type=ReferenceType.CLASS_INHERIT,
            source_uid=1, line_number=1
        )
        table.add_reference(ref1)
        
        # 验证
        assert table.has_symbol("UserManager")
        assert len(table.symbol_references) == 1
        
        # 序列化/反序列化
        table_dict = table.to_dict()
        table2 = FileSymbolTable.from_dict(table_dict)
        
        assert len(table2.symbols) == 1
        assert len(table2.symbol_references) == 1
        
        print("\n[通过] FileSymbolTable 基本功能测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 符号提取测试 ====================

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
        
        all_symbols = symbol_table.get_all_symbols()
        
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
        
        func1 = symbol_table.get_symbol("计算总价")
        func2 = symbol_table.get_symbol("登录")
        
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
        
        all_symbols = symbol_table.get_all_symbols()
        
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


# ==================== 符号引用提取测试 ====================

def test_behavior_references_extraction():
    """测试行为引用提取"""
    print("=" * 60)
    print("测试行为引用提取")
    print("=" * 60)
    
    code = """class UserManager():
    func 添加用户(用户名, 密码):
        验证 $用户名$ 和 $密码$ 格式
        调用 $数据库.插入$($用户数据$)
        返回成功"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        behavior_refs = symbol_table.get_references_by_type(ReferenceType.BEHAVIOR_REF)
        
        ref_names = [ref.ref_symbol_name for ref in behavior_refs]
        assert "用户名" in ref_names
        assert "密码" in ref_names
        assert "数据库.插入" in ref_names
        assert "用户数据" in ref_names
        
        print(f"\n行为引用数: {len(behavior_refs)}")
        print(f"引用列表: {ref_names}")
        print("\n[通过] 行为引用提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_references_extraction():
    """测试模块引用提取"""
    print("=" * 60)
    print("测试模块引用提取")
    print("=" * 60)
    
    code = """module json: JSON处理库
module requests: HTTP请求库
module threading: 线程支持

class DataProcessor():
    func 处理数据():
        执行处理"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        module_refs = symbol_table.get_references_by_type(ReferenceType.MODULE_CALL)
        
        assert len(module_refs) == 3
        ref_names = [ref.ref_symbol_name for ref in module_refs]
        assert "json" in ref_names
        assert "requests" in ref_names
        assert "threading" in ref_names
        
        print(f"\n模块引用数: {len(module_refs)}")
        print("\n[通过] 模块引用提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_inheritance_references_extraction():
    """测试类继承引用提取"""
    print("=" * 60)
    print("测试类继承引用提取")
    print("=" * 60)
    
    code = """class UserManager(BaseManager: 基础管理器):
    func 添加用户():
        执行添加

class AdminManager(UserManager: 用户管理器):
    func 删除用户():
        执行删除"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbol_table = symbol_gen.process_symbols()
        
        inherit_refs = symbol_table.get_references_by_type(ReferenceType.CLASS_INHERIT)
        
        assert len(inherit_refs) == 2
        ref_names = [ref.ref_symbol_name for ref in inherit_refs]
        assert "BaseManager" in ref_names
        assert "UserManager" in ref_names
        
        print(f"\n继承引用数: {len(inherit_refs)}")
        print("\n[通过] 类继承引用提取测试通过\n")
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
        table_dict = symbol_table.to_dict()
        
        # 反序列化
        restored_table = FileSymbolTable.from_dict(table_dict)
        
        # 验证
        assert len(restored_table.symbols) == len(symbol_table.symbols)
        assert len(restored_table.symbol_references) == len(symbol_table.symbol_references)
        
        # 验证符号
        for name in symbol_table.symbols.keys():
            original = symbol_table.get_symbol(name)
            restored = restored_table.get_symbol(name)
            assert original.uid == restored.uid
            assert original.symbol_type == restored.symbol_type
        
        # 验证引用
        for orig_ref, rest_ref in zip(symbol_table.symbol_references, restored_table.symbol_references):
            assert orig_ref.ref_symbol_name == rest_ref.ref_symbol_name
            assert orig_ref.ref_type == rest_ref.ref_type
        
        print(f"\n符号数: {len(table_dict['symbols'])}")
        print(f"引用数: {len(table_dict['symbol_references'])}")
        print("\n[通过] 符号表序列化测试通过\n")
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
        
        all_symbols = symbol_table.get_all_symbols()
        print(f"  提取符号数: {len(all_symbols)}")
        print(f"  提取引用数: {len(symbol_table.symbol_references)}")
        
        # 步骤2: 验证初始状态
        print("\n步骤2: 验证符号初始状态...")
        unnormalized = symbol_table.get_unnormalized_symbols()
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
        
        for symbol_name, (normalized_name, visibility) in normalization_map.items():
            symbol = symbol_table.get_symbol(symbol_name)
            if symbol:
                symbol.update_normalized_info_from_str(normalized_name, visibility)
                print(f"  - {symbol_name} -> {normalized_name} ({visibility})")
        
        # 步骤4: 验证规范化结果
        print("\n步骤4: 验证规范化结果...")
        unnormalized_after = symbol_table.get_unnormalized_symbols()
        print(f"  未规范化符号: {len(unnormalized_after)}/{len(all_symbols)}")
        assert len(unnormalized_after) == 0, "所有符号都应已规范化"
        
        # 步骤5: 序列化
        print("\n步骤5: 序列化符号表...")
        table_dict = symbol_table.to_dict()
        print(f"  序列化完成，符号数: {len(table_dict['symbols'])}, 引用数: {len(table_dict['symbol_references'])}")
        
        # 步骤6: 反序列化并验证
        print("\n步骤6: 反序列化并验证...")
        restored_table = FileSymbolTable.from_dict(table_dict)
        
        for symbol_name in all_symbols.keys():
            original = symbol_table.get_symbol(symbol_name)
            restored = restored_table.get_symbol(symbol_name)
            
            if original and restored:
                assert restored.is_normalized() or original.is_normalized() == False
                if original.is_normalized():
                    assert original.normalized_name == restored.normalized_name
                    assert original.visibility == restored.visibility
        
        print("  数据一致性验证通过")
        
        # 验证引用
        module_refs = symbol_table.get_references_by_type(ReferenceType.MODULE_CALL)
        class_refs = symbol_table.get_references_by_type(ReferenceType.CLASS_INHERIT)
        behavior_refs = symbol_table.get_references_by_type(ReferenceType.BEHAVIOR_REF)
        
        print(f"\n引用统计:")
        print(f"  模块调用: {len(module_refs)}")
        print(f"  类继承: {len(class_refs)}")
        print(f"  行为引用: {len(behavior_refs)}")
        
        # 验证函数参数
        login_func = symbol_table.get_symbol("登录")
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
            ("SymbolReference基本功能", test_symbol_reference_basics),
            ("FileSymbolTable基本功能", test_file_symbol_table_basics),
        ]),
        ("符号提取测试", [
            ("基本符号提取", test_basic_symbol_extraction),
            ("函数参数提取", test_function_parameters_extraction),
            ("类成员符号提取", test_class_with_members_extraction),
        ]),
        ("符号引用提取测试", [
            ("行为引用提取", test_behavior_references_extraction),
            ("模块引用提取", test_module_references_extraction),
            ("类继承引用提取", test_class_inheritance_references_extraction),
        ]),
        ("序列化与集成测试", [
            ("符号表序列化", test_symbol_table_serialization),
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
