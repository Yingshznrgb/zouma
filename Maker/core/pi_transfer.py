import paramiko
from pathlib import Path
from config import config

class PiTransfer:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            hostname=config.PI_HOST,
            username=config.PI_USER,
            password=config.PI_PASS
        )
    
    def send_file(self, local_path: Path, remote_subdir: str = ""):
        """传输文件到树莓派"""
        sftp = self.ssh.open_sftp()
        
        # 确保远程目录存在
        remote_dir = f"{config.PI_REMOTE_DIR}/{remote_subdir}"
        try:
            sftp.stat(remote_dir)
        except IOError:
            sftp.mkdir(remote_dir)
        
        # 上传文件
        remote_path = f"{remote_dir}/{local_path.name}"
        sftp.put(str(local_path), remote_path)
        sftp.close()
        return remote_path
    
    def send_text(self, text: str, filename: str):
        """发送文本到树莓派（保存为文件）"""
        local_path = config.LOCAL_STORAGE / f"{filename}.txt"
        with open(local_path, 'w') as f:
            f.write(text)
        return self.send_file(local_path, "texts")
    
    def __del__(self):
        self.ssh.close()