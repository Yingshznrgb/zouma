from flask import Flask, request, jsonify, render_template
import os

app = Flask(__name__)

# 确保有一个目录存放上传的图片
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')  # 返回一个HTML页面（可选）

@app.route('/upload', methods=['POST'])
def upload():
    # 接收文字信息
    text_data = request.form.get('text')
    print(f"Received text: {text_data}")

    # 接收图片文件
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != '':
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
            print(f"Image saved to: {image_path}")

    return jsonify({"status": "success", "message": "Data received!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # 允许局域网访问