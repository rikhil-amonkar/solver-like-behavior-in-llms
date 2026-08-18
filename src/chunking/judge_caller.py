"""Call Gemini judge model to chunk reasoning traces."""

from pathlib import Path
from .vertex_batch_judge import call_vertex_judge


def call_judge(
    reasoning_text: str,
    judge_prompt_path: str,
    use_vertex: bool = True,
    model_id: str = None,
    max_output_tokens: int = None
) -> dict:
    """
    Call judge model to classify and chunk reasoning trace.

    Args:
        reasoning_text: The reasoning trace before code block
        judge_prompt_path: Path to judge prompt file to use
        use_vertex: Whether to use Vertex AI (default True) vs direct API
        model_id: Gemini model ID (defaults to gemini-2.5-pro from .env)
        max_output_tokens: Max tokens for response (defaults to MAX_JUDGE_TOKENS from .env)

    Returns:
        Dict with: raw_response, metadata
    """
    # Load judge prompt
    judge_prompt = Path(judge_prompt_path).read_text(encoding="utf-8")

    if use_vertex:
        # Use Vertex AI (recommended for production)
        # Defaults to gemini-2.5-pro with MAX_JUDGE_TOKENS from .env
        result = call_vertex_judge(
            reasoning_text=reasoning_text,
            judge_prompt=judge_prompt,
            model_id=model_id,
            max_output_tokens=max_output_tokens
        )
        response_text = result["response_text"]
        metadata = result["metadata"]
    else:
        # TODO: Implement direct Gemini API call (non-Vertex)
        # Would use google.generativeai or REST API
        raise NotImplementedError("Direct Gemini API (non-Vertex) not yet implemented")

    # Parse response (done in chunk_parser.py)
    # For now, return raw response
    return {
        "raw_response": response_text,
        "metadata": metadata
    }
