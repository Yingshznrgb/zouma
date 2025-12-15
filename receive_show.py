# receive_and_show_pi.py
# 在树莓派上运行的服务器，用于接收并循环显示/更新图片。

from flask import Flask, request, jsonify
import os
import subprocess
from werkzeug.utils import secure_filename
import logging
import signal # 导入signal库来优雅地终止进程

# --- 配置 ---
UPLOAD_FOLDER = '/home/yzb/Desktop/zzm/received_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PI_PORT = 5002

# --- 初始化 ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- 全局变量 ---
# 用于保存当前正在运行的feh进程对象
current_feh_process = None

def allowed_file(filename):
    """检查文件扩展名是否在允许的列表中"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def show_image_on_screen(filepath):
    """
    使用feh命令在屏幕上全屏显示图片，并管理进程以实现更新。
    """
    global current_feh_process
    logging.info(f"🖥️  准备更新屏幕显示: {filepath}")

    # 1. 如果已经有一个feh进程在运行，先优雅地终止它
    if current_feh_process:
        try:
            logging.info(f"Terminating old feh process (PID: {current_feh_process.pid})")
            # 使用SIGTERM信号来请求进程终止
            current_feh_process.terminate()
            # 等待一小段时间确保进程已关闭
            current_feh_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            logging.warning("Old feh process did not terminate gracefully, killing it.")
            current_feh_process.kill()
        except Exception as e:
            logging.error(f"Error terminating old feh process: {e}")
        current_feh_process = None

    # 2. 准备启动新的feh进程
    env = os.environ.copy()
    env['DISPLAY'] = ':0'

    try:
        # feh 命令参数:
        # -Y: 隐藏鼠标指针
        # -F: 全屏显示
        # --auto-zoom: 自动缩放图片以适应屏幕
        # --hide-pointer: 另一个隐藏指针的选项
        # --borderless: 无边框
        # --cycle-once: 如果提供多个文件，只循环一次（这里只有一个文件，此参数影响不大）
        # *** 关键：去掉了 '-D 15' 参数，让feh持续运行 ***
        command = ['feh', '-Y', '-F', '--auto-zoom', '--borderless', str(filepath)]
        
        # 3. 启动新的feh进程，并保存其进程对象
        current_feh_process = subprocess.Popen(command, env=env)
        
        logging.info(f"✅ 新的 'feh' 进程已启动 (PID: {current_feh_process.pid})，显示图片: {os.path.basename(filepath)}")
        
    except FileNotFoundError:
        logging.error("❌ 命令 'feh' 未找到。请先执行 'sudo apt install feh'。")
        current_feh_process = None
    except Exception as e:
        logging.error(f"❌ 启动 'feh' 时发生未知错误: {e}")
        current_feh_process = None


@app.route('/show_image', methods=['POST'])
def show_image_endpoint():
    """接收来自PC的图片并调用显示函数"""
    if 'image' not in request.files:
        logging.warning("请求中未找到图片文件部分 'image'")
        return jsonify({"error": "请求中未找到图片文件部分 'image'"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        logging.warning("收到了一个没有文件名的空文件部分")
        return jsonify({"error": "没有选择文件"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 为了避免文件名冲突导致feh显示旧图，可以每次都用一个固定的名字，或者加上时间戳
        # 这里我们直接覆盖同名文件
        file.save(save_path)
        logging.info(f"🖼️  图片已接收并保存至: {save_path}")
        
        # 调用函数在屏幕上显示或更新
        show_image_on_screen(save_path)
        
        return jsonify({"status": "success", "message": f"Image '{filename}' received and is being displayed."}), 200
    else:
        logging.warning(f"收到了一个不允许的文件类型: {file.filename}")
        return jsonify({"error": "文件类型不被允许"}), 400

def cleanup():
    """在程序退出时，清理feh进程"""
    global current_feh_process
    if current_feh_process:
        logging.info("程序退出，正在清理 feh 进程...")
        current_feh_process.terminate()
        current_feh_process = None

if __name__ == '__main__':
    import atexit
    # 注册一个退出函数，确保Ctrl+C时也能清理feh进程
    atexit.register(cleanup)
    
    logging.info(f"--- 树莓派图片循环显示服务器已启动 ---")
    logging.info(f"监听地址: http://0.0.0.0:{PI_PORT}")
    logging.info(f"上传的图片将保存在: {UPLOAD_FOLDER}")
    logging.info("等待PC发送图片...")
    app.run(host='0.0.0.0', port=PI_PORT)