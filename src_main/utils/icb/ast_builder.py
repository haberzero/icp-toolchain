import os
import json
from typing import List, Dict, Any, Optional
from utils.icb.lines_parser import LinesParser

from libs.diag_handler import DiagHandler, IcbEType, IcbWType

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
        self.module_nodes = []  # 存储module节点，确保它们只出现在文件顶部

    def build(self) -> bool:
        curr_line_num = 0

        curr_indent_level = 0
        last_indent_level = 0

        curr_node = None
        last_node = self.lines_parser.gen_root_ast_node()

        last_intent_comment = ""

        expected_next = ["ALL"]

        self.ast_node_dict[-1] = last_node  # 根节点作为ast_dict的起始元素
        self.ast_uid_stack.append(-1)   # 根节点入栈

        # 检查module节点是否只出现在文件顶部的标志
        module_section_ended = False

        # 开始进行遍历。遍历过程中任何在中间直接出现的continue都意味着没有新的ast_node被加入dict或stack
        for structured_line in self.structured_lines:
            curr_line_num = structured_line['line_num']
            content_str = structured_line['content']
            curr_indent_level = structured_line['indent_level']

            # 解析当前行
            curr_node = self.lines_parser.parse_line(content_str, curr_line_num)
            if curr_node is None:
                continue

            # 检查module关键字是否只出现在文件顶部
            if curr_node['type'] == 'module':
                if module_section_ended:
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.MODULE_NOT_AT_TOP)
                    continue
                self.module_nodes.append(curr_node)
            else:
                # 一旦出现非module节点，module部分就结束了
                module_section_ended = True

            # 检测当前行是否需要进行出栈操作。
            # 出栈操作后，expected_next 需要从栈中进行一次获取。否则以结尾处expected_next判断逻辑结果为准
            if curr_indent_level < last_indent_level:
                # 根据当前缩进级别调整栈
                while len(self.ast_uid_stack) > curr_indent_level + 1:
                    if self.ast_uid_stack:
                        temp_node_uid = self.ast_uid_stack.pop()
                        temp_ast_node = self.ast_node_dict[temp_node_uid]
                        # 处理special_align节点的额外出栈
                        if temp_ast_node.get('special_align', False):
                            if self.ast_uid_stack:
                                self.ast_uid_stack.pop()
                    if self.expected_next_stack:
                        self.expected_next_stack.pop()
                
                # 更新expected_next为栈顶元素对应的值
                if self.expected_next_stack:
                    expected_next = self.expected_next_stack[-1]
                else:
                    expected_next = ["ALL"]

            # 处理意图注释和description关键字的附加。未来还需要处理它们俩的对齐问题，目前暂时忽略
            # （如果意图注释出现在缩进等级降低的过程中可能有隐性bug，暂时没想清楚）
            if last_intent_comment != "":
                curr_node['intent_comment'] = last_intent_comment
                last_intent_comment = ""

            if curr_node['type'] == "description":
                # 将description附加到上一个同缩进级别的节点
                if self.ast_uid_stack:
                    # 获取当前缩进级别对应的栈位置
                    indent_level = curr_indent_level
                    if indent_level < len(self.ast_uid_stack):
                        # 找到同一缩进级别的父节点
                        target_uid = self.ast_uid_stack[indent_level]
                        if target_uid in self.ast_node_dict:
                            target_node = self.ast_node_dict[target_uid]
                            target_node['description'] = curr_node['value']
                # 即使是description节点也需要添加到ast_node_dict中
                self.ast_node_dict[curr_line_num] = curr_node
                continue

            if curr_node['type'] == "intent_comment":
                last_intent_comment = curr_node['value']
                # 即使是intent_comment节点也需要添加到ast_node_dict中
                self.ast_node_dict[curr_line_num] = curr_node
                continue

            # 特殊缩进对齐检查
            if curr_node.get('special_align', False):
                if curr_indent_level != last_indent_level:
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_SPECIAL_ALIGN)
                    # 即使有错误也需要添加到ast_node_dict中
                    self.ast_node_dict[curr_line_num] = curr_node
                    continue

            # 常规缩进检查
            else:
                if curr_indent_level == last_indent_level and last_node.get('is_block_start', False):
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.MISSING_INDENT_BLOCKSTART)
                    # 即使有错误也需要添加到ast_node_dict中
                    self.ast_node_dict[curr_line_num] = curr_node
                    continue
                elif curr_indent_level == last_indent_level+1 and not last_node.get('is_block_start', False):
                    self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_INDENT_INC)
                    # 即使有错误也需要添加到ast_node_dict中
                    self.ast_node_dict[curr_line_num] = curr_node
                    continue
                elif curr_indent_level > last_indent_level+1:
                    # 修复：允许合理的缩进增加，而不是直接抛出异常
                    # 检查是否是有效的块开始
                    if not last_node.get('is_block_start', False):
                        self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_INDENT_INC)
                        # 即使有错误也需要添加到ast_node_dict中
                        self.ast_node_dict[curr_line_num] = curr_node
                        continue

            # 核心语法检查(expected_next / expected_child)
            parent_uid = self.ast_uid_stack[-1] if self.ast_uid_stack else -1
            parent_node = self.ast_node_dict[parent_uid]
            expected_child = parent_node['expected_child']

            # 检查当前节点类型是否是父节点期望的下一个节点
            if curr_node['type'] not in expected_next and expected_next != ["ALL"]:
                self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_NEXT_NODE)
                # 即使有错误也需要添加到ast_node_dict中
                self.ast_node_dict[curr_line_num] = curr_node
                continue

            # 检查当前节点类型是否是父节点期望的子节点
            if expected_child and curr_node['type'] not in expected_child and "ALL" not in expected_child:
                self.diag_handler.set_line_error(curr_line_num, IcbEType.UNEXPECTED_CHILD_NODE)
                # 即使有错误也需要添加到ast_node_dict中
                self.ast_node_dict[curr_line_num] = curr_node
                continue

            # 节点之间归属记录
            curr_node['parent'] = parent_uid
            if parent_uid in self.ast_node_dict:
                self.ast_node_dict[parent_uid].setdefault('child_list', []).append(curr_line_num)

            # 当前节点的expected_next如果是['NONE']，则继承上一个expected_next（包括['ALL']的情况）
            if curr_node['expected_next'] == ['NONE']:
                curr_node['expected_next'] = expected_next

            # 当前节点是块的开始，入栈
            if curr_node.get('is_block_start', False):
                self.ast_uid_stack.append(curr_line_num)
                self.expected_next_stack.append(expected_next)  # 保存当前expected_next
                expected_next = ['ALL']
            
            else:
                expected_next = curr_node['expected_next']

            self.ast_node_dict[curr_line_num] = curr_node

            last_node = curr_node
            last_indent_level = curr_indent_level

            continue # 便于阅读

        # 清空栈
        self.ast_uid_stack.clear()
        self.expected_next_stack.clear()

        if self.ast_node_dict == {}:
            return False
        
        return True
    
    def _find_parent_node_at_indent(self, indent_level: int) -> int:
        """
        根据缩进级别查找对应的父节点UID
        """
        # 如果缩进级别为0，父节点是根节点
        if indent_level == 0:
            return -1
            
        # 根据缩进级别计算应该关联到哪个节点
        # 缩进级别对应栈中的位置（从0开始）
        stack_index = indent_level
        if stack_index < len(self.ast_uid_stack):
            return self.ast_uid_stack[stack_index]
        else:
            # 如果栈中没有对应位置，返回最后一个节点
            return self.ast_uid_stack[-1] if self.ast_uid_stack else -1
    
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