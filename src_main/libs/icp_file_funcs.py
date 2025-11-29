import os
import json
from typing import List, Dict, Optional, Union, Set, Any

class FileFuncs:



    def _initialize_update_status(
        self,
        file_creation_order_list: List[str],
        staging_dir_path: str,
        ibc_root_path: str,
    ) -> Dict[str, bool]:
        """
        初始化更新状态字典
        
        遍历所有文件，检查以下条件判断是否需要重新生成：
        1. 需求文件的MD5是否与已保存的符号表中的MD5匹配
        2. 目标IBC文件是否存在
        3. 符号表文件是否存在
        
        满足以下任一条件则需要更新：
        - 需求文件的MD5发生变化
        - 需求文件不存在
        - IBC文件不存在
        - 符号表文件不存在
        
        Args:
            file_creation_order_list: 文件创建顺序列表
            staging_dir_path: staging目录路径
            ibc_root_path: IBC根目录路径
            
        Returns:
            Dict[str, bool]: 更新状态字典，key为文件路径，value为是否需要更新
        """
        update_status = {}
        ibc_data_manager = get_ibc_data_manager()
        
        for file_path in file_creation_order_list:
            # 计算当前需求文件的MD5
            req_file_path = os.path.join(staging_dir_path, f"{file_path}_one_file_req.txt")
            current_md5 = self._calculate_file_md5(req_file_path)
            
            # 检查需求文件是否存在
            if not current_md5:
                update_status[file_path] = True
                continue
            
            # 检查IBC文件是否存在
            ibc_file_path = os.path.join(ibc_root_path, f"{file_path}.ibc")
            if not os.path.exists(ibc_file_path):
                update_status[file_path] = True
                continue
            
            # 检查符号表文件是否存在
            symbol_table_file = os.path.join(ibc_root_path, f"{file_path}_symbols.json")
            if not os.path.exists(symbol_table_file):
                update_status[file_path] = True
                continue
            
            # 加载已保存的符号表
            file_symbol_table = ibc_data_manager.load_file_symbols(ibc_root_path, file_path)
            
            # 判断MD5是否匹配
            if file_symbol_table.file_md5 != current_md5:
                update_status[file_path] = True
            else:
                update_status[file_path] = False
        
        return update_status

    def _check_dependency_updated(
        self,
        dependencies: List[str],
        update_status: Dict[str, bool]
    ) -> bool:
        """
        检查当前文件的依赖文件是否有更新
        
        Args:
            dependencies: 依赖文件列表
            update_status: 更新状态字典
            
        Returns:
            bool: 如果任一依赖文件需要更新，返回True
        """
        for dep_file in dependencies:
            if update_status.get(dep_file, False):
                return True
        return False

    def _calculate_file_md5(self, file_path: str) -> str:
        """计算文件的MD5校验值"""
        if not os.path.exists(file_path):
            return ""
        
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 计算文件MD5失败 {file_path}: {e}{Colors.ENDC}")
            return ""

    def _get_file_content(self, file_path: str) -> str:
        """获取文件内容"""
        if not os.path.exists(file_path):
            return ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"  {Colors.WARNING}警告: 读取文件失败 {file_path}: {e}{Colors.ENDC}")
            return ""
