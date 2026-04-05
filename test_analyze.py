import requests
import os
from PIL import Image
import io

# URL for the local FastAPI server
URL = "http://localhost:8000/analyze/image"

# Path to the image we want to use for testing
# We'll create a small dummy image for testing
img = Image.new('RGB', (100, 100), color=(255, 0, 0))
buf = io.BytesIO()
img.save(buf, format='JPEG')
img_bytes = buf.getvalue()

# Data for the form
data = {
    "claim": "This is a test claim for analysis.",
    "source_name": "Test Source",
    "source_url": "http://example.com/test",
    "claimed_location": "Tunis, Tunisia"
}

# Files part of the POST request
files = {
    "image": ("test_image.jpg", img_bytes, "image/jpeg")
}

print(f"Sending test POST request to {URL}...")
try:
    response = requests.post(URL, data=data, files=files)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success! JSON response:")
        print(response.json())
    else:
        print(f"Error ({response.status_code}):")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
