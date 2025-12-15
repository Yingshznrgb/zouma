# 树莓派配置
## 基础环境配置
```bash
# 1. 确保开启SSH服务
sudo raspi-config
# 选择 Interfacing Options → SSH → Enable

# 2. 创建接收目录（与主控程序配置一致）
mkdir -p ~/received_data/{images,texts}
chmod 777 ~/received_data

# 3. 安装监控工具（可选）
sudo apt install inotify-tools  # 用于文件变化监控
```
## 接收脚本 
~/receiver.py
## 自动启动配置
```bash
# 1. 安装Python依赖
sudo apt install python3-pip
pip3 install watchdog

# 2. 创建systemd服务
sudo nano /etc/systemd/system/file_receiver.service
```
粘贴以下内容
```ini
[Unit]
Description=File Receiver Service
After=network.target

[Service]
User=pi
ExecStart=/usr/bin/python3 /home/pi/receiver.py
Restart=always
WorkingDirectory=/home/pi

[Install]
WantedBy=multi-user.target
```
启用服务
```bash
sudo systemctl daemon-reload
sudo systemctl enable file_receiver
sudo systemctl start file_receiver
```
# 验证部署

## 主控端
```PowerShell
# 测试文本传输
python main.py text "Hello Raspberry Pi" --filename test

# 测试图片传输
python main.py image https://example.com/test.jpg --style 3
```
## 树莓派端
```bash
# 查看接收的文件
ls -l ~/received_data/texts/
ls -l ~/received_data/images/

# 查看服务日志
journalctl -u file_receiver -f
```

# 注意
环境变量：echo $env:DASHSCOPE_API_KEY
确保网页设备与树莓派在同一局域网。

校园网有多个路由器，建议PC（网页设备）和树莓派连接在同一手机热点上