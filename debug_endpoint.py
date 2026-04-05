import io
import os
import asyncio
from fastapi import UploadFile
from app import endpoint_full_image

async def debug():
    # Mock data to simulate the request to endpoint_full_image
    from PIL import Image
    img = Image.new('RGB', (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    img_bytes = buf.getvalue()
    
    # Create a mock-UploadFile
    mock_file = UploadFile(filename="test.jpg", file=io.BytesIO(img_bytes))
    
    # We also need these parameters for endpoint_full_image:
    # claim: str = Form(""),
    # source_name: str = Form(""),
    # source_url: str = Form(""),
    # claimed_location: str = Form(""),
    
    print("Executing endpoint_full_image logic...")
    try:
        # Call the endpoint directly with our parameters
        # In actual FastAPI, 'await image.read()' is called. Our mock_file must return bytes.
        result = await endpoint_full_image(
            image=mock_file,
            claim="Test claim",
            source_name="Test Source",
            source_url="http://test.com",
            claimed_location="Test Location"
        )
        print("Success! Result:")
        print(result)
    except Exception as e:
        print("CRASHED with exception:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
