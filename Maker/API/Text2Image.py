import requests

def generate_image(prompt, width=768, height=768, model='flux', seed=None):
    url = f"https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&seed={seed}"
    response = requests.get(url)
    if response.status_code == 200:
        with open('generated_image.jpg', 'wb') as file:
            file.write(response.content)
            print('Image downloaded!')
    else:
        print('Error:', response.status_code)
def refine_prompt(prompt):
    base = f"\"{prompt}\",请将这个句子转化为一副书法作品"
    return base

if __name__ == "__main__":
    prompt = refine_prompt("A beautiful sunset over the ocean")
    generate_image("福建省的地图", width=1280, height=720, model='turbo', seed=42)
