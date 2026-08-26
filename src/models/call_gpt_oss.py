from vllm import LLM, SamplingParams
from dotenv import load_dotenv
import os

load_dotenv()

# Global vLLM model cache (lazy loaded)
_gpt_llm = None


def _load_gpt_model():
    """Lazy load GPT-OSS model with vLLM (heavy operation)."""
    global _gpt_llm

    if _gpt_llm is None:
        model_id = "openai/gpt-oss-120b"
        print(f"Loading GPT-OSS model with vLLM: {model_id}...", flush=True)

        # Get HF token from environment
        hf_token = os.getenv("HF_TOKEN")

        _gpt_llm = LLM(
            model=model_id,
            tokenizer=model_id,
            trust_remote_code=True,
            download_dir=None,  # Uses HF cache
            tokenizer_mode="auto",
            tensor_parallel_size=1,  # Adjust based on GPU count
            gpu_memory_utilization=0.9,
            max_model_len=32768,  # GPT-OSS max context
            max_num_seqs=256,  # Reduce for memory constraints
            enforce_eager=False,  # Use CUDA graphs for speed
        )
        print("GPT-OSS model loaded with vLLM.", flush=True)

    return _gpt_llm


def call_gpt_oss(prompt: str, max_tokens: int = None, reasoning_effort: str = "medium") -> dict:
    """
    Call GPT-OSS-120B with vLLM (optimized inference).

    Args:
        prompt: The user prompt text
        max_tokens: Max new tokens to generate (defaults to MAX_OPENAI_TOKENS from .env)
        reasoning_effort: Reasoning effort level ("low", "medium", "high")

    Returns:
        dict with keys: reasoning_trace, metadata (tokens, model, etc.)
    """
    if max_tokens is None:
        max_tokens = int(os.getenv("MAX_OPENAI_TOKENS", 32768))

    llm = _load_gpt_model()

    messages = [{"role": "user", "content": prompt}]

    # Format prompt with chat template
    tokenizer = llm.get_tokenizer()
    formatted_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    # Sampling parameters (reasoning_effort controls temperature/top_p)
    effort_params = {
        "low": {"temperature": 0.5, "top_p": 0.8},
        "medium": {"temperature": 0.7, "top_p": 0.9},
        "high": {"temperature": 0.9, "top_p": 0.95},
    }
    params = effort_params.get(reasoning_effort, effort_params["medium"])

    sampling_params = SamplingParams(
        max_tokens=max_tokens,
        temperature=params["temperature"],
        top_p=params["top_p"],
        skip_special_tokens=False,  # Keep reasoning tags
    )

    # Generate
    outputs = llm.generate([formatted_prompt], sampling_params)
    output = outputs[0]

    # Extract generated text (with special tokens)
    reasoning_trace = output.outputs[0].text

    # Check for reasoning markers
    has_reasoning_tokens = any(
        marker in reasoning_trace
        for marker in ["<think>", "<reasoning>", "<thought>", "|im_start|"]
    )

    return {
        "reasoning_trace": reasoning_trace,
        "metadata": {
            "model": "openai/gpt-oss-120b",
            "max_tokens": max_tokens,
            "reasoning_effort": reasoning_effort,
            "prompt_length": len(output.prompt_token_ids),
            "generated_tokens": len(output.outputs[0].token_ids),
            "has_reasoning_tokens": has_reasoning_tokens,
            "inference_engine": "vllm",
        }
    }


if __name__ == "__main__":
    # Test call
    result = call_gpt_oss("Explain quantum computing in simple terms.")
    print(result["reasoning_trace"])