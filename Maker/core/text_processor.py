from pathlib import Path
from config import config

class TextProcessor:
    @staticmethod
    def save_text(text: str, filename: str):
        """保存文本到本地（可扩展NLP处理）"""
        path = config.LOCAL_STORAGE / f"{filename}.txt"
        with open(path, 'w') as f:
            f.write(text)
        return path