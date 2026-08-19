from transformers import AutoModelForCausalLM, AutoTokenizer
from dotenv import load_dotenv
import os

load_dotenv()

# Global model/tokenizer cache (lazy loaded)
_gpt_model = None
_gpt_tokenizer = None


def _load_gpt_model():
    """Lazy load GPT-OSS model and tokenizer (heavy operation)."""
    global _gpt_model, _gpt_tokenizer

    if _gpt_model is None:
        model_id = "openai/gpt-oss-120b"
        print(f"Loading GPT-OSS model: {model_id}...", flush=True)
        _gpt_tokenizer = AutoTokenizer.from_pretrained(model_id)
        _gpt_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto"
        )
        _gpt_model.eval()
        print("GPT-OSS model loaded.", flush=True)

    return _gpt_model, _gpt_tokenizer


def call_gpt_oss(prompt: str, max_tokens: int = None, reasoning_effort: str = "medium") -> dict:
    """
    Call GPT-OSS-120B with reasoning effort enabled.

    Args:
        prompt: The user prompt text
        max_tokens: Max new tokens to generate (defaults to MAX_OPENAI_TOKENS from .env)
        reasoning_effort: Reasoning effort level ("low", "medium", "high")

    Returns:
        dict with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_OPENAI_TOKENS", 32768))

    model, tokenizer = _load_gpt_model()

    messages = [{"role": "user", "content": prompt}]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        reasoning_effort=reasoning_effort,
        return_tensors="pt",
        return_dict=True,
    ).to(model.device)

    output_ids = model.generate(**inputs, max_new_tokens=max_tokens)

    # Decode WITHOUT skipping special tokens first to capture any reasoning markers
    full_output_with_special = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=False
    )

    # Also decode with special tokens skipped (standard)
    output_clean = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[-1]:],
        skip_special_tokens=True
    )

    # GPT-OSS may use special tokens for reasoning sections
    # Check for common reasoning markers (<think>, <reasoning>, etc.)
    has_reasoning_tokens = any(
        marker in full_output_with_special
        for marker in ["<think>", "<reasoning>", "<thought>", "|im_start|"]
    )
    reasoning_trace = full_output_with_special if has_reasoning_tokens else output_clean

    return {
        "reasoning_trace": reasoning_trace,
        "metadata": {
            "model": "openai/gpt-oss-120b",
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "prompt_length": inputs["input_ids"].shape[-1],
            "generated_tokens": len(output_ids[0]) - inputs["input_ids"].shape[-1],
            "has_reasoning_tokens": has_reasoning_tokens,
        }
    }


if __name__ == "__main__":
    # Test call
    result = call_gpt_oss("Explain quantum computing in simple terms.")
    print(result["reasoning_trace"])