import sys
import os

from src_main.utils.mcbc.analyzer.mcbc_analyzer import McbcAnalyzer
from src_main.lib.diag_handler import DiagHandler
from src_main.utils.dir_generator.dir_generator import DirGenerator

from src_main.utils import mccp_dir_content_manager

from src_main.cfg import proj_cfg_manager

# 本文件的目的：
# 通过dir_generator获取目录列表，然后逐步根据dependent map 分析目录下的mcbc文件，生成ast和symbol表
# 本文件在dir_generator调用完毕以后被调用。（后面大概率还需要一个mcbc_generator，专门用来从dir_content和原始需求表中生成mcbc代码）

class McbcOperator:
    def __init__(self, project_root):
        self.project_root = project_root
        self.dir_generator = DirGenerator(self.project_root)
        self.diag_handler = DiagHandler()
    
    def analyze_project(self):
        pass
