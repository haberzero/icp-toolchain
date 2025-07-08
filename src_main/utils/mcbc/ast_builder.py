import os
import json
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser

class AstBuilder:
    def __init__(self, structured_lines: List[Dict[str, Any]], diag_handler: DiagHandler, active_file: str, project_root: str):
        self.structured_lines = structured_lines
        self.lines_parser = LinesParser(diag_handler)
        self.ast: Dict[str, Any] = self.lines_parser.gen_root_ast_node()
        self.diag_handler = diag_handler
        self.active_file = active_file
        self.project_root = project_root
        self.ast_dict: Dict[int, Dict[str, Any]] = {}  # line_num -> node
        self.ast_tree: Dict[int, List[int]] = {}      # line_num -> [child_line_num]
        self.ast_stack: List[int] = []               # 保存当前节点的line_num

    def build(self):
        previous_line_num: Optional[int] = None
        last_intent_comment: str = ""

        for structured_line in self.structured_lines:
            line_num = structured_line['line_num']
            content = structured_line['content']
            indent_level = structured_line['indent_level']

            # 解析当前行
            current_parsed_node = self.lines_parser.parse_line(content, line_num)
            if current_parsed_node is None:
                continue

            # 1. 保存当前节点信息到 ast_dict
            self.ast_dict[line_num] = current_parsed_node
            current_parsed_node['line_num'] = line_num  # 确保line_num存在

            # 2. 处理描述节点
            if current_parsed_node['type'] == 'description' and previous_line_num:
                if indent_level == self.ast_dict[previous_line_num].get('indent_level', 0):
                    self.ast_dict[previous_line_num]['description'] = current_parsed_node['value']
                else:
                    self.diag_handler.set_line_error(line_num, EType.INDENTATION_LEVEL_ERROR)
                previous_line_num = line_num
                continue

            # 3. 处理意图注释
            if last_intent_comment and current_parsed_node.get('is_ast_node', True):
                current_parsed_node['intent_comment'] = last_intent_comment
                last_intent_comment = ""

            # 4. 处理块起始和缩进
            current_parsed_node['indent_level'] = indent_level
            current_line_num = line_num

            # 5. 处理缩进减少（块结束）
            if previous_line_num is not None:
                prev_indent = self.ast_dict[previous_line_num].get('indent_level', 0)
                if indent_level < prev_indent:
                    # 弹出栈直到找到合适父节点
                    while len(self.ast_stack) > 1 and self.ast_dict[self.ast_stack[-1]].get('indent_level', 0) >= indent_level:
                        self.ast_stack.pop()
                    parent_line = self.ast_stack[-1] if self.ast_stack else None
                    if parent_line:
                        self._add_child_to_tree(parent_line, current_line_num)
                elif indent_level == prev_indent:
                    # 同级节点
                    if self.ast_stack:
                        parent_line = self.ast_stack[-1]
                        self._add_child_to_tree(parent_line, current_line_num)
                    else:
                        # 根节点
                        self._add_child_to_tree(self.ast['line_num'], current_line_num)
                elif indent_level > prev_indent:
                    # 新块起始
                    self._add_child_to_tree(previous_line_num, current_line_num)
                    self.ast_stack.append(current_line_num)
                else:
                    # 无效缩进
                    self.diag_handler.set_line_error(line_num, EType.INDENTATION_LEVEL_ERROR)

            else:
                # 根节点下的第一个节点
                self._add_child_to_tree(self.ast['line_num'], current_line_num)
                self.ast_stack.append(current_line_num)

            previous_line_num = line_num

        # 保存 AST 到文件
        self.save_ast_info()

        return self.ast

    def _add_child_to_tree(self, parent_line: int, child_line: int):
        if parent_line not in self.ast_tree:
            self.ast_tree[parent_line] = []
        self.ast_tree[parent_line].append(child_line)

    def save_ast_info(self):
        # 构建最终的结构
        full_ast_info = {
            self.active_file: {
                'name': self.active_file,
                'incremental_update_count': 0,
                'ast_list': self.ast_dict,
                'ast_tree': self.ast_tree
            }
        }

        # 创建 temp 文件夹（如果不存在）
        temp_dir = os.path.join(self.project_root, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        # 写入 JSON 文件
        file_path = os.path.join(temp_dir, 'full_ast_info.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(full_ast_info, f, indent=2)
