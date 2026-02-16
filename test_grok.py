import os
from langchain_openai import ChatOpenAI

API_KEY = os.getenv("GROQ_API_KEY")
BASE_URL = "https://api.x.ai/v1"

try:
    print(f"Connecting to Grok at {BASE_URL}...")
    llm = ChatOpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        model="grok-2-latest",
        temperature=0.3
    )
    result = llm.invoke("Hello, who are you?")
    print("Success!")
    print(result.content)
except Exception as e:
    print(f"Error: {e}")
