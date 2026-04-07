import io
import traceback
from PIL import Image
from authenticity import analyze_image_authenticity
from heatmap import generate_heatmap

def diagnose():
    print("--- [DIAGNOSING IMAGE AXIS] ---")
    img = Image.new('RGB', (200, 200), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    img_bytes = buf.getvalue()

    print("\n1. Testing analyze_image_authenticity...")
    try:
        res = analyze_image_authenticity(img_bytes)
        print("Success!")
        print(f"Verdict: {res.get('verdict')}")
    except Exception:
        print("FAILED!")
        traceback.print_exc()

    print("\n2. Testing generate_heatmap...")
    try:
        res = generate_heatmap(img_bytes)
        print("Success!")
        print(f"Assessment: {res.get('overall_assessment')}")
    except Exception:
        print("FAILED!")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
