import requests, io, time
from PIL import Image

img = Image.new('RGB',(128,128),(123,222,100))
b = io.BytesIO(); img.save(b,'JPEG'); b.seek(0)
files={'image':('test.jpg',b,'image/jpeg')}
data={'claim':'test claim','source_name':'me','source_url':'http://example.com','claimed_location':'Cairo'}
start=time.time()
try:
    r=requests.post('http://127.0.0.1:8000/analyze/image', data=data, files=files, timeout=180)
    print('STATUS', r.status_code)
    print('TIME', time.time()-start)
    try:
        print('JSON keys:', list(r.json().keys()) )
    except Exception as e:
        print('Non-JSON response:', r.text[:1000])
except Exception as e:
    print('Request failed:', e)
