import paramiko
import os


class PiFileTransfer:
    def __init__(self, host, username, password, port=22):
        self.connection = {
            "host": host,
            "username": username,
            "password": password,
            "port": port
        }

    def upload(self, local_path, remote_dir):
        """上传文件到树莓派"""
        try:
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(**self.connection)

                with ssh.open_sftp() as sftp:
                    # 确保远程目录存在
                    try:
                        sftp.stat(remote_dir)
                    except IOError:
                        sftp.mkdir(remote_dir)

                    # 上传文件
                    filename = os.path.basename(local_path)
                    remote_path = f"{remote_dir}/{filename}"
                    sftp.put(local_path, remote_path)
                    return remote_path

        except Exception as e:
            raise RuntimeError(f"上传失败: {str(e)}")