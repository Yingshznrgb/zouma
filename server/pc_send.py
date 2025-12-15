# generate_and_send.py
# 在PC上运行的自动化脚本，用于生成图片并自动发送到树莓派。

import requests
import os
from PIL import Image, ImageDraw, ImageFont
import datetime
import io

# --- 配置 ---
PI_IP = "192.168.79..65"  # <--- 必须修改为你的树莓派的IP地址
PI_PORT = 5002            # 必须与树莓派服务器脚本中的端口一致
PI_SHOW_URL = f'http://{PI_IP}:{PI_PORT}/show_image'

# ==============================================================================
#  核心部分 1: 图片生成/获取逻辑
#  你可以将这个函数完全替换成你自己的需求。
# ==============================================================================
def get_image_data():
    """
    生成或获取图片数据。
    这个函数的目标是返回两个值：图片的二进制数据(bytes)和文件名。
    
    *** 这是你需要根据你的实际需求修改的地方 ***
    """
    
    # # --- 示例 1: 动态生成一张带有当前时间的图片 (在内存中操作) ---
    # print("🖼️  正在动态生成图片...")
    
    # # 创建一张黑色的画布
    # img = Image.new('RGB', (800, 600), color = 'black')
    # d = ImageDraw.Draw(img)
    
    # # 获取当前时间
    # now = datetime.datetime.now()
    # timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # # 准备字体 (Pillow可能需要你指定一个字体文件的路径)
    # # 在Windows上, 可以在 'C:/Windows/Fonts/' 找到. 'arial.ttf' 通常都存在.
    # try:
    #     font = ImageFont.truetype("arial.ttf", 40)
    # except IOError:
    #     print("警告: 'arial.ttf' 字体未找到, 使用默认字体。")
    #     font = ImageFont.load_default()

    # # 在图片上绘制文字
    # d.text((10,10), "来自PC的自动消息", fill=(255,255,0), font=font)
    # d.text((10,60), f"生成时间: {timestamp_str}", fill=(255,255,255), font=font)
    
    # # 将图片保存在内存中的一个二进制流里，而不是物理文件
    # img_byte_arr = io.BytesIO()
    # img.save(img_byte_arr, format='PNG')
    # image_bytes = img_byte_arr.getvalue()
    
    # # 定义一个文件名
    # filename = f"auto_generated_{now.strftime('%Y%m%d_%H%M%S')}.png"
    
    # print(f"✅ 图片生成完毕，文件名为 '{filename}'。")
    # return image_bytes, filename

    # --- 示例 2: 如果你只是想发送一个固定的本地图片 ---
    # 取消注释下面的代码块，并注释掉上面的 "示例 1" 部分
    print("🖼️  正在读取本地图片...")
    image_path = r"D:\Camel\project\Zouma\chang.jpg" # <--- 修改为你的图片路径
    if not os.path.exists(image_path):
        print(f"❌ 错误: 指定的图片文件不存在: {image_path}")
        return None, None
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    filename = os.path.basename(image_path)
    print(f"✅ 本地图片 '{filename}' 读取完毕。")
    return image_bytes, filename

# ==============================================================================
#  核心部分 2: 图片发送逻辑 (通常无需修改)
# ==============================================================================
def send_image(image_bytes, filename):
    """将给定的图片二进制数据发送到树莓派"""
    
    if not image_bytes or not filename:
        print("❌ 发送中止，因为没有有效的图片数据或文件名。")
        return

    print(f"📦 准备发送图片: {filename}")
    print(f"📡 目标地址: {PI_SHOW_URL}")

    try:
        # 'files' 字典需要文件名和二进制数据
        files = {'image': (filename, image_bytes)}
        
        # 发送POST请求
        response = requests.post(PI_SHOW_URL, files=files, timeout=15)

        # 处理响应
        if response.status_code == 200:
            print("✅ 成功! 图片已发送到树莓派。")
            print(f"   服务器响应: {response.json().get('message', '')}")
        else:
            print(f"❌ 失败! 服务器返回错误。")
            print(f"   状态码: {response.status_code}")
            try:
                print(f"   错误信息: {response.json().get('error', response.text)}")
            except requests.exceptions.JSONDecodeError:
                print(f"   原始响应: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"❌ 网络错误: 无法连接到树莓派 {PI_IP}。")
        print("   请检查: IP地址, 网络连接, 树莓派服务是否运行, 防火墙设置。")
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")


# ==============================================================================
#  主执行流程
# ==============================================================================
if __name__ == "__main__":
    print("--- 自动图片生成与发送任务启动 ---")
    
    # 1. 调用函数获取图片数据
    image_data, image_filename = get_image_data()
    
    # 2. 调用函数发送图片
    send_image(image_data, image_filename)
    
    print("--- 任务结束 ---")