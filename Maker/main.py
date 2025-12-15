from core.image_processor import ImageProcessor
from core.text_processor import TextProcessor
from core.pi_transfer import PiTransfer
from pathlib import Path
import argparse

def process_image(image_url: str, style: int):
    print("🖼️ 图片处理中...")
    processor = ImageProcessor()
    transfer = PiTransfer()
    
    try:
        local_path = processor.generate_image(image_url, style)
        remote_path = transfer.send_file(local_path, "images")
        print(f"✅ 图片已传输到树莓派: {remote_path}")
    except Exception as e:
        print(f"❌ 图片处理失败: {str(e)}")

def process_text(text: str, filename: str):
    print("📝 文本处理中...")
    processor = TextProcessor()
    transfer = PiTransfer()
    
    try:
        remote_path = transfer.send_text(text, filename)
        print(f"✅ 文本已传输到树莓派: {remote_path}")
    except Exception as e:
        print(f"❌ 文本处理失败: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="主控传输系统")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # 图片处理命令
    img_parser = subparsers.add_parser('image')
    img_parser.add_argument('url', help="图片URL")
    img_parser.add_argument('--style', type=int, default=3, help="风格索引(0-9)")

    # 文本处理命令
    text_parser = subparsers.add_parser('text')
    text_parser.add_argument('content', help="文本内容")
    text_parser.add_argument('--filename', default="text_data", help="保存文件名")

    args = parser.parse_args()
    
    if args.command == 'image':
        process_image(args.url, args.style)
    elif args.command == 'text':
        process_text(args.content, args.filename)
