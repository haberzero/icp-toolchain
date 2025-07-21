import sys
import os
import json
import argparse

# 导入并使用
from src_main.cfg import mccp_config_manager
from src_main.cfg import mccp_dir_content_manager

# 这个文件最主要的作用：从dir_content_manager中读取展平后的目录内容
# 每个iter迭代的时候会从展平的目录内容生成三个对应的路径: mcbc mcpc src_main
# 随后提供几个方法，各自目录的具体路径。至于说是创建还是别的什么文件操作，放在顶层而不在这处理
# 基于这个原因，我想把dir_content类给重构一下，一点点来。现在vibe出来的东西我自己用不了 很愚蠢
# dir_content类重构好以后回来实现这边

class DirIterator:
    pass
    # def __init__(self, project_path):
    #     self.project_path = project_path
    #     self.dir_content = g_mccp_dir_content_manager.read_all_dir()
    #     self.current_dir_content = self.dir_content[project_path]
    #     self.current_dir_content_length = len(self.current_dir_content)

    # def __iter__(self):
    #     self.current_index = 0
    #     return self

    # def __next__(self):
    #     if self.current_index < self.current_dir_content_length:
    #         item = self.current_dir_content[self.current_index]
    #         self.current_index += 1
    #         return item
    #     else:
    #         raise StopIteration()
