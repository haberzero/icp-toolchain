import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.ibc_analyzer.ibc_lexer import IbcLexer
from utils.ibc_analyzer.ibc_parser import IbcParser

# 测试带路径分隔符的module声明
code = """module utils.logger: 日志工具模块
module config.settings: 配置管理
module database.connection.pool: 数据库连接池"""

try:
    lexer = IbcLexer(code)
    tokens = lexer.tokenize()
    
    print("Tokens:")
    for token in tokens:
        if token.type.name != 'NEWLINE' and token.type.name != 'EOF':
            print(f"  {token.type.name}: '{token.value}'")
    
    parser = IbcParser(tokens)
    ast = parser.parse()
    
    print("\n解析成功!")
    root = ast[0]
    
    for uid in root.children_uids:
        node = ast[uid]
        print(f"Module: identifier='{node.identifier}', content='{node.content}'")
    
except Exception as e:
    print(f"\n解析失败: {e}")
    import traceback
    traceback.print_exc()
