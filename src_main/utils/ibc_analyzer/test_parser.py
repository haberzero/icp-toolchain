import sys
import os

# 添加当前目录到路径，确保可以导入 parser 和 lexer
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import parse_ibc_code


def test_simple_module():
    """测试简单模块解析"""
    code = """module requests: Python第三方HTTP请求库
module threading: 系统线程库
module utils"""
    
    ast = parse_ibc_code(code)
    print("Simple module test:")
    print(f"AST nodes count: {len(ast)}")
    for uid, node in ast.items():
        print(f"  {uid}: {node}")
    print()


def test_function_with_params():
    """测试带参数的函数"""
    code = """\
func 计算订单总价(商品列表: 包含价格信息的商品对象数组, 折扣率: 0到1之间的小数):
    初始化 总价 = 0
    遍历 商品列表 中的每个 商品:
        总价 = 总价 + 商品.价格
    总价 = 总价 × 折扣率
    返回 总价"""
    
    ast = parse_ibc_code(code)
    print("Function with params test:")
    print(f"AST nodes count: {len(ast)}")
    for uid, node in ast.items():
        print(f"  {uid}: {node}")
    print()


def test_class_with_inheritance():
    """测试带继承的类"""
    code = """class UserManager(BaseManager: 使用公共基类管理生命周期):
    var users: 用户数据字典
    var dbConnection: 数据库连接对象
    
    func 添加用户(用户名, 密码: 经过哈希处理的密码字符串):
        验证 用户名 和 密码 格式
        创建新用户对象
        将用户保存到数据库
        返回 操作结果"""
    
    ast = parse_ibc_code(code)
    print("Class with inheritance test:")
    print(f"AST nodes count: {len(ast)}")
    for uid, node in ast.items():
        print(f"  {uid}: {node}")
    print()


def test_description_and_intent():
    """测试描述和意图注释"""
    code = """description: 处理用户登录请求，验证凭据并返回认证结果
@ 线程安全设计，所有公共方法都内置锁机制
class AuthService():"""
    
    ast = parse_ibc_code(code)
    print("Description and intent test:")
    print(f"AST nodes count: {len(ast)}")
    for uid, node in ast.items():
        print(f"  {uid}: {node}")
    print()


def main():
    """主测试函数"""
    print("Testing IBC Parser")
    print("=" * 50)
    
    test_simple_module()
    test_function_with_params()
    test_class_with_inheritance()
    test_description_and_intent()


if __name__ == "__main__":
    main()