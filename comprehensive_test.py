import requests
import io
from PIL import Image
try:
    import numpy as np
    import wave
except ImportError:
    np = None
    wave = None

BASE_URL = "http://localhost:8000"

def test_root():
    print("--- [ROOT] ---")
    try:
        response = requests.get(f"{BASE_URL}/", allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Target URL: {response.url}")
        if response.status_code == 200:
            print("OK: Root/UI is active.")
        else:
            print(f"FAIL: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

def test_image_analysis():
    print("\n--- [IMAGE ANALYSIS] ---")
    img = Image.new('RGB', (200, 200), color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    img_bytes = buf.getvalue()

    files = {"image": ("test.jpg", img_bytes, "image/jpeg")}
    data = {"claim": "This is a test claim for image forensics."}

    try:
        response = requests.post(f"{BASE_URL}/analyze/image", files=files, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            res = response.json()
            print(f"Verdict: {res.get('verdict')}")
            print(f"AI Score: {res.get('ai_score')}")
            print(f"Heatmap present: {'heatmap_image_base64' in res.get('heatmap', {})}")
        else:
            print(f"FAIL: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

def test_audio_analysis():
    print("\n--- [AUDIO ANALYSIS] ---")
    # Generating a dummy .wav file
    buf = io.BytesIO()
    if wave:
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            # 1 second of noise
            data = (np.random.randn(44100) * 1000).astype(np.int16)
            wf.writeframes(data.tobytes())
    else:
        buf.write(b"RIFF dummy audio data")

    files = {"audio": ("test.wav", buf.getvalue(), "audio/wav")}

    try:
        response = requests.post(f"{BASE_URL}/analyze/voice", files=files)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            res = response.json()
            print(f"Verdict: {res.get('verdict')}")
            print(f"Interpretation: {res.get('interpretation')[:50]}...")
        else:
            print(f"FAIL: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

def test_certificate_generation():
    print("\n--- [CERTIFICATE GENERATION] ---")
    img = Image.new('RGB', (256, 256), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()

    files = {"image": ("report_test.png", img_bytes, "image/png")}
    data = {
        "claim": "Testing PDF certificate generation.",
        "source_name": "Test Suite",
        "source_url": "http://test.internal",
        "claimed_location": "Tunis Data Center"
    }

    try:
        response = requests.post(f"{BASE_URL}/report/certificate", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        if response.status_code == 200 and response.headers.get('Content-Type') == 'application/pdf':
            print("OK: PDF stream received correctly.")
            content_disp = response.headers.get('Content-Disposition')
            print(f"Filename Header: {content_disp}")
        else:
            print(f"FAIL: {response.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_root()
    test_image_analysis()
    # Skip audio if numpy/wave are missing, but let's try anyway
    test_audio_analysis()
    test_certificate_generation()
