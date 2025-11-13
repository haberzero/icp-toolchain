"""
测试 IbcSymbolGenerator 符号生成器
从AST中提取符号信息，验证符号表的生成是否正确
"""
import sys
import os

# 添加src_main目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_gen import IbcSymbolGenerator
from typedef.ibc_data_types import (
    SymbolNode, SymbolType, FileSymbolTable,
    ClassNode, FunctionNode, VariableNode
)


def test_basic_symbol_extraction():
    """测试基本符号提取功能"""
    print("=" * 60)
    print("测试基本符号提取")
    print("=" * 60)
    
    code = """module requests: Python第三方HTTP请求库
var userCount: 当前在线用户数量

func 计算总价(商品列表, 折扣率):
    初始化 总价 = 0
    返回 总价

class UserManager():
    var users: 用户数据字典
    
    func 添加用户(用户名, 密码):
        验证用户信息"""
    
    try:
        # 1. 解析IBC代码生成AST
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 2. 使用符号生成器提取符号
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        # 3. 验证符号表
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        print("\n符号列表:")
        for name, symbol in all_symbols.items():
            print(f"  - {name}: {symbol.symbol_type.value} (uid={symbol.uid})")
            if symbol.description:
                print(f"    描述: {symbol.description}")
        
        # 验证具体符号
        assert "userCount" in all_symbols, "缺少变量 userCount"
        assert "计算总价" in all_symbols, "缺少函数 计算总价"
        assert "UserManager" in all_symbols, "缺少类 UserManager"
        assert "users" in all_symbols, "缺少成员变量 users"
        assert "添加用户" in all_symbols, "缺少成员方法 添加用户"
        
        # 验证符号类型
        assert all_symbols["userCount"].symbol_type == SymbolType.VARIABLE
        assert all_symbols["计算总价"].symbol_type == SymbolType.FUNCTION
        assert all_symbols["UserManager"].symbol_type == SymbolType.CLASS
        
        # 验证未规范化状态（normalized_name和visibility应该为空）
        for symbol in all_symbols.values():
            assert symbol.normalized_name == "", f"符号 {symbol.symbol_name} 的 normalized_name 应该为空"
            assert symbol.visibility == None, f"符号 {symbol.symbol_name} 的 visibility 应该为空"
            assert not symbol.is_normalized(), f"符号 {symbol.symbol_name} 不应该已规范化"
        
        print("\n✓ 基本符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_class_with_members():
    """测试类及其成员的符号提取"""
    print("=" * 60)
    print("测试类成员符号提取")
    print("=" * 60)
    
    code = """description: 线程安全的配置管理器
@ 所有公共方法都保证线程安全
class ConfigManager():
    var configData: 当前配置数据
    var configPath: 主配置文件路径
    var rwLock: 读写锁对象
    
    description: 初始化配置管理器
    func __init__(配置文件路径):
        self.configPath = 配置文件路径
        self.加载配置()
    
    description: 从文件加载配置数据
    @ 使用JSON格式解析
    func 加载配置():
        文件内容 = 读取文件(self.configPath)"""
    
    try:
        # 解析并提取符号
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        print("\n符号列表:")
        for name, symbol in all_symbols.items():
            print(f"  - {name}: {symbol.symbol_type.value}")
            if symbol.description:
                print(f"    描述: {symbol.description}")
        
        # 验证类符号
        assert "ConfigManager" in all_symbols, "缺少类 ConfigManager"
        class_symbol = all_symbols["ConfigManager"]
        assert class_symbol.symbol_type == SymbolType.CLASS
        assert class_symbol.description == "线程安全的配置管理器", "类描述不匹配"
        
        # 验证成员变量
        expected_vars = ["configData", "configPath", "rwLock"]
        for var_name in expected_vars:
            assert var_name in all_symbols, f"缺少成员变量 {var_name}"
            assert all_symbols[var_name].symbol_type == SymbolType.VARIABLE
        
        # 验证成员方法
        expected_funcs = ["__init__", "加载配置"]
        for func_name in expected_funcs:
            assert func_name in all_symbols, f"缺少成员方法 {func_name}"
            assert all_symbols[func_name].symbol_type == SymbolType.FUNCTION
        
        # 验证方法描述
        assert all_symbols["__init__"].description == "初始化配置管理器"
        assert all_symbols["加载配置"].description == "从文件加载配置数据"
        
        print("\n✓ 类成员符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complex_code_symbols():
    """测试复杂代码的符号提取"""
    print("=" * 60)
    print("测试复杂代码符号提取")
    print("=" * 60)
    
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
        # 解析并提取符号
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        print("\n符号分类统计:")
        
        # 统计各类符号数量
        symbol_count = {
            SymbolType.CLASS: 0,
            SymbolType.FUNCTION: 0,
            SymbolType.VARIABLE: 0
        }
        
        for symbol in all_symbols.values():
            symbol_count[symbol.symbol_type] += 1
        
        print(f"  类: {symbol_count[SymbolType.CLASS]}")
        print(f"  函数: {symbol_count[SymbolType.FUNCTION]}")
        print(f"  变量: {symbol_count[SymbolType.VARIABLE]}")
        
        # 详细列表
        print("\n详细符号列表:")
        for stype in [SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.VARIABLE]:
            symbols_of_type = [(name, s) for name, s in all_symbols.items() if s.symbol_type == stype]
            if symbols_of_type:
                print(f"\n  {stype.value}:")
                for name, symbol in symbols_of_type:
                    desc_preview = symbol.description[:40] + "..." if len(symbol.description) > 40 else symbol.description
                    print(f"    - {name}: {desc_preview if desc_preview else '(无描述)'}")
        
        # 验证预期符号数量
        assert symbol_count[SymbolType.CLASS] == 1, f"预期1个类，实际{symbol_count[SymbolType.CLASS]}"
        assert symbol_count[SymbolType.FUNCTION] == 2, f"预期2个函数，实际{symbol_count[SymbolType.FUNCTION]}"
        assert symbol_count[SymbolType.VARIABLE] == 3, f"预期3个变量，实际{symbol_count[SymbolType.VARIABLE]}"
        
        # 验证所有符号都未规范化
        unnormalized = symbol_table.get_unnormalized_symbols()
        assert len(unnormalized) == len(all_symbols), \
            f"所有符号都应该未规范化，但有 {len(all_symbols) - len(unnormalized)} 个已规范化"
        
        print("\n✓ 复杂代码符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbol_with_inheritance():
    """测试带继承的类符号提取"""
    print("=" * 60)
    print("测试继承类符号提取")
    print("=" * 60)
    
    code = """class UserManager(BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典
    
    description: 添加新用户到系统
    func 添加用户(用户名, 密码):
        验证 用户名 和 密码 格式
        创建新用户对象
        self.users[用户名] = 新用户"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        for name, symbol in all_symbols.items():
            print(f"  - {name}: {symbol.symbol_type.value}")
        
        # 验证类符号
        assert "UserManager" in all_symbols, "缺少类 UserManager"
        # 注意：继承信息存储在AST的ClassNode中，不在SymbolNode中
        # 符号表只记录符号的基本信息
        
        # 验证成员
        assert "users" in all_symbols, "缺少成员变量 users"
        assert "添加用户" in all_symbols, "缺少成员方法 添加用户"
        
        print("\n✓ 继承类符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiline_function_symbols():
    """测试多行函数声明的符号提取"""
    print("=" * 60)
    print("测试多行函数符号提取")
    print("=" * 60)
    
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

description: 验证用户登录凭据
func 验证登录(用户名: 用户登录名, 密码: 用户密码):
    查找用户
    验证密码哈希"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        for name, symbol in all_symbols.items():
            print(f"  - {name}: {symbol.symbol_type.value}")
            if symbol.description:
                print(f"    描述: {symbol.description}")
        
        # 验证函数符号
        assert "计算订单总价" in all_symbols, "缺少函数 计算订单总价"
        assert "验证登录" in all_symbols, "缺少函数 验证登录"
        
        # 验证类型和描述
        assert all_symbols["计算订单总价"].symbol_type == SymbolType.FUNCTION
        assert all_symbols["验证登录"].symbol_type == SymbolType.FUNCTION
        assert all_symbols["验证登录"].description == "验证用户登录凭据"
        
        print("\n✓ 多行函数符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbol_table_serialization():
    """测试符号表的序列化和反序列化"""
    print("=" * 60)
    print("测试符号表序列化")
    print("=" * 60)
    
    code = """class DataProcessor():
    var cache: 数据缓存
    
    func 处理数据(输入数据):
        执行处理逻辑"""
    
    try:
        # 生成符号表
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        symbol_table.file_md5 = "test_md5_12345"
        
        # 转换为字典
        table_dict = symbol_table.to_dict()
        print(f"\n序列化后的字典:")
        print(f"  MD5: {table_dict['md5']}")
        print(f"  符号数量: {len(table_dict['symbols'])}")
        
        # 从字典恢复
        restored_table = FileSymbolTable.from_dict(table_dict)
        print(f"\n反序列化后:")
        print(f"  MD5: {restored_table.file_md5}")
        print(f"  符号数量: {len(restored_table.symbols)}")
        
        # 验证数据一致性
        assert restored_table.file_md5 == symbol_table.file_md5, "MD5不匹配"
        assert len(restored_table.symbols) == len(symbol_table.symbols), "符号数量不匹配"
        
        for name in symbol_table.symbols.keys():
            original = symbol_table.get_symbol(name)
            restored = restored_table.get_symbol(name)
            
            assert original is not None, f"原始符号 {name} 不应为 None"
            assert restored is not None, f"恢复后缺少符号 {name}"
            assert original.uid == restored.uid, f"{name} 的 uid 不匹配"
            assert original.symbol_name == restored.symbol_name, f"{name} 的 symbol_name 不匹配"
            assert original.description == restored.description, f"{name} 的 description 不匹配"
            assert original.symbol_type == restored.symbol_type, f"{name} 的 symbol_type 不匹配"
        
        print("\n✓ 符号表序列化测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_normalization():
    """集成测试：模拟完整的符号提取和规范化流程"""
    print("=" * 60)
    print("集成测试：符号提取与规范化")
    print("=" * 60)
    
    code = """description: 用户认证服务
class AuthService():
    var sessionStore: 会话存储
    
    description: 用户登录
    func login(username, password):
        验证凭据
        创建会话
    
    description: 用户登出
    func logout(sessionId):
        清除会话"""
    
    try:
        # 1. 解析并生成符号表
        print("\n步骤1: 解析IBC代码并提取符号...")
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        print(f"  提取了 {len(all_symbols)} 个符号")
        
        # 2. 验证所有符号都未规范化
        print("\n步骤2: 验证符号初始状态（未规范化）...")
        unnormalized = symbol_table.get_unnormalized_symbols()
        print(f"  未规范化符号: {len(unnormalized)}/{len(all_symbols)}")
        assert len(unnormalized) == len(all_symbols), "所有符号应该都未规范化"
        
        # 3. 模拟AI规范化过程
        print("\n步骤3: 模拟AI规范化符号...")
        normalization_map = {
            "AuthService": ("AuthService", "public"),
            "sessionStore": ("sessionStore", "private"),
            "login": ("Login", "public"),
            "logout": ("Logout", "public")
        }
        
        for symbol_name, (normalized_name, visibility) in normalization_map.items():
            symbol = symbol_table.get_symbol(symbol_name)
            if symbol:
                symbol.update_normalized_info(normalized_name, visibility)
                print(f"  - {symbol_name} -> {normalized_name} ({visibility})")
        
        # 4. 验证规范化结果
        print("\n步骤4: 验证规范化结果...")
        unnormalized_after = symbol_table.get_unnormalized_symbols()
        print(f"  未规范化符号: {len(unnormalized_after)}/{len(all_symbols)}")
        assert len(unnormalized_after) == 0, "所有符号都应该已规范化"
        
        # 5. 序列化保存
        print("\n步骤5: 序列化符号表...")
        symbol_table.file_md5 = "integration_test_md5"
        table_dict = symbol_table.to_dict()
        print(f"  序列化完成，包含 {len(table_dict['symbols'])} 个符号")
        
        # 6. 反序列化并验证
        print("\n步骤6: 反序列化并验证...")
        restored_table = FileSymbolTable.from_dict(table_dict)
        
        for symbol_name in all_symbols.keys():
            original = symbol_table.get_symbol(symbol_name)
            restored = restored_table.get_symbol(symbol_name)
            
            assert original is not None, f"原始符号 {symbol_name} 不应为 None"
            assert restored is not None, f"恢复后符号 {symbol_name} 不应为 None"
            assert restored.is_normalized(), f"恢复后符号 {symbol_name} 应该是已规范化的"
            assert original.normalized_name == restored.normalized_name, \
                f"{symbol_name} 的 normalized_name 不一致"
            assert original.visibility == restored.visibility, \
                f"{symbol_name} 的 visibility 不一致"
        
        print("  数据一致性验证通过")
        
        print("\n✓ 集成测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_description_symbols():
    """测试没有描述的符号提取"""
    print("=" * 60)
    print("测试无描述符号提取")
    print("=" * 60)
    
    code = """var data1, data2, data3

class SimpleClass():
    func simpleFunc(param1, param2):
        执行操作"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolGenerator(ast_dict)
        symbol_table = symbol_gen.extract_symbols()
        
        all_symbols = symbol_table.get_all_symbols()
        
        print(f"\n提取的符号数量: {len(all_symbols)}")
        for name, symbol in all_symbols.items():
            desc = symbol.description if symbol.description else "(无描述)"
            print(f"  - {name}: {symbol.symbol_type.value} - {desc}")
        
        # 验证符号存在
        expected_symbols = ["data1", "data2", "data3", "SimpleClass", "simpleFunc"]
        for sym_name in expected_symbols:
            assert sym_name in all_symbols, f"缺少符号 {sym_name}"
        
        # 验证空描述
        for sym_name in ["data1", "data2", "data3"]:
            assert all_symbols[sym_name].description == "", \
                f"{sym_name} 的描述应该为空字符串"
        
        print("\n✓ 无描述符号提取测试通过\n")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("开始测试 IbcSymbolGenerator 符号生成器")
    print("=" * 60)
    
    try:
        test_results = []
        
        test_results.append(("基本符号提取", test_basic_symbol_extraction()))
        test_results.append(("类成员符号提取", test_class_with_members()))
        test_results.append(("复杂代码符号提取", test_complex_code_symbols()))
        test_results.append(("继承类符号提取", test_symbol_with_inheritance()))
        test_results.append(("多行函数符号提取", test_multiline_function_symbols()))
        test_results.append(("符号表序列化", test_symbol_table_serialization()))
        test_results.append(("集成测试", test_integration_with_normalization()))
        test_results.append(("无描述符号提取", test_empty_description_symbols()))
        
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
