import os, requests, base64, json
from dotenv import load_dotenv
load_dotenv()

from PIL import Image
import io

img = Image.new('RGB', (100, 100), color=(255, 0, 0))
buf = io.BytesIO()
img.save(buf, format='JPEG')
test_bytes = buf.getvalue()
test_b64 = base64.b64encode(test_bytes).decode()

lines = []

# Test HF alternative models for AI image detection
hf_key = os.environ.get("HF_API_KEY", "")
hf_models = [
    "microsoft/resnet-50",
    "google/vit-base-patch16-224",
    "nateraw/vit-age-classifier",
    "Falconsai/nsfw_image_detection",
    "openai/clip-vit-base-patch32",
]
for m in hf_models:
    try:
        r = requests.post(f"https://api-inference.huggingface.co/models/{m}",
                          headers={"Authorization": f"Bearer {hf_key}"}, data=test_bytes, timeout=20)
        lines.append(f"HF|{m}|{r.status_code}|{r.text[:150]}")
    except Exception as e:
        lines.append(f"HF|{m}|ERR|{str(e)[:100]}")

# Test OpenRouter models (find working vision ones)
or_key = os.environ.get("OPENROUTER_API_KEY", "")
or_models = [
    "meta-llama/llama-3.2-11b-vision-instruct",
    "meta-llama/llama-4-scout:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "google/gemma-3-12b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]
for m in or_models:
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://menacraft-trustcheck.app"},
            json={"model": m, "messages": [{"role":"user","content":"Say OK"}], "max_tokens": 5}, timeout=15)
        lines.append(f"OR|{m}|{r.status_code}|{r.text[:150]}")
    except Exception as e:
        lines.append(f"OR|{m}|ERR|{str(e)[:100]}")

with open("diag_out2.txt", "w") as f:
    f.write("\n".join(lines))
print("DONE")
