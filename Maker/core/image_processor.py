import requests
from pathlib import Path
from config import config

class ImageProcessor:
    def __init__(self):
        if not config.DASHSCOPE_API_KEY:
            raise ValueError("Missing API Key")

    def generate_image(self, image_url: str, style_index: int):
        """调用百炼API生成图片"""
        task_id = self._create_task(image_url, style_index)
        return self._download_result(task_id)
    
    def _create_task(self, image_url: str, style_index: int):
        headers={
            "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
            "X-DashScope-Async": "enable",
            "Content-Type": "application/json"
        }
        payload={
            "model": "wanx-style-repaint-v1",
            "input": {
                "image_url": image_url,
                "style_index": style_index
                }
        }
        if style_index == -1:
            style_ref = "https://images.cnblogs.com/cnblogs_com/blogs/844253/galleries/2464931/o_250703045940_style.jpg"
            payload["input"]["style_ref_url"] = style_ref
        response = requests.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation",
            headers=headers,
            json=payload
        )
        return response.json()["output"]["task_id"]
    
    def _download_result(self, task_id: str):
        """下载生成结果到本地"""
        local_path = config.LOCAL_STORAGE / f"generated_{task_id[:8]}.jpg"
        
        while True:
            response = requests.get(
                f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {config.DASHSCOPE_API_KEY}"}
            )
            data = response.json()
            
            if data["output"]["task_status"] == "SUCCEEDED":
                image_url = data["output"]["results"][0]["url"]
                with requests.get(image_url, stream=True) as img_r:
                    with open(local_path, 'wb') as f:
                        for chunk in img_r.iter_content(8192):
                            f.write(chunk)
                return local_path
            elif data["output"]["task_status"] == "FAILED":
                raise RuntimeError("Image generation failed")