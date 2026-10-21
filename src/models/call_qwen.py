from vllm import LLM, SamplingParams
from dotenv import load_dotenv
import os

load_dotenv()

# Global vLLM model cache (lazy loaded)
_qwen_llm = None

# Context window (prompt + generation); generation budgets are clamped to fit
MAX_MODEL_LEN = 131072


def _load_qwen_model():
    """Lazy load Qwen model with vLLM (heavy operation)."""
    global _qwen_llm

    if _qwen_llm is None:
        model_id = "Qwen/Qwen3.8-27B"
        print(f"Loading Qwen model with vLLM: {model_id}...", flush=True)

        # Get HF token if needed
        hf_token = os.getenv("HF_TOKEN", None)

        _qwen_llm = LLM(
            model=model_id,
            tokenizer=model_id,
            trust_remote_code=True,
            download_dir=None,  # Uses HF cache
            tokenizer_mode="auto",
            tensor_parallel_size=1,  # Adjust based on GPU count
            gpu_memory_utilization=0.9,
            max_model_len=MAX_MODEL_LEN,  # Qwen max context
            max_num_seqs=256,  # Reduce for memory constraints
            enforce_eager=False,  # Use CUDA graphs for speed
        )
        print("Qwen model loaded with vLLM.", flush=True)

    return _qwen_llm


def call_qwen(prompt: str, max_tokens: int = None, enable_thinking: bool = True) -> dict:
    """
    Call Qwen3.8-27B with vLLM (optimized inference).

    Args:
        prompt: The user prompt text
        max_tokens: Max new tokens to generate (defaults to MAX_QWEN_TOKENS from .env)
        enable_thinking: Whether to enable thinking mode (adds system prompt for reasoning)

    Returns:
        dict with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    # Single prompt: call batch version and return first result
    results = call_qwen_batch([prompt], max_tokens=max_tokens, enable_thinking=enable_thinking)
    return results[0]


def call_qwen_batch(prompts: list[str], max_tokens: int = None, enable_thinking: bool = True) -> list[dict]:
    """
    Call Qwen3.8-27B with vLLM in batch mode (optimized for multiple prompts).

    Args:
        prompts: List of user prompt texts
        max_tokens: Max new tokens to generate (defaults to MAX_QWEN_TOKENS from .env)
        enable_thinking: Whether to enable thinking mode (adds system prompt for reasoning)

    Returns:
        List of dicts with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_QWEN_TOKENS", 131072))

    llm = _load_qwen_model()
    tokenizer = llm.get_tokenizer()

    # Format all prompts
    formatted_prompts = []
    for prompt in prompts:
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        formatted_prompts.append(formatted_prompt)

    # Sampling parameters
    # One SamplingParams per prompt so long prompts don't push generation past the context window
    prompt_lengths = [len(tokenizer.encode(p)) for p in formatted_prompts]
    sampling_params = [
        SamplingParams(
            max_tokens=max(1, min(max_tokens, MAX_MODEL_LEN - n)),
            temperature=0.7,
            top_p=0.9,
            skip_special_tokens=False,  # Keep thinking tags
        )
        for n in prompt_lengths
    ]

    # Generate (batch mode)
    outputs = llm.generate(formatted_prompts, sampling_params)

    # Process all outputs
    results = []
    for output in outputs:
        reasoning_trace = output.outputs[0].text
        has_thinking_tags = "<|im_start|>think" in reasoning_trace or "<think>" in reasoning_trace

        results.append({
            "reasoning_trace": reasoning_trace,
            "metadata": {
                "model": "Qwen/Qwen3.8-27B",
                "max_tokens": max_tokens,
                "enable_thinking": enable_thinking,
                "prompt_length": len(output.prompt_token_ids),
                "generated_tokens": len(output.outputs[0].token_ids),
                "has_thinking_tags": has_thinking_tags,
                "inference_engine": "vllm",
            }
        })

    return results


if __name__ == "__main__":
    # Test call
    result = call_qwen("Explain quantum computing in simple terms.")
    print(result["reasoning_trace"])