# find_mic.py
import pyaudio

p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

print("找到的输入设备:")
for i in range(0, numdevices):
    device_info = p.get_device_info_by_host_api_device_index(0, i)
    if (device_info.get('maxInputChannels')) > 0:
        print(f"  Index: {i}, 名称: {device_info.get('name')}")

p.terminate()