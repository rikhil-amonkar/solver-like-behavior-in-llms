"""Model calling logic for DeepSeek, Qwen, and GPT-OSS."""

from models.call_deepseek import call_deepseek
from models.call_qwen import call_qwen, call_qwen_batch
from models.call_gpt_oss import call_gpt_oss, call_gpt_oss_batch


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


def call_model_batch(model_name: str, prompts: list[str], max_tokens: int = None, **kwargs) -> list[dict]:
    """
    Unified interface for calling any supported model in batch mode.

    Batch mode is optimized for vLLM models (qwen, gpt) and falls back to
    sequential processing for API-based models (deepseek).

    Args:
        model_name: One of "deepseek", "qwen", "gpt"
        prompts: List of prompt texts
        max_tokens: Max tokens to generate
        **kwargs: Model-specific parameters (reasoning_effort, enable_thinking, etc.)

    Returns:
        List of dicts with keys: reasoning_trace, metadata
    """
    if model_name == "deepseek":
        # DeepSeek is API-based, no native batch support
        # Fall back to sequential calls
        return [call_deepseek(prompt, max_tokens=max_tokens, **kwargs) for prompt in prompts]
    elif model_name == "qwen":
        return call_qwen_batch(prompts, max_tokens=max_tokens, **kwargs)
    elif model_name == "gpt":
        return call_gpt_oss_batch(prompts, max_tokens=max_tokens, **kwargs)
    else:
        raise ValueError(f"Unknown model: {model_name}. Choose from: deepseek, qwen, gpt")
