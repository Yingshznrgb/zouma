import folium
import requests
import json
from amap import get_api_key
# 高德地图API配置（需申请Key）
AMAP_KEY = get_api_key()

# 加载 JSON 文件
def load_provinces(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# 查询省份编号
def query_province(province_name):
    file_path = 'sf.json'
    provinces = load_provinces(file_path)
    return provinces.get(province_name, None)
    

def get_province_by_address(address):
    """通过地址获取所属省份"""
    url = f"https://restapi.amap.com/v3/geocode/geo?address={address}&key={AMAP_KEY}"
    response = requests.get(url).json()
    if response["status"] == "1" and response["geocodes"]:
        # 提取省份信息（部分API直接返回province字段）
        location = response["geocodes"][0]["location"].split(",")
        lng, lat = location[0], location[1]
        # 逆地理编码获取详细行政信息（可选）
        reverse_url = f"https://restapi.amap.com/v3/geocode/regeo?location={lng},{lat}&key={AMAP_KEY}"
        reverse_resp = requests.get(reverse_url).json()
        province = reverse_resp["regeocode"]["addressComponent"].get("province", "未知")
        return province, (float(lat), float(lng))  # 返回省份和坐标
    return "未知", None

def show_province_map(province_name):
    """显示省份地图（示例：使用folium加载全国地图并高亮目标省份）"""
    # 实际项目中，这里应加载目标省份的GeoJSON边界数据
    # 简化示例：生成全国地图并标记中心点
    m = folium.Map(location=[35, 105], zoom_start=4)  # 中国中心坐标
    folium.Marker(
        location=[35, 105],  # 示例标记（实际应替换为省份中心坐标）
        popup=f"目标省份: {province_name}",
        icon=folium.Icon(color="red")
    ).add_to(m)
    m.save("province_map.html")
    print("地图已生成：province_map.html")

# 用户交互
if __name__ == "__main__":
    address = input("请输入地址：")
    province, coord = get_province_by_address(address)
    print(f"地址所属省份：{province}")
    if coord:
        show_province_map(province)
    else:
        print("无法获取地图数据")
    province_code = query_province(province)
    if province_code:
        print(f"省份 '{province}' 的编号是：{province_code}")
    else:
        print(f"未找到省份 '{province}' 的编号。")
