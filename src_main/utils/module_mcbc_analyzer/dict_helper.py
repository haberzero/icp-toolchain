# 后面这个文件应该变成：1. 可以直接阅读到结构； 2. 可以被某个help函数调用，在cli接口里面提供说明书
"""
structured_lines:
{
    'line_num': line_num,
    'indent_level': current_indent_level,
    'content': fully_stripped_line
}
"""

"""
parsed_lines:
{
    'type': 'root',
    'name': None,
    'value': None,
    'description': None,
    'intent': None,
    'line_num': 0,
    'is_block_start': False,
    'children': [],
    'attributes': None,
    'condition_or_action': None,
    'parent': None,
    'expected_next_types': ['class', 'func', 'var', 'behavior']
}
"""