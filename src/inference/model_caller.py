"""Model calling logic for DeepSeek, Qwen, and GPT-OSS."""

from models.call_deepseek import call_deepseek
from models.call_qwen import call_qwen
from models.call_gpt_oss import call_gpt_oss


def call_model(model_name: str, prompt: str, max_tokens: int = None, **kwargs) -> dict:
    """
    Unified interface for calling any supported model.

    Args:
        model_name: One of "deepseek", "qwen", "gpt"
        prompt: The prompt text
        max_tokens: Max tokens to generate
        **kwargs: Model-specific parameters (reasoning_effort, enable_thinking, etc.)

    Returns:
        dict with keys: reasoning_trace, metadata
    """
    if model_name == "deepseek":
        return call_deepseek(prompt, max_tokens=max_tokens, **kwargs)
    elif model_name == "qwen":
        return call_qwen(prompt, max_tokens=max_tokens, **kwargs)
    elif model_name == "gpt":
        return call_gpt_oss(prompt, max_tokens=max_tokens, **kwargs)
    else:
        raise ValueError(f"Unknown model: {model_name}. Choose from: deepseek, qwen, gpt")
