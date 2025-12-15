# appkey:n1hRVr4qn1NsR0LL
# token:41b82fb0357c467ba7047359e27466d4
import pyaudio
import wave

# -*- coding: UTF-8 -*-
# Python 2.x引入httplib模块。
# import httplib
# Python 3.x引入http.client模块。
import http.client
# Python 2.x引入urllib模块。
# import urllib
# Python 3.x引入urllib.parse模块。
import urllib.parse
import json,os
from contextlib import contextmanager #去除烦人的alsa
import sys

target_file = "/home/yzb/Desktop/zzm/recorded_transcript.txt"
result_file = "answer_audio.wav"

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

def processGETRequest(appKey, token, text, audioSaveFile, format, sampleRate) :
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'
    url = 'https://' + host + '/stream/v1/tts'
    # 设置URL请求参数
    url = url + '?appkey=' + appKey
    url = url + '&token=' + token
    url = url + '&text=' + text
    url = url + '&format=' + format
    url = url + '&sample_rate=' + str(sampleRate)
    # voice 发音人，可选，默认是xiaoyun。
    # url = url + '&voice=' + 'xiaoyun'
    # volume 音量，范围是0~100，可选，默认50。
    # url = url + '&volume=' + str(50)
    # speech_rate 语速，范围是-500~500，可选，默认是0。
    # url = url + '&speech_rate=' + str(0)
    # pitch_rate 语调，范围是-500~500，可选，默认是0。
    # url = url + '&pitch_rate=' + str(0)
    print(url)
    # Python 2.x请使用httplib。
    # conn = httplib.HTTPSConnection(host)
    # Python 3.x请使用http.client。
    conn = http.client.HTTPSConnection(host)
    conn.request(method='GET', url=url)
    # 处理服务端返回的响应。
    response = conn.getresponse()
    # print('Response status and response reason:')
    # print(response.status ,response.reason)
    contentType = response.getheader('Content-Type')
    # print(contentType)
    body = response.read()
    if 'audio/mpeg' == contentType :
        with open(audioSaveFile, mode='wb') as f:
            f.write(body)
        print('The GET request succeed!')
    else :
        print('The GET request failed: ' + str(body))
    conn.close()
def processPOSTRequest(appKey, token, text, audioSaveFile, format, sampleRate) :
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'
    url = 'https://' + host + '/stream/v1/tts'
    # 设置HTTPS Headers。
    httpHeaders = {
        'Content-Type': 'application/json'
        }
    # 设置HTTPS Body。
    body = {'appkey': appKey, 'token': token, 'text': text, 'format': format, 'sample_rate': sampleRate}
    body = json.dumps(body)
    # print('The POST request body content: ' + body)
    # Python 2.x请使用httplib。
    # conn = httplib.HTTPSConnection(host)
    # Python 3.x请使用http.client。
    conn = http.client.HTTPSConnection(host)
    conn.request(method='POST', url=url, body=body, headers=httpHeaders)
    # 处理服务端返回的响应。
    response = conn.getresponse()
    # print('Response status and response reason:')
    # print(response.status ,response.reason)
    contentType = response.getheader('Content-Type')
    # print(contentType)
    body = response.read()
    if 'audio/mpeg' == contentType :
        with open(audioSaveFile, mode='wb') as f:
            f.write(body)
        print('The POST request succeed!')
    else :
        print('The POST request failed: ' + str(body))
    conn.close()
appKey = 'n1hRVr4qn1NsR0LL'
token = '621f49be03a64312bc7aa53d22531d38'
def speak(text_file,result_file):
    with open(text_file,'r',encoding='utf-8') as fp:
        text = fp.read()
    # 采用RFC 3986规范进行urlencode编码。
    textUrlencode = text
    # Python 2.x请使用urllib.quote。
    # textUrlencode = urllib.quote(textUrlencode, '')
    # Python 3.x请使用urllib.parse.quote_plus。
    textUrlencode = urllib.parse.quote_plus(textUrlencode)
    textUrlencode = textUrlencode.replace("+", "%20")
    textUrlencode = textUrlencode.replace("*", "%2A")
    textUrlencode = textUrlencode.replace("%7E", "~")
    # print('text: ' + textUrlencode)
    # audioSaveFile = 'output_syAudio.wav'
    audioSaveFile = result_file
    format = 'wav'
    sampleRate = 16000
    # GET请求方式
    processGETRequest(appKey, token, textUrlencode, audioSaveFile, format, sampleRate)
    # POST请求方式
    # processPOSTRequest(appKey, token, text, audioSaveFile, format, sampleRate)

    # 替换为你的录音文件路径
    # audio_file = "output_syAudio.wav"
    audio_file = result_file

    # 打开音频文件
    wf = wave.open(audio_file, 'rb')

    # 初始化PyAudio
    # 使用上下文管理器来初始化 PyAudio，抑制ALSA错误
    print("正在初始化 PyAudio...")
    with ignore_stderr():
        p = pyaudio.PyAudio()
    print("PyAudio 初始化完毕。")
    p = pyaudio.PyAudio()

    # 打开音频流
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # 读取音频数据并播放
    data = wf.readframes(1024)
    while data:
        stream.write(data)
        data = wf.readframes(1024)

    # 关闭音频流和PyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()
    print("播放完成")

if __name__ == '__main__':
    speak(target_file,result_file)