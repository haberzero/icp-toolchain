import json
import os
from typing import Any, Dict, List, Optional, Tuple

from libs.dir_json_funcs import DirJsonFuncs
from typedef.ibc_data_types import (BehaviorStepNode, ClassNode, FunctionNode,
                                    IbcBaseAstNode, ModuleNode, SymbolMetadata,
                                    VariableNode, create_symbol_metadata)

from .path_manager import get_instance as get_path_manager


class ProjectStore:
    """
    Manages project-specific data and artifacts.
    Replaces IbcDataStore, IbcFileManager, SymbolTableManager, VerifyDataManager.
    """
    def __init__(self):
        self.path_manager = get_path_manager()

    # --- Dependency & Structure ---

    def load_depend_analysis(self) -> Dict[str, Any]:
        """Loads icp_dir_content_with_depend.json"""
        path = self.path_manager.get_proj_data_file('icp_dir_content_with_depend.json')
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading depend analysis: {e}")
            return {}

    def get_file_creation_order(self) -> List[str]:
        data = self.load_depend_analysis()
        if not data:
            return []
        return DirJsonFuncs.build_file_creation_order(data.get('dependent_relation', {}))

    def get_dependent_relation(self) -> Dict[str, List[str]]:
        data = self.load_depend_analysis()
        return data.get('dependent_relation', {})

    def get_proj_root_dict(self) -> Dict[str, Any]:
        data = self.load_depend_analysis()
        return data.get('proj_root_dict', {})

    # --- User Requirements & One File Req ---

    def load_user_requirements(self) -> str:
        """Loads user prompt from UserDataStore (legacy) or potentially from a file."""
        # For now, sticking to the pattern where it might be in memory or file.
        # But let's assume it's passed around or stored in a file if we want persistence.
        # The legacy UserDataStore was just memory.
        # Let's check if we can read it from a file? 
        # Usually it comes from `icp_implementation_plan.txt` or similar?
        # Let's return empty for now, or check a common file.
        return "" 

    def load_one_file_req(self, file_path: str) -> str:
        """Loads the requirement for a single file from staging."""
        filename = f"{file_path}_one_file_req.txt"
        path = self.path_manager.get_staging_file(filename)
        if not os.path.exists(path):
            return ""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading req for {file_path}: {e}")
            return ""

    # --- IBC Content ---

    def load_ibc_content(self, file_path: str) -> str:
        path = self.path_manager.get_ibc_file(file_path)
        if not os.path.exists(path):
            return ""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading IBC {file_path}: {e}")
            return ""

    def save_ibc_content(self, file_path: str, content: str):
        path = self.path_manager.get_ibc_file(file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving IBC {file_path}: {e}")

    # --- AST ---

    def build_ast_path(self, file_path: str) -> str:
        """Returns the full path to the AST file."""
        # Legacy format: file_path + "_ibc_ast.json"
        # file_path is like "utils/my_util"
        ibc_dir = self.path_manager.get_ibc_dir()
        normalized_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_dir, f"{normalized_path}_ibc_ast.json")

    def save_ast(self, file_path: str, ast_dict: Dict[int, IbcBaseAstNode]):
        path = self.build_ast_path(file_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        serializable_dict = {}
        for uid, node in ast_dict.items():
            node_dict = node.to_dict()
            node_dict["_class_type"] = type(node).__name__
            serializable_dict[str(uid)] = node_dict
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving AST {file_path}: {e}")

    def load_ast(self, file_path: str) -> Dict[int, IbcBaseAstNode]:
        path = self.build_ast_path(file_path)
        if not os.path.exists(path):
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                serializable_dict = json.load(f)
            
            ast_dict = {}
            for uid_str, node_dict in serializable_dict.items():
                uid = int(uid_str)
                node = self._create_node_from_dict(node_dict)
                ast_dict[uid] = node
            return ast_dict
        except Exception as e:
            print(f"Error loading AST {file_path}: {e}")
            return {}

    def _create_node_from_dict(self, node_dict: Dict[str, Any]) -> IbcBaseAstNode:
        class_type = node_dict.get("_class_type", "IbcBaseAstNode")
        if class_type == "ModuleNode":
            return ModuleNode.from_dict(node_dict)
        elif class_type == "ClassNode":
            return ClassNode.from_dict(node_dict)
        elif class_type == "FunctionNode":
            return FunctionNode.from_dict(node_dict)
        elif class_type == "VariableNode":
            return VariableNode.from_dict(node_dict)
        elif class_type == "BehaviorStepNode":
            return BehaviorStepNode.from_dict(node_dict)
        else:
            return IbcBaseAstNode.from_dict(node_dict)

    # --- Symbols ---

    def build_symbols_path(self, file_path: str) -> str:
        """Returns the full path to the symbols.json file for the directory of the file."""
        ibc_dir = self.path_manager.get_ibc_dir()
        file_dir = os.path.dirname(file_path)
        if file_dir:
            symbols_dir = os.path.join(ibc_dir, file_dir)
        else:
            symbols_dir = ibc_dir
        return os.path.join(symbols_dir, 'symbols.json')

    def load_symbols(self, file_path: str) -> Tuple[Dict[str, Any], Dict[str, SymbolMetadata]]:
        """Loads symbols for a specific file from the directory-level symbols.json."""
        path = self.build_symbols_path(file_path)
        file_name = os.path.basename(file_path)
        
        if not os.path.exists(path):
            return {}, {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                dir_symbols = json.load(f)
        except Exception:
            return {}, {}
            
        file_data = dir_symbols.get(file_name, {})
        if not file_data:
            return {}, {}
            
        symbols_tree = file_data.get("symbols_tree", {})
        symbols_metadata_dict = file_data.get("symbols_metadata", {})
        
        symbols_metadata = {}
        for key, meta_dict in symbols_metadata_dict.items():
            try:
                symbols_metadata[key] = create_symbol_metadata(meta_dict)
            except ValueError:
                continue
                
        return symbols_tree, symbols_metadata

    def save_symbols(self, file_path: str, symbols_tree: Dict[str, Any], symbols_metadata: Dict[str, SymbolMetadata]):
        """Saves symbols for a specific file into the directory-level symbols.json."""
        path = self.build_symbols_path(file_path)
        file_name = os.path.basename(file_path)
        
        dir_symbols = {}
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    dir_symbols = json.load(f)
            except Exception:
                dir_symbols = {}
        
        symbols_metadata_dict = {k: v.to_dict() for k, v in symbols_metadata.items()}
        
        dir_symbols[file_name] = {
            "symbols_tree": symbols_tree,
            "symbols_metadata": symbols_metadata_dict,
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(dir_symbols, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving symbols {file_path}: {e}")

    def load_dependency_symbols(self, file_path: str) -> Dict[str, Tuple[Dict, Dict]]:
        """Loads symbols for all dependencies of the given file."""
        relations = self.get_dependent_relation()
        deps = relations.get(file_path, [])
        
        result = {}
        for dep in deps:
            tree, meta = self.load_symbols(dep)
            if tree or meta:
                result[dep] = (tree, meta)
        return result

    # --- Verify Data ---
    
    def get_verify_data_path(self) -> str:
        return self.path_manager.get_proj_data_file("icp_verify_data.json")

    def load_verify_data(self) -> Dict[str, Any]:
        path = self.get_verify_data_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_verify_data(self, data: Dict[str, Any]):
        path = self.get_verify_data_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving verify data: {e}")

    def update_file_verify_data(self, file_path: str, updates: Dict[str, Any]):
        data = self.load_verify_data()
        if file_path not in data:
            data[file_path] = {}
        data[file_path].update(updates)
        self.save_verify_data(data)

