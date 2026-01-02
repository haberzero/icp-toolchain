class ChatResponseCleaner:
    @staticmethod
    def clean_code_block_markers(content: str) -> str:
        """清理响应内容中可能存在的代码块标记（```）
        
        Args:
            content: 原始响应内容
            
        Returns:
            str: 清理后的内容
        """
        cleaned_content = content.strip()
        
        # 移除可能的代码块标记
        lines = cleaned_content.split('\n')
        
        # 检查并移除开头的代码块标记
        if lines and lines[0].strip().startswith('```'):
            lines = lines[1:]
        
        # 检查并移除结尾的代码块标记
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        
        return '\n'.join(lines).strip()
    