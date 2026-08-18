from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def call_deepseek(prompt: str, max_tokens: int = None, reasoning_effort: str = "medium") -> dict:
    """
    Call DeepSeek-V4-Flash with reasoning/thinking enabled.

    Args:
        prompt: The user prompt text
        max_tokens: Max tokens to generate (defaults to MAX_DEEPSEEK_TOKENS from .env)
        reasoning_effort: Reasoning effort level ("low", "medium", "high")

    Returns:
        dict with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment")

    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_DEEPSEEK_TOKENS", 32768))

    model_id = "deepseek-v4-flash"
    client = OpenAI(base_url="https://api.deepseek.com", api_key=api_key)

    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "enabled"}, "reasoning_effort": reasoning_effort},
        max_tokens=max_tokens,
        stream=False
    )

    reasoning_trace = response.choices[0].message.content or ""

    return {
        "reasoning_trace": reasoning_trace,
        "metadata": {
            "model": model_id,
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "completion_tokens": response.usage.completion_tokens if response.usage else None,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
        }
    }


if __name__ == "__main__":
    # Test call
    result = call_deepseek("Explain quantum computing in simple terms.")
    print(result["reasoning_trace"])