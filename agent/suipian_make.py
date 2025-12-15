# -*- coding: utf-8 -*-
# 经过修改，用于生成旅行碎片的新功能代码
# 会读入地点关键字的文件内容作为输入

import _thread as thread
import os
import base64
import datetime
import hashlib
import hmac
import json
from urllib.parse import urlparse
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
import websocket  # 使用websocket_client

# --- 全局变量 ---
# 用于存储API返回的完整答案
answer = ""
# 用于处理流式输出的标志
isFirstcontent = False

# 地点关键字所在的文件地址
LOCATION_FILE = "location.txt"

class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    # 生成url
    def create_url(self):
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        # 拼接字符串
        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        # 拼接鉴权参数，生成url
        url = self.Spark_url + '?' + urlencode(v)
        return url

# --- 新功能函数 ---

def read_location_from_file(file_path=LOCATION_FILE):
    """从指定文件读取地点关键词"""
    try:
        if not os.path.exists(file_path):
            print(f"错误: 地点文件 '{file_path}' 不存在。请创建该文件并写入一个地点。")
            return None
        
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                print(f"错误: 地点文件 '{file_path}' 为空。")
                return None
            print(f"成功读取地点: 【{content}】")
            return content
            
    except Exception as e:
        print(f"读取地点文件时发生异常: {e}")
        return None

def build_travel_prompt(location_name):
    """
    为旅行碎片功能构建专属的Prompt。
    """
    prompt = f"""
你是一位充满创意的旅行体验设计师。你的任务是为一个特定的地点生成引导用户沉浸式体验的“任务碎片”。

# 地点:
{location_name}

# 你的任务:
请将这个地点想象成一个充满秘密和故事的旅行目的地。你需要创造5个“碎片”，引导用户通过视觉、听觉和感悟去探索它，以达到提供用户更好的旅行体验。每个碎片尽量用简短的话语概括，限制在15个字以内，请严格按照以下要求和JSON格式返回内容：

1.  **生成5个碎片**：
    *   3个 **视觉碎片**：结合当地特色，描述三个具体的、需要用户去寻找和拍照的地点、美食、文化等等，最好要包含用户自己的出境照片。例如，“鸣沙山的日落剪影”、“红叶下的和服留影”、“一份精致的怀石料理”。
    *   1个 **音频碎片**：描述一种用户需要用心聆听的声音，最好具有当地特色。例如，“闭上眼睛，聆听风吹过古老城墙的呼啸声”或“岚山竹林的风声”或“古老驼铃的声响”。
    *   1个 **文字感悟碎片**：提出一个引导用户进行思考或记录的问题。例如，“站在这里，你感觉时间流逝的速度是变快了还是变慢了？写下你的感受。”

2.  **输出格式要求**:
    *   **必须** 返回一个严格的JSON对象。
    *   JSON对象中**必须**包含一个名为 "shards" 的键。
    *   "shards" 键对应的值**必须**是一个包含5个字符串元素的列表。
    *   列表的顺序应为：[视觉碎片1, 视觉碎片2, 视觉碎片3, 音频碎片, 文字感悟碎片]。
    *   **不要**在JSON之外包含任何解释、说明、注释或markdown标记（如 ```json ... ```）。

# 输出示例:
{{
  "shards": [
    "视觉碎片描述1",
    "视觉碎片描述2",
    "视觉碎片描述3",
    "音频碎片描述",
    "文字感悟碎片描述"
  ]
}}
"""
    return prompt

def parse_and_save_fragments(json_string):
    """
    解析API返回的JSON字符串，并分别保存5个碎片到独立文件。
    """
    print("\n--- 开始解析和保存碎片 ---")
    try:
        # 清理可能的markdown代码块标记
        if json_string.strip().startswith("```json"):
            json_string = json_string.strip()[7:-3].strip()
        
        data = json.loads(json_string)
        
        if "shards" not in data or not isinstance(data["shards"], list):
            print("错误: 返回的JSON格式不正确，缺少 'shards' 列表。")
            print("收到的内容:", json_string)
            return

        fragments = data["shards"]
        if len(fragments) != 5:
            print(f"警告: 期望收到5个碎片，但实际收到了{len(fragments)}个。")
            print("收到的内容:", json_string)
            # 即使数量不对，也尝试保存已有的
        
        # 确保输出目录存在
        output_dir = "fragments"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        for i, fragment_text in enumerate(fragments):
            file_path = os.path.join(output_dir, f"fragment_{i+1}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fragment_text)
            print(f"碎片 {i+1} 已成功保存到: {file_path}")

        print("--- 所有碎片已保存完毕 ---")

    except json.JSONDecodeError:
        print("错误: API返回的不是有效的JSON格式。")
        print("收到的原始文本内容:\n", json_string)
    except Exception as e:
        print(f"解析或保存文件时发生未知错误: {e}")

# --- Websocket 核心回调函数 (基本保持原样) ---

def on_error(ws, error):
    print("### error:", error)

def on_close(ws, one, two):
    print("### Websocket连接已关闭 ###")

def on_open(ws):
    thread.start_new_thread(run, (ws,))

def run(ws, *args):
    data = json.dumps(gen_params(appid=ws.appid, domain=ws.domain, question=ws.question))
    ws.send(data)

def on_message(ws, message):
    data = json.loads(message)
    code = data['header']['code']
    
    if code != 0:
        print(f'请求错误: {code}, {data}')
        ws.close()
        return

    choices = data["payload"]["choices"]
    status = choices["status"]
    content = choices['text'][0]['content']
    
    global answer
    answer += content
    print(content, end="") # 实时打印API返回的内容
    
    if status == 2:
        # 消息接收完毕
        ws.close()

# --- 参数生成和主调用函数 (基本保持原样) ---
def gen_params(appid, domain, question):
    """通过appid和用户的提问来生成请求参数"""
    data = {
        "header": {
            "app_id": appid,
            "uid": "1234", # uid可自定义
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.8, # 温度可以适当调整，0.8-1.2之间可以让创意更多样
                "max_tokens": 4096
            }
        },
        "payload": {
            "message": {
                "text": question
            }
        }
    }
    return data

def call_spark_api(appid, api_key, api_secret, spark_url, domain, question):
    """封装调用Spark API的过程"""
    wsParam = Ws_Param(appid, api_key, api_secret, spark_url)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.question = question
    ws.domain = domain
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# --- 对话历史管理 (保持原样，虽然本次只调用一次，但结构完整) ---
text_history = []
def getText(role, content):
    jsoncon = {"role": role, "content": content}
    text_history.append(jsoncon)
    return text_history

def getlength(text):
    length = 0
    for content in text:
        temp = content["content"]
        leng = len(temp)
        length += leng
    return length

def checklen(text):
    while (getlength(text) > 8000):
        del text[0]
    return text

# --- 新的主逻辑函数 ---
def run_travel_fragment_generator():
    """
    执行生成旅行碎片的完整流程。
    """
    # 1. 从文件读取地点
    location = read_location_from_file()
    if not location:
        return # 如果地点为空或文件不存在，则直接退出
    
    # 2. 根据地点构建Prompt
    prompt = build_travel_prompt(location)
    
    # 3. 准备发送给API的问题
    # 注意：对于单次任务，对话历史不是必须的，但我们沿用原结构
    question = checklen(getText("user", prompt))
    
    # 4. 调用API
    print("\n--- 正在向星火大模型发送请求... ---")
    global answer
    answer = "" # 每次调用前清空全局变量
    call_spark_api(appid, api_key, api_secret, Spark_url, domain, question)
    
    # 5. API调用结束后，处理返回的结果
    if answer:
        parse_and_save_fragments(answer)
    else:
        print("错误：未能从API获取到任何回复。")


if __name__ == '__main__':
    # --- 配置信息 ---
    # 请从讯飞星火控制台获取: https://console.xfyun.cn/services/bmx1
    appid = "c73d990e"  # 填写你的 APPID
    api_secret = "NTRkZDZmMTBhMTQzNTczMmMyMGI2NTA2"  # 填写你的 APISecret
    api_key = "a826d05bded10a9ea8f6943f4f0d3081"  # 填写你的 APIKey
    
    # 使用的模型版本和地址
    # domain可选值：x1(v1.5), x2(v2.0), x3(v3.0), x3_5(v3.5)
    domain = "4.0Ultra"
    Spark_url = "wss://spark-api.xf-yun.com/v4.0/chat"

    # --- 启动主流程 ---
    run_travel_fragment_generator()