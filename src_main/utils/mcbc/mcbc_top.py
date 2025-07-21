import sys
import os

from src_main.utils.mcbc.analyzer.mcbc_analyzer import McbcAnalyzer
from src_main.lib.diag_handler import DiagHandler
from src_main.utils.dir_generator.dir_generator import DirIterator

from cfg.mccp_config_manager import MccpConfigManager

class McbcTop:
    def __init__(self):
        self.mccp_config_manager = MccpConfigManager.get_instance()
        self.project_root = self.mccp_config_manager.get_proj_path()
        self.diag_handler = DiagHandler()
        self.dir_iterator = DirIterator(self.project_root)
    
    def analyze_project(self):
        pass
