from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
MAX_TOKENS = int(os.getenv("MAX_DEEPSEEK_TOKENS"))

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=API_KEY
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "medium"
    },
    max_tokens=MAX_TOKENS,
    stream=False
)

print(response.choices[0].message.content)