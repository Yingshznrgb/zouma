from PIL import Image, ImageDraw, ImageFont

def text_to_image(text, output_path="art_text.png", font_path=None, font_size=40, bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """
    将文本转换为艺术字图片并保存
    :param text: 输入的文本
    :param output_path: 输出图片路径
    :param font_path: 字体文件路径（可选）
    :param font_size: 字体大小
    :param bg_color: 背景颜色 (RGB)
    :param text_color: 文本颜色 (RGB)
    """
    # 创建一个空白图像（白色背景）
    image = Image.new("RGB", (800, 200), bg_color)
    draw = ImageDraw.Draw(image)
    
    # 加载字体（如果未指定，使用默认字体）
    try:
        font = ImageFont.truetype(font_path or "arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # 计算文本宽度和高度，调整图片大小（可选）
    # 注意：Pillow 10.0+ 使用 textbbox 替代
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # 为了简化，这里直接使用固定图片大小，或动态调整：
    image = image.resize((text_width + 50, text_height + 50))  # 加一些边距
    draw = ImageDraw.Draw(image)  # 重新创建 draw 对象
    
    # 绘制文本（居中显示）
    text_position = ((image.width - text_width) // 2, (image.height - text_height) // 2)
    draw.text(text_position, text, fill=text_color, font=font)
    
    # 保存图片
    image.save(output_path)
    print(f"艺术字图片已保存到: {output_path}")

# 示例调用
font_path = 'fonts/ZiHunJianQiShouShu-2.ttf'
text_to_image("你好，世界！", "hello_world.png", font_path=font_path, font_size=60, text_color=(255, 0, 0))  # 红色文本