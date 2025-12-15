# ==============================================================================
# --- 导入所需库 ---
# ==============================================================================
import os
import json
import base64
import hashlib
import hmac
import _thread as thread
import re
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import requests
import websocket  # 需要安装: pip install websocket-client
from flask import Flask, jsonify, request # 需要安装: pip install Flask

# ==============================================================================
# --- 全局配置 ---
# ==============================================================================
# 1. 讯飞星火 API 配置 (从 https://console.xfyun.cn/services/bmx1 获取)
SPARK_APPID = "c73d990e"      # 你的 APPID
SPARK_API_KEY = "a826d05bded10a9ea8f6943f4f0d3081"    # 你的 APIKey
SPARK_API_SECRET = "NTRkZDZmMTBhMTQzNTczMmMyMGI2NTA2" # 你的 APISecret
SPARK_DOMAIN = "4.0Ultra"          # 模型版本，例如 "x1"
SPARK_URL = "wss://spark-api.xf-yun.com/v4.0/chat"  # 服务地址

# 2. 树莓派配置
PI_IP = "192.168.79.65"      # <--- 修改为你的树莓派的IP地址
PI_PORT = 5001
PI_RESPONSE_URL = f'http://{PI_IP}:{PI_PORT}/receive_command' # 修改了接口名，更清晰

# 3. 本机PC服务器配置
PC_PORT = 5000

# 4. 文件路径配置
#    请确保这里的路径是正确的，建议使用绝对路径
AUDIO_EMOTION_FILE = r"D:\desktop\Tired\SpeechEmotionRecognition-Pytorch-master\predict.txt"
LLM_RESULT_FILE = r"result.json"

# ==============================================================================
# --- 全局变量 (用于讯飞 WebSocket 通信) ---
# ==============================================================================
# 用于存储从WebSocket接收到的完整回复
llm_answer = ""
# 用于管理对话历史
chat_history = []

# ==============================================================================
# --- 讯飞星火大模型 WebSocket API 相关代码 ---
# ==============================================================================
class Ws_Param(object):
    """用于生成 WebSocket URL 的参数类"""
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    def create_url(self):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        v = {"authorization": authorization, "date": date, "host": self.host}
        url = self.Spark_url + '?' + urlencode(v)
        return url

# --- WebSocket 事件处理器 ---
def on_error(ws, error):
    print(f"❌ WebSocket 发生错误: {error}")

def on_close(ws, close_status_code, close_msg):
    # print("✅ WebSocket 连接已关闭")
    pass

def on_open(ws):
    """连接建立后，在新的线程中发送数据"""
    def run(*args):
        data = json.dumps(gen_params(appid=ws.appid, domain=ws.domain, question=ws.question))
        ws.send(data)
    thread.start_new_thread(run, ())

def on_message(ws, message):
    """处理从服务器收到的每一条消息"""
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        print(f'❌ 请求错误: {code}, {data}')
        ws.close()
    else:
        choices = data["payload"]["choices"]
        status = choices["status"]
        content = choices['text'][0]['content']
        
        global llm_answer
        llm_answer += content
        
        if status == 2:
            # 消息接收完毕
            ws.close()

# --- 数据准备和参数生成 ---
def gen_params(appid, domain, question):
    """生成发送给大模型的参数"""
    data = {
        "header": {"app_id": appid, "uid": "1234"},
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 1.2,
                "max_tokens": 4096,
            }
        },
        "payload": {"message": {"text": question}}
    }
    return data

def run_spark_main(appid, api_key, api_secret, spark_url, domain, question):
    """启动 WebSocket 客户端的主函数"""
    wsParam = Ws_Param(appid, api_key, api_secret, spark_url)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.question = question
    ws.domain = domain
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


# ==============================================================================
# --- 业务逻辑辅助函数 ---
# ==============================================================================
def extract_emotion_label(file_path):
    """从指定文件中提取情感标签"""
    if not os.path.exists(file_path):
        print(f"⚠️ 情感文件未找到: {file_path}. 默认使用 '中性'.")
        return "中性"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        match = re.search(r"标签：([^，]+)", content)
        if match:
            emotion = match.group(1).strip()
            print(f"🔊 从音频分析出的情感: '{emotion}'")
            return emotion
        else:
            print(f"⚠️ 无法从文件中提取情感标签. 默认使用 '中性'.")
            return "中性"
    except Exception as e:
        print(f"❌ 读取或解析情感文件时出错: {e}")
        return "中性"

def build_prompt(user_text, audio_emotion):
    """构建发送给灯灵Agent的Prompt"""
    prompt = f"""
你是一个富有同理心的灯灵Agent。你的任务是根据用户输入的文本和分析出的用户音频情感，来决定如何回应用户。

# 输入信息:
1. 用户输入的文本内容: "{user_text}"
2. 从用户语音中分析出的情感: "{audio_emotion}"

# 你的任务:
请综合以上两个信息，进行智能分析，并严格按照以下JSON格式返回三项内容：
1. `responseText`: 对用户进行回复的文本内容，要自然、符合灯灵的角色。
2. `lightColor`: 根据当前情景，选择一个最合适的灯光颜色。可选颜色：[红色, 橙色, 黄色, 绿色, 青色, 蓝色, 紫色, 白色, 粉色, 彩虹色]。
3. `soundEffect`: 根据当前情景，选择一个最合适的音效。可选音效：[Calm, Happy, Healing, Hypnosis, Memory, Relax, Sad]。

# 输出要求:
- 必须严格返回一个JSON对象。
- 不要包含任何JSON格式之外的额外解释、文字或代码块标记。
"""
    return prompt

def parse_llm_response_and_save(response_text, file_path):
    """
    尝试将LLM返回的文本解析为JSON对象，并保存到文件。
    LLM有时返回的不是严格的JSON，此函数会尽力提取。
    """
    try:
        # 找到JSON对象的开始和结束位置
        start_index = response_text.find('{')
        end_index = response_text.rfind('}') + 1
        if start_index != -1 and end_index != 0:
            json_str = response_text[start_index:end_index]
            result_data = json.loads(json_str)
            
            # 验证关键字段是否存在
            if all(k in result_data for k in ["responseText", "lightColor", "soundEffect"]):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                print(f"✅ LLM结果成功解析并保存至: {file_path}")
                return result_data
            else:
                print("❌ LLM返回的JSON缺少必要字段。")
                return None
        else:
            print("❌ LLM的回复中未找到有效的JSON格式。")
            return None
    except json.JSONDecodeError as e:
        print(f"❌ 解析LLM返回的JSON时出错: {e}. 回复内容: '{response_text}'")
        return None
    except Exception as e:
        print(f"❌ 处理或保存LLM响应时出错: {e}")
        return None

def manage_chat_history(role, content):
    """管理对话历史，防止超出长度限制"""
    global chat_history
    chat_history.append({"role": role, "content": content})
    # 简单的长度控制：只保留最近的10轮对话
    if len(chat_history) > 20: 
        chat_history = chat_history[-20:]
    return chat_history

# ==============================================================================
# --- 核心调用逻辑 ---
# ==============================================================================
def call_spark_llm(user_text):
    """
    封装了完整的LLM调用流程：构建prompt -> 调用API -> 解析结果
    """
    print("-" * 30)
    print(f"🧠 开始处理用户输入: '{user_text}'")

    # 1. 重置全局回复变量
    global llm_answer
    llm_answer = ""

    # 2. 获取音频情感
    audio_emotion = extract_emotion_label(AUDIO_EMOTION_FILE)

    # 3. 构建Prompt
    prompt = build_prompt(user_text, audio_emotion)
    print("📝 构建的Prompt (部分): " + prompt.splitlines()[2])

    # 4. 管理对话历史并获取当前要发送的内容
    question_for_api = manage_chat_history("user", prompt)

    # 5. 调用讯飞星火大模型
    print("🚀 正在调用讯飞星火大模型...")
    try:
        run_spark_main(
            appid=SPARK_APPID,
            api_key=SPARK_API_KEY,
            api_secret=SPARK_API_SECRET,
            spark_url=SPARK_URL,
            domain=SPARK_DOMAIN,
            question=question_for_api
        )
        print(f"🤖 大模型原始回复: '{llm_answer}'")
        
        # 将模型回复也加入历史
        manage_chat_history("assistant", llm_answer)

    except Exception as e:
        print(f"❌ 调用讯飞星火API时发生严重错误: {e}")
        return None

    # 6. 解析LLM的回复
    if llm_answer:
        parsed_result = parse_llm_response_and_save(llm_answer, LLM_RESULT_FILE)
        return parsed_result
    else:
        print("❌ 大模型未返回任何内容。")
        return None

# ==============================================================================
# --- Flask Web 服务器 ---
# ==============================================================================
app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask_endpoint():
    """接收来自树莓派的问题，处理后将回复发回"""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "请求格式错误，需要'text'字段"}), 400

    question_text = data['text']
    print(f"\n\n- - - 新的请求 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - - -")
    print(f"💬 收到来自树莓派的问题: '{question_text}'")

    # 1. 调用LLM处理问题，获取包含指令的JSON对象
    llm_result = call_spark_llm(question_text)

    if not llm_result:
        error_message = "抱歉，我的大脑暂时无法连接，请稍后再试。"
        # 即使LLM失败，也尝试给树莓派一个友好的文本回复
        llm_result = {"responseText": error_message, "lightColor": "白色", "soundEffect": "Sad"}

    # 2. 将LLM的完整结果(JSON)发送回树莓派
    try:
        print(f"🗣️ 正在将完整指令发送到树莓派: {PI_RESPONSE_URL}")
        print(f"   发送内容: {json.dumps(llm_result, ensure_ascii=False)}")
        requests.post(PI_RESPONSE_URL, json=llm_result, timeout=10)
        print("✅ 指令已成功发送至树莓派。")
        return jsonify({"status": "success", "message": "Processed and sent to Pi"}), 200
        
    except requests.RequestException as e:
        print(f"❌ 发送指令到树莓派失败: {e}")
        return jsonify({"status": "error", "message": "Failed to send command to Pi"}), 500

# ==============================================================================
# --- 程序入口 ---
# ==============================================================================
if __name__ == '__main__':
    # 启动前检查
    # if "c73d990e" in SPARK_APPID:
    #     print("⚠️ 警告：请将讯飞星火的 APPID, API_KEY, API_SECRET 替换为您自己的密钥！")
    
    print("\n--- 智能灯灵 PC 大脑服务器已启动 ---")
    print(f"   监听地址: http://0.0.0.0:{PC_PORT}")
    print(f"   树莓派目标地址: {PI_RESPONSE_URL}")
    print(f"   情感分析文件路径: {AUDIO_EMOTION_FILE}")
    print("-" * 40)
    
    # 以生产模式启动服务器，如果你在开发，可以使用 app.run(host='0.0.0.0', port=PC_PORT, debug=True)
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=PC_PORT)
    app.run(host='0.0.0.0', port=PC_PORT, debug=True)