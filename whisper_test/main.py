import pyaudio
import wave
import whisper # 引入 whisper
import threading
from gpiozero import Button
from signal import pause
import os # 引入 os 来检查文件
from contextlib import contextmanager #去除烦人的alsa
import sys

# --- 配置 ---
BUTTON_PIN = 17
AUDIO_FILENAME = "/home/yzb/Desktop/zzm/recording_hold.wav"
MODEL_TYPE = "base" 
transcript_filename = "/home/yzb/Desktop/zzm/recorded_transcript.txt"

# 音频参数
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100 
CHUNK = 4096

# 定义一个上下文管理器来抑制标准错误输出
@contextmanager
def ignore_stderr():
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

# --- 全局变量 ---
is_recording = False
recording_thread = None

# 使用上下文管理器来初始化 PyAudio，抑制ALSA错误
print("正在初始化 PyAudio...")
with ignore_stderr():
    audio_instance = pyaudio.PyAudio()
print("PyAudio 初始化完毕。")

# 初始化 Whisper 模型
print("正在加载 Whisper 模型...")
whisper_model = whisper.load_model(MODEL_TYPE)
print("模型加载完毕。")

def transcribe_task(filename):
    """
    这是一个耗时的任务，在独立的线程中运行。
    """
    print(f"\n[转录线程] 开始转录文件: {filename}")
    try:
        # 使用 aarch64 上的 CPU，FP16 不被支持是正常的，它会自动使用 FP32
        result = whisper_model.transcribe(filename, fp16=False)
        message = result["text"]
        print("识别结果: " + message)
        with open(transcript_filename, 'w', encoding="utf-8") as f:
            f.write(message)
        print(f"Transcript saved to {transcript_filename}")

    except Exception as e:
        print(f"[转录线程] 识别时发生错误: {e}")

def record_task():
    """录音线程的目标，负责所有耗时的录音工作。"""
    global is_recording
    stream, wave_file = None, None
    try:
        stream = audio_instance.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        wave_file = wave.open(AUDIO_FILENAME, 'wb')
        wave_file.setnchannels(CHANNELS)
        wave_file.setsampwidth(audio_instance.get_sample_size(FORMAT))
        wave_file.setframerate(RATE)
        
        print(">> [录音线程] 录音中...")
        while is_recording:
            data = stream.read(CHUNK, exception_on_overflow=False)
            wave_file.writeframes(data)
    finally:
        print(">> [录音线程] 录音结束，正在关闭文件...")
        if stream:
            stream.stop_stream()
            stream.close()
        if wave_file:
            wave_file.close()
        # is_recording 在这里已经被主线程设置为 False

def transcription_handler():
    """
    “监工”线程，负责等待录音完成，然后启动识别。
    """
    global recording_thread
    if recording_thread:
        # 等待录音线程完全结束（包括文件关闭）
        recording_thread.join()
        print("[监工] 检测到录音线程已结束。")
        
        # 检查文件是否存在且不为空
        if os.path.exists(AUDIO_FILENAME) and os.path.getsize(AUDIO_FILENAME) > 44: # 44字节是空的WAV文件头大小
            # 创建并启动一个新的线程来做耗时的识别工作
            # 这样就不会阻塞主线程或其他按钮事件
            threading.Thread(target=transcribe_task, args=(AUDIO_FILENAME,)).start()
        else:
            print("[监工] 录音文件无效或为空，取消识别。")

def start_recording():
    global is_recording, recording_thread
    if is_recording: return
    is_recording = True
    print("\n[按钮按下] 开始录音...")
    recording_thread = threading.Thread(target=record_task)
    recording_thread.start()

def stop_recording():
    global is_recording
    if not is_recording: return
    print("[按钮松开] 正在停止录音...")
    is_recording = False
    # 松开按钮时，我们不直接调用识别
    # 而是启动“监工”线程，让它去处理后续流程
    threading.Thread(target=transcription_handler).start()

# --- 主程序 ---
button = Button(BUTTON_PIN, pull_up=False, bounce_time=0.1)
button.when_pressed = start_recording
button.when_released = stop_recording

print("程序已启动。请按住按钮进行录音。")
print("按 Ctrl+C 退出程序。")

try:
    pause()
except KeyboardInterrupt:
    print("\n程序被用户中断。")
finally:
    print("开始清理程序资源...")
    if is_recording:
        is_recording = False
        if recording_thread:
            recording_thread.join()
    button.close()
    audio_instance.terminate()
    print("所有资源已清理，程序安全退出。")