"""验证数据管理器 - 专门处理IBC文件校验码的存储与加载"""
import json
import os
from typing import Dict, List


class VerifyDataManager:
    """验证数据管理器
    
    职责：
    - 统一管理IBC文件的MD5校验码
    - 新版：统一verify文件管理（保存在 icp_proj_data/icp_verify_data.json）
    - 旧版：单文件verify管理（等待废弃，保留向后兼容）
    
    所有方法均为静态方法，可独立使用。
    
    说明：
    新版校验数据采用统一文件存储，所有文件的校验码保存在同一个JSON文件中。
    存储结构示例（icp_verify_data.json）：
    {
        "src/ball_physics/ball": {
            "ibc_verify_code": "abc123...",
            "symbols_verify_code": "def456..."
        },
        "src/ball_physics/heptagon": {
            "ibc_verify_code": "xyz789..."
        }
    }
    """
    
    # ==================== 新版统一verify文件管理 ====================
    
    @staticmethod
    def load_file_verify_data(data_dir_path: str, file_path: str) -> Dict[str, str]:
        """从统一的verify文件中加载指定文件的校验数据
        
        Args:
            data_dir_path: 数据目录路径（通常为 icp_proj_data）
            file_path: 文件路径（如 "src/ball_physics/ball"）
            
        Returns:
            Dict[str, str]: 该文件的校验数据，不存在时返回空字典
        """
        verify_file_path = os.path.join(data_dir_path, 'icp_verify_data.json')
        
        if not os.path.exists(verify_file_path):
            return {}
        
        try:
            with open(verify_file_path, 'r', encoding='utf-8') as f:
                all_verify_data = json.load(f)
            return all_verify_data.get(file_path, {})
        except Exception as e:
            # 不抛出异常，返回空字典，避免阻塞流程
            return {}
    
    @staticmethod
    def save_file_verify_data(data_dir_path: str, file_path: str, verify_data: Dict[str, str]) -> None:
        """将指定文件的校验数据保存到统一的verify文件中
        
        Args:
            data_dir_path: 数据目录路径（通常为 icp_proj_data）
            file_path: 文件路径（如 "src/ball_physics/ball"）
            verify_data: 该文件的校验数据
            
        Raises:
            IOError: 保存失败时抛出
        """
        verify_file_path = os.path.join(data_dir_path, 'icp_verify_data.json')
        
        # 加载所有verify数据
        all_verify_data = {}
        if os.path.exists(verify_file_path):
            try:
                with open(verify_file_path, 'r', encoding='utf-8') as f:
                    all_verify_data = json.load(f)
            except Exception as e:
                # 读取失败时使用空字典
                all_verify_data = {}
        
        # 更新当前文件的数据
        all_verify_data[file_path] = verify_data
        
        # 保存回文件
        try:
            os.makedirs(data_dir_path, exist_ok=True)
            with open(verify_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_verify_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"保存verify文件失败 [{verify_file_path}]: {e}") from e
    
    @staticmethod
    def update_file_verify_data(data_dir_path: str, file_path: str, updates: Dict[str, str]) -> None:
        """更新指定文件的校验数据中的特定字段（增量更新）
        
        此方法会自动加载现有数据，合并更新，然后保存。
        相比 save_file_verify_data，此方法只更新指定的字段，保留其他字段不变。
        
        Args:
            data_dir_path: 数据目录路径（通常为 icp_proj_data）
            file_path: 文件路径（如 "src/ball_physics/ball"）
            updates: 要更新的字段字典，例如 {"ibc_verify_code": "new_md5"}
        
        Example:
            >>> # 只更新 ibc_verify_code，保留其他字段不变
            >>> VerifyDataManager.update_file_verify_data(
            ...     data_dir_path,
            ...     "src/ball/ball",
            ...     {"ibc_verify_code": "abc123"}
            ... )
        """
        # 加载现有的验证数据
        verify_data = VerifyDataManager.load_file_verify_data(data_dir_path, file_path)
        
        # 合并更新
        verify_data.update(updates)
        
        # 保存回去
        VerifyDataManager.save_file_verify_data(data_dir_path, file_path, verify_data)
    
    @staticmethod
    def batch_update_ibc_verify_codes(
        data_dir_path: str,
        ibc_root: str,
        file_paths: List[str]
    ) -> None:
        """批量更新所有ibc文件的MD5校验码到统一的verify文件
        
        Args:
            data_dir_path: 数据目录路径（通常为 icp_proj_data）
            ibc_root: IBC根目录路径
            file_paths: 要更新的文件路径列表
        """
        from data_store.ibc_file_manager import IbcFileManager
        from libs.ibc_funcs import IbcFuncs
        
        for file_path in file_paths:
            ibc_path = IbcFileManager.build_ibc_path(ibc_root, file_path)
            
            if not os.path.exists(ibc_path):
                continue
            
            try:
                ibc_content = IbcFileManager.load_ibc_content(ibc_path)
                if not ibc_content:
                    continue
                
                # 计算MD5
                current_md5 = IbcFuncs.calculate_text_md5(ibc_content)
                
                # 使用 update 方法只更新 ibc_verify_code 字段
                VerifyDataManager.update_file_verify_data(data_dir_path, file_path, {
                    'ibc_verify_code': current_md5
                })
            except Exception as e:
                # 单个文件失败不影响其他文件
                continue
    
    # ==================== 旧版校验数据管理（等待废弃，保留以保持向后兼容） ====================
    
    @staticmethod
    def build_verify_path(ibc_root: str, file_path: str) -> str:
        """构建verify文件路径: ibc_root/file_path_verify.json
        
        @deprecated: 请使用 load_file_verify_data 和 save_file_verify_data
        
        Args:
            ibc_root: IBC文件根目录
            file_path: 文件相对路径
            
        Returns:
            str: verify文件路径
        """
        # 解决Windows和Linux路径分隔符问题
        normalized_file_path = file_path.replace('/', os.sep)
        return os.path.join(ibc_root, f"{normalized_file_path}_verify.json")
    
    @staticmethod
    def save_verify_data(verify_path: str, verify_data: Dict[str, str]) -> None:
        """保存校验数据到文件
        
        @deprecated: 请使用 save_file_verify_data
        
        Args:
            verify_path: verify文件路径
            verify_data: 校验数据字典
            
        Raises:
            IOError: 保存失败时抛出
        """
        try:
            directory = os.path.dirname(verify_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(verify_path, 'w', encoding='utf-8') as f:
                json.dump(verify_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"保存校验数据失败 [{verify_path}]: {e}") from e
    
    @staticmethod
    def load_verify_data(verify_path: str) -> Dict[str, str]:
        """加载校验数据，文件不存在时返回空字典
        
        @deprecated: 请使用 load_file_verify_data
        
        Args:
            verify_path: verify文件路径
            
        Returns:
            Dict[str, str]: 校验数据字典，文件不存在时返回空字典
            
        Raises:
            IOError: 读取失败时抛出
        """
        if not os.path.exists(verify_path):
            return {}
        
        try:
            with open(verify_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"读取校验数据失败 [{verify_path}]: {e}") from e
    
    @staticmethod
    def update_verify_code(ibc_root: str, file_path: str, code_type: str = 'ibc') -> None:
        """更新单个文件的校验码
        
        @deprecated: 请使用 batch_update_ibc_verify_codes
        
        Args:
            ibc_root: IBC文件根目录
            file_path: 文件相对路径
            code_type: 校验码类型（默认为'ibc'）
            
        Raises:
            FileNotFoundError: IBC文件不存在
            ValueError: IBC文件内容为空
        """
        from data_store.ibc_file_manager import IbcFileManager
        from libs.ibc_funcs import IbcFuncs
        
        ibc_path = IbcFileManager.build_ibc_path(ibc_root, file_path)
        verify_path = VerifyDataManager.build_verify_path(ibc_root, file_path)
        
        if not os.path.exists(ibc_path):
            raise FileNotFoundError(f"IBC文件不存在: {ibc_path}")
        
        ibc_content = IbcFileManager.load_ibc_content(ibc_path)
        if not ibc_content:
            raise ValueError(f"IBC文件内容为空: {ibc_path}")
        
        # 计算MD5
        current_md5 = IbcFuncs.calculate_text_md5(ibc_content)
        
        # 加载并更新校验数据
        verify_data = VerifyDataManager.load_verify_data(verify_path)
        verify_data[f'{code_type}_verify_code'] = current_md5
        
        VerifyDataManager.save_verify_data(verify_path, verify_data)
    
    @staticmethod
    def batch_update_verify_codes(ibc_root: str, file_paths: List[str]) -> None:
        """批量更新校验码
        
        @deprecated: 请使用 batch_update_ibc_verify_codes
        
        Args:
            ibc_root: IBC文件根目录
            file_paths: 要更新的文件路径列表
        """
        for file_path in file_paths:
            VerifyDataManager.update_verify_code(ibc_root, file_path)
