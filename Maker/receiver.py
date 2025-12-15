#!/usr/bin/env python3
import os
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/yzb/Desktop/zzm/receiver.log'),
        logging.StreamHandler()
    ]
)

class FileHandler(FileSystemEventHandler):
    def __init__(self, target_dir):
        self.target_dir = Path(target_dir)
        
    def on_created(self, event):
        if not event.is_directory:
            filepath = Path(event.src_path)
            logging.info(f"📥 收到新文件: {filepath.name}")
            
            # 根据文件类型处理
            if filepath.suffix == '.txt':
                self._process_text(filepath)
            elif filepath.suffix.lower() in ('.jpg', '.png'):
                self._process_image(filepath)

    def _process_text(self, filepath):
        """处理文本文件"""
        with open(filepath, 'r') as f:
            content = f.read()
        logging.info(f"📝 文本内容: {content[:50]}...")  # 只打印前50字符

    def _process_image(self, filepath):
        """处理图片文件"""
        logging.info(f"🖼️ 图片已保存到: {filepath}")
        # 这里可以添加图片处理逻辑，如调用本地AI模型

if __name__ == "__main__":
    watch_dir = "/home/yzb/Desktop/zzm/received_data"  # 必须与主控程序配置的PI_REMOTE_DIR一致
    
    if not os.path.exists(watch_dir):
        os.makedirs(watch_dir)
    
    event_handler = FileHandler(watch_dir)
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    
    try:
        logging.info(f"👂 开始监控目录: {watch_dir}")
        observer.start()
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()