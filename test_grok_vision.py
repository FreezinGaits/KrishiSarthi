
import asyncio
import base64
import httpx
import json
import os

API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-2-vision-1212" # Trying specific vision model

async def test_vision():
    # Create simple green image
    img_data = base64.b64encode(b'FakeImageData').decode('utf-8') 
    # Wait, fake image data might cause 400. Let's use real small image data.
    # 1x1 green pixel base64
    img_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mVk+M9QDwAD0wGQHcL0mgAAAABJRU5ErkJggg=="
    
    payload = {
        "model": "grok-2-latest", # Trying the one in config first
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_data}"}},
                ],
            },
        ],
        "max_tokens": 10,
    }
    
    print(f"Sending request to {BASE_URL} with model {payload['model']}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                BASE_URL, json=payload,
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_vision())
