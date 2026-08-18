from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
MAX_TOKENS = int(os.getenv("MAX_QWEN_TOKENS"))

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3.8-27B",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": True
        }
    },
    max_tokens=MAX_TOKENS,
    stream=False
)

print(response.choices[0].message.content)