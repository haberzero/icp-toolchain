# 后面这个文件里用来统一存放mcbc分析过程中涉及的特定数据结构,不要再用一大堆字典处理了,看着烦人.顺便这里也可以处理helper

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