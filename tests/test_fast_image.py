import requests, io
from PIL import Image

# Ensure server is running locally on port 8000 before running this test

def test_fast_image():
    img = Image.new('RGB',(64,64),(200,100,50))
    b = io.BytesIO(); img.save(b,'JPEG'); b.seek(0)
    files={'image':('fast.jpg',b,'image/jpeg')}
    data={'claim':'fast test','fast':'true'}
    r = requests.post('http://127.0.0.1:8000/analyze/image', data=data, files=files, timeout=60)
    assert r.status_code == 200
    j = r.json()
    # fast path should include heatmap and task_timings
    assert 'heatmap' in j
    assert 'task_timings' in j or 'task_errors' in j
