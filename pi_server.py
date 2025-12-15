# pi_assistant.py
import pyaudio
import wave
import whisper
import threading
import time # 引入time模块
from gpiozero import Button
from signal import pause
import os
import sys
from contextlib import contextmanager
import requests
from flask import Flask, request, jsonify
import http.client
import urllib.parse

# --- 配置 ---
# ... (其他配置保持不变) ...
# GPIO
BUTTON_PIN = 17
# 文件路径
RECORDING_FILENAME = "/home/yzb/Desktop/zzm/user_recording.wav"
RESPONSE_AUDIO_FILENAME = "/home/yzb/Desktop/zzm/ai_response.wav"
# 为音效文件创建一个目录
SOUND_EFFECTS_DIR = "/home/yzb/Desktop/zzm/sound_effects"
os.makedirs(SOUND_EFFECTS_DIR, exist_ok=True)
# Whisper 模型
MODEL_TYPE = "tiny"
# PC服务器地址
PC_IP = "192.168.79.178"
PC_PORT = 5000
PC_ASK_URL = f'http://{PC_IP}:{PC_PORT}/ask'
# 本机服务端口
PI_PORT = 5001
# 阿里云 TTS
ALI_APPKEY = 'n1hRVr4qn1NsR0LL'
ALI_TOKEN = '41b82fb0357c467ba7047359e27466d4'
# 音频参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 4096


# --- 全局变量 ---
is_recording = False
recording_thread = None
audio_instance = None
whisper_model = None
# ⬇️⬇️⬇️ 新增：背景音乐播放器实例 ⬇️⬇️⬇️
bgm_player = None

# --- 上下文管理器 ---
@contextmanager
def ignore_stderr():
    # ... (代码不变) ...
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# ===================================================================
#  模块一: 音频播放 (重构)
# ===================================================================

# ⬇️⬇️⬇️ 新增：背景音乐播放器类 ⬇️⬇️⬇️
class BackgroundMusicPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_playing = threading.Event()
        self.thread = None

    def _play_loop(self, filename, loop=False):
        try:
            while self.is_playing.is_set():
                wf = wave.open(filename, 'rb')
                if self.stream is None:
                    self.stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                               channels=wf.getnchannels(),
                                               rate=wf.getframerate(),
                                               output=True)
                data = wf.readframes(CHUNK)
                while data and self.is_playing.is_set():
                    self.stream.write(data)
                    data = wf.readframes(CHUNK)
                
                wf.close()
                if not loop:
                    break # 如果不循环，播放一次后退出
            
        except Exception as e:
            print(f"❌ [BGM] 播放循环中出错: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            self.is_playing.clear()
            print("✅ [BGM] 播放线程已停止。")

    def play(self, filename, loop=True):
        if self.is_playing.is_set():
            self.stop()
            time.sleep(0.1) # 等待旧线程完全停止

        if not os.path.exists(filename):
            print(f"❌ [BGM] 文件不存在: {filename}")
            return

        print(f"🎶 [BGM] 开始在后台播放: {os.path.basename(filename)}")
        self.is_playing.set()
        self.thread = threading.Thread(target=self._play_loop, args=(filename, loop))
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.is_playing.is_set():
            print("🛑 [BGM] 正在停止背景音乐...")
            self.is_playing.clear()
            if self.thread:
                self.thread.join(timeout=1) # 等待线程结束
    
    def terminate(self):
        self.stop()
        self.p.terminate()

# 这个函数保持不变，用于播放需要等待的短音频（如TTS语音）
def play_audio(filename):
    """(阻塞式)播放WAV文件"""
    # ... (代码不变) ...
    if not os.path.exists(filename):
        print(f"❌ [播放] 文件不存在: {filename}")
        return
    print(f"🔊 [播放] 正在播放: {filename}")
    try:
        wf = wave.open(filename, 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(), rate=wf.getframerate(), output=True)
        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("✅ [播放] 播放完成。")
    except Exception as e:
        print(f"❌ [播放] 播放音频时出错: {e}")

def text_to_speech_and_play(text, save_path, resume_bgm_file=None): # <--- 增加参数
    """调用阿里云TTS并将文本转为语音，然后(阻塞式)播放。播放完毕后可选择性地恢复BGM。"""
    
    # 停止背景音乐，以免和TTS语音冲突
    if bgm_player and bgm_player.is_playing.is_set():
        print("🟡 [TTS] 播放语音前，暂停背景音乐。")
        bgm_player.stop()

    # --- TTS合成部分，保持不变 ---
    if not text:
        print("🟡 [TTS] 文本为空，跳过语音合成。")
        # 即使文本为空，如果需要，也要恢复BGM
        if resume_bgm_file and os.path.exists(resume_bgm_file):
            print("🎶 [BGM] 恢复背景音乐播放。")
            bgm_player.play(resume_bgm_file, loop=True)
        return
        
    print(f"🗣️ [TTS] 准备合成语音: '{text[:30]}...'")
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'
    url = f'https://{host}/stream/v1/tts'
    text_encoded = urllib.parse.quote_plus(text)
    request_url = f"{url}?appkey={ALI_APPKEY}&token={ALI_TOKEN}&text={text_encoded}&format=wav&sample_rate=16000"
    
    try:
        conn = http.client.HTTPSConnection(host)
        conn.request(method='GET', url=request_url)
        response = conn.getresponse()
        
        if response.status == 200:
            body = response.read()
            with open(save_path, mode='wb') as f:
                f.write(body)
            print(f"✅ [TTS] 语音合成成功，已保存。")
            play_audio(save_path) # 使用阻塞式播放
        else:
            print(f"❌ [TTS] 请求失败: {response.status} {response.reason}")
    except Exception as e:
        print(f"❌ [TTS] 语音合成时发生网络错误: {e}")
    
    # --- 播放完毕后，检查是否需要恢复BGM ---
    if resume_bgm_file and os.path.exists(resume_bgm_file):
        print("🎶 [BGM] 恢复背景音乐播放。")
        # 加一个短暂延时，让语音和BGM之间有个自然的间隔
        time.sleep(0.5) 
        bgm_player.play(resume_bgm_file, loop=True)
# ===================================================================
#  模块二: 接收并执行PC指令
# ===================================================================
app = Flask(__name__)

def execute_light_command(color_name):
    # ... (代码不变) ...
    print(f"💡 [灯光] 收到指令，设置灯光颜色为: {color_name}")
    pass

# ⬇️⬇️⬇️ 修改 execute_sound_effect 函数 ⬇️⬇️⬇️
def execute_sound_effect(effect_name):
    """
    使用BGM播放器在后台播放音效。
    返回播放的音频文件路径，如果未播放则返回None。
    """
    global bgm_player
    bgm_file_to_resume = None # <--- 新增：用于记录文件路径的变量

    if effect_name and effect_name != "无":
        effect_file = os.path.join(SOUND_EFFECTS_DIR, f"{effect_name}.wav")
        if os.path.exists(effect_file):
            # 使用我们的BGM播放器来播放，不会阻塞
            bgm_player.play(effect_file, loop=True)
            bgm_file_to_resume = effect_file # <--- 记录下这个路径
        else:
            print(f"🟡 [音效] 警告: 未找到音效文件 '{effect_file}'")
            bgm_player.stop() # 确保没有残留音乐
    else:
        # 如果指令是“无”，则停止当前播放的音乐
        bgm_player.stop()
    
    return bgm_file_to_resume # <--- 返回路径

def command_executor_task(command_data):
    """在新线程中按顺序执行收到的指令，并处理BGM的暂停与恢复。"""
    # 1. 提取指令
    text_to_speak = command_data.get('responseText', '我不知道该说什么。')
    light_color = command_data.get('lightColor', '白色')
    sound_effect = command_data.get('soundEffect', '无')

    print(f"✅ [指令中心] 已接收指令: 朗读='{text_to_speak[:20]}...', 灯光='{light_color}', 音效='{sound_effect}'")
    
    # 2. 执行灯光和音效指令
    execute_light_command(light_color)
    # 调用音效函数，并获取需要恢复的BGM文件路径
    bgm_to_resume = execute_sound_effect(sound_effect) # <--- 获取返回的路径
    
    # 因为BGM已经开始播放，这里可以加个短暂的延时，让用户先感受到氛围
    # 如果没有BGM，就没必要等了
    if bgm_to_resume:
        time.sleep(0.5) 
    
    # 3. 执行TTS和播放，并告诉它播放完后要恢复哪个BGM
    text_to_speech_and_play(text_to_speak, RESPONSE_AUDIO_FILENAME, resume_bgm_file=bgm_to_resume) # <--- 传入路径

@app.route('/receive_command', methods=['POST'])
def receive_command_endpoint():
    # ... (代码不变) ...
    command_data = request.get_json()
    if not command_data:
        return jsonify({"status": "error", "message": "No data received."}), 400
    threading.Thread(target=command_executor_task, args=(command_data,)).start()
    return jsonify({"status": "ok", "message": "Command received and processing started."})

def run_flask_app():
    # ... (代码不变) ...
    print(f"--- 树莓派指令接收服务已启动 ---")
    print(f"监听地址: http://0.0.0.0:{PI_PORT}")
    app.run(host='0.0.0.0', port=PI_PORT)

# ===================================================================
#  模块三: 按钮录音并发送
# ===================================================================
def process_and_send_task(filename):
    # ... (代码不变) ...
    print("\n🎤 [工作流] 开始处理录音...")
    try:
        # ... (whisper转录和发送代码不变) ...
        print("📝 [Whisper] 正在转录音频...")
        result = whisper_model.transcribe(filename, fp16=False)
        user_text = result["text"].strip()
        if not user_text:
            print("- [Whisper] 未识别到有效内容。")
            return
        print(f"👤 [Whisper] 识别结果: {user_text}")
        print(f"📤 [网络] 正在发送文本到PC: {PC_ASK_URL}")
        requests.post(PC_ASK_URL, json={'text': user_text}, timeout=15)
        print("✅ [网络] 文本已发送。等待PC回复指令...")
    except requests.RequestException as e:
        print(f"❌ [网络] 无法连接到PC服务器: {e}")
        text_to_speech_and_play("网络好像出问题了，无法连接到我的大脑。", RESPONSE_AUDIO_FILENAME)
    except Exception as e:
        print(f"❌ [工作流] 处理音频时发生严重错误: {e}")

def record_task():
    # ... (代码不变) ...
    global is_recording
    stream = audio_instance.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    wf = wave.open(RECORDING_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio_instance.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    print(">> [录音] 录音中... 松开按钮停止。")
    while is_recording:
        data = stream.read(CHUNK, exception_on_overflow=False)
        wf.writeframes(data)
    print(">> [录音] 录音结束，正在保存文件...")
    stream.stop_stream()
    stream.close()
    wf.close()

# ⬇️⬇️⬇️ 修改 start_recording 函数 ⬇️⬇️⬇️
def start_recording():
    global is_recording, recording_thread, bgm_player
    if is_recording: return
    
    # 在开始录音前，停止背景音乐
    if bgm_player and bgm_player.is_playing.is_set():
        bgm_player.stop()

    is_recording = True
    print("\n[按钮按下] 开始录音...")
    recording_thread = threading.Thread(target=record_task)
    recording_thread.start()

def stop_recording():
    # ... (代码不变) ...
    global is_recording
    if not is_recording: return
    print("[按钮松开] 正在停止录音...")
    is_recording = False
    recording_thread.join()
    if os.path.exists(RECORDING_FILENAME) and os.path.getsize(RECORDING_FILENAME) > 44:
        threading.Thread(target=process_and_send_task, args=(RECORDING_FILENAME,)).start()
    else:
        print("[主逻辑] 录音文件无效，取消发送。")


# --- 主程序 ---
# if __name__ == "__main__":
#     print("--- 树莓派智能灯灵客户端 ---")
    
#     flask_thread = threading.Thread(target=run_flask_app)
#     flask_thread.daemon = True
#     flask_thread.start()
    
#     print("正在初始化音频系统...")
#     with ignore_stderr():
#         audio_instance = pyaudio.PyAudio()
#         # ⬇️⬇️⬇️ 初始化我们的播放器 ⬇️⬇️⬇️
#         bgm_player = BackgroundMusicPlayer()
#     print("音频系统准备就绪。")

#     print("正在加载 Whisper 模型...")
#     whisper_model = whisper.load_model(MODEL_TYPE)
#     print("模型加载完毕。")

#     button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.1)
#     button.when_pressed = start_recording
#     button.when_released = stop_recording

#     print("\n✅ 系统准备就绪！请按住按钮提问。")
#     print("按 Ctrl+C 退出程序。")

#     try:
#         pause()
#     except KeyboardInterrupt:
#         print("\n程序被用户中断。")
#     finally:
#         print("正在清理资源...")
#         button.close()
#         if bgm_player:
#             bgm_player.terminate()
#         if audio_instance:
#             # PyAudio 实例已经在 BGM 播放器中管理，这里无需再次 terminate
#             pass
#         print("程序安全退出。")

if __name__ == "__main__":
    print("--- 树莓派智能灯灵客户端 ---")
    
    # 初始化一个事件，用于通知所有后台线程退出
    shutdown_event = threading.Event()

    # 1. 修改 run_flask_app，让它能响应退出事件
    def run_flask_app():
        print(f"--- 树莓派指令接收服务已启动 ---")
        print(f"监听地址: http://0.0.0.0:{PI_PORT}")
        # 使用 waitress，一个更健壮的服务器
        from waitress import serve
        serve(app, host='0.0.0.0', port=PI_PORT, _quiet=True)

    # 2. 启动后台服务
    flask_thread = threading.Thread(target=run_flask_app)
    # 不再将 flask 线程设置为 daemon，我们将手动管理它的关闭
    # flask_thread.daemon = True 
    flask_thread.start()
    
    # 3. 初始化硬件和模型
    print("正在初始化音频系统...")
    with ignore_stderr():
        audio_instance = pyaudio.PyAudio()
        bgm_player = BackgroundMusicPlayer()
    print("音频系统准备就绪。")

    print("正在加载 Whisper 模型...")
    whisper_model = whisper.load_model(MODEL_TYPE)
    print("模型加载完毕。")

    button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.1)
    button.when_pressed = start_recording
    button.when_released = stop_recording

    print("\n✅ 系统准备就绪！请按住按钮提问。")
    print("按 Ctrl+C 退出程序。")

    # 4. 主循环，等待退出信号
    try:
        # pause() 函数在这里有时不太可靠，我们用一个循环来等待事件
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[主程序] 检测到用户中断 (Ctrl+C)...")
    finally:
        print("\n[主程序] 开始优雅退出流程...")
        shutdown_event.set() # 通知所有线程该退出了

        # 5. 清理资源 (按正确的顺序)

        # a. 停止硬件交互
        print("[清理] 关闭按钮...")
        button.close()

        # b. 停止所有自定义的后台服务
        print("[清理] 停止背景音乐播放器...")
        if 'bgm_player' in locals() and bgm_player:
            bgm_player.terminate()

        # c. 停止Flask服务器
        # 由于 waitress 没有内置的 shutdown 方法，我们无法从外部优雅停止它。
        # 但因为它运行在非守护线程中，我们不再需要显式停止它。
        # 程序退出时，该线程也会自然结束。
        # 如果你使用的是支持 shutdown 的服务器（如 werkzeug 的开发服务器），可以在这里调用 shutdown。
        print("[清理] Flask 服务器线程将随主程序退出。")

        # d. 等待后台线程结束
        # 这里我们给一点时间让打印等操作完成
        time.sleep(0.5)

        # e. 清理pyaudio实例 (它已经被bgm_player.terminate()处理了)
        # if audio_instance:
        #     audio_instance.terminate()

        print("✅ [主程序] 程序安全退出。")