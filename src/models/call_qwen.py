from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
import os

load_dotenv()

# Global model/tokenizer cache (lazy loaded)
_qwen_model = None
_qwen_tokenizer = None


def _load_qwen_model():
    """Lazy load Qwen model and tokenizer (heavy operation)."""
    global _qwen_model, _qwen_tokenizer

    if _qwen_model is None:
        model_id = "Qwen/Qwen3.8-27B"
        print(f"Loading Qwen model: {model_id}...", flush=True)
        _qwen_tokenizer = AutoTokenizer.from_pretrained(model_id)
        _qwen_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto"
        )
        _qwen_model.eval()
        print("Qwen model loaded.", flush=True)

    return _qwen_model, _qwen_tokenizer


def call_qwen(prompt: str, max_tokens: int = None, enable_thinking: bool = True) -> dict:
    """
    Call Qwen3.8-27B with thinking enabled.

    Args:
        prompt: The user prompt text
        max_tokens: Max new tokens to generate (defaults to MAX_QWEN_TOKENS from .env)
        enable_thinking: Whether to enable thinking mode

    Returns:
        dict with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_QWEN_TOKENS", 131072))

    model, tokenizer = _load_qwen_model()

    messages = [{"role": "user", "content": prompt}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
        return_tensors="pt",
        return_dict=True,
    ).to(model.device)

    output_ids = model.generate(**inputs, max_new_tokens=max_tokens)
    reasoning_trace = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )

    return {
        "reasoning_trace": reasoning_trace,
        "metadata": {
            "model": "Qwen/Qwen3.8-27B",
            "max_tokens": max_tokens,
            "enable_thinking": enable_thinking,
            "prompt_length": inputs["input_ids"].shape[-1],
            "generated_tokens": len(output_ids[0]) - inputs["input_ids"].shape[-1],
        }
    }


if __name__ == "__main__":
    # Test call
    result = call_qwen("Explain quantum computing in simple terms.")
    print(result["reasoning_trace"])