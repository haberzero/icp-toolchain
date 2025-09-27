import os
import json
from typing import List, Dict, Any, Optional
from lines_parser import LinesParser

from lib.diag_handler import DiagHandler, IcbEType, IcbWType

class AstBuilder:
    def __init__(
            self, 
            structured_lines: List[Dict[str, Any]], 
            diag_handler: DiagHandler, 
            active_file: str, 
            project_root: str):
        self.structured_lines = structured_lines
        self.lines_parser = LinesParser(diag_handler)
        self.diag_handler = diag_handler
        self.active_file = active_file
        self.project_root = project_root
        self.ast_node_dict = {}  # 所有ast_node的存储字典
        self.ast_uid_stack = []  # 处理节点归属的栈，内容是节点的uid，现在直接使用linue_num作为uid
        self.expected_next_stack = []  # 存储每个子层级入栈时的当前expected_next，出栈至同层级后恢复
        self.uid_tree = {}  # 存储uid的树结构，目前先用原生字典做一个很简陋的树结构（其实还没想清楚这个要怎么利用起来）

    def build(self):
        curr_line_num = 0
        last_line_num = -1
        # parent_line_num = -1

        curr_indent_level = 0
        last_indent_level = 0
        # parent_indent_level = 0

        curr_node = None
        last_node = self.lines_parser.gen_root_ast_node()
        parent_node = last_node

        last_intent_comment = ""

        expected_next = ["ALL"]
        expected_child = parent_node['expected_child']

        self.ast_node_dict[-1] = last_node  # 根节点作为ast_dict的起始元素
        self.ast_uid_stack.append(-1)   # 根节点入栈

        # 开始进行遍历。遍历过程中任何在中间直接出现的continue都意味着没有新的ast_node被加入dict或stack
        for structured_line in self.structured_lines:
            curr_line_num = structured_line['line_num']
            content_str = structured_line['content']
            curr_indent_level = structured_line['indent_level']

            # 解析当前行
            curr_node = self.lines_parser.parse_line(content_str, curr_line_num)
            if curr_node is None:
                continue

            # 检测当前行是否需要进行出栈操作。
            # 出栈操作后，expected_next 需要从栈中进行一次获取。否则以结尾处expected_next判断逻辑结果为准
            if curr_indent_level < last_indent_level:
                pop_num = last_indent_level - curr_indent_level
                for _ in range(pop_num):
                    temp_node_uid = self.ast_uid_stack.pop()
                    temp_ast_node = self.ast_node_dict[temp_node_uid]
                    expected_next = self.expected_next_stack.pop()
                    # 因为有special_align，所以需要一次额外pop。
                    # 未来考虑到input / output书写也可能分多行，因此检查special_align而非begin关键字
                    # 未来考虑将indent_level也进行栈管理，可能引入1.5缩进等级，用来指示special_align的存在
                    # 这样一来就不需要用if来处理special_align，而是在压栈的时候添加indent_level
                    if temp_ast_node['special_align'] == True:
                        expected_next = self.expected_next_stack.pop()
                        self.ast_uid_stack.pop()

            # 处理意图注释和description关键字的附加。未来还需要处理它们俩的对齐问题，目前暂时忽略
            # （如果意图注释出现在缩进等级降低的过程中可能有隐性bug，暂时没想清楚）
            if last_intent_comment != "":
                curr_node['intent_comment'] = last_intent_comment
                last_intent_comment = ""

            if curr_node['type'] == "description":
                last_node['description'] = curr_node['value']
                continue

            if curr_node['intent_comment'] != "":
                last_intent_comment = curr_node['intent_comment']
                continue

            # 特殊缩进对齐检查
            if curr_node['special_align'] == True:
                if curr_indent_level != last_indent_level:
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_SPECIAL_ALIGN)
                    continue

            # 常规缩进检查
            else:
                if curr_indent_level == last_indent_level and last_node['is_block_start'] == True:
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.MISSING_INDENT_BLOCKSTART)
                    continue
                elif curr_indent_level == last_indent_level+1 and last_node['is_block_start'] == False:
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_INDENT_INC)
                    continue
                elif curr_indent_level > last_indent_level+1:
                    raise Exception("Undefined indent level increase!! Are there some bugs in the parser or loader?")

            # 核心语法检查(expected_next / expected_child)
            parent_uid = self.ast_uid_stack[-1]
            parent_node = self.ast_node_dict[parent_uid]
            expected_child = parent_node['expected_child']

            if curr_node['type'] not in expected_next:
                self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_NEXT_NODE)
                continue

            if curr_node['type'] not in expected_child:
                self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_CHILD_NODE)
                continue

            # 节点之间归属记录
            curr_node['parent'] = parent_uid
            self.ast_node_dict[parent_uid]['child_list'].append(curr_line_num)

            # 当前节点的expected_next如果是['NONE']，则继承上一个expected_next（包括['ALL']的情况）
            if curr_node['expected_next'] == ['NONE']:
                curr_node['expected_next'] = expected_next

            # 当前节点是块的开始，入栈
            if curr_node['is_block_start'] == True:
                self.ast_uid_stack.append(curr_line_num)
                self.expected_next_stack.append(curr_node['expected_next'])
                expected_next = ['ALL']
            
            else:
                expected_next = curr_node['expected_next']

            self.ast_node_dict[curr_line_num] = curr_node

            last_line_num = curr_line_num
            last_node = curr_node
            last_indent_level = curr_indent_level

            continue # 便于阅读

        # 清空栈
        self.ast_uid_stack.clear()
        self.expected_next_stack.clear()

        if self.ast_node_dict == {}:
            return False
        
        return True
    
    def get_node_dict(self):
        return self.ast_node_dict

    # 构建仅包含 UID 的嵌套树结构，格式为：{uid: {child_uid: {grandchild_uid: ...}, ...}}
    def _generate_uid_tree(self):
        root_uid = -1
        self.uid_tree = self._build_uid_subtree(root_uid)

    # 递归构建
    def _build_uid_subtree(self, uid):
        subtree = {}
        for child_uid in self.ast_node_dict.get(uid, {}).get('child_list', []):
            if child_uid in self.ast_node_dict:
                subtree[child_uid] = self._build_uid_subtree(child_uid)
        return {uid: subtree}
