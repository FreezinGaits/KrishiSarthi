import requests
import json
import os

API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.x.ai/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

data = {
    "messages": [
        {"role": "system", "content": "You are a test assistant."},
        {"role": "user", "content": "Testing connectivity."}
    ],
    "model": "grok-2-latest",
    "stream": False,
    "temperature": 0
}

try:
    print(f"POSTing to {BASE_URL}...")
    response = requests.post(BASE_URL, headers=headers, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
