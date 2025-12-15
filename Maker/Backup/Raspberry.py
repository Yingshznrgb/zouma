from flask import Flask, request, jsonify
from PIL import Image
import requests
from io import BytesIO
import os

app = Flask(__name__)

@app.route('/display', methods=['POST'])
def display():
    data = request.get_json()
    image_url = data.get('imageUrl')
    text = data.get('text')

    # 下载图片
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    img.show()  # 显示图像

    # TTS 播放
    os.system(f'espeak "{text}"')  # 或用 pyttsx3

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
