import os
from pathlib import Path

class Config:
    # 树莓派连接配置
    PI_HOST = "192.168.126.65"
    PI_USER = "yzb"
    PI_PASS = "'"
    PI_REMOTE_DIR = "/home/yzb/Desktop/zzm/received_data"
    
    # 本地存储
    LOCAL_STORAGE = Path("./temp_storage")
    LOCAL_STORAGE.mkdir(exist_ok=True)
    
    # API配置
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

config = Config()