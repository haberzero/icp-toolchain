"""
符号向量数据库管理器

负责管理符号表的向量化存储和检索，使用LanceDB
"""
import os
import lancedb
from typing import List, Dict, Tuple, Optional
from typedef.ibc_data_types import FileSymbolTable, SymbolNode
from typedef.cmd_data_types import Colors


class SymbolVectorDBManager:
    """符号向量数据库管理器，使用LanceDB存储和检索符号向量"""
    
    def __init__(self, db_path: str, embedding_handler):
        """
        初始化符号向量数据库管理器
        
        Args:
            db_path: 数据库存储路径
            embedding_handler: 嵌入向量处理器（ICPEmbeddingHandler实例）
        """
        self.db_path = db_path
        self.embedding_handler = embedding_handler
        self.db = None
        
        # 三个表的名称
        self.table_name_original = "symbols_original_name"
        self.table_name_normalized = "symbols_normalized_name"
        self.table_name_description = "symbols_description"
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self) -> bool:
        """初始化LanceDB数据库"""
        try:
            # 确保数据库目录存在
            os.makedirs(self.db_path, exist_ok=True)
            
            # 连接到LanceDB
            self.db = lancedb.connect(self.db_path)
            print(f"{Colors.OKGREEN}符号向量数据库初始化成功: {self.db_path}{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}符号向量数据库初始化失败: {e}{Colors.ENDC}")
            return False
    
    def add_file_symbols(
        self, 
        file_path: str, 
        symbol_table: FileSymbolTable
    ) -> bool:
        """
        将文件符号表添加到向量数据库
        
        Args:
            file_path: 文件路径
            symbol_table: 文件符号表
            
        Returns:
            bool: 是否添加成功
        """
        if not self.db:
            print(f"{Colors.FAIL}错误: 数据库未初始化{Colors.ENDC}")
            return False
        
        symbols = symbol_table.get_all_symbols()
        if not symbols:
            return True
        
        try:
            # 准备三种数据
            original_data = []
            normalized_data = []
            description_data = []
            
            for symbol_name, symbol in symbols.items():
                # 跳过未规范化的符号
                if not symbol.normalized_name:
                    continue
                
                # 获取符号的向量表示
                original_vec, status1 = self.embedding_handler.embed_query(symbol_name)
                if status1 != "SUCCESS":
                    print(f"{Colors.WARNING}警告: 符号 {symbol_name} 原始名向量化失败{Colors.ENDC}")
                    continue
                
                normalized_vec, status2 = self.embedding_handler.embed_query(symbol.normalized_name)
                if status2 != "SUCCESS":
                    print(f"{Colors.WARNING}警告: 符号 {symbol_name} 规范化名向量化失败{Colors.ENDC}")
                    continue
                
                # 处理描述向量
                desc_text = symbol.description if symbol.description else symbol_name
                desc_vec, status3 = self.embedding_handler.embed_query(desc_text)
                if status3 != "SUCCESS":
                    print(f"{Colors.WARNING}警告: 符号 {symbol_name} 描述向量化失败{Colors.ENDC}")
                    continue
                
                # 构建记录
                base_record = {
                    "file_path": file_path,
                    "symbol_name": symbol_name,
                    "normalized_name": symbol.normalized_name,
                    "symbol_type": symbol.symbol_type.value if symbol.symbol_type else "unknown",
                    "description": desc_text,
                    "visibility": symbol.visibility.value if symbol.visibility else "unknown"
                }
                
                original_data.append({
                    **base_record,
                    "vector": original_vec
                })
                
                normalized_data.append({
                    **base_record,
                    "vector": normalized_vec
                })
                
                description_data.append({
                    **base_record,
                    "vector": desc_vec
                })
            
            # 存储到三个表中
            if original_data:
                self._upsert_to_table(self.table_name_original, original_data)
            
            if normalized_data:
                self._upsert_to_table(self.table_name_normalized, normalized_data)
            
            if description_data:
                self._upsert_to_table(self.table_name_description, description_data)
            
            print(f"{Colors.OKGREEN}文件符号已添加到向量数据库: {file_path} ({len(original_data)} 个符号){Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}错误: 添加符号到向量数据库失败: {e}{Colors.ENDC}")
            return False
    
    def _upsert_to_table(self, table_name: str, data: List[Dict]) -> None:
        """
        插入或更新数据到指定表
        
        Args:
            table_name: 表名
            data: 数据列表
        """
        try:
            # 检查表是否存在
            table_names = self.db.table_names()
            
            if table_name in table_names:
                # 表存在，追加数据
                table = self.db.open_table(table_name)
                table.add(data)
            else:
                # 表不存在，创建新表
                self.db.create_table(table_name, data)
        except Exception as e:
            print(f"{Colors.WARNING}警告: 更新表 {table_name} 失败: {e}{Colors.ENDC}")
    
    def search_symbol(
        self, 
        query_text: str, 
        top_k: int = 5
    ) -> Optional[str]:
        """
        搜索最匹配的符号（规范化名称）
        
        使用加权策略：
        - 原始符号名: 0.4
        - 规范化符号名: 0.4
        - 符号描述: 0.2
        
        Args:
            query_text: 查询文本
            top_k: 每个表返回的top结果数量
            
        Returns:
            Optional[str]: 最匹配的规范化符号名，未找到时返回None
        """
        if not self.db:
            print(f"{Colors.FAIL}错误: 数据库未初始化{Colors.ENDC}")
            return None
        
        try:
            # 获取查询向量
            query_vec, status = self.embedding_handler.embed_query(query_text)
            if status != "SUCCESS":
                print(f"{Colors.WARNING}警告: 查询文本向量化失败: {query_text}{Colors.ENDC}")
                return None
            
            # 检查表是否存在
            table_names = self.db.table_names()
            
            results_dict = {}  # {normalized_name: weighted_score}
            
            # 从三个表中搜索
            if self.table_name_original in table_names:
                table = self.db.open_table(self.table_name_original)
                results = table.search(query_vec).limit(top_k).to_list()
                for result in results:
                    norm_name = result['normalized_name']
                    # 距离越小越相似，转换为分数
                    score = 1.0 / (1.0 + result['_distance'])
                    results_dict[norm_name] = results_dict.get(norm_name, 0) + score * 0.4
            
            if self.table_name_normalized in table_names:
                table = self.db.open_table(self.table_name_normalized)
                results = table.search(query_vec).limit(top_k).to_list()
                for result in results:
                    norm_name = result['normalized_name']
                    score = 1.0 / (1.0 + result['_distance'])
                    results_dict[norm_name] = results_dict.get(norm_name, 0) + score * 0.4
            
            if self.table_name_description in table_names:
                table = self.db.open_table(self.table_name_description)
                results = table.search(query_vec).limit(top_k).to_list()
                for result in results:
                    norm_name = result['normalized_name']
                    score = 1.0 / (1.0 + result['_distance'])
                    results_dict[norm_name] = results_dict.get(norm_name, 0) + score * 0.2
            
            # 找出得分最高的符号
            if results_dict:
                best_match = max(results_dict.items(), key=lambda x: x[1])
                return best_match[0]
            
            return None
            
        except Exception as e:
            print(f"{Colors.FAIL}错误: 符号搜索失败: {e}{Colors.ENDC}")
            return None
    
    def clear_database(self) -> bool:
        """清空数据库"""
        try:
            if not self.db:
                return False
            
            table_names = self.db.table_names()
            for table_name in table_names:
                self.db.drop_table(table_name)
            
            print(f"{Colors.OKGREEN}符号向量数据库已清空{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"{Colors.FAIL}错误: 清空数据库失败: {e}{Colors.ENDC}")
            return False
