import requests
import os
def get_api_key():
    """从环境变量获取API Key"""
    api_key = os.getenv("AMAP_KEY")
    if not api_key:
        raise ValueError("未找到环境变量 AMAP_KEY，请先配置")
    return api_key

def get_province_by_location(lng, lat):
    """通过经纬度获取省份信息（高德逆地理编码API）"""
    AMAP_KEY = get_api_key()
    url = f"https://restapi.amap.com/v3/geocode/regeo?location={lng},{lat}&key={AMAP_KEY}&radius=1000&extensions=base"
    response = requests.get(url)
    data = response.json()
    
    if data.get("status") == "1" and data.get("regeocode"):
        address = data["regeocode"]["addressComponent"]
        province = address.get("province", "").replace("市", "")  # 处理直辖市后缀（如“北京市”）
        city = address.get("city", "") if address.get("city") != address.get("province") else ""  # 避免重复显示直辖市
        district = address.get("district", "")
        return {
            "province": province,
            "city": city,
            "district": district,
            "formatted_address": data["regeocode"].get("formatted_address", "")
        }
    else:
        error_msg = data.get("info", "未知错误")
        raise ValueError(f"高德API调用失败: {error_msg}")
if __name__ == "__main__":
    # 示例：北京天安门坐标
    print(get_province_by_location(116.397428, 39.90923))
    # 输出: {'province': '北京市', 'city': '', 'district': '东城区', 'formatted_address': '北京市东城区东长安街...'}