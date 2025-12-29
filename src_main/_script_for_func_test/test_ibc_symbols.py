"""IBC符号系统完整测试套件

测试范围：
1. 符号树/元数据构建
2. 函数参数存储
3. 符号表序列化/反序列化（基于元数据）
4. 符号规范化流程（基于元数据）
"""
import sys
import os
import json
from typing import Dict, Any

# 添加src_main目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser
from utils.ibc_analyzer.ibc_symbol_processor import IbcSymbolProcessor
from typedef.ibc_data_types import (
    VisibilityTypes
)

# ==================== 数据类型基础测试 ======================================

# ==================== 符号提取测试（基于符号树/元数据） ====================

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
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 验证符号：仅检查元数据中的名字集合
        symbol_names = {path.split('.')[-1] for path, meta in symbols_metadata.items() if meta.get("type") in ("class", "func", "var")}
        
        assert "userCount" in symbol_names
        assert "计算总价" in symbol_names
        assert "UserManager" in symbol_names
        assert "users" in symbol_names
        assert "添加用户" in symbol_names
        
        print(f"\n提取符号数: {len(symbol_names)}")
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
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 根据元数据查找函数
        func1_meta = None
        func2_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "计算总价" and meta.get("type") == "func":
                func1_meta = meta
            if name == "登录" and meta.get("type") == "func":
                func2_meta = meta
        
        assert func1_meta is not None
        assert func2_meta is not None
        
        # 验证参数
        params1 = func1_meta.get("parameters", {})
        params2 = func2_meta.get("parameters", {})
        assert len(params1) == 3
        assert "商品列表" in params1
        assert params1["折扣率"] == "0到1之间的小数"
        
        assert len(params2) == 2
        assert params2["用户名"] == "登录用户名"
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
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 验证类和成员
        class_meta = None
        config_data_meta = None
        config_path_meta = None
        load_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split('.')[-1]
            if name == "ConfigManager" and meta.get("type") == "class":
                class_meta = meta
            if name == "configData" and meta.get("type") == "var":
                config_data_meta = meta
            if name == "configPath" and meta.get("type") == "var":
                config_path_meta = meta
            if name == "加载配置" and meta.get("type") == "func":
                load_meta = meta
        
        assert class_meta is not None
        assert class_meta.get("description") == "配置管理器"
        assert config_data_meta is not None
        assert config_path_meta is not None
        assert load_meta is not None
        assert load_meta.get("description") == "加载配置"
        # 字段变量应标记为 field 作用域
        assert config_data_meta.get("scope") == "field"
        assert config_path_meta.get("scope") == "field"
        
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
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 序列化
        # 这里只测试元数据的序列化/反序列化
        table_dict = symbols_metadata
        
        # 反序列化
        restored_table: Dict[str, Dict[str, Any]] = json.loads(json.dumps(table_dict))
        
        # 验证
        assert len(restored_table) == len(symbols_metadata)
        
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
    """测试符号层次结构（基于符号树和元数据）"""
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
        symbols_tree, symbols_metadata = symbol_processor.build_symbol_tree()
        
        print(f"\n提取的符号数量: {len(symbols_metadata)}")
        
        # 1. 验证类符号存在
        user_manager_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "UserManager" and meta.get("type") == "class":
                user_manager_meta = meta
                break
        if not user_manager_meta:
            print("\n✗ 未找到UserManager类")
            return False
        print("  ✓ 找到 UserManager 类元数据")
        
        # 2. 验证类成员（2个变量 + 2个方法）
        expected_children = {"userList", "sessionStore", "添加用户", "删除用户"}
        actual_children_in_tree = set(symbols_tree.get("UserManager", {}).keys())
        print(f"\nUserManager 子节点(来自符号树): {actual_children_in_tree}")
        if actual_children_in_tree != expected_children:
            print(f"✗ UserManager 子符号集合不匹配\n  期望: {expected_children}\n  实际: {actual_children_in_tree}")
            return False
        print("  ✓ UserManager 的子符号结构正确")
        
        # 3. 验证成员符号的元数据存在且作用域正确
        user_list_meta = None
        session_store_meta = None
        add_user_meta = None
        delete_user_meta = None
        global_func_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "userList" and meta.get("type") == "var":
                user_list_meta = meta
            elif name == "sessionStore" and meta.get("type") == "var":
                session_store_meta = meta
            elif name == "添加用户" and meta.get("type") == "func":
                add_user_meta = meta
            elif name == "删除用户" and meta.get("type") == "func":
                delete_user_meta = meta
            elif name == "全局函数" and meta.get("type") == "func":
                global_func_meta = meta
        
        if not (user_list_meta and session_store_meta and add_user_meta and delete_user_meta):
            print("\n✗ UserManager 的成员符号元数据不完整")
            return False
        print("  ✓ UserManager 成员符号元数据完整")
        
        # 字段变量应标记为 field 作用域
        assert user_list_meta.get("scope") == "field"
        assert session_store_meta.get("scope") == "field"
        print("  ✓ 字段变量作用域为 field")
        
        # 全局函数应存在于元数据中
        if not global_func_meta:
            print("\n✗ 未找到全局函数的元数据")
            return False
        print("  ✓ 全局函数元数据存在")
        
        print("\n[通过] 符号层次结构测试通过\n")
        return True
        
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==================== 集成测试 ====================

def test_complete_workflow():
    """完整工作流程测试：提取、规范化、序列化（基于符号元数据）"""
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
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        print(f"  提取符号数: {len(symbols_metadata)}")
        
        # 步骤2: 验证关键符号是否存在
        print("\n步骤2: 验证关键符号是否存在...")
        required_names = {"UserService", "sessionStore", "登录", "登出"}
        existing_names = {path.split(".")[-1] for path in symbols_metadata.keys()}
        missing = required_names - existing_names
        if missing:
            print(f"✗ 缺少符号: {missing}")
            return False
        print("  ✓ 关键符号均已提取")
        
        # 步骤3: 模拟AI规范化（在元数据上写入 normalized_name 字段）
        print("\n步骤3: 模拟AI规范化符号...")
        normalization_map = {
            "UserService": "UserService",
            "sessionStore": "SessionStore",
            "登录": "Login",
            "登出": "Logout",
        }
        
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name in normalization_map:
                meta["normalized_name"] = normalization_map[name]
                print(f"  - {name} -> {normalization_map[name]}")
        
        # 步骤4: 验证规范化结果
        print("\n步骤4: 验证规范化结果...")
        for name, normalized in normalization_map.items():
            matched = False
            for path, meta in symbols_metadata.items():
                if path.split(".")[-1] == name and meta.get("type") in ("class", "func", "var"):
                    assert meta.get("normalized_name") == normalized
                    matched = True
                    break
            if not matched:
                print(f"✗ 未找到需要验证规范化结果的符号: {name}")
                return False
        print("  ✓ 所有目标符号的规范化名称已写入元数据")
        
        # 步骤5: 序列化/反序列化并验证
        print("\n步骤5: 序列化符号元数据并验证...")
        table_dict = symbols_metadata
        serialized = json.dumps(table_dict, ensure_ascii=False)
        restored_table: Dict[str, Dict[str, Any]] = json.loads(serialized)
        
        for path, meta in restored_table.items():
            if path in symbols_metadata and "normalized_name" in symbols_metadata[path]:
                assert meta.get("normalized_name") == symbols_metadata[path].get("normalized_name")
        print("  数据一致性验证通过")
        
        print("\n[通过] 完整工作流程测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_visibility_from_ast():
    """测试可见性从 AST 节点直接填充"""
    print("=" * 60)
    print("测试可见性从 AST 填充")
    print("=" * 60)
    
    code = """class DataProcessor():
    private
    var _buffer: 缓冲区
    
    protected
    func _process():
        执行内部处理
    
    public
    func process():
        调用内部处理
"""
    
    try:
        # 解析代码
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        # 提取符号
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 验证可见性已经从 AST 填充
        print("\n验证符号可见性:")
        # 1. 类本身存在
        assert any(path.split(".")[-1] == "DataProcessor" for path in symbols_metadata.keys())
        print("  ✓ DataProcessor 存在于符号元数据中")
        
        # 2. 验证字段和方法的可见性
        buffer_meta = None
        internal_func_meta = None
        public_func_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "_buffer" and meta.get("type") == "var":
                buffer_meta = meta
            elif name == "_process" and meta.get("type") == "func":
                internal_func_meta = meta
            elif name == "process" and meta.get("type") == "func":
                public_func_meta = meta
        
        assert buffer_meta is not None
        assert internal_func_meta is not None
        assert public_func_meta is not None
        
        # 字段变量应为 private 且 scope=field
        assert buffer_meta.get("visibility") == VisibilityTypes.PRIVATE.value
        assert buffer_meta.get("scope") == "field"
        # 受保护方法
        assert internal_func_meta.get("visibility") == VisibilityTypes.PROTECTED.value
        # 公共方法
        assert public_func_meta.get("visibility") == VisibilityTypes.PUBLIC.value
        print("  ✓ 字段和方法的可见性从 AST 正确填充")
        
        print("\n[通过] 可见性从 AST 正确填充\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_local_variable_scope_and_name_collision():
    """测试不同函数中同名局部变量的作用域和路径"""
    print("=" * 60)
    print("测试同名局部变量作用域和路径")
    print("=" * 60)
    
    code = """class BoundaryDetector():
    func 检测碰撞():
        var 法向量: 检测用局部法向量
    
    func 计算法向量():
        var 法向量: 计算用局部法向量"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 查找所有名为"法向量"、类型为变量的条目
        local_vars = []
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "法向量" and meta.get("type") == "var":
                local_vars.append((path, meta))
        
        # 应该找到两个局部变量，且路径不同
        assert len(local_vars) == 2
        paths = {p for p, _ in local_vars}
        assert len(paths) == 2
        
        # 所有"法向量"都应标记为 scope=local
        for path, meta in local_vars:
            assert meta.get("scope") == "local"
        
        # 不应存在平铺键 "法向量"（避免全局名冲突）
        assert "法向量" not in symbols_metadata
        
        print("\n[通过] 同名局部变量作用域与路径测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_visibility_scopes():
    """测试嵌套的可见性作用域：多个可见性声明的交替使用"""
    print("=" * 60)
    print("测试嵌套可见性作用域")
    print("=" * 60)
    
    code = """class DataProcessor():
    public
    var publicData: 公开数据
    
    func publicMethod():
        执行公开操作
    
    private
    var _internalBuffer: 内部缓冲区
    var _tempCache: 临时缓存
    
    func _internalProcess():
        执行内部处理
    
    protected
    var _protectedState: 受保护状态
    
    func _protectedHelper():
        执行受保护辅助操作
    
    public
    func anotherPublicMethod():
        执行另一个公开操作
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 验证公开成员
        public_members = []
        private_members = []
        protected_members = []
        
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            visibility = meta.get("visibility")
            symbol_type = meta.get("type")
            
            if symbol_type in ("var", "func"):
                if visibility == VisibilityTypes.PUBLIC.value:
                    public_members.append(name)
                elif visibility == VisibilityTypes.PRIVATE.value:
                    private_members.append(name)
                elif visibility == VisibilityTypes.PROTECTED.value:
                    protected_members.append(name)
        
        # 验证公开成员
        assert "publicData" in public_members
        assert "publicMethod" in public_members
        assert "anotherPublicMethod" in public_members
        print(f"  ✓ 公开成员正确: {len(public_members)} 个")
        
        # 验证私有成员
        assert "_internalBuffer" in private_members
        assert "_tempCache" in private_members
        assert "_internalProcess" in private_members
        print(f"  ✓ 私有成员正确: {len(private_members)} 个")
        
        # 验证受保护成员
        assert "_protectedState" in protected_members
        assert "_protectedHelper" in protected_members
        print(f"  ✓ 受保护成员正确: {len(protected_members)} 个")
        
        print("\n[通过] 嵌套可见性作用域测试通过\n")
        return True
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_inheritance_symbols():
    """测试多重继承的符号提取（注：IBC语法实际不支持多重继承，此处测试单继承链）"""
    print("=" * 60)
    print("测试继承符号提取")
    print("=" * 60)
    
    # IBC语法不支持多重继承，此处测试继承链
    code = """class Base():
    var base_data: 基类数据

class Derived($Base: 继承基类):
    var derived_data: 派生类数据
    
    func process():
        处理数据
"""
    
    try:
        lexer = IbcLexer(code)
        tokens = lexer.tokenize()
        parser = IbcParser(tokens)
        ast_dict = parser.parse()
        
        symbol_gen = IbcSymbolProcessor(ast_dict)
        symbols_tree, symbols_metadata = symbol_gen.build_symbol_tree()
        
        # 找到类节点
        base_class_meta = None
        derived_class_meta = None
        for path, meta in symbols_metadata.items():
            name = path.split(".")[-1]
            if name == "Base" and meta.get("type") == "class":
                base_class_meta = meta
            elif name == "Derived" and meta.get("type") == "class":
                derived_class_meta = meta
        
        assert base_class_meta is not None, "未找到Base类"
        assert derived_class_meta is not None, "未找到Derived类"
        
        print(f"  ✓ 基类和派生类节点已提取")
        
        # 验证类成员也正确提取
        base_member_names = []
        derived_member_names = []
        for path, meta in symbols_metadata.items():
            if "Base." in path and "." in path:
                base_member_names.append(path.split(".")[-1])
            elif "Derived." in path and "." in path:
                derived_member_names.append(path.split(".")[-1])
        
        assert "base_data" in base_member_names
        assert "derived_data" in derived_member_names
        assert "process" in derived_member_names
        print(f"  ✓ 基类成员: {base_member_names}")
        print(f"  ✓ 派生类成员: {derived_member_names}")
        
        print("\n[通过] 继承符号提取测试通过\n")
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
        ("符号提取测试", [
            ("基本符号提取", test_basic_symbol_extraction),
            ("函数参数提取", test_function_parameters_extraction),
            ("类成员符号提取", test_class_with_members_extraction),
            ("同名局部变量作用域", test_local_variable_scope_and_name_collision),
            ("嵌套可见性作用域", test_nested_visibility_scopes),
            ("继承符号提取", test_multiple_inheritance_symbols),
        ]),
        ("序列化与集成测试", [
            ("符号表序列化", test_symbol_table_serialization),
            ("符号层次结构", test_symbol_hierarchy),
            ("完整工作流程", test_complete_workflow),
            ("可见性AST填充", test_visibility_from_ast),
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
