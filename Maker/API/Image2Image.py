import os
import requests
import time

# 配置API Key (请替换为您的实际API Key)
API_KEY = "your_api_key_here"

# 异步API端点
GENERATION_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation"
TASK_QUERY_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/"

def get_api_key():
    """从环境变量获取API Key"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("未找到环境变量 DASHSCOPE_API_KEY，请先配置")
    return api_key
API_KEY = get_api_key()
def generate_image(image_url, style_index, style_ref_url=None):
    """
    创建图像生成任务
    :param image_url: 输入图像URL
    :param style_index: 风格索引 (-1到9)
    :param style_ref_url: 参考风格图像URL (当style_index=-1时必需)
    :return: 任务ID
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-DashScope-Async": "enable",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "wanx-style-repaint-v1",
        "input": {
            "image_url": image_url,
            "style_index": style_index
        }
    }

    # 如果使用参考风格图像
    if style_index == -1 and style_ref_url:
        payload["input"]["style_ref_url"] = style_ref_url

    response = requests.post(GENERATION_URL, headers=headers, json=payload)
    response.raise_for_status()

    result = response.json()
    task_id = result["output"]["task_id"]
    print(f"任务已创建，任务ID: {task_id}")
    return task_id


def query_task_result(task_id, max_retries=30, interval=2):
    """
    查询任务结果
    :param task_id: 任务ID
    :param max_retries: 最大重试次数
    :param interval: 查询间隔(秒)
    :return: 生成结果或None
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    for i in range(max_retries):
        response = requests.get(f"{TASK_QUERY_URL}{task_id}", headers=headers)
        response.raise_for_status()

        result = response.json()
        status = result["output"]["task_status"]

        if status == "SUCCEEDED":
            print("任务处理成功!")
            return result["output"]["results"][0]["url"]
        elif status in ["PENDING", "RUNNING"]:
            print(f"任务处理中... (尝试 {i + 1}/{max_retries})")
            time.sleep(interval)
        else:
            error_msg = result["output"].get("message", "未知错误")
            raise Exception(f"任务处理失败: {error_msg}")

    raise Exception("任务处理超时")


def download_image(image_url, save_path):
    """下载图片并保存到本地"""
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"图片已保存到: {save_path}")
        return True
    except Exception as e:
        print(f"下载图片失败: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # 示例调用 - 使用预定义风格
        # input_image = "https://public-vigen-video.oss-cn-shanghai.aliyuncs.com/public/dashscope/test.png"
        # style_idx = 3  # 小清新风格

        # 示例调用 - 使用自定义参考风格
        input_image = "https://images.cnblogs.com/cnblogs_com/blogs/844253/galleries/2464931/o_250703050005_1.jpg"
        style_idx = -1
        style_ref = "https://images.cnblogs.com/cnblogs_com/blogs/844253/galleries/2464931/o_250703045940_style.jpg"

        print("正在创建图像生成任务...")
        task_id = generate_image(input_image, style_idx, style_ref)

        print("查询任务结果...")
        result_url = query_task_result(task_id)

        print(f"\n生成图像URL: {result_url}")
        print("注意: 生成的图像URL将在24小时后失效，请及时下载保存")

    except Exception as e:
        print(f"发生错误: {str(e)}")