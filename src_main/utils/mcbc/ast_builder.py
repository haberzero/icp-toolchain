import sys
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser

class AstBuilder:
    def __init__(self, structured_lines: List[Dict[str, Any]], diag_handler: DiagHandler):
        self.structured_lines = structured_lines
        self.lines_parser = LinesParser(diag_handler)
        self.ast: Dict[str, Any] = self.lines_parser.gen_root_ast_node()
        self.expected_next_types: List[str] = []
        self.diag_handler = diag_handler
    
    def build(self):
        ast_stack: List[Dict[str, Any]] = [self.ast]
        last_intent_comment: str = ""
        previous_parsed_node: Optional[Dict[str, Any]] = None

        
        for structured_line in self.structured_lines:
            line_num = structured_line['line_num']
            content = structured_line['content']
            indent_level = structured_line['indent_level']
            
            current_parsed_node = self.lines_parser.parse_line(content, line_num)
            
            # 当前行解析失败时记录错误并继续处理下一行
            if current_parsed_node is None:
                continue
            
            if current_parsed_node['type'] == 'intent_comment':
                # 错误处理得在这里增加内容，意图注释之后的行如果不是所期望的行，建议器应该把它挪位置或者直接删掉
                last_intent_comment = current_parsed_node['value']
                continue
            
            current_context_node = ast_stack[-1]
            
            if current_parsed_node['type'] not in current_context_node['expected_next_types']:
                self.diag_handler.set_line_error(line_num, EType.UNEXPECTED_NODE_TYPE)
                continue  # 记录错误后继续处理下一行
            
            # 这里要修一下，现在还不是atrribute,
            if current_parsed_node['type'] in ['input', 'output', 'description', 'inh']:
                if previous_parsed_node:
                    if 'attributes' not in previous_parsed_node:
                        previous_parsed_node['attributes'] = {}
                    previous_parsed_node['attributes'][current_parsed_node['type']] = current_parsed_node['value']
                continue
            
            if current_parsed_node.get('is_block_start', False):
                ast_stack.append(current_parsed_node)
            # 注意：有one_line_child_content的不能增加深度
            
            # expected_next_types只影响"同级别代码块"或"下一级别缩进代码块",不影响外部代码块，外部代码块的expected type由前面的父节点决定

            # 这里 对吗？好像不太合理
            current_parsed_node['parent'] = current_context_node
            previous_parsed_node = current_parsed_node

            # 目前考虑，如果是root节点上判断出现了behavior code，那么暂时直接忽略，标记一个建议删除

            self._append_node_to_parent(current_context_node, current_parsed_node)
            
        
        return self.ast
    
    def _append_node_to_parent(self, parent_node: Dict[str, Any], child_node: Dict[str, Any]):
        if 'children' not in parent_node:
            parent_node['children'] = []
        parent_node['children'].append(child_node)
